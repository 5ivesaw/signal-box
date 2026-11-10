"""Vendor pinned, official WASM runtimes. Downloads have a 200 MB shared ceiling."""
from pathlib import Path
import hashlib,json,urllib.request
ROOT=Path(__file__).resolve().parents[1]/'web/vendor'
LEDGER=ROOT/'download-ledger.json'
LIMIT=200_000_000
records=json.loads(LEDGER.read_text()) if LEDGER.exists() else []
spent=sum(r['bytes'] for r in records)

def fetch(url,path,expected=None):
    global spent
    if path.exists():
        if expected and hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise RuntimeError('Existing hash mismatch: '+str(path))
        return
    path.parent.mkdir(parents=True,exist_ok=True)
    with urllib.request.urlopen(url,timeout=120) as response:
        size=int(response.headers.get('Content-Length',0))
        if spent+size>LIMIT:raise RuntimeError('Download budget exceeded')
        parts=[]
        while True:
            allowance=LIMIT-spent
            if allowance<=0:raise RuntimeError('Download budget reached')
            block=response.read(min(65536,allowance))
            if not block:break
            spent+=len(block);parts.append(block)
    data=b''.join(parts);digest=hashlib.sha256(data).hexdigest()
    if expected and digest!=expected:raise RuntimeError('SHA-256 mismatch')
    path.write_bytes(data)
    records.append({'url':url,'file':str(path.relative_to(ROOT)),'bytes':len(data),'sha256':digest})
    LEDGER.write_text(json.dumps(records,indent=2)+'\n')
    print(path.name,len(data),flush=True)

fetch('https://cdn.jsdelivr.net/npm/@ffmpeg/core@0.12.10/dist/umd/ffmpeg-core.js',ROOT/'ffmpeg/ffmpeg-core.js')
fetch('https://cdn.jsdelivr.net/npm/@ffmpeg/core@0.12.10/dist/umd/ffmpeg-core.wasm',ROOT/'ffmpeg/ffmpeg-core.wasm')
base='https://cdn.jsdelivr.net/pyodide/v0.27.7/full/'
for name in ['pyodide.js','pyodide.asm.js','pyodide.asm.wasm','python_stdlib.zip','pyodide-lock.json']:
    fetch(base+name,ROOT/'pyodide'/name)
meta=json.loads((ROOT/'pyodide/pyodide-lock.json').read_text())
for name in ['numpy','scipy','openblas']:
    item=meta['packages'][name];fetch(base+item['file_name'],ROOT/'pyodide'/item['file_name'],item['sha256'])
# Record hashes for initial metadata/loader requests made before the helper existed.
for row in records:
    row['sha256']=hashlib.sha256((ROOT/row['file']).read_bytes()).hexdigest()
LEDGER.write_text(json.dumps(records,indent=2)+'\n')
print(f'Total runtime downloads: {spent/1e6:.2f} MB',flush=True)
