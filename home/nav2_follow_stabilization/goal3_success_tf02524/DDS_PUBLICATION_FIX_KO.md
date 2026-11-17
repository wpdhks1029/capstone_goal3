# 모터 처리 주기를 막는 DDS 발행 분리

사용자 로그에서 직접 확인한 사실: status_publish_s=1.282031957, 다음 tick_gap_s=1.283651733. 그때 armed=false, RPM0, 장치 상태0, 수신 버퍼20바이트였다. 정상 PID4 처리 뒤 상태 발행 호출이 오래 걸려 응답 감시 기한을 놓친 경로다. 왜 저장 당시에는 없었는지, DDS 내부의 어떤 잠금/버퍼 조건이 원인인지까지 확정한 것은 아니다.

유사 사례(같은 결함/버전/발생 조건이라는 의미는 아님):
- https://github.com/ros2/rmw_fastrtps/issues/754 : 발행 호출 blocking, 비동기 발행 중 History 자원에 따른 blocking 설명.
- https://github.com/ros2/rmw/issues/209 : rmw_publish blocking/자원 제한 사례.
- https://github.com/eProsima/Fast-DDS/issues/1042 : 새 구독자 참가 시 발행 지연의 과거 사례. 이는 오래된 버전 이슈로, 현재 로봇에 동일 결함이 남았다는 근거로 사용하지 않는다.

적용: 원본 driver 폴더는 그대로 보존. 별도 transport_driver의 실행 진입점에서만 오돔/위치/상태를 독립 발행 프로세스로 전달한다. 부모는 고정 크기 최신값 슬롯에 비차단 복사하고, 자식은 슬롯 잠금을 해제한 후 DDS publish한다. 과거 메시지를 줄줄이 재생하거나 원본 데이터의 시각을 현재로 바꾸지 않는다. 자식이 실패하면 기존 모터 오류 정지 경로를 유지한다.

성공본의 모터 제어/경로/추종/엔코더/오도메트리 계산/정지5cm와 .3초 명령·응답·피드백 감시는 그대로다. TF0.25.24 코어도 유지한다.

검증: GIL을 잡는 1.7초 발행 지연을 실제 자식 프로세스에 주입한 메모리 통신 시험 등 11개, 실제 tick 코드의 자식 실패 정지 및 부모 자체 지연 시 기존 RESPONSE_TIMEOUT 유지 시험 2개 통과. 실제 하드웨어 주행을 도구로 실행하지 않았다.

평가 실행은 끈 상태에서 드라이버만 Ctrl+C 후 start_driver.bash로 재시작. 시작 로그에 DDS telemetry isolated in child processes가 있어야 한다. 센서·AMCL·중계기는 유지한다. 다른 터미널에서 check_driver_idle.bash를 실행하면 5분간 조회 전용으로 관측한다. 관측은 arm/주행/설정 변경을 수행하지 않는다. 5분 관측 성공도 전체 코스 주행 성공을 뜻하지 않는다.
