#!/usr/bin/env bash
set -e
restore_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python3 -B "$restore_dir/verify_restore.py"
source "$HOME/nav2_follow_integration/baseline/follower_diagnostics/integration_async_env.bash"
exec python3 -B "$restore_dir/transport_driver/follower_drive_node.py" \
  --run-hardware --ack-hardware-zero-rpm-tx --isolated-telemetry \
  --input-kind local_avoidance --ack-bounded-pivot-candidate \
  --ack-continuous20-candidate --enable-motion-input \
  --trial-max-rpm 10 --trial-seconds 0
