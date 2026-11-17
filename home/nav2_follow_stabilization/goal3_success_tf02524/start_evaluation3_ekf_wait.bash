#!/usr/bin/env bash
set -e
restore_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python3 -B "$restore_dir/verify_restore.py"
reference="${1:-}"
if test -z "$reference"; then
  IFS= read -r reference < "$restore_dir/evaluation3_reference_wait/latest_reference_path.txt"
fi
export CONVOY_TF_STATIC_TOPIC=/tf_static
echo '평가3: 성공본 정지5cm + EKF·모터상태 대기/재개 + 상태발행·경로계산 프로세스 분리'
exec bash "$restore_dir/evaluation3_ekf_wait/start_evaluation3.bash" "$reference"
