"""Read-only independent subscriber: no publishers, services, arm or commands."""
import json
import time
from pathlib import Path
import rclpy
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu, LaserScan
from rclpy.qos import QoSProfile, ReliabilityPolicy


def main():
    rclpy.init()
    node=rclpy.create_node('goal3_sensor_delivery_observer')
    qos=QoSProfile(depth=1,reliability=ReliabilityPolicy.BEST_EFFORT)
    report=Path(__file__).parent/'reports'/('sensor_delivery_'+str(time.time_ns())+'.jsonl')
    report.parent.mkdir(exist_ok=True)
    state={}
    subscriptions=[]
    def receive(topic,msg):
        mono=time.monotonic();ns=node.get_clock().now().nanoseconds
        stamp=msg.header.stamp.sec*10**9+msg.header.stamp.nanosec
        old=state.get(topic)
        state[topic]=dict(count=(old['count']+1 if old else 1),source_ns=stamp,
            received_mono=mono,source_age_at_receive_s=(ns-stamp)/1e9,
            max_receive_gap_s=max(old['max_receive_gap_s'],mono-old['received_mono']) if old else 0.)
    for topic,kind in (('/follower/imu/data',Imu),('/follower/odometry/filtered',Odometry),
                       ('/follower/odom_raw',Odometry),('/follower/scan',LaserScan)):
        state[topic]=None
        subscriptions.append(node.create_subscription(kind,topic,lambda m,t=topic:receive(t,m),qos))
    print('조회 전용 60초: IMU·EKF·원시 오뎀·스캔 독립 수신 기록. 주행·arm 요청 없음.',flush=True)
    print('REPORT='+str(report),flush=True)
    started=time.monotonic();next_report=started
    try:
        with report.open('w') as out:
            while rclpy.ok() and time.monotonic()-started<60.:
                rclpy.spin_once(node,timeout_sec=.02)
                mono=time.monotonic()
                if mono<next_report:continue
                ns=node.get_clock().now().nanoseconds;next_report=mono+.25
                row=dict(ros_ns=ns,inputs={t:dict(received=False) if s is None else
                    dict(count=s['count'],source_ns=s['source_ns'],source_age_s=(ns-s['source_ns'])/1e9,
                         receive_age_s=mono-s['received_mono'],max_receive_gap_s=s['max_receive_gap_s'])
                    for t,s in state.items()})
                out.write(json.dumps(row)+'\n');out.flush()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node();rclpy.shutdown()
    print('REPORT='+str(report),flush=True)


if __name__=='__main__':main()
