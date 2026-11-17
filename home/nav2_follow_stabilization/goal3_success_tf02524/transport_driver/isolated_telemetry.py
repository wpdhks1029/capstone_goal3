"""ROS publication in spawn-only child processes; never owns a motor interface.

Hardware callbacks only serialize small messages and offer to bounded mmap slots.
Every parent slot lock is nonblocking. The child releases it BEFORE DDS publish.
One child per topic prevents a blocked status publisher from stopping raw odom.
"""
import fcntl
import mmap
import multiprocessing
import os
from pathlib import Path
import shutil
import struct
import tempfile
import time

CAPACITY=131072
HEADER=64
TOPICS={'/follower/odom_raw':('nav_msgs/msg/Odometry','raw'),
        '/follower/odom_position_candidate':('nav_msgs/msg/Odometry','position'),
        '/follower/motor_candidate/status':('std_msgs/msg/String','status')}

class LatestSlot:
    def __init__(self,path,create=False,capacity=CAPACITY):
        self.path=str(path);self.capacity=capacity
        flags=os.O_RDWR|(os.O_CREAT|os.O_EXCL if create else 0)
        self.fd=os.open(self.path,flags,0o600)
        if create:os.ftruncate(self.fd,HEADER+capacity)
        self.memory=mmap.mmap(self.fd,HEADER+capacity)
        if create:self.memory[:]=bytes(HEADER+capacity)
        self.dropped=0
    def _lock(self):
        try:fcntl.flock(self.fd,fcntl.LOCK_EX|fcntl.LOCK_NB);return True
        except BlockingIOError:return False
    def _unlock(self):fcntl.flock(self.fd,fcntl.LOCK_UN)
    def offer(self,payload):
        if not isinstance(payload,bytes) or len(payload)>self.capacity:raise ValueError('TELEMETRY_PAYLOAD_INVALID')
        if not self._lock():self.dropped+=1;return False
        try:
            self.memory[HEADER:HEADER+len(payload)]=payload
            struct.pack_into('<I',self.memory,8,len(payload))
            struct.pack_into('<d',self.memory,16,time.monotonic())
            struct.pack_into('<Q',self.memory,0,struct.unpack_from('<Q',self.memory,0)[0]+1)
            return True
        finally:self._unlock()
    def snapshot(self,last_sequence):
        if not self._lock():return None
        try:
            seq=struct.unpack_from('<Q',self.memory,0)[0]
            if seq==last_sequence:return None
            size=struct.unpack_from('<I',self.memory,8)[0]
            if size>self.capacity:raise ValueError('TELEMETRY_SLOT_CORRUPT')
            return seq,bytes(self.memory[HEADER:HEADER+size]),struct.unpack_from('<d',self.memory,16)[0]
        finally:self._unlock()
    def metadata(self):
        if not self._lock():return None
        try:
            return dict(sequence=struct.unpack_from('<Q',self.memory,0)[0],ready=bool(self.memory[24]),
                        stop=bool(self.memory[25]),failed=bool(self.memory[26]),
                        published=struct.unpack_from('<Q',self.memory,32)[0],
                        publish_started_mono=struct.unpack_from('<d',self.memory,40)[0],
                        last_publish_s=struct.unpack_from('<d',self.memory,48)[0],dropped=self.dropped)
        finally:self._unlock()
    def mark(self,**values):
        # Child may wait for a short copy; hardware parent never waits here.
        fcntl.flock(self.fd,fcntl.LOCK_EX)
        try:
            for key,value in values.items():
                if key in ('ready','stop','failed'):self.memory[{'ready':24,'stop':25,'failed':26}[key]]=int(bool(value))
                elif key=='published':struct.pack_into('<Q',self.memory,32,value)
                elif key in ('publish_started_mono','last_publish_s'):struct.pack_into('<d',self.memory,{'publish_started_mono':40,'last_publish_s':48}[key],value)
                else:raise ValueError('Invalid telemetry metadata')
        finally:self._unlock()
    def request_stop(self):
        if not self._lock():return False
        try:self.memory[25]=1;return True
        finally:self._unlock()
    def close(self):self.memory.close();os.close(self.fd)

def _ros_publisher_process(path,parent_pid,topic,type_name,depth,node_name):
    slot=LatestSlot(path);node=None;ros=None
    try:
        import rclpy
        from rclpy.serialization import deserialize_message
        from rosidl_runtime_py.utilities import get_message
        ros=rclpy;ros.init(args=[])
        node=ros.create_node(node_name,enable_rosout=False)
        msg_type=get_message(type_name);pub=node.create_publisher(msg_type,topic,depth)
        slot.mark(ready=True);last=0;count=0
        while os.getppid()==parent_pid:
            meta=slot.metadata()
            if meta is not None and meta['stop']:break
            packet=slot.snapshot(last)
            if packet is None:time.sleep(.003);continue
            last,payload,offered=packet
            # Never relabel or drain a stale publication backlog.
            if time.monotonic()-offered>.3:continue
            message=deserialize_message(payload,msg_type)
            started=time.monotonic();slot.mark(publish_started_mono=started)
            pub.publish(message)  # No shared slot lock held during DDS.
            count+=1;slot.mark(published=count,last_publish_s=time.monotonic()-started,publish_started_mono=0.)
    except KeyboardInterrupt:
        pass  # Foreground Ctrl+C is operator shutdown, not a DDS failure.
    except BaseException as exc:
        slot.mark(failed=True)
        print('TELEMETRY_PROCESS_FAILED '+topic+': '+repr(exc),flush=True)
    finally:
        if node is not None:node.destroy_node()
        if ros is not None and ros.ok():ros.shutdown()
        slot.close()

class PublisherProcess:
    def __init__(self,path,topic,type_name,depth,node_name,*,target=_ros_publisher_process,startup_timeout=12.):
        self.slot=LatestSlot(path,create=True);self.closed=False;self.last_meta={}
        self.process=multiprocessing.get_context('spawn').Process(target=target,args=(str(path),os.getpid(),topic,type_name,depth,node_name),daemon=True)
        try:
            self.process.start()
            end=time.monotonic()+startup_timeout
            while time.monotonic()<end:
                meta=self.slot.metadata()
                if meta and meta['failed']:raise RuntimeError('TELEMETRY_CHILD_START_FAILED')
                if not self.process.is_alive():raise RuntimeError('TELEMETRY_CHILD_EXITED')
                if meta and meta['ready']:return
                time.sleep(.01)
            raise RuntimeError('TELEMETRY_CHILD_START_TIMEOUT')
        except BaseException:self.close();raise
    def offer(self,payload):return self.slot.offer(payload)
    def stats(self):
        meta=self.slot.metadata()
        if meta is not None:self.last_meta=meta
        return dict(self.last_meta,pid=self.process.pid,alive=self.process.is_alive())
    def failed(self):
        meta=self.stats();return meta.get('failed',False) or not meta['alive']
    def close(self):
        if self.closed:return
        self.closed=True
        # Called only after hardware shutdown. This can never delay zero RPM.
        if self.process.is_alive():
            if self.slot.request_stop():self.process.join(timeout=.3)
            if self.process.is_alive():self.process.terminate();self.process.join(timeout=.5)
            if self.process.is_alive():self.process.kill();self.process.join(timeout=.5)
        self.slot.close()

class _Publisher:
    def __init__(self,worker,serialize):self.worker=worker;self.serialize=serialize
    def publish(self,message):self.worker.offer(bytes(self.serialize(message)))

class IsolatedTelemetry:
    def __init__(self,node,*,serialize=None,target=_ros_publisher_process):
        if serialize is None:
            from rclpy.serialization import serialize_message
            serialize=serialize_message
        self.node=node;self.serialize=serialize;self.target=target;self.workers={}
        self.directory=Path(tempfile.mkdtemp(prefix='convoy-telemetry-'))
    def resolve_topic_name(self,topic):return self.node.resolve_topic_name(topic)
    def get_publishers_info_by_topic(self,topic):return self.node.get_publishers_info_by_topic(topic)
    def create_publisher(self,msg_type,topic,depth):
        if topic not in TOPICS or topic in self.workers:raise ValueError('TELEMETRY_TOPIC_NOT_ALLOWED_OR_DUPLICATE')
        type_name,suffix=TOPICS[topic]
        # Warm serialization/type support before any hardware control ticks.
        self.serialize(msg_type())
        worker=PublisherProcess(self.directory/(suffix+'.slot'),topic,type_name,depth,'follower_drive_telemetry_'+suffix,target=self.target)
        self.workers[topic]=worker
        return _Publisher(worker,self.serialize)
    def failed(self):return any(w.failed() for w in self.workers.values())
    def stats(self):return {topic:w.stats() for topic,w in self.workers.items()}
    def close(self):
        for worker in self.workers.values():worker.close()
        shutil.rmtree(self.directory)
