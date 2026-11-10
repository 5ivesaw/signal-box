"""Buildless site assets generated from the canonical Python engine/catalog."""
from pathlib import Path
import sys,json,zipfile,shutil
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from signalbox.catalog import CATALOG
from signalbox.analysis import PRESETS
web=ROOT/'web';web.mkdir(exist_ok=True)
(web/'catalog.json').write_text(json.dumps({'version':'0.2.0','effects':[asdict(e) for e in CATALOG],'presets':PRESETS},ensure_ascii=False))
with zipfile.ZipFile(web/'engine.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in (ROOT/'signalbox').glob('*.py'):
        if p.stem not in ('tui','cli','__main__'):z.write(p,'signalbox/'+p.name)
(web/'examples').mkdir(exist_ok=True)
for name in ['test-pattern.mp4','tape-demo.mp4']:
    shutil.copyfile(ROOT/'examples'/name,web/'examples'/name)
(web/'.nojekyll').write_text('')
print(f'Built browser catalog ({len(CATALOG)} entries), shared engine, and examples.')
