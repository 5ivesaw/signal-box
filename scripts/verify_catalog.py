#!/usr/bin/env python3
"""Extended local integration check. Slower than unit suite (Cinepak in particular)."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from signalbox.catalog import CATALOG
from signalbox.model import Project
from signalbox.render import render,preflight
from signalbox.media import ffmpeg,probe


def main():
    results=[]
    with tempfile.TemporaryDirectory(prefix='signalbox-verify-') as tmp:
        root=Path(tmp);source=root/'fixture.mp4'
        subprocess.run(ffmpeg()+['-f','lavfi','-i','testsrc2=size=128x96:rate=12:duration=3',
           '-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=3',
           '-c:v','libx264','-threads','2','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(source)],check=True)
        cases=[(e.id,[e]) for e in CATALOG if e.kind in ('vcodec','acodec')]
        cases += [('builtin_stack',[e for e in CATALOG if e.kind in ('frame','vf','af','audio','meta')]),
                  ('asset_stack',[e for e in CATALOG if e.asset])]
        for name,effects in cases:
            p=Project(source=str(source),width=96,fps=12)
            for e in effects:
                p.set(e.id);p.effects[e.id].strength=.3
                if e.asset:p.effects[e.id].asset=str(source)
            errors=preflight(p)['errors']
            if errors:
                results.append({'case':name,'status':'unavailable','reasons':errors});continue
            try:
                start=time.monotonic();output=root/f'{name}.mp4';duration=1 if name.endswith('_stack') else 3
                render(p,output,duration=duration)
                info=probe(output)
                if abs(info['duration']-duration)>.15:raise AssertionError(f'Duration changed: {info["duration"]}')
                subprocess.run(ffmpeg()+['-i',str(output),'-f','null','-'],check=True,capture_output=True)
                row={'case':name,'status':'passed','effects':len(effects),'seconds':round(time.monotonic()-start,2)}
            except Exception as exc:row={'case':name,'status':'failed','reason':str(exc)}
            results.append(row);print(json.dumps(row),flush=True)
    if len(sys.argv)>1:Path(sys.argv[1]).write_text(json.dumps(results,indent=2)+'\n')
    return int(any(row['status']=='failed' for row in results))

if __name__=='__main__':raise SystemExit(main())
