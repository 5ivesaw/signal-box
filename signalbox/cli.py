from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from . import __version__
from .model import Project
from .catalog import CATALOG,BY_ID
from .media import Job,Cancelled


def project_args(parser):
    parser.add_argument('source',nargs='?',help='Local source video (or use --project)')
    parser.add_argument('--project',help='Load a saved JSON project')
    parser.add_argument('--effects',default='',help='Comma-separated effect IDs')
    parser.add_argument('--preset',choices=['tape','film','microcassette','damaged_stream'])
    parser.add_argument('--all',action='store_true',help='Enable literally every catalog entry, including asset slots')
    parser.add_argument('--chaos',action='store_true')
    parser.add_argument('--auto',action='store_true',help='Analyze the entire source and adapt selection')
    parser.add_argument('--seed',type=int)
    parser.add_argument('--width',type=int,help='Working width; 0 keeps source display size (default 854)')
    parser.add_argument('--fps',type=float,help='0 keeps source average rate (default)')
    parser.add_argument('--threads',type=int)
    parser.add_argument('--set',action='append',default=[],metavar='ID.FIELD=JSON',help='Set strength, enabled, locked, asset, start, end or roi')


def make_project(args,job=None):
    from .analysis import apply_preset,select_all,chaos,analyze,apply_auto
    p=Project.load(args.project) if args.project else Project()
    if args.source:p.source=str(Path(args.source).expanduser().resolve())
    for key in ('width','fps','seed','threads'):
        if getattr(args,key,None) is not None:setattr(p,key,getattr(args,key))
    if args.preset:apply_preset(p,args.preset)
    if args.all:select_all(p)
    if args.chaos:chaos(p)
    if args.auto:apply_auto(p,analyze(p.source,job=job))
    for key in filter(None,args.effects.split(',')):
        if key not in BY_ID:raise ValueError('Unknown effect: '+key)
        p.set(key)
    for item in args.set:
        target,value=item.split('=',1);key,field=target.split('.',1)
        if key not in BY_ID:raise ValueError('Unknown effect: '+key)
        if field not in ('enabled','strength','locked','asset','start','end','roi'):raise ValueError('Invalid effect field '+field)
        from .model import Setting
        s=p.effects.setdefault(key,Setting())
        try:value=json.loads(value)
        except json.JSONDecodeError:
            if field!='asset':raise ValueError('Parameter value must be valid JSON') from None
        setattr(s,field,value)
    p.validate()
    return p


def main(argv=None):
    parser=argparse.ArgumentParser(prog='signalbox',description='Signalbox — signal, tape, film and digital-fault workbench')
    parser.add_argument('--version',action='version',version=__version__)
    sub=parser.add_subparsers(dest='command')
    tui=sub.add_parser('tui',help='Interactive terminal workbench');project_args(tui)
    cat=sub.add_parser('catalog',help='Browse/export every effect');cat.add_argument('query',nargs='?',default='');cat.add_argument('--json',action='store_true')
    doctor=sub.add_parser('doctor',help='Check installed dependencies and codec support')
    ana=sub.add_parser('analyze',help='Analyze every decoded frame across the whole source');ana.add_argument('source');ana.add_argument('-o','--output')
    for name in ('render','preview','plan','save'):
        item=sub.add_parser(name);project_args(item)
        if name in ('render','preview'):
            item.add_argument('-o','--output');item.add_argument('--start',type=float,default=0);item.add_argument('--duration',type=float)
            item.add_argument('--scratch');item.add_argument('--overwrite',action='store_true')
        if name=='preview':item.add_argument('--effect',choices=list(BY_ID));item.add_argument('--cache',default='.signalbox-cache')
        if name=='save':item.add_argument('-o','--output',required=True)
    args=parser.parse_args(argv)
    last=['']
    def progress(event):
        stage=event['stage'];f=event.get('fraction');msg=stage+(f' {f:.0%}' if f is not None else '')
        if msg!=last[0]:print(msg,file=sys.stderr);last[0]=msg
        if event.get('warnings'):
            for warning in event['warnings']:print('Note: '+warning,file=sys.stderr)
    job=Job(progress)
    try:
        if args.command is None:
            from .tui import launch
            launch(Project());return 0
        if args.command=='catalog':
            rows=[e for e in CATALOG if all(word in (e.id+' '+e.name+' '+e.description+' '+e.category).lower() for word in args.query.lower().split())]
            if args.json:
                from dataclasses import asdict
                print(json.dumps([asdict(e) for e in rows],indent=2))
            else:
                for e in rows:print(f'{e.id:24} {e.name:44} {e.cost:8} {e.fidelity:8}'+(f' [needs {e.asset}]' if e.asset else ''))
            return 0
        if args.command=='doctor':
            from .media import capabilities
            from .render import AUDIO_CODECS,VIDEO_ENCODERS
            import numpy,scipy,shutil
            caps=capabilities();enc=set(VIDEO_ENCODERS.values())|{v[0] for v in AUDIO_CODECS.values()}
            print(json.dumps({'python':sys.version.split()[0],'numpy':numpy.__version__,'scipy':scipy.__version__,
                'ffmpeg':shutil.which('ffmpeg'),'ffprobe':shutil.which('ffprobe'),'ffplay':shutil.which('ffplay'),
                'catalog_entries':len(CATALOG),'missing_optional_encoders':sorted(enc-caps['encoders']),
                'downloaded_by_app_bytes':0,'core_ready':{'libx264','aac'}<=caps['encoders']},indent=2));return 0
        if args.command=='analyze':
            from .analysis import analyze
            data=analyze(args.source,job=job);text=json.dumps(data,indent=2)
            if args.output:Path(args.output).write_text(text+'\n')
            else:print(text)
            return 0
        p=make_project(args,job)
        if args.command=='tui':
            from .tui import launch
            launch(p);return 0
        if args.command=='save':p.save(args.output);print(args.output);return 0
        from .render import preflight,render,preview
        if args.command=='plan':
            report=preflight(p);print(json.dumps(report,indent=2));return int(bool(report['errors']))
        if args.command=='preview':
            if args.output:
                import copy
                from .model import Setting
                if args.effect:p.effects={args.effect:copy.deepcopy(p.effects.get(args.effect,Setting()))};p.effects[args.effect].enabled=True
                p.width=min(p.width,480) if p.width else 480
                render(p,args.output,start=args.start,duration=args.duration or 8,job=job,overwrite=args.overwrite,scratch=args.scratch)
                print(args.output)
            else:print(preview(p,args.cache,effect_id=args.effect,start=args.start,duration=args.duration or 8,job=job))
        else:
            if not args.output:raise ValueError('render requires -o OUTPUT.mp4')
            render(p,args.output,start=args.start,duration=args.duration,job=job,overwrite=args.overwrite,scratch=args.scratch);print(args.output)
        return 0
    except KeyboardInterrupt:
        job.cancel();print('Cancelled',file=sys.stderr);return 130
    except Cancelled:
        print('Cancelled',file=sys.stderr);return 130
    except (ValueError,RuntimeError,OSError,TypeError,KeyError) as exc:
        job.cancel();print(str(exc),file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
