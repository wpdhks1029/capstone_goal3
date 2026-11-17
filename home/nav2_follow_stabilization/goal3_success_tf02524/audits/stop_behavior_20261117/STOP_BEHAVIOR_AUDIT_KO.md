# 성공 백업과 현재 평가3 실행 동작 비교

대상: 성공 커밋 7df1f0f의 evaluation3_reference_wait와 현재 start_evaluation3_ekf_wait.bash.
활성 인수: continuous20, dynamic-box, map-rejoin, pose-source=filtered,
post-rejoin-follow-m=2, seconds=0, reference-wait, isolated-io.
이번 작업은 조회·오프라인 비교만 수행했다. 로봇 실행·arm·주행·제어 조건 변경은 하지 않았다.

## 검증 범위와 한계

- 성공 프로필 원본 605개 파일은 백업과 일치한다. 실행 파일 무결성 검사도 통과했다.
- 제어 코어·정지 재관측·지도 유도·추종·참조 대기 등 핵심 모듈 9개의 바이트 일치를 확인했다.
- 두 프로필의 실제 순수 함수에 같은 입력을 넣은 16개 시나리오(각 프로필 16회)의 결과가 모두 일치했다.
- 시나리오: raw/EKF/IMU/scan 지연, 선두 후진·회전, 오돔 변화, 작업영역 초과,
  예측 궤적 여유 부족, 발자국 여유 재관측과 2초 제한, 지도 점프와 경로 이력 교체.
- 운영 실행기의 예외 처리·분기·타이머는 코드 경로를 추적했다.
  AST로 추출한 raise 지점은 백업 61개, 현재 69개다. 이는 종료 사유 수가 아니며
  준비·조회 모드 등 비활성 분기도 포함한다.
- 실제 ROS 스케줄링·DDS·센서 발행·로봇 움직임을 모두 재현한 비교는 아니다.
  단위 입력 재생 결과를 실물 완주 검증으로 해석하지 않는다.

## 원본에서 현재로 바뀐 동작

| 상황 | 성공 백업 | 현재 실행본 | 남은 제약 |
|---|---|---|---|
| 선두/후발 지도 위치·경로 참조가 늦음 | 속도0 대기, 안정 복구 시 재개 | 같은 동작 | 대기 중 로컬 센서 검사는 계속 수행 |
| 스캔과 EKF 보간이 늦음 | 주행 중 일부 정렬 실패는 대기 | 주행 중 대기 + START/선두 출발/arm 직전 대기 추가 | 지도 위치↔EKF 보간은 별도 0.2초 제한 |
| EKF가 과거 값으로 남음 | 0.8초 기준 예외 종료 | 0.6초부터 속도0 대기, 새 EKF 정렬·정지 안정 확인 후 재개 | raw/IMU/scan도 늦으면 종료. EKF 누락·미래 시각 등은 별도 종료 |
| 모터 상태 수신이 늦음 | 수신 나이 0.3초 초과 시 종료 | 속도0 대기 후 같은 epoch·정지·새 상태 확인 시 재개 | raw/IMU/scan도 늦으면 종료. 실제 driver fault는 복구하지 않음 |
| DDS 상태/오뎀 발행이 막힘 | 드라이버 통신 주기를 막을 수 있음 | 드라이버 텔레메트리·실행기 표시 상태를 자식 프로세스로 분리 | 실제 제어 명령 발행·그래프 조회·로그 기록은 여전히 제어 스레드에 있음 |
| 경로 계산 중 인터프리터 부하 | ThreadPool | 같은 planner를 spawn ProcessPool에서 실행 | 경로 탐색·결과 검증의 실패/시간 제한은 동일 |
| 콜백 처리 | 노드 등록/해제 및 서로 다른 timeout의 spin 반복 | 한 executor에 한 번 등록하고 같은 timeout으로 처리 | 외부 센서/TF 지연과 실제 드라이버 오류는 해결 범위 밖 |

## 우선 확인해야 하는 종료 경로

| 우선 항목 | 실제 조건과 경로 | 동작 | 성공 백업 대비 |
|---|---|---|---|
| 로컬 입력 지연 | raw/IMU/scan 원본 시각 또는 수신 나이가 0.8초 초과 | RAW_STALE / IMU_STALE / SCAN_STALE로 세션 종료 | 동일. 추가 EKF/모터 상태 대기 안에서도 fresh_zero_sources가 검사 |
| 지도↔EKF 정렬 | 회피 후 지도 유도 단계에서 지도 위치 시각에 맞는 EKF 보간이 안 되고 0.2초 경과 | MAP_FILTERED_POSE_ALIGNMENT_TIMEOUT 종료 | 동일. 스캔↔EKF 무기한 대기와 다른 분기 |
| 예측 궤적 여유 부족 | 차체·불확실성·약 1초 예측 궤적 여유가 5cm 이하 | STOP_SWEPT_CLEARANCE 즉시 종료 | 동일. 재관측은 FOOTPRINT 사유로 이미 시작된 경우에만 예외적으로 적용 |
| 정지 후 장애물 재관측 | FOOTPRINT 여유 5cm 이하로 대기 진입, 2초 내 복구 못함 또는 세 번째 진입 | STOP_NEAR_RETURN_WAIT_TIMEOUT / STOP_NEAR_RETURN_REPEAT_LIMIT 종료 | 동일. 5cm를 다시 넘는 것만으로 복구하지 않음: 여유 10cm 이상, 예측 여유 10cm 초과, 새 스캔 5개와 측정 정지 필요 |
| 선두 후진·제자리 회전 | 선두 v < -0.01 또는 정지에 가까운 v에서 abs(w)>0.05 | 후진은 먼저 실행되는 local scene에서 LEADER_UNEXPECTED_MOTION 종료. 저속 제자리 회전은 gate의 STOP_LEADER_ROTATING을 Abort로 승격 | 동일. abs(w)>0.1 또는 v>0.1도 local scene에서 먼저 종료. STOP_LEADER_REVERSE는 gate 단독 호출의 사유지만 정상 운영 순서에서는 local scene 검사가 먼저임 |
| 대기 뒤 오돔 변화 | 마지막 core.command에서 기록한 자세와 위치 차이 >10cm 또는 각도 차이 >0.12rad(약 6.9도) | STOP_FILTERED_ODOM_JUMP 종료 | 동일. 이 검사는 측정 dt를 반영하지 않고 제어 호출 사이 자세를 비교 |
| 지도 위치 변화 | 수신된 후발 지도 위치가 이전 관측 대비 20cm 초과 이동 | PATH_FOLLOWER_MAP_JUMP 종료 | 동일. 수신 간격을 반영하지 않는 검사. 별도로 dt를 반영하는 MAP_REJOIN_LOCALIZATION_JUMP 검사도 존재 |
| 드라이버 명령 단절 | 유효 명령이 0.3초 안에 갱신되지 않거나 명령 시각이 오래됨 | 드라이버 COMMAND_TIMEOUT latch, 속도0·비무장 | 동일. 운영 실행기의 무기한 대기와 독립된 감시 |

## 그 외 세션 종료 가능 항목

| 항목 | 활성 동작 |
|---|---|
| 작업영역 | 회피 중 기준선 좌표 x>4.5m 또는 abs(y)>1.25m이면 STOP_APF_WORKSPACE_BOUND. 추종 전환 뒤 x 한도는 handoff 시 연장 가능 |
| 경로 이력 | append-only 이력이 줄거나 앞부분이 교체되면 PATH_SESSION_CHANGED_RESTART. 인접 구간 각도 변화 >120도, 경로 끝 방향과 선두 방향 차이 >90도, 진행 위치 불연속도 종료 가능 |
| 추종 목표 | 목표가 뒤쪽이면 STOP_TARGET_BEHIND, 추종 목표 방향 오차 >45도면 STOP_ALIGN_REQUIRED 등으로 종료 |
| 선두와 거리 | 1m 이하면 STOP_NEAR_LEADER로 종료. 1~1.5m는 STOP_FOLLOW_DISTANCE를 허용된 0속도 대기로 처리. 선두 정지는 STOP_LEADER_STOPPED를 허용된 대기로 처리 |
| 회피 곡률·바퀴 | 목표가 뒤쪽, 곡률 abs(k)>8, 양자화 후 전진 불가능 또는 10RPM 초과 등은 종료. 낮은 램프가 0RPM으로 반올림되는 CONTINUOUS_RAMP_WARMUP은 0속도 후 계속 진행 |
| 탐색 제한 | search 자체 60초, PLAN_BRAKE/PLANNING 단계 65초 제한. 유효 경로 없음·상자 형상 확인 실패·계산된 경로가 현재 스캔과 불일치하면 종료 |
| 복귀 후 추종 확인 | 목표가 2m인 현재 프로필은 활성 확인 구간 130초 이내 검증하지 못하면 POST_REJOIN_FOLLOW_NOT_CONFIRMED. 입력 대기의 일부 시간은 타이머에서 보정 |
| 시작·arm | 준비 입력/그래프, 계획 후 자세 변화 3cm 또는 0.05rad 초과, 선두 출발 확인 4초, 서비스 응답 1초 등의 검사 남음. 현재 START 정렬 대기 시간은 출발 확인 4초에서 제외 |
| arm 뒤 새 측정 | arm 뒤 시각의 측정이 준비되지 않으면 0속도로 잠시 기다리지만 arm 후 0.8초 초과 시 POST_ARM_MEASUREMENTS_NOT_READY 종료 가능 |
| 데이터 값·시각 | 누락/잘못된 프레임/미래 또는 역행 시각, 중복 측정으로 core input이 무효화되는 경우에는 STALE이 아니라 MISSING/INVALID로 종료 가능 |
| 스캔 보간의 추가 조건 | 원본 시각 나이가 0.8초 이내라도 보간 양끝 EKF 간격은 0.2초 이하가 필요하고, 최신 EKF 뒤로는 최대 0.05초만 hold 허용. 나이 검사 통과와 보간 성공은 별개 |
| 방향 일치 | EKF와 IMU 상대방향 차이가 8도 + 시각 차이에 따른 보정 한도를 넘으면 FILTERED_IMU_HEADING_DIVERGENCE 종료 |
| 소유권·세션 | GRAPH_CHANGED, SESSION_CHANGED, UNEXPECTED_DISARM, driver profile mismatch, 실제 모터 오류는 종료 |
| 드라이버 실제 오류 | RESPONSE_TIMEOUT / FEEDBACK_STALE(0.3초), DEVICE_STATUS_NONZERO, serial 오류, 위치 피드백 오류, 잘못된 명령 envelope 등은 종료/비무장 |
| 새로 추가된 프로세스 | 드라이버 텔레메트리 자식 실패는 TELEMETRY_PROCESS_FAILED. planner 자식 실패는 예외 경로. 분리는 지연 원인을 줄이는 조치이며 모든 장애를 대기로 바꾸지는 않음 |

## 왜 WAIT 뒤에 종료될 수 있는가

현재 우선순위: 경로 관측 오류 → 그래프 → 모터 상태 → 세션 → 모터 상태 복구 → EKF 대기 →
선두/지도/경로 참조 대기 → local scene → 스캔 보간 → 단계·지도 유도 → 제어 코어 →
재관측 → STOP_ 사유 승격 → 전송 직전 시각 검사 → 명령 발행.

모터 상태 대기와 EKF 대기는 fresh_zero_sources(raw, imu, scan)를 요구한다.
따라서 모터 상태 대기를 시작한 뒤 IMU 수신 나이가 0.8초를 넘으면
pause_motor_status 내부에서 IMU_STALE가 발생해 바깥 예외 처리로 세션이 끝난다.
이것이 최근 사용자 기록의 실제 종료 경로다. 무기한 대기는 모든 오류를 흡수하는
최상위 상태가 아니라 일부 조건에 붙은 대기 분기다.

reference_wait와 EKF/모터 상태 wait가 중첩되면 대기가 정상 복구되어도
core.last_pose와 지도 tracker의 이전 관측은 유지된다. 복구 뒤 오래된 자세와 현재
자세의 차이를 점프로 판정할 수 있는 조건이 남아 있다. 실제 움직임/위치추정 점프를
구분하지 않고 해당 검사를 지우면 안 되며, 같은 측정 시각 기준 재검증이 별도로 필요하다.

## 현재 결론

“시간 제한 없음/대기·재개”가 모든 지연을 처리한다고 설명할 수 없다.
성공 당시 실행되지 않았던 분기가 현재 조건에서 실행되면 같은 원본 코드도 종료한다.
우선 수정 검토 대상은 ① 로컬 입력 지연의 세션 유지 정책, ② 지도↔EKF 정렬 0.2초 제한,
③ 장애물 재관측 2초/횟수 제한, ④ 복구 후 측정 간격을 무시하는 점프 판정이다.
선두 후진/회전·작업영역·경로 이력 제한도 현재 평가 시나리오와 맞는지 확인해야 한다.
이번 감사에서는 이 조건을 변경하거나 보호 기능을 해제하지 않았다.

파일:
- compare_behavior.py: 순수 함수 실행 비교
- behavior_comparison.json: 16개 비교 결과
- operator_abort_inventory.json: 운영 실행기 분기/raise 위치
