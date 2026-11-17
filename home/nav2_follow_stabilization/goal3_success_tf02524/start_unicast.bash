#!/usr/bin/env bash
set -e
restore_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python3 -B "$restore_dir/verify_restore.py"
source "$HOME/nav2_follow_integration/baseline/follower_diagnostics/integration_async_env.bash"
exec python3 -B "$restore_dir/convoy_unicast_relay.py" --role follower --peer 10.253.245.81
