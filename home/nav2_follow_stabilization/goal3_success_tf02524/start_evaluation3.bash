#!/usr/bin/env bash
set -e
restore_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python3 -B "$restore_dir/verify_restore.py"
export CONVOY_TF_STATIC_TOPIC=/tf_static
exec bash "$restore_dir/evaluation3_reference_wait/start_evaluation3.bash" "$@"
