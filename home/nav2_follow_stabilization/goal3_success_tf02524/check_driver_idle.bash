#!/usr/bin/env bash
set -e
restore_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$HOME/nav2_follow_integration/baseline/follower_diagnostics/integration_async_env.bash"
exec python3 -B "$restore_dir/watch_driver_idle.py"
