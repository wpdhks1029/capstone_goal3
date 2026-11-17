#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
root=Path(__file__).resolve().parent
rows=json.loads((root/'MANIFEST.json').read_text())['files']
bad=[]
for r in rows:
 p=root/r['path']
 if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256'] or bool(p.stat().st_mode&0o111)!=r['executable']:bad.append(r['path'])
print(json.dumps({'files':len(rows),'mismatches':bad},ensure_ascii=False))
sys.exit(bool(bad))
