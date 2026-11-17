# 정량목표3 — 2026-11-17 사용자 확인 성공 실행본

정량목표3: 후발 장애물 회피 → 지도/선두 경로 재합류 → 추종 재개.
후발 최신 실행 루트: ~/nav2_follow_stabilization/goal3_success_tf02524.
선두 파일은 2026-11-13 실제 수집본을 유지했다. 이번 작업에서 선두를 다시 SSH 수집하지 않았다.
정량목표1·2의 실행 변경은 이 업데이트 범위가 아니다.

## 모든 선두·후발 ROS 터미널 환경

```bash
source /opt/ros/humble/setup.bash
source ~/robot_ws/install/setup.bash
export ROS_DOMAIN_ID=10
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export RMW_FASTRTPS_PUBLICATION_MODE=ASYNCHRONOUS
export RMW_FASTRTPS_USE_QOS_FROM_XML=0
```

각 코드는 별도 터미널에서 실행한다. 이미 실행 중인 같은 노드를 중복 실행하지 않는다.

## 정량목표1·3 공통 선두 노드

선두 1: 모터·센서·EKF
```bash
ros2 launch ~/leader_diagnostics/leader_nav_yaw_calibrated.launch.py allow_motion:=true
```

선두 2: 지도·AMCL
```bash
ros2 launch nav2_bringup localization_launch.py \
  map:=/home/sunuk/robot_ws/maps/leader_mapping_20261107_143101_9R24Wc/leader_map.yaml \
  params_file:=/home/sunuk/leader_diagnostics/nav2_015_rotation_shim_check.yaml \
  use_sim_time:=false autostart:=true
```

선두 3: Bridge
```bash
FASTRTPS_DEFAULT_PROFILES_FILE="$HOME/convoy_udp_only_pilot.xml" \
python3 -B ~/leader_diagnostics/leader_bridge_latest_candidate.py \
  --ros-args -p map_frame:=map -p base_frame:=base_link -p publish_rate:=20.0
```

선두 4: 유니캐스트
```bash
FASTRTPS_DEFAULT_PROFILES_FILE="$HOME/convoy_udp_only_pilot.xml" \
python3 -B ~/leader_diagnostics/convoy060_dfa647fff6de/convoy_unicast_relay.py \
  --role leader --peer 10.253.245.192
```

## 후발 — 각각 별도 터미널

이미 실행 중인 중복 노드는 종료하고 실행한다. 선두 Nav2/gate 및 teleop은 평가3와 동시에 실행하지 않는다.

### 1. 모터 드라이버
```bash
bash ~/nav2_follow_stabilization/goal3_success_tf02524/start_driver.bash
```

### 2. 센서·EKF·지도·AMCL·Bridge
```bash
bash ~/nav2_follow_stabilization/goal3_success_tf02524/start_localization.bash
```

### 3. 유니캐스트
```bash
bash ~/nav2_follow_stabilization/goal3_success_tf02524/start_unicast.bash
```

RViz Fixed Frame=map, 선두 초기 위치=/initialpose, 후발 초기 위치=/follower/initialpose.
후발 실제 위치·방향을 지정한다. 초기 위치를 자동으로 복원하지 않는다.

### 4. 기준선 저장 및 주행
양쪽 정지·후발 비무장 상태에서 새 기준선을 저장한다. 보존된 과거 기준선을 바로 재사용하지 않는다.
```bash
bash ~/nav2_follow_stabilization/goal3_success_tf02524/capture_reference.bash
```
REFERENCE_JSON 저장 성공 후:
```bash
bash ~/nav2_follow_stabilization/goal3_success_tf02524/start_evaluation3_ekf_wait.bash
```
준비되면 START + Enter.
이번 버전 결과 식별자: callback_dispatch=PERSISTENT_EXECUTOR_FIXED_TIMEOUT.

## 보존 설정과 변경

계획 여유 10cm, 정지 5cm, 10RPM 제한, 회피 최대 0.025m/s, 세션 전체 시간 제한 없음.
AMCL에만 공식 TF 0.25.24 코어를 적용하고, DDS 텔레메트리/표시 상태/경로 계산을 분리했다.
EKF·모터 상태·시작 정렬 대기와 고정 executor 콜백 처리가 현재 실행본에 적용됐다.
원본 제어 수학·드라이버 0.3초 감시는 유지했다. 모든 오류가 대기로 바뀐 것은 아니다.
남은 종료 경로: home/nav2_follow_stabilization/goal3_success_tf02524/audits/stop_behavior_20261117/STOP_BEHAVIOR_AUDIT_KO.md.

## 성공 근거

사용자가 이번 실물 주행 성공을 확인했다. 기록에 장애물 감지·회피 경로 설치·지도 복귀 후 추종 전환이 있다.
최종 종료는 OPERATOR_STOP, 양쪽 0속도 확인, post_stop_faults=[]이다.
자동 trial_success=false, evaluation_pass=false는 원문 그대로 보존했다.
정량 평가 합격 또는 모든 상황의 동작을 자동 검증했다고 주장하지 않는다.

## 복원

ROS/모터를 종료한 별도 시점에 다운로드 사본에서 python3 -B verify_snapshot.py로 해시를 검사한다.
home/는 후발 $HOME, leader_home/는 선두 $HOME 기준이다. 검토 후 필요한 파일을 복원한다.
노드 시작·arm·패키지 설치·기존 홈 덮어쓰기는 자동 실행하지 않는다.
일부 /home/sunuk 고정 경로·장치/IP·기존 ROS Humble 및 robot_ws 빌드가 필요하다.
TF 라이브러리는 현 ARM64 빌드 산출물과 재빌드 소스를 함께 보존했다.
