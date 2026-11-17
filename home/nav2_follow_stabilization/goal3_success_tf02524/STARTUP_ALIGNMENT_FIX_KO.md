# START 이후 스캔·EKF 정렬 대기

확인한 실패 기록: evaluation3_ekf_wait/candidate/follower_diagnostics/logs/local_avoidance_trial_1794910100313712862.jsonl.
19:08:59에 종료됐으며 FILTERED_ODOM_SCAN_BRACKET_MISSING, arm_requested=false,
post_stop_faults=[]였다. 이후 19:12:39에 저장한 시작 단계 수정 전 실행 기록이다.

기존 실행기는 주행 중 정렬 지연을 대기 처리했지만 START 이후, 선두 출발 확인 중,
arm 직전의 scene 조회에는 같은 처리가 없었다. 세 구간에 prearm_scene 대기를 적용했다.

정렬 이력의 WAITING_FOR_NEWER_POSE 또는 POSE_HISTORY_GAP에 대해 선두 속도0,
후발 비무장으로 기다린다. 새 입력 3개 이상과 1초 안정 구간 및 양쪽 측정 정지를
확인해야 시작 절차를 계속한다. 선두 출발 확인의 4초 제한에는 이 대기 시간을 산입하지 않는다.
실제 모터 오류, 그래프 변경, 잘못된 시각, IMU 오류는 이 대기로 숨기지 않는다.
계획 후 자세 변화 3cm/0.05rad 검사도 유지한다.

정지5cm·계획여유10cm·주행 중 오돔/추종 수학·드라이버 0.3초 감시는 변경하지 않았다.
원본 evaluation3_reference_wait 파일도 수정하지 않았다.

시작 지연 6개 검사와 기존 참조·EKF·모터 상태 대기/복구 16개 검사는
fake ROS/가상 시계로 통과했다. 실제 로봇 주행은 별도 확인이 필요하다.
정상 결과에는 startup_alignment_wait_episodes와 startup_alignment_wait_total_s가 포함된다.

이미 켜진 드라이버·센서·AMCL·중계기는 유지한다. 양쪽 정지·후발 비무장 상태에서:

```bash
bash ~/nav2_follow_stabilization/goal3_success_tf02524/capture_reference.bash
bash ~/nav2_follow_stabilization/goal3_success_tf02524/start_evaluation3_ekf_wait.bash
```
