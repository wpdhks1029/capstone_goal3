# 정량목표3 — 2026-11-17 성공 백업 갱신

후발 장애물 회피 → 지도/선두 경로 재합류 → 추종 재개 구성.
사용자가 현재 콜백 수정본의 실물 성공을 확인한 버전이다.

- **현재 실행 명령:** [RUNBOOK_KO.md](RUNBOOK_KO.md)
- **성공 기록:** [SUCCESS_RECORD.json](evidence/20261117_success/SUCCESS_RECORD.json)
- **실제 마지막 결과 원문:** [trial_end_original.json](evidence/20261117_success/trial_end_original.json)
- **원본 11월 13일 실행표:** [RUNBOOK_20261113_KO.md](RUNBOOK_20261113_KO.md)
- **소스·모드·바이너리 무결성:** `python3 -B verify_snapshot.py`

현재 후발 루트는 `home/nav2_follow_stabilization/goal3_success_tf02524`다.
원본 evaluation3_reference_wait와 11월 13일 소스는 삭제하지 않았다. 이전 커밋 7df1f0f도 보존한다.
선두는 11월 13일 실제 수집 파일을 유지했으며 이번에 재수집하지 않았다.
현재 실행에는 TF0.25.24 코어·발행/계산 분리·입력 대기·콜백 수신 수정이 포함된다.

관측 성공과 정식 평가 합격은 구분한다. 마지막 결과 OPERATOR_STOP,
trial_success=false, evaluation_pass=false를 임의로 성공으로 변경하지 않았다.
전체 시간 제한은 없지만 남은 센서/모터/기하 검사에 따라 종료될 수 있다.

home/와 leader_home/는 각 호스트 HOME 기준이다. 전체 인증정보·SSH 키·개인 홈·캐시를 저장하지 않는다.
대용량 원시 주행 로그는 로컬 백업에 보존하고 GitHub에는 원문 마지막 결과와 주요 이벤트를 보존했다.
실행에 필요한 TF ARM64 라이브러리는 예외적으로 소스와 함께 저장했다.
ROS 설치·빌드 환경·권한·실제 초기 위치 지정은 대상 장치에서 별도로 필요하다.
복원/실행/arm을 자동 수행하는 설치 절차는 없다.
