#!/usr/bin/env bash
set -e
restore_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python3 -B "$restore_dir/verify_restore.py"
exec bash "$restore_dir/evaluation3_reference_wait/capture_reference.bash"
