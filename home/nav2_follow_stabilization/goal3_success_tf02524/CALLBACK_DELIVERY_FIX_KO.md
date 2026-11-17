# 평가 실행기 IMU 수신 지연 비교 및 콜백 처리 수정

독립 기록: reports/sensor_delivery_1794911760429113232.jsonl.
실패 시 실행기의 IMU 시각은 1794911799826581664에서 멈췄고,
source_age=0.819531855초, receive_age=0.802929324초였다.
같은 구간 독립 기록기는 계속 새 IMU를 받았다. 전체 60초 IMU 최대 수신 간격은
0.29665307초, 관측된 최대 원본 시각 나이는 0.187497143초였다.
따라서 이번 IMU_STALE은 센서 전체 발행 중단이 아니라 실행기 경로에서의 지연이다.
독립 관측에서도 EKF 최대 수신 간격 1.16119747초가 있었으므로 모든 입력 지연이
하나의 원인이라고 단정하지 않는다.

설치된 Humble rclpy Executor.wait_for_ready_callbacks는 호출 인수가 바뀌면
진행 중 ready-callback iterator를 새로 만든다. 기존 실행기는 .01초 spin과
0초 drain을 반복했다. 앞쪽 입력이 계속 준비되면 뒤쪽 IMU 콜백까지 도달하지
못하는 경우가 생길 수 있다. 설치된 메서드를 AST로 추출한 ROS 없는 재현에서
9개 준비 콜백 중 기존 방식의 마지막 콜백은 50주기 동안 처리되지 않았다.

수정: CallbackPump가 SingleThreadedExecutor에 노드를 한 번 등록한다.
모든 spin은 같은 timeout 인수를 사용해, 짧은 처리 예산으로 중간에 돌아가도
다음 주기에 대기 큐의 나머지를 이어서 처리한다. 콜백과 제어 연산은 같은 스레드에서
실행하므로 새 동시 접근 경합은 추가하지 않는다.

0.8초 센서 신선도, 0.3초 드라이버 감시, 정지5cm, 계획여유10cm, 원본 경로/오돔
수학은 변경하지 않았다. 실제 IMU 발행이 끊기는 경우의 종료도 그대로다.
원본 evaluation3_reference_wait는 보존하고 별도 evaluation3_ekf_wait만 수정했다.

실물 재시험은 아직 필요하다. 현재 프로세스에는 수정 코드가 소급 적용되지 않는다.
평가 실행기만 다시 켜면 되며 드라이버·센서·AMCL·중계기는 유지한다.
결과 callback_dispatch가 PERSISTENT_EXECUTOR_FIXED_TIMEOUT인지 확인한다.

근거 소스: https://github.com/ros2/rclpy/blob/humble/rclpy/rclpy/executors.py
