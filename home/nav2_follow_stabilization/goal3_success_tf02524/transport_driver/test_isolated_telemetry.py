"""Real child processes and a deliberately GIL-holding 1.7s publisher stall.
No ROS, network or hardware is opened. MotorContract uses MemoryTransport.
"""
import ctypes
import fcntl
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from isolated_telemetry import LatestSlot,PublisherProcess,IsolatedTelemetry
from test_local_avoidance_drive import Tests as Setup

def blocked_publication(path,parent_pid,topic,type_name,depth,node_name):
    slot=LatestSlot(path);slot.mark(ready=True);last=0;count=0;history=[]
    try:
        while os.getppid()==parent_pid:
            meta=slot.metadata()
            if meta is not None and meta['stop']:break
            packet=slot.snapshot(last)
            if packet is None:time.sleep(.002);continue
            last,data,offered=packet
            started=time.monotonic();slot.mark(publish_started_mono=started)
            if data==b'block':
                # PyDLL retains the interpreter GIL, unlike time.sleep.
                libc=ctypes.PyDLL(None);libc.usleep.argtypes=[ctypes.c_uint];libc.usleep.restype=ctypes.c_int
                libc.usleep(1_700_000)
            count+=1;history.append({'sequence':last,'data':data.decode()})
            target=Path(type_name);tmp=target.with_suffix('.tmp');tmp.write_text(json.dumps(history));tmp.replace(target)
            slot.mark(published=count,last_publish_s=time.monotonic()-started,publish_started_mono=0.)
    finally:slot.close()

def startup_failure(path,*args):
    slot=LatestSlot(path);slot.mark(failed=True);slot.close()

def wait_until(predicate,timeout=4.):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if predicate():return
        time.sleep(.005)
    raise AssertionError('Timed out waiting for test worker')

class Tests(unittest.TestCase):
    def test_slot_is_bounded_latest_only_and_parent_never_waits_for_reader_lock(self):
        with tempfile.TemporaryDirectory() as d:
            slot=LatestSlot(Path(d)/'slot',create=True,capacity=32)
            reader=LatestSlot(Path(d)/'slot',capacity=32)
            try:
                slot.offer(b'old');slot.offer(b'new');self.assertEqual(reader.snapshot(0)[1],b'new')
                fcntl.flock(reader.fd,fcntl.LOCK_EX)
                start=time.monotonic();self.assertFalse(slot.offer(b'dropped'));self.assertLess(time.monotonic()-start,.05)
                self.assertEqual(slot.dropped,1)
                fcntl.flock(reader.fd,fcntl.LOCK_UN)
                self.assertEqual(reader.snapshot(0)[1],b'new')
                with self.assertRaises(ValueError):slot.offer(b'x'*33)
            finally:reader.close();slot.close()
    def test_recorded_publish_stall_does_not_block_motor_io_or_replay_backlog(self):
        with tempfile.TemporaryDirectory() as d:
            trace=Path(d)/'trace.json';worker=PublisherProcess(Path(d)/'slot','test',str(trace),10,'test',target=blocked_publication)
            try:
                worker.offer(b'block');wait_until(lambda:worker.stats().get('publish_started_mono',0)>0)
                clock,device,port,contract=Setup().contract(seconds=0);contract.continuous20=True
                start_count=contract.core.valid_count;epoch=contract.core.epoch
                for i in range(100):self.assertTrue(worker.offer(('latest-'+str(i)).encode()))
                start=time.monotonic();previous=start;max_gap=0.;ticks=0
                while time.monotonic()-start<1.9:
                    now=time.monotonic();max_gap=max(max_gap,now-previous);previous=now
                    obj=Setup().envelope(clock,contract,'STOP',0.,0.)
                    self.assertTrue(contract.command(json.dumps(obj),clock.ros));contract.tick(clock.ros);clock.now+=.02;ticks+=1
                    self.assertIsNone(contract.core.fault);self.assertEqual(device.rpm,(0,0))
                    time.sleep(.01)
                wait_until(lambda:worker.stats().get('published',0)>=2)
                trace_rows=json.loads(trace.read_text())
                self.assertEqual([r['data'] for r in trace_rows],['block','latest-99'])
                self.assertLess(max_gap,.3);self.assertGreater(ticks,30)
                self.assertGreater(contract.core.valid_count,start_count+10)
                self.assertTrue(contract.core.armed);self.assertEqual(contract.core.epoch,epoch)
                contract.disarm();contract.tick(clock.ros);self.assertEqual(device.rpm,(0,0))
            finally:worker.close()
    def test_blocked_status_does_not_block_independent_raw_publication(self):
        with tempfile.TemporaryDirectory() as d:
            status=PublisherProcess(Path(d)/'status','status',str(Path(d)/'status.json'),10,'status',target=blocked_publication)
            raw=PublisherProcess(Path(d)/'raw','raw',str(Path(d)/'raw.json'),20,'raw',target=blocked_publication)
            try:
                status.offer(b'block');wait_until(lambda:status.stats().get('publish_started_mono',0)>0)
                raw.offer(b'fresh-raw');wait_until(lambda:raw.stats().get('published',0)>=1,timeout=1.)
                self.assertEqual(status.stats()['published'],0)
                self.assertEqual(json.loads((Path(d)/'raw.json').read_text())[0]['data'],'fresh-raw')
            finally:status.close();raw.close()
    def test_failed_child_prevents_start_instead_of_silent_telemetry_loss(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(RuntimeError):PublisherProcess(Path(d)/'slot','test','test',10,'test',target=startup_failure)
    def test_manager_only_allows_telemetry_topics(self):
        class Node:
            def resolve_topic_name(self,t):return t
            def get_publishers_info_by_topic(self,t):return []
        manager=IsolatedTelemetry(Node(),serialize=lambda msg:b'{}')
        try:
            with self.assertRaises(ValueError):manager.create_publisher(object,'/cmd_vel',10)
            self.assertFalse(manager.workers)
        finally:manager.close()

if __name__=='__main__':unittest.main()

class GuardTests(unittest.TestCase):
    def test_parent_scheduler_stall_still_faults_with_unchanged_response_deadline(self):
        clock,device,port,contract=Setup().contract(seconds=0)
        contract.disarm();contract.tick(clock.ros)
        if contract.core.waiting_since is None:
            for _ in range(20):
                clock.now+=.02;contract.tick(clock.ros)
                if contract.core.waiting_since is not None:break
        self.assertIsNotNone(contract.core.waiting_since)
        self.assertEqual(contract.core.config.response_timeout,.3)
        clock.now+=1.678642849;contract.tick(clock.ros)
        self.assertEqual(contract.core.fault,'RESPONSE_TIMEOUT')
        self.assertFalse(contract.core.armed);self.assertEqual(device.rpm,(0,0))
    def test_actual_driver_tick_stops_on_telemetry_child_failure(self):
        import ast,copy
        from collections import deque
        from types import SimpleNamespace as S
        import follower_drive_node as driver
        root=ast.parse(Path(driver.__file__).read_text())
        tick=copy.deepcopy(next(n for n in ast.walk(root) if isinstance(n,ast.FunctionDef) and n.name=='tick'))
        tick.body=[ast.Global(names=n.names) if isinstance(n,ast.Nonlocal) else n for n in tick.body]
        clock,device,port,contract=Setup().contract(seconds=0);contract.continuous20=True
        log=[]
        node=S(get_clock=lambda:S(now=lambda:S(nanoseconds=clock.ros,to_msg=lambda:None)),get_logger=lambda:S(error=log.append))
        env=dict(time=time,contract=contract,telemetry=S(failed=lambda:True,stats=lambda:{}),node=node,
                 last_status=0.,last_fault=None,last_finished=None,fault_snapshot_seen=None,
                 fault_writer=None,tick_history=deque(maxlen=24),raw_pub=S(publish=lambda m:None),
                 fill_odom=lambda *a:None,Odometry=lambda:None,position=S(publish=lambda *a:False),
                 publish_position_guarded=driver.publish_position_guarded,a=S(run_hardware=False,input_kind='local_avoidance'),
                 String=lambda **kw:S(**kw),status_pub=S(publish=lambda msg:None),json=json)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[tick],type_ignores=[])),driver.__file__,'exec'),env)
        env['tick']()
        self.assertEqual(contract.core.fault,'TELEMETRY_PROCESS_FAILED');self.assertFalse(contract.core.armed)
        self.assertEqual(device.rpm,(0,0));self.assertTrue(log)
