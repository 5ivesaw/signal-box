from __future__ import annotations
from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import threading
import time


class Cancelled(RuntimeError): pass


class Job:
    """Cancellation and progress contract shared by CLI, TUI and future API workers."""
    def __init__(self, callback=None):
        self.callback=callback or (lambda event: None)
        self.cancelled=threading.Event()
        self.lock=threading.Lock()
        self.processes=[]

    def emit(self, stage, fraction=None, **extra):
        self.callback(dict(stage=stage, fraction=fraction, **extra))

    def check(self):
        if self.cancelled.is_set():raise Cancelled('Job cancelled')

    def cancel(self):
        self.cancelled.set()
        with self.lock:
            for p in self.processes:
                if p.poll() is None:p.terminate()

    def spawn(self, args, **kwargs):
        self.check()
        p=subprocess.Popen([str(x) for x in args],**kwargs)
        with self.lock:
            self.processes.append(p)
            if self.cancelled.is_set():p.terminate()
        return p

    def reap(self,p):
        try:
            # Close read pipes before signalling: FFmpeg can otherwise stay blocked
            # writing an unread raw frame and defer SIGTERM indefinitely.
            if p.stdout is not None and not p.stdout.closed:p.stdout.close()
            if p.poll() is None:
                p.terminate()
                try:p.wait(timeout=3)
                except subprocess.TimeoutExpired:p.kill();p.wait()
        finally:
            with self.lock:
                if p in self.processes:self.processes.remove(p)

    def run(self,args,stage='Processing'):
        self.emit(stage)
        with tempfile.TemporaryFile() as log:
            p=self.spawn(args,stdout=subprocess.DEVNULL,stderr=log,stdin=subprocess.DEVNULL)
            try:
                while p.poll() is None:
                    self.check();time.sleep(.08)
                self.check()
                if p.returncode:
                    log.seek(0);message=log.read().decode(errors='replace')[-5000:]
                    raise RuntimeError(f'{stage} failed:\n{message}')
            finally:self.reap(p)


def local_file(path):
    p=Path(path).expanduser().resolve()
    if not p.is_file():raise ValueError(f'File not found: {p}')
    return p


def probe(path):
    path=local_file(path)
    if not shutil.which('ffprobe'):raise RuntimeError('FFprobe is required. Install FFmpeg separately.')
    result=subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)],capture_output=True,text=True,timeout=60)
    if result.returncode:raise ValueError('Cannot read media: '+result.stderr[-1200:])
    info=json.loads(result.stdout)
    videos=[x for x in info.get('streams',[]) if x.get('codec_type')=='video' and not x.get('disposition',{}).get('attached_pic')]
    audios=[x for x in info.get('streams',[]) if x.get('codec_type')=='audio']
    v=videos[0] if videos else {}
    num,_,den=v.get('avg_frame_rate','0/1').partition('/')
    try:fps=float(num)/float(den or 1)
    except (ValueError,ZeroDivisionError):fps=0
    duration=float(v.get('duration') or info.get('format',{}).get('duration') or 0)
    return {'path':str(path),'duration':duration,'width':v.get('width',0),'height':v.get('height',0),
            'fps':fps or 25.,'audio':bool(audios),'video':bool(videos),'streams':info.get('streams',[]),
            'format':info.get('format',{}),'video_index':v.get('index',0)}


def parse_capability_table(text, kind):
    values=set()
    for line in text.splitlines():
        parts=line.split()
        if len(parts)<2 or parts[1]=='=':continue
        if kind=='filters':
            # FFmpeg removed the command-support flag in newer releases.
            # The input/output signature is stable across both listing formats.
            valid=len(parts)>=3 and '->' in parts[2]
        else:valid=len(parts[0])==6 and parts[0][0] in 'VAS'
        if valid:values.add(parts[1])
    return values


_CAPS={}
def capabilities():
    if _CAPS:return _CAPS
    if not shutil.which('ffmpeg'):raise RuntimeError('FFmpeg is required. No dependencies are downloaded automatically.')
    for key,args in [('filters',['-filters']),('encoders',['-encoders']),('bsfs',['-bsfs'])]:
        p=subprocess.run(['ffmpeg','-hide_banner',*args],capture_output=True,text=True,timeout=30)
        text=p.stdout+'\n'+p.stderr
        if key=='bsfs':values=set(line.strip() for line in text.splitlines())
        else:values=parse_capability_table(text,key)
        _CAPS[key]=values
    return _CAPS


def ffmpeg(threads=2):
    return ['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-threads',str(threads),
            '-filter_threads','1','-filter_complex_threads','1']


def read_exact(stream,count):
    blocks=[];remaining=count
    while remaining:
        b=stream.read(remaining)
        if not b:break
        blocks.append(b);remaining-=len(b)
    return b''.join(blocks)
