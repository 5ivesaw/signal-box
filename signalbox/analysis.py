"""Full-duration, bounded-memory analysis and transparent adaptive selection.
Every decoded video frame is examined at a reduced spatial resolution; every
sample of the first audio track contributes. This is a heuristic scorer, not a
trained neural network, semantic classifier or a promise to understand horror.
"""
from pathlib import Path
import copy
import json
import math
import tempfile
import numpy as np
from .media import Job, probe, ffmpeg, read_exact
from .model import Setting
from .catalog import CATALOG, BY_ID


def analyze(source, *, job=None):
    job=job or Job();info=probe(source)
    if not info['video']:raise ValueError('Analysis requires a video stream')
    w,h=160,96
    histogram=np.zeros(256,np.int64);sums=np.zeros(8);frames=0;previous=None;last_mean=None
    cuts=[];scenes=0;max_motion=0.;prev_time=0
    with tempfile.TemporaryFile() as log:
        # No fps filter: include EVERY decoded frame, including VFR frames. PTS are
        # streamed alongside frames through showinfo's log in a separate reader.
        import threading,re
        times=[];time_lock=threading.Lock();time_ready=threading.Condition(time_lock)
        stderr_lines=[]
        args=ffmpeg()+['-loglevel','info','-i',info['path'],'-map',f'0:{info["video_index"]}','-an','-vf',f'scale={w}:{h},showinfo',
                      '-fps_mode','passthrough','-pix_fmt','rgb24','-f','rawvideo','pipe:1']
        proc=job.spawn(args,stdout=__import__('subprocess').PIPE,stderr=__import__('subprocess').PIPE)
        # A bounded timestamp queue avoids retaining one timestamp per frame.
        from collections import deque
        pts_queue=deque();reader_done=False
        def log_reader():
            nonlocal reader_done
            for b in iter(proc.stderr.readline,b''):
                line=b.decode(errors='replace')
                match=re.search(r'\bn:\s*\d+.*?pts_time:([\d.eE+\-]+)',line)
                if match:
                    with time_ready:pts_queue.append(float(match.group(1)));time_ready.notify()
                else:
                    stderr_lines.append(line)
                    if len(stderr_lines)>50:del stderr_lines[0]
            with time_ready:reader_done=True;time_ready.notify_all()
        thread=threading.Thread(target=log_reader,daemon=True);thread.start()
        try:
            while True:
                job.check();raw=read_exact(proc.stdout,w*h*3)
                if not raw:break
                if len(raw)!=w*h*3:raise RuntimeError('Incomplete analysis frame')
                with time_ready:
                    time_ready.wait_for(lambda:bool(pts_queue) or reader_done or job.cancelled.is_set(),timeout=5)
                    t=pts_queue.popleft() if pts_queue else frames/info['fps']
                f=np.frombuffer(raw,np.uint8).reshape(h,w,3).astype(np.float32)/255
                y=f[:,:,0]*.299+f[:,:,1]*.587+f[:,:,2]*.114
                hist=np.bincount(np.minimum(255,(y*255).astype(np.int32)).ravel(),minlength=256);histogram+=hist
                mean=float(y.mean());contrast=float(y.std())
                edges=(np.mean(np.abs(np.diff(y,axis=0)))+np.mean(np.abs(np.diff(y,axis=1))))/2
                chroma=np.max(f,axis=2)-np.min(f,axis=2)
                lap=4*y[1:-1,1:-1]-y[:-2,1:-1]-y[2:,1:-1]-y[1:-1,:-2]-y[1:-1,2:]
                noise=float(np.median(np.abs(lap)))/4
                motion=float(np.mean(np.abs(y-previous))) if previous is not None else 0
                flicker=abs(mean-last_mean) if last_mean is not None else 0
                clip=float(np.mean((y<.025)|(y>.975)))
                sums+= [mean,contrast,edges,float(chroma.mean()),noise,motion,flicker,clip]
                if motion>.15:
                    scenes+=1;cuts.append({'time':round(t,3),'change':round(motion,4)})
                    cuts=sorted(cuts,key=lambda x:x['change'],reverse=True)[:24]
                max_motion=max(max_motion,motion);previous=y;last_mean=mean;frames+=1;prev_time=t
                if frames%24==0:job.emit('Analyze every picture',min(.7,.7*t/max(.001,info['duration'])),frames=frames)
            proc.wait();thread.join(timeout=5);job.check()
            if proc.returncode:raise RuntimeError('Analysis decode failed: '+''.join(stderr_lines)[-3000:])
        finally:
            job.reap(proc);proc.stdout.close();thread.join(timeout=3);proc.stderr.close()
    if not frames:raise ValueError('No video frames decoded')
    keys=['luma','contrast','detail','saturation','noise_proxy','motion','flicker','clipped_fraction']
    metrics=dict(zip(keys,(sums/frames).tolist()))
    total=histogram.sum();metrics.update(dark_fraction=float(histogram[:45].sum()/total),
          bright_fraction=float(histogram[210:].sum()/total),max_motion=max_motion,
          cuts_per_minute=scenes/max(.001,info['duration']/60))
    audio={'present':info['audio'],'samples':0}
    if info['audio']:
        import subprocess
        with tempfile.TemporaryFile() as log:
            proc=job.spawn(ffmpeg()+['-i',info['path'],'-map','0:a:0','-vn','-ar','16000','-ac','2','-f','f32le','pipe:1'],stdout=subprocess.PIPE,stderr=log)
            sq=0.;peak=0.;silent=0;count=0;centroid_sum=0.;high_sum=0.;low_sum=0.;windows=0;cross=0.;left2=0.;right2=0
            try:
                while True:
                    job.check();raw=read_exact(proc.stdout,16000*2*4)
                    if not raw:break
                    f=np.frombuffer(raw[:len(raw)//8*8],'<f4').reshape(-1,2)
                    if not len(f):continue
                    f=np.nan_to_num(f,nan=0,posinf=1,neginf=-1)
                    sq+=float(np.sum(f.astype(np.float64)**2));peak=max(peak,float(np.max(np.abs(f))))
                    silent+=int(np.sum(np.max(np.abs(f),axis=1)<.003));count+=len(f)
                    cross+=float(np.sum(f[:,0]*f[:,1]));left2+=float(np.sum(f[:,0]**2));right2+=float(np.sum(f[:,1]**2))
                    mono=f.mean(axis=1);spectrum=abs(np.fft.rfft(mono*np.hanning(len(mono))))**2
                    freq=np.fft.rfftfreq(len(mono),1/16000);energy=max(1e-15,float(spectrum.sum()))
                    centroid_sum+=float(np.sum(freq*spectrum)/energy)
                    high_sum+=float(spectrum[freq>4000].sum()/energy);low_sum+=float(spectrum[freq<250].sum()/energy);windows+=1
                    job.emit('Analyze entire audio track',.7+.3*min(1,count/16000/max(.001,info['duration'])))
                proc.wait();job.check()
                if proc.returncode:log.seek(0);raise RuntimeError(log.read().decode(errors='replace')[-3000:])
            finally:job.reap(proc);proc.stdout.close()
        audio.update(samples=count,rms=math.sqrt(sq/max(1,count*2)),peak=peak,silence_fraction=silent/max(1,count),
            spectral_centroid=centroid_sum/max(1,windows),high_band=high_sum/max(1,windows),low_band=low_sum/max(1,windows),
            stereo_correlation=cross/max(1e-12,math.sqrt(left2*right2)))
    result={'schema':1,'source':info['path'],'duration':info['duration'],'fps':info['fps'],'width':info['width'],'height':info['height'],
            'frames_examined':frames,'metrics':metrics,'audio':audio,'interesting_times':sorted(cuts,key=lambda x:x['time']),
            'method':'All decoded frames at 160x96; every decoded audio sample at 16 kHz stereo. No semantic model. Noise is a texture-sensitive proxy.'}
    result['recommendations']=recommend(result)
    job.emit('Analysis complete',1,frames=frames)
    return result


def recommend(report,limit=12):
    m=report['metrics'];au=report['audio'];candidates=[]
    def score(key,value,reason,strength=.4):
        candidates.append({'id':key,'score':round(float(value),3),'strength':round(float(np.clip(strength,.15,.7)),2),'reason':reason})
    score('chroma_bleed',.4+m['saturation'],f"Chroma energy {m['saturation']:.2f}: bandwidth loss can soften color boundaries",.25+m['saturation']*.4)
    score('composite',.35+m['detail']*3,f"Fine-detail score {m['detail']:.3f}: composite separation can expose edge interactions")
    score('sensor_noise',.2+m['dark_fraction']*.8-m['noise_proxy']*3,f"Dark pixels {m['dark_fraction']:.0%}; existing noise proxy {m['noise_proxy']:.3f}",.2+m['dark_fraction']*.35)
    score('bloom',.2+m['bright_fraction']*1.4,f"Highlight coverage {m['bright_fraction']:.0%}: bloom follows actual bright content")
    score('echo',.2+m['motion']*3,f"Mean motion {m['motion']:.3f}: temporal persistence reveals moving edges",.25+m['motion'])
    score('rolling_shutter',.15+m['motion']*2,f"Motion score {m['motion']:.3f}: row timing becomes visible on movement",.25)
    score('gate_weave',.35+(1-min(1,m['motion']*8))*.2,f"Motion {m['motion']:.3f}: subtle registration movement suits held shots",.25)
    score('film_grain',.45-m['noise_proxy']*4,f"Existing texture/noise proxy {m['noise_proxy']:.3f}: avoid piling grain onto noisy input",.3)
    score('tracking',.3+min(.3,report['duration']/600),f"Duration {report['duration']:.1f}s allows evolving timing instability",.25)
    score('multipath',.3+m['contrast']*.8,f"Contrast {m['contrast']:.2f} gives delayed signal ghosts visible edges",.3)
    score('compression',.2+m['detail']+m['motion'],f"Detail {m['detail']:.3f} and motion {m['motion']:.3f} drive codec stress",.3)
    score('exposure_pump',.3-m['flicker']*3,f"Existing flicker {m['flicker']:.3f}: avoid amplifying already unstable brightness",.2)
    score('chroma_delay',.2+m['saturation']*.5,f"Measured saturation {m['saturation']:.2f} supports visible chroma delay",.3)
    score('tape_dropout',.25+min(.25,report['duration']/300),f"Duration {report['duration']:.1f}s gives intermittent dropouts room to develop",.2)
    if au['present']:
        score('wow',.45+min(.25,au.get('low_band',0)),f"Low-band energy {au.get('low_band',0):.0%}: gentle speed modulation",.25)
        score('hiss',.35+au.get('silence_fraction',0)*.25,f"Quiet-sample fraction {au.get('silence_fraction',0):.0%}: a faint tape noise floor",.2)
        score('lowpass',.3+au.get('high_band',0),f"High-band energy {au.get('high_band',0):.0%}: bandwidth loss adapts to source brightness",.3)
        score('print_through',.3+max(0,au.get('peak',0)-au.get('rms',0)),f"Peak {au.get('peak',0):.2f} vs RMS {au.get('rms',0):.2f}: forward pre-echo can precede transients",.25)
        score('tape_saturation',.3+max(0,.3-au.get('rms',0)),f"RMS {au.get('rms',0):.2f}: mild saturation adds density",.25)
    ranked=sorted(candidates,key=lambda x:x['score'],reverse=True)
    # Limit category concentration without relying on one fixed preset.
    chosen=[];counts={}
    for row in ranked:
        category=BY_ID[row['id']].category
        if counts.get(category,0)>=3:continue
        chosen.append(row);counts[category]=counts.get(category,0)+1
        if len(chosen)>=limit:break
    return chosen


def apply_auto(project,report):
    for e in CATALOG:
        s=project.effects.get(e.id)
        if s and not s.locked:s.enabled=False
    for row in report['recommendations']:
        s=project.effects.setdefault(row['id'],Setting())
        if not s.locked:s.enabled=True;s.strength=row['strength']
    return project


def chaos(project,count=None,seed=None):
    rng=np.random.default_rng(project.seed if seed is None else seed)
    if seed is not None:project.seed=int(seed)
    for s in project.effects.values():
        if not s.locked:s.enabled=False
    available=[e for e in CATALOG if not e.asset and not project.effects.get(e.id,Setting()).locked]
    if count is None:count=int(rng.integers(5,22))
    if count<0:raise ValueError('Chaos count cannot be negative')
    for index in rng.choice(len(available),min(count,len(available)),replace=False):
        e=available[int(index)];s=project.effects.setdefault(e.id,Setting())
        s.enabled=True;s.strength=float(rng.uniform(.2,.95))
    return project


def select_all(project):
    for e in CATALOG:project.set(e.id,True)
    return project

PRESETS={
 'tape':['chroma_bleed','chroma_delay','tracking','head_switch','tape_dropout','wow','flutter','hiss'],
 'film':['film_grain','dust','scratches','gate_weave','bloom','polaroid'],
 'microcassette':['phone','wow','tape_saturation','hiss','print_through'],
 'damaged_stream':['compression','packet_loss','concealment','voip'],
}

def apply_preset(project,name):
    for s in project.effects.values():
        if not s.locked:s.enabled=False
    for key in PRESETS[name]:
        s=project.effects.setdefault(key,Setting())
        if not s.locked:s.enabled=True
    return project
