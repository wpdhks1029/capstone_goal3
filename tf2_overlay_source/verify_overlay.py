"""Verify locally built upstream tf2 core; no ROS nodes or hardware access."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
manifest = json.loads((root / 'validated_build.json').read_text())
for relative, expected in manifest['sha256'].items():
    path = root / relative
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SystemExit('TF2_OVERLAY_NOT_VALIDATED: ' + str(path))
if not manifest['installed_deadlock_reproduced'] or not manifest['overlay_regression_passed']:
    raise SystemExit('TF2_OVERLAY_TESTS_NOT_PASSED')
print('TF2: AMCL에만 공식 0.25.24 교착 수정 코어 적용. 시스템 패키지·모터 설정 변경 없음.', flush=True)
