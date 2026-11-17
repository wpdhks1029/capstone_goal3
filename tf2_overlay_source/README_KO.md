# AMCL TF 정지: 2026-11-17 근거와 격리 수정

## 관측

live_20261117_164803.txt에서 모터 fault=null, feedback_fresh=true이며
raw 137개, filtered 278개, scan 150개, odom->base TF 278개를 수신했다.
AMCL은 active지만 map->follower/odom 및 /follower/odom_map은 없었다.
AMCL의 TF 구독 Best Effort 변경도 적용돼 있었으므로 해당 변경은 해결책이 아니었다.
AMCL 로그는 initialpose가 도착해도 내부 odom TF 최신 시간이
1794901472.327874에 고정돼 있었다. 외부 관측자의 TF는 계속 갱신됐다.

## 설치본에서 재현한 결함

설치 tf2 / tf2_ros 버전: 0.25.23.
공식 수정: https://github.com/ros2/geometry2/pull/990
수정 버전: 0.25.24.
공식 재현 시험 wait_for_transform_does_not_deadlock_with_set_transform을
ROS 노드/하드웨어 없이 실행했다.

- 시스템 0.25.23: 5초 대기 뒤 교착 검출, exit 1.
- 별도 0.25.24 코어: 약 51ms에 통과, exit 0.
- 노드를 만드는 timer_ros 시험은 제외하고 공식 Buffer 시험 10개를 20회 반복:
  200개 통과. upstream_regression.log 참고.
- 설치본의 공개 함수 심볼 누락 0개. buffer_core.hpp는 공백 외 동일하다.

이는 설치 라이브러리에 결함이 있음을 직접 확인한 것이다.
현재 AMCL 정지의 직접 원인이라는 최종 판단은 실물 실행 결과로 확인해야 한다.
실행 중인 AMCL의 스레드 역추적까지 확보한 것은 아니다.

## 적용 범위

시스템 /opt/ros 패키지 및 원본 성공 백업은 변경하지 않았다.
cache.cpp, buffer_core.cpp, static_cache.cpp, time.cpp는 공식 0.25.24 소스다.
헤더와 나머지 ROS 라이브러리는 설치본을 사용한다.
동일 SONAME libtf2.so를 별도 빌드해 AMCL 프로세스의 LD_LIBRARY_PATH에만 넣는다.
다른 모터/센서/EKF/Bridge 프로세스에는 이 경로를 추가하지 않는다.
AMCL 파라미터 및 TF 구독 QoS는 원본 성공 설정을 사용한다.
새 실행 래퍼는 검증된 소스/바이너리 해시를 확인한 후 실행한다.

추가 시작 검사 수정: 원본 센서 실행기의 position_profile_contract.preflight는
3초 수집 후 마지막 위치 데이터 나이가 0.3초를 초과하면 전체 launch를 종료했다.
사용자의 Candidate measurement missing/stale/future 오류는 이 경로에서 발생한다.
별도 센서 실행본은 depth=1 Best Effort로 최신 입력을 관측하고, 원본 시각 및
수신 시각이 모두 0.3초 이내인 새 위치 입력까지 정지 상태로 무기한 대기한다.
발행자 중복, 기존 EKF 실행, 잘못된 프레임은 여전히 오류로 거부한다.
센서/장착 TF/EKF 프로세스 설정과 원본 실행 파일은 변경하지 않았다.
시작 검사 및 실행 범위 회귀 시험 7개 통과; 실제 센서 실행은 사용자 검증이 필요하다.

3cm 정지, 10cm 계획 여유, 상태/참조/EKF/여유 재관측 대기는 변경하지 않았다.
수신 지연에는 0속도로 기다리고 신선한 입력·정지 확인 후 재개하는 정책을 유지한다.
드라이버의 실제 하드웨어/응답 감시도 변경하지 않았다.

## 사용자 실행

평가 주행은 끄고 정지·비무장 상태에서 기존 후발 위치추정 통합 터미널만
Ctrl+C로 종료한 후 아래 실행. 드라이버와 유니캐스트 중계기는 유지한다.

```bash
bash ~/nav2_follow_stabilization/success_tf_recovery/start_localization_tf_fixed.bash
```

재시작이므로 RViz /follower/initialpose에 현재 위치·방향을 한 번 지정하고,
다른 터미널에서 정지 상태 90초 관측:

```bash
bash ~/nav2_follow_stabilization/goal3_comparison_20261117/audit_live.bash 90
```

AMCL /proc/maps의 tf2_libraries가 이 폴더 build/lib/libtf2.so인지,
map->follower/odom 및 odom_map이 지속 갱신되는지 확인해야 한다.
아직 실제 주행 성공으로 판정하지 않았다.

## 빌드 재현

```bash
source /opt/ros/humble/setup.bash
cmake -S "$HOME/nav2_follow_stabilization/goal3_comparison_20261117/tf2_deadlock_fix" \
  -B "$HOME/nav2_follow_stabilization/goal3_comparison_20261117/tf2_deadlock_fix/build" \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build "$HOME/nav2_follow_stabilization/goal3_comparison_20261117/tf2_deadlock_fix/build" -j2
```

재빌드하면 바이너리 해시가 달라질 수 있으므로 검증 manifest는 자동 갱신하지 않는다.
새 바이너리는 시험과 해시 검증을 다시 완료하기 전 실행 래퍼가 거부할 수 있다.
