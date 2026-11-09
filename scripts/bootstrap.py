#!/usr/bin/env python3
"""Optional installer. Requires Python 3.10+ and pip/venv; never installs FFmpeg.
Reuses installed NumPy/SciPy. Otherwise downloads compatible binary wheels only,
with a shared 200 MB payload ceiling (100 MB below the user's total budget).
No source builds, model weights, GPU libraries, or automatic optional tools.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
LIMIT=200_000_000
spent=0
ledger=[]


def get(url,limit):
    global spent
    with urllib.request.urlopen(url,timeout=60) as response:
        length=int(response.headers.get('Content-Length',0))
        if length and length>min(limit,LIMIT-spent):raise RuntimeError('Download budget would be exceeded')
        chunks=[];count=0
        while True:
            allowance=min(limit-count,LIMIT-spent)
            if allowance<=0:raise RuntimeError('Download limit reached; no further data requested')
            block=response.read(min(65536,allowance))
            if not block:break
            spent+=len(block);count+=len(block);chunks.append(block)
        ledger.append({'url':url,'bytes':count})
        return b''.join(chunks)


def main():
    if sys.version_info<(3,10):raise RuntimeError('Python 3.10+ required')
    if all(importlib.util.find_spec(name) for name in ('numpy','scipy')):
        print('NumPy and SciPy already available. Downloaded 0 bytes. Run ./signalbox-run doctor');return
    try:
        from pip._vendor.packaging.tags import sys_tags
        from pip._vendor.packaging.utils import parse_wheel_filename
    except ImportError:raise RuntimeError('pip is required as a foundational tool; install it separately') from None
    tags=list(sys_tags());ranks={tag:i for i,tag in enumerate(tags)}
    packages=[('numpy','2.2.6'),('scipy','1.15.3')]
    planned=[]
    for name,version in packages:
        metadata=json.loads(get(f'https://pypi.org/pypi/{name}/{version}/json',2_000_000))
        candidates=[]
        for item in metadata['urls']:
            if item['packagetype']!='bdist_wheel' or item.get('yanked'):continue
            _,_,_,wheel_tags=parse_wheel_filename(item['filename'])
            score=min((ranks[tag] for tag in wheel_tags if tag in ranks),default=None)
            if score is not None:candidates.append((score,item))
        if not candidates:raise RuntimeError(f'No supported binary wheel for {name} on this interpreter. Use Python 3.10–3.13 or supply dependencies separately; no source build attempted.')
        item=min(candidates,key=lambda x:x[0])[1];planned.append(item)
    if spent+sum(item['size'] for item in planned)>LIMIT:raise RuntimeError('Planned wheels exceed the 200 MB installer ceiling')
    print(f'Planned wheel payload: {sum(x["size"] for x in planned)/1e6:.1f} MB; total ceiling 200 MB')
    cache=ROOT/'.dependency-cache';cache.mkdir(exist_ok=True);paths=[]
    try:
        for item in planned:
            content=get(item['url'],item['size']+1)
            if hashlib.sha256(content).hexdigest()!=item['digests']['sha256']:raise RuntimeError('Wheel SHA-256 mismatch')
            path=cache/item['filename'];path.write_bytes(content);paths.append(path)
        venv=ROOT/'.venv'
        subprocess.run([sys.executable,'-m','venv',str(venv)],check=True)
        python=venv/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python')
        subprocess.run([str(python),'-m','pip','install','--no-index','--no-deps',*[str(x) for x in paths]],check=True)
        print(f'Installed. Downloaded {spent/1e6:.2f} MB. Run ./signalbox-run doctor')
    finally:
        (cache/'download-ledger.json').write_text(json.dumps({'bytes':spent,'ceiling':LIMIT,'requests':ledger},indent=2)+'\n')

if __name__=='__main__':
    try:main()
    except Exception as exc:print(f'Installer stopped: {exc}',file=sys.stderr);sys.exit(1)
