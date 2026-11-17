"""Five-minute read-only observation. Publishes no commands or arm requests."""
import json
import time
from pathlib import Path


def main():
    import rclpy
    from rclpy.qos import QoSProfile, ReliabilityPolicy
    from std_msgs.msg import String
    rclpy.init(args=[])
    node=rclpy.create_node('success_driver_idle_observer',enable_rosout=False)
    start=time.monotonic();last=None;received=0;max_gap=0.;latest={};problem=None

    def receive(message):
        nonlocal last,received,max_gap,latest,problem
        now=time.monotonic()
        try:latest=json.loads(message.data)
        except (ValueError,TypeError):problem='STATUS_JSON_INVALID';return
        if last is not None:max_gap=max(max_gap,now-last)
        last=now;received+=1
        if latest.get('fault'):problem=latest['fault']
        elif latest.get('armed'):problem='IDLE_OBSERVATION_REQUIRES_DISARMED'
        elif latest.get('measured_rpm')!=[0,0]:problem='IDLE_OBSERVATION_REQUIRES_ZERO_RPM'
        elif not latest.get('telemetry_isolated'):problem='ISOLATED_DRIVER_NOT_RUNNING'

    subscription=node.create_subscription(String,'/follower/motor_candidate/status',receive,
        QoSProfile(depth=1,reliability=ReliabilityPolicy.BEST_EFFORT))
    print('조회 전용: 5분 정지·비무장 관측. 주행·arm·설정 변경 없음.',flush=True)
    next_notice=start+60.
    try:
        while time.monotonic()-start<300. and problem is None:
            rclpy.spin_once(node,timeout_sec=.05)
            now=time.monotonic()
            if last is None and now-start>15.:problem='STATUS_NOT_RECEIVED'
            elif last is not None and now-last>5.:problem='STATUS_NOT_RECEIVED_FOR_5S'
            if now>=next_notice:
                print(f'관측 {int(now-start)}초: 수신 {received}, fault={latest.get("fault")}',flush=True)
                next_notice+=60.
    except KeyboardInterrupt:problem='OPERATOR_STOP'
    finally:
        result=dict(reason=problem or 'OBSERVATION_COMPLETE_NO_REPORTED_FAULT',
            seconds=time.monotonic()-start,received=received,maximum_status_receive_gap_s=max_gap,
            fault=latest.get('fault'),armed=latest.get('armed'),feedback_fresh=latest.get('feedback_fresh'),
            feedback_age_s=latest.get('feedback_age_s'),telemetry_isolated=latest.get('telemetry_isolated'),
            valid_feedback=latest.get('valid_feedback'),physical_motion_test=False)
        folder=Path(__file__).resolve().parent/'reports';folder.mkdir(exist_ok=True)
        path=folder/f'driver_idle_{time.time_ns()}.json';path.write_text(json.dumps(result,indent=2))
        print(json.dumps(result,ensure_ascii=False,indent=2),flush=True);print('REPORT='+str(path),flush=True)
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
    return 0 if problem is None else 1


if __name__=='__main__':raise SystemExit(main())
