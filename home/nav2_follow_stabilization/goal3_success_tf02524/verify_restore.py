"""Check frozen success-source restoration; no ROS nodes or hardware access."""
import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parent
manifest=json.loads((root/'RESTORE_MANIFEST.json').read_text())
for section in ('restored_sources','shared_sources'):
    for name,expected in manifest[section].items():
        path=root/name if section=='restored_sources' else Path(name)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise SystemExit('SUCCESS_RESTORE_FILE_CHANGED: '+str(path))
print('성공 백업 7df1f0f 제어 코드·정지5cm 유지. AMCL TF 0.25.24 코어 + 모터 DDS 발행 분리 적용.',flush=True)
