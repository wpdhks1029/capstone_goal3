# 정량목표3 성공 백업 + TF 교착 수정 코어

원본: git@github.com:wpdhks1029/capstone_goal3.git
커밋: 7df1f0f69b947196e87db621a353aa3afc99cf16

로컬 성공 스냅샷의 MANIFEST 1,617개 파일을 모두 검증했다.
평가3 프로필 605개 파일은 백업과 바이트 단위로 동일하게 복사했다.
공통 센서/설정/환경 소스도 백업과 동일함을 확인했다.
driver/candidate 제어 소스는 수정하지 않았다.

백업 설정: 계획 여유 10cm / 정지 5cm / 시간 제한 없는 기존 reference-wait.
원본 evaluation3_reference_wait 폴더는 그대로 보존했다.
현재 실행용 evaluation3_ekf_wait에는 EKF·모터 상태·시작 정렬 대기와
표시 상태 발행·경로 계산의 프로세스 분리를 별도로 적용했다.
stop03 및 오돔 검사 수학 변경은 이 복원본에 넣지 않았다.
변경 근거는 OPERATOR_IO_FIX_KO.md와 STARTUP_ALIGNMENT_FIX_KO.md에 기록했다.

AMCL 프로세스의 LD_LIBRARY_PATH에 공식 TF 0.25.24
교착 수정 코어 libtf2.so를 먼저 넣는 것이다. AMCL 파라미터/리매핑/구독 QoS는
원본과 동일하다. 시스템 ROS 패키지는 변경하지 않았다.
라이브러리는 앞서 공식 재현 시험에서 설치 0.25.23은 교착 실패,
수정본은 통과함을 확인했던 동일 바이너리다. 새 복사본의 로더 경로와
공식 교착 재현 시험도 확인했다. 실제 이 복원본 주행 성공은 별도 확인해야 한다.

원본 드라이버로 복원 후에도 status_publish가 1.282031957초 동안 막혀
RESPONSE_TIMEOUT이 발생한 사용자 로그가 확인됐다. 이 발행 경로만
transport_driver의 별도 프로세스 발행으로 분리했다. 원본 driver 폴더는 그대로다.
start_driver.bash는 transport_driver를 실행하며, 원본 실행 래퍼는
start_driver_original.bash로 보존했다.
모터 제어/엔코더/오도메트리/정지거리/0.3초 watchdog 코드는 원본과 동일하다.
이 수정은 DDS write가 하드웨어 tick을 막지 못하게 하는 조치다.
왜 성공 백업 시점에는 증상이 없었는지, 어떤 DDS 내부 조건이 발행을 막았는지는
당시 실행 환경 기록이 부족하여 아직 확정하지 않았다.

원본 및 이전 작업 폴더는 보존했다. RESTORE_MANIFEST.json 및
verify_restore.py로 복원 소스의 무결성을 확인한다.

## 실행

기존 후발 평가/모터/센서 통합/중계기 실행은 종료한다. 선두의 평가3 공통 노드는 유지한다.
선두 Nav2/gate 및 다른 cmd_vel 발행기는 평가3와 동시에 실행하지 않는다.
각각 별도 후발 터미널:

```bash
bash ~/nav2_follow_stabilization/goal3_success_tf02524/start_driver.bash
```

```bash
bash ~/nav2_follow_stabilization/goal3_success_tf02524/start_localization.bash
```

```bash
bash ~/nav2_follow_stabilization/goal3_success_tf02524/start_unicast.bash
```

RViz에서 /follower/initialpose로 실제 후발 위치/방향을 지정한다.
양쪽 정지 및 후발 비무장 상태에서 다른 터미널:

```bash
bash ~/nav2_follow_stabilization/goal3_success_tf02524/capture_reference.bash
```

저장 성공 후:

```bash
bash ~/nav2_follow_stabilization/goal3_success_tf02524/start_evaluation3_ekf_wait.bash
```

START 입력 시 선두/후발 시험을 시작한다. 시작 정렬이 지연되면 선두 속도0·후발 비무장으로
대기하며, 새 입력·정렬·정지를 확인한 뒤 시작 절차를 이어간다.
원본 실행 래퍼 start_evaluation3.bash도 별도로 보존했다.
