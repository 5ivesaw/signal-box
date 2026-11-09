"""Curses frontend. Worker jobs only communicate through an event queue."""
from __future__ import annotations
import copy
import curses
import json
import os
from pathlib import Path
import queue
import secrets
import shutil
import subprocess
import textwrap
import threading
import time
from .catalog import CATALOG, BY_ID
from .model import Project,Setting
from .media import Job,Cancelled

HELP='''SIGNALBOX — controls

UP/DOWN or j/k: browse. PageUp/PageDown: page. Home/End: first/last.
/: live search (name, ID, category, description); Esc clears search.
Tab / Shift-Tab: category. s: selected-only. h: heavy-only.
Space: toggle focused effect. + / -: strength. l: lock enabled OR excluded state.
e: edit strength, time window, normalized region, asset path.
f: toggle every filtered result. A: select ALL 258 entries. N: clear selection.
1: tape preset. 2: film. 3: microcassette. 4: damaged stream.
a: analyze ENTIRE source and select adaptively. c: new seeded chaos.
Locks protect your choices from automatic mode, chaos, and presets.
Select All explicitly enables everything, including asset-dependent techniques.

O: open source video. L: load project. S: save project JSON.
g: preview start/duration. p: preview focused effect (even if disabled).
v: preview selected stack. b: baseline preview. o: play last preview with FFplay.
R: render full video. d: preflight report. i: analysis / recommendation report.
w: working resolution, FPS, CPU threads. x: cancel current job. ?: help.
q: quit (autosaves to ~/.local/state/signalbox/last-project.json).

Preview files are real motion clips with audio. Default length: 8 seconds.
Use g to inspect another time or a longer temporal evolution. Compare b with p/v.
Temporal state begins at the selected preview start; long-memory effects may
settle differently than in a full render. Cached previews include input stat,
assets, settings, source interval, version and seed in their key.

Strength 0 bypasses an effect. Frame/DSP/asset effects support source-time
windows. Whole-stream filters, codecs and metadata effects do not; preflight
rejects unsupported windows instead of silently ignoring them.

For figures, use footage on a black background; luminance controls opacity.
Regions are normalized x,y,width,height. Face distortion is manually positioned.
Some techniques need authored footage, speech, an IR, or externally processed
model output. Empty slots are explicit preflight errors. No auto downloads.
No REC/battery/timestamp decorations or fake CRT scanline overlay are included.

Heavy operations can take much longer than real time, especially optical flow,
Cinepak, error diffusion, pixel sorting and many codec generations. Preview first.
Every selected stage runs; some can mask earlier stages. Source files are never
modified. Outputs are published atomically and existing names are protected.
'''


class App:
    def __init__(self,screen,project):
        self.screen=screen;self.p=project;self.index=0;self.top=0;self.search='';self.category=0
        self.categories=['All']+list(dict.fromkeys(e.category for e in CATALOG))
        self.selected_only=False;self.heavy_only=False;self.events=queue.Queue();self.job=None;self.worker=None
        self.status='O open video  / search  Space toggle  ? help';self.report=None;self.preview_start=0.;self.preview_duration=8.
        self.last_preview=None;self.messages=[];self.fraction=None;self.dirty=False;self.saved_path=None
        self.cache=Path(os.environ.get('XDG_CACHE_HOME',Path.home()/'.cache'))/'signalbox'
        self.state=Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state'))/'signalbox'
        self.screen.timeout(100);curses.curs_set(0)
        if curses.has_colors():
            curses.start_color();curses.use_default_colors()
            for pair,color in [(1,curses.COLOR_CYAN),(2,curses.COLOR_GREEN),(3,curses.COLOR_YELLOW),(4,curses.COLOR_RED)]:curses.init_pair(pair,color,-1)

    def put(self,y,x,text,attr=0):
        h,w=self.screen.getmaxyx()
        if 0<=y<h and 0<=x<w:
            try:self.screen.addnstr(y,x,str(text).replace('\n',' '),max(0,w-x-1),attr)
            except curses.error:pass

    def rows(self):
        words=self.search.lower().split()
        return [e for e in CATALOG if (self.category==0 or e.category==self.categories[self.category])
                and (not self.selected_only or self.p.effects.get(e.id,Setting(enabled=False)).enabled)
                and (not self.heavy_only or e.cost=='heavy' or e.id in ('pixel_sort','error_dither'))
                and all(word in (e.id+' '+e.name+' '+e.description+' '+e.category).lower() for word in words)]

    def current(self):
        rows=self.rows()
        return rows[min(self.index,len(rows)-1)] if rows else None

    def draw(self):
        self.screen.erase();h,w=self.screen.getmaxyx()
        if h<20 or w<70:
            self.put(0,0,'Signalbox needs a terminal at least 70 columns x 20 rows. Resize or q to quit.');self.screen.refresh();return
        accent=curses.color_pair(1)|curses.A_BOLD
        self.put(0,1,'SIGNALBOX   /   signal + tape + film + codec workbench',accent)
        self.put(1,1,f'Source: {self.p.source or "[O to open a local video]"}')
        enabled=len(self.p.enabled());heavy=sum(e.cost=='heavy' or e.id in ('pixel_sort','error_dither') for e,s in self.p.enabled())
        self.put(2,1,f'{enabled}/{len(CATALOG)} enabled | {heavy} expensive | width {self.p.width or "native"} | seed {self.p.seed} | '+('JOB RUNNING (x cancels)' if self.busy() else 'ready'),curses.color_pair(3) if heavy else 0)
        self.put(4,1,f'Category [Tab]: {self.categories[self.category]}  Search [/]: {self.search or "-"}'+('  SELECTED' if self.selected_only else '')+('  HEAVY' if self.heavy_only else ''),accent)
        split=max(42,int(w*.54)) if w>=100 else w
        rows=self.rows();self.index=max(0,min(self.index,len(rows)-1));visible=h-12
        self.top=min(self.top,self.index)
        if self.index>=self.top+visible:self.top=self.index-visible+1
        for line,e in enumerate(rows[self.top:self.top+visible],6):
            idx=self.top+line-6;s=self.p.effects.get(e.id,Setting(enabled=False));flag='x' if s.enabled else ' '
            lock='L' if s.locked else ' ';need='@' if e.asset and not s.asset else ' '
            cost='!' if e.cost=='heavy' or e.id in ('pixel_sort','error_dither') else ' '
            text=f'[{flag}]{lock}{need}{cost} {e.name}'
            text=text[:split-9].ljust(split-9)+f'{s.strength:3.0%}'
            self.put(line,1,text,curses.A_REVERSE if idx==self.index else 0)
        e=self.current()
        if split<w and e:
            s=self.p.effects.get(e.id,Setting(enabled=False));x=split+1
            details=[e.name,'',e.id,f'{e.category} | {e.fidelity}',
                f'Cost: {e.cost}'+(' / moving preview recommended' if e.temporal else ''),'',e.description,'',
                f'Strength: {s.strength:.0%}   Locked: {s.locked}',
                f'Time: {s.start:g}s to {s.end if s.end is not None else "end"}',
                f'Region: {s.roi}',f'Asset: {s.asset or ("REQUIRED: "+e.asset if e.asset else "none needed")}']
            y=6
            for detail in details:
                for part in textwrap.wrap(detail,max(10,w-x-2)) or ['']:
                    if y<h-6:self.put(y,x,part,curses.color_pair(3) if 'REQUIRED' in part or 'heavy' in part else 0)
                    y+=1
        elif e:self.put(h-6,1,f'{e.id} | {e.fidelity} | {e.cost} | e to edit/info')
        self.put(h-5,1,f'Preview: {self.preview_start:g}s + {self.preview_duration:g}s  [g edit]  [p effect] [v stack] [b source] [o play]',accent)
        self.put(h-4,1,self.status,curses.color_pair(2))
        self.put(h-3,1,'Space toggle  +/- strength  e edit  l lock  a auto  c chaos  A all  N none  f filtered')
        self.put(h-2,1,'O source  L load  S save  R render  d check  i report  w quality  x cancel  ? help  q quit')
        self.screen.refresh()

    def prompt(self,title,default=''):
        value=str(default);cursor=len(value);curses.curs_set(1);self.screen.timeout(-1)
        try:
            while True:
                h,w=self.screen.getmaxyx();y=h-3
                self.put(y,0,' '*(w-1));self.put(y,1,title+': '+value)
                try:self.screen.move(y,min(w-2,len(title)+3+cursor))
                except curses.error:pass
                self.screen.refresh();key=self.screen.get_wch()
                if key in ('\n','\r',curses.KEY_ENTER):return value
                if key=='\x1b':return None
                if key in ('\x7f','\b',curses.KEY_BACKSPACE):
                    if cursor:value=value[:cursor-1]+value[cursor:];cursor-=1
                elif key=='\x15':value='';cursor=0
                elif key==curses.KEY_LEFT:cursor=max(0,cursor-1)
                elif key==curses.KEY_RIGHT:cursor=min(len(value),cursor+1)
                elif isinstance(key,str) and key.isprintable():value=value[:cursor]+key+value[cursor:];cursor+=1
        except curses.error:return None
        finally:curses.curs_set(0);self.screen.timeout(100)

    def view(self,title,text):
        offset=0
        while True:
            self.screen.erase();h,w=self.screen.getmaxyx();self.put(0,1,title,curses.A_BOLD|curses.color_pair(1))
            lines=[]
            for row in text.splitlines():lines.extend(textwrap.wrap(row,max(10,w-4),replace_whitespace=False) or [''])
            for i,row in enumerate(lines[offset:offset+h-4],2):self.put(i,1,row)
            self.put(h-1,1,'Up/Down or PgUp/PgDn to scroll. Esc/q/Enter closes.');self.screen.refresh()
            key=self.screen.getch()
            if key in (27,ord('q'),10,13):break
            if key in (curses.KEY_DOWN,ord('j')):offset=min(max(0,len(lines)-h+4),offset+1)
            if key in (curses.KEY_UP,ord('k')):offset=max(0,offset-1)
            if key==curses.KEY_NPAGE:offset=min(max(0,len(lines)-h+4),offset+h-4)
            if key==curses.KEY_PPAGE:offset=max(0,offset-h+4)

    def live_search(self):
        old=self.search;curses.curs_set(1);self.screen.timeout(-1)
        try:
            while True:
                self.index=0;self.draw();key=self.screen.get_wch()
                if key in ('\n','\r'):return
                if key=='\x1b':self.search=old;return
                if key in ('\x7f','\b',curses.KEY_BACKSPACE):self.search=self.search[:-1]
                elif key=='\x15':self.search=''
                elif isinstance(key,str) and key.isprintable():self.search+=key
        except curses.error:pass
        finally:curses.curs_set(0);self.screen.timeout(100)

    def busy(self):return self.worker is not None and self.worker.is_alive()

    def start_job(self,fn,done):
        if self.busy():self.status='A job is already running. x cancels it.';return
        self.job=Job(lambda event:self.events.put(('progress',event)))
        def work():
            try:self.events.put(('done',(done,fn(self.job))))
            except Cancelled:self.events.put(('cancel','Job cancelled; unfinished output removed.'))
            except Exception as ex:self.events.put(('error',str(ex)))
        self.worker=threading.Thread(target=work,daemon=True);self.worker.start()

    def pump(self):
        # Drain without redrawing every progress event.
        while True:
            try:kind,value=self.events.get_nowait()
            except queue.Empty:break
            if kind=='progress':
                self.status=value['stage']+(f' {value["fraction"]:.0%}' if value.get('fraction') is not None else '')
                self.messages.extend(value.get('warnings',[]))
            elif kind=='done':
                callback,result=value;callback(result)
            elif kind=='cancel':self.status=value
            else:self.status='Failed: '+value.splitlines()[0]+' (i for details)';self.messages.append(value)

    def autosave(self):
        self.state.mkdir(parents=True,exist_ok=True);self.p.save(self.state/'last-project.json')

    def edit(self):
        e=self.current()
        if not e:return
        s=copy.deepcopy(self.p.effects.get(e.id,Setting()))
        self.view(e.name,e.description+f'\n\nFidelity: {e.fidelity}\nCost: {e.cost}\nKind: {e.kind}\n\nEnter closes this description and opens the parameter fields. Escape in a field cancels the edit.')
        strength=self.prompt('Strength 0..1',s.strength)
        if strength is None:return
        s.strength=float(strength)
        if e.kind in ('frame','audio','asset_video','asset_audio') or e.recipe=='audio_reverse':
            window=self.prompt('Source time start,end (blank end = forever)',f'{s.start},{s.end or ""}')
            if window is None:return
            lo,hi=window.split(',');s.start=float(lo or 0);s.end=float(hi) if hi.strip() else None
        if e.asset:
            asset=self.prompt(f'{e.asset.title()} asset path',s.asset)
            if asset is None:return
            s.asset=str(Path(asset).expanduser().resolve()) if asset else ''
        if e.kind in ('frame','asset_video'):
            region=self.prompt('Region x,y,width,height (normalized)',','.join(str(v) for v in s.roi))
            if region is None:return
            s.roi=[float(x) for x in region.split(',')]
        test=copy.deepcopy(self.p);test.effects[e.id]=s;test.validate();self.p=test;self.dirty=True;self.status='Updated '+e.name

    def do_preview(self,mode):
        from .render import preview
        p=copy.deepcopy(self.p);effect=self.current();start=self.preview_start;duration=self.preview_duration
        if mode=='effect' and not effect:return
        if mode=='baseline':p.effects={}
        eid=effect.id if mode=='effect' else None
        def done(path):self.last_preview=path;self.status=f'Preview ready: o plays {path.name}';self.messages.append('Preview: '+str(path))
        self.start_job(lambda job:preview(p,self.cache,effect_id=eid,start=start,duration=duration,job=job),done)

    def handle(self,key):
        rows=self.rows();h,w=self.screen.getmaxyx();e=self.current()
        if key in (curses.KEY_DOWN,ord('j')):self.index+=1
        elif key in (curses.KEY_UP,ord('k')):self.index-=1
        elif key==curses.KEY_NPAGE:self.index+=h-12
        elif key==curses.KEY_PPAGE:self.index-=h-12
        elif key==curses.KEY_HOME:self.index=0
        elif key==curses.KEY_END:self.index=len(rows)-1
        elif key==9:self.category=(self.category+1)%len(self.categories);self.index=0
        elif key==curses.KEY_BTAB:self.category=(self.category-1)%len(self.categories);self.index=0
        elif key==ord('/'):self.live_search()
        elif key==27:self.search=''
        elif key==ord('s'):self.selected_only=not self.selected_only;self.index=0
        elif key==ord('h'):self.heavy_only=not self.heavy_only;self.index=0
        elif key in (ord(' '),ord('+'),ord('='),ord('-'),ord('l')) and e:
            s=self.p.effects.setdefault(e.id,Setting(enabled=False))
            if key==ord(' '):s.enabled=not s.enabled
            elif key==ord('l'):s.locked=not s.locked
            else:s.strength=round(max(0,min(1,s.strength+(-.05 if key==ord('-') else .05))),2)
            self.dirty=True
        elif key==ord('e'):self.edit()
        elif key==ord('f'):
            enable=not all(self.p.effects.get(e.id,Setting(enabled=False)).enabled for e in rows)
            for e in rows:self.p.set(e.id,enable)
            self.dirty=True
        elif key==ord('A'):
            from .analysis import select_all
            select_all(self.p);self.status=f'All {len(CATALOG)} enabled. Asset slots need files; d lists missing inputs.';self.dirty=True
        elif key==ord('N'):
            for s in self.p.effects.values():s.enabled=False
            self.dirty=True
        elif key in [ord(str(n)) for n in range(1,5)]:
            from .analysis import apply_preset,PRESETS
            apply_preset(self.p,list(PRESETS)[key-ord('1')]);self.dirty=True
        elif key==ord('c'):
            from .analysis import chaos
            chaos(self.p,seed=secrets.randbelow(2**31));self.status=f'Chaos selected {len(self.p.enabled())} effects; seed {self.p.seed}';self.dirty=True
        elif key==ord('a'):
            from .analysis import analyze,apply_auto
            source=self.p.source
            def done(report):
                if self.p.source!=source:self.status='Source changed; analysis retained but selection not applied.'
                else:apply_auto(self.p,report);self.dirty=True;self.status=f'Analyzed {report["frames_examined"]} frames. i shows reasons; locked choices kept.'
                self.report=report
            self.start_job(lambda job:analyze(source,job=job),done)
        elif key==ord('O'):
            path=self.prompt('Source video path',self.p.source)
            if path:
                from .media import local_file
                self.p.source=str(local_file(path));self.report=None;self.dirty=True
        elif key==ord('L'):
            path=self.prompt('Project JSON path',self.saved_path or '')
            if path:self.p=Project.load(path);self.saved_path=path;self.dirty=False;self.status='Project loaded'
        elif key==ord('S'):
            path=self.prompt('Save project JSON',self.saved_path or 'signalbox-project.json')
            if path:self.p.save(path);self.saved_path=path;self.dirty=False;self.status='Saved '+path
        elif key==ord('g'):
            interval=self.prompt('Preview start,duration seconds',f'{self.preview_start},{self.preview_duration}')
            if interval:
                start,duration=map(float,interval.split(','))
                if start<0 or duration<=0:raise ValueError('Preview interval must be positive')
                self.preview_start,self.preview_duration=start,duration
        elif key==ord('p'):self.do_preview('effect')
        elif key==ord('v'):self.do_preview('stack')
        elif key==ord('b'):self.do_preview('baseline')
        elif key==ord('o'):
            if not self.last_preview:self.status='Generate a preview first (p, v, or b).'
            elif not shutil.which('ffplay'):self.status='FFplay is not installed. Open '+str(self.last_preview)
            else:subprocess.Popen(['ffplay','-autoexit','-loglevel','error',str(self.last_preview)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);self.status='Playing preview in FFplay'
        elif key==ord('R'):
            from .render import render
            path=self.prompt('Output .mp4 or .mkv (existing files protected)','signalbox-render.mp4')
            if path:
                p=copy.deepcopy(self.p)
                self.start_job(lambda job:render(p,path,job=job),lambda result:setattr(self,'status','Rendered '+result['output']))
        elif key==ord('d'):
            from .render import preflight
            p=copy.deepcopy(self.p)
            def done(result):self.messages.append(json.dumps(result,indent=2));self.status=f'Preflight: {len(result["errors"])} errors, {len(result["warnings"])} notes. i shows details.'
            self.start_job(lambda job:preflight(p),done)
        elif key==ord('i'):self.view('Analysis and job report',(json.dumps(self.report,indent=2)+'\n\n' if self.report else '')+'\n\n'.join(self.messages[-20:]) or 'No report yet. a analyzes; d checks requirements.')
        elif key==ord('w'):
            result=self.prompt('Width (0 native), FPS (0 source), threads',f'{self.p.width},{self.p.fps},{self.p.threads}')
            if result:
                width,fps,threads=result.split(',');p=copy.deepcopy(self.p);p.width=int(width);p.fps=float(fps);p.threads=int(threads);p.validate();self.p=p;self.dirty=True
        elif key==ord('x'):
            if self.job:self.job.cancel();self.status='Cancelling…'
        elif key==ord('?'):self.view('Signalbox help',HELP.replace('258',str(len(CATALOG))))
        elif key==ord('q'):
            if self.busy():self.job.cancel();self.status='Cancelling before exit…';self.worker.join(timeout=5)
            self.autosave();return False
        self.index=max(0,min(self.index,len(self.rows())-1));return True

    def run(self):
        last_save=time.monotonic()
        while True:
            self.pump();self.draw();key=self.screen.getch()
            try:
                if key!=-1 and not self.handle(key):break
                if self.dirty and time.monotonic()-last_save>15:self.autosave();last_save=time.monotonic()
            except (ValueError,RuntimeError,OSError,TypeError) as ex:self.status=str(ex).splitlines()[0];self.messages.append(str(ex))


def launch(project):
    import sys
    if not sys.stdin.isatty() or not sys.stdout.isatty():raise ValueError('TUI requires an interactive terminal; use catalog, plan, analyze, preview or render for scripts')
    os.environ.setdefault('ESCDELAY','25')
    curses.wrapper(lambda screen:App(screen,project).run())
