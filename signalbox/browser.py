"""Browser adapters for the same catalog, frame engine, DSP and adaptive scorer.
No subprocesses, paths supplied by a webpage, or arbitrary Python execution API.
FFmpeg work is scheduled by the local WebAssembly orchestrator.
"""
import json, math
from dataclasses import asdict
import numpy as np
from scipy.signal import fftconvolve,butter,sosfilt
from .model import Project,Setting
from .catalog import CATALOG,BY_ID
from .frame import FrameEngine
from .audio import synth,RATE
from .filters import video_filter,audio_filter
from .analysis import recommend
from .render import VIDEO_ENCODERS,AUDIO_CODECS

_engine=None
_project=None
_audio=None
_stats=None


def configure(project_json,info_json):
    global _project,_engine
    _project=Project.from_dict(json.loads(project_json));info=json.loads(info_json)
    w,h,fps=info['width'],info['height'],info['fps']
    frame=[(e,s) for e,s in _project.enabled() if e.kind=='frame' or e.recipe=='databend']
    _engine=FrameEngine(frame,w,h,fps,_project.seed)
    selected=[]
    for e,s in _project.enabled():
        if not s.strength:continue
        item=asdict(e);item['setting']=asdict(s)
        if e.kind=='vf':item['filter']=video_filter(e.recipe,s,w,h,fps)
        if e.kind=='af' and e.recipe!='audio_reverse':item['filter']=audio_filter(e.recipe,s)
        if e.kind=='vcodec':item['encoder']=VIDEO_ENCODERS[e.recipe]
        if e.kind=='acodec':item['codec']=AUDIO_CODECS[e.recipe]
        selected.append(item)
    return json.dumps(selected)


def process_frames(data,meta_json):
    meta=json.loads(meta_json);w,h=_engine.w,_engine.h
    raw=np.frombuffer(data,dtype=np.uint8).reshape(-1,h,w,3)
    out=np.empty_like(raw)
    for i,frame in enumerate(raw):
        t=meta['start']+i/_engine.fps
        out[i]=_engine.process(frame,round(t*_engine.fps),t)
    return out.tobytes()


def composite_asset(data,asset_data,meta_json):
    meta=json.loads(meta_json);e=BY_ID[meta['id']];s=_project.effects[e.id]
    w,h,fps=_engine.w,_engine.h,_engine.fps
    raw=np.frombuffer(data,np.uint8).reshape(-1,h,w,3).copy()
    assets=np.frombuffer(asset_data,np.uint8).reshape(-1,h,w,3)
    if not len(assets):raise ValueError('Asset produced no frames: '+e.name)
    for i in range(len(raw)):
        t=meta['start']+i/fps
        if t<s.start or (s.end is not None and t>=s.end):continue
        if e.recipe=='single' and abs(t-s.start)>=1/fps:continue
        index=max(0,round((t-meta['asset_origin'])*fps))%len(assets)
        asset=assets[index].astype(np.float32)/255;f=raw[i].astype(np.float32)/255
        if e.recipe in ('replace','single'):f=asset
        elif e.recipe=='rivalry':
            mix=(.5+.5*np.sin((t-s.start)*2))*s.strength;f=f*(1-mix)+asset*mix
        else:
            x,y,rw,rh=s.roi;x0=int(x*w);x1=max(x0+1,int((x+rw)*w));y0=int(y*h);y1=max(y0+1,int((y+rh)*h))
            ys=np.linspace(0,h-1,y1-y0).astype(int);xs=np.linspace(0,w-1,x1-x0).astype(int)
            patch=asset[ys[:,None],xs[None,:]];base=f[y0:y1,x0:x1]
            alpha=np.mean(patch,axis=2,keepdims=True)*s.strength*.5
            if e.recipe=='shadow':alpha*=1-np.mean(base,axis=2,keepdims=True)
            f[y0:y1,x0:x1]=base*(1-alpha)+patch*alpha
        raw[i]=np.clip(f*255,0,255).astype(np.uint8)
    return raw.tobytes()


def begin_audio(data):
    global _audio
    _audio=np.frombuffer(data,dtype='<f4').reshape(-1,2).copy()
    return len(_audio)


def audio_effect(effect_id,offset=0,asset_data=None):
    global _audio
    import hashlib
    e=BY_ID[effect_id];s=_project.effects[effect_id];data=_audio
    out=np.empty_like(data);asset=None
    if asset_data is not None:asset=np.frombuffer(asset_data,'<f4').reshape(-1,2)
    salt=int.from_bytes(hashlib.blake2s(e.id.encode(),digest_size=4).digest(),'little')
    for start in range(0,len(data),RATE*4):
        end=min(len(data),start+RATE*4);idx=np.arange(start,end);t=idx/RATE+offset
        f=data[start:end].copy();active=(t>=s.start)&((t<s.end) if s.end is not None else True)
        if e.recipe=='audio_reverse':g=data[len(data)-end:len(data)-start][::-1]
        elif e.kind=='asset_audio':
            if asset is None or not len(asset):raise ValueError('Audio asset is empty: '+e.name)
            if e.recipe=='impulse':
                ir=asset[:RATE*10];ir=ir/max(1,float(np.sum(np.abs(ir),axis=0).max()))
                lo=max(0,start-len(ir)+1);chunk=data[lo:end];skip=start-lo
                g=np.stack([fftconvolve(chunk[:,c],ir[:,c],mode='full')[skip:skip+len(idx)] for c in range(2)],axis=1)
                g=f*(1-s.strength)+g*s.strength
            else:
                local=((t-s.start)*RATE).astype(np.int64);pos=local%len(asset)
                if e.recipe=='whisper':pos=len(asset)-1-pos
                carrier=asset[pos].copy()
                if e.recipe=='event':g=carrier*(local<len(asset))[:,None]*s.strength
                elif e.recipe=='vocoder':
                    lo=max(0,start-RATE//4);context=data[lo:end];shift=start-lo
                    cp=((np.arange(lo,end)/RATE+offset-s.start)*RATE).astype(np.int64)%len(asset)
                    cc=asset[cp];v=np.zeros_like(context)
                    for low,high in zip(np.geomspace(100,8000,17)[:-1],np.geomspace(100,8000,17)[1:]):
                        band=butter(2,[low,high],btype='bandpass',fs=RATE,output='sos')
                        speech=sosfilt(band,context,axis=0);car=sosfilt(band,cc,axis=0)
                        env=sosfilt(butter(1,30,fs=RATE,output='sos'),np.abs(speech),axis=0)
                        v+=car*env*12
                    g=f*(1-s.strength)+v[shift:]*s.strength
                else:g=f+carrier*s.strength*(.08 if e.recipe=='whisper' else .2)
        else:g=synth(e.recipe,data,idx,s,_project.seed+salt)
        f[active]=g[active];out[start:end]=np.nan_to_num(f,nan=0,posinf=1,neginf=-1).clip(-4,4)
    _audio=out
    return len(out)


def finish_audio():
    global _audio
    value=_audio.astype('<f4').tobytes();_audio=None;return value


class Analysis:
    def __init__(self,info):
        self.info=info;self.hist=np.zeros(256,np.int64);self.sums=np.zeros(8);self.frames=0
        self.previous=None;self.last_mean=None;self.cuts=[];self.scenes=0;self.max_motion=0
        self.sq=self.peak=self.silent=self.count=self.centroid=self.high=self.low=self.windows=0
        self.cross=self.left2=self.right2=0
    def pictures(self,data,start):
        raw=np.frombuffer(data,np.uint8).reshape(-1,96,160,3)
        for i,item in enumerate(raw):
            f=item.astype(np.float32)/255;y=f[:,:,0]*.299+f[:,:,1]*.587+f[:,:,2]*.114
            self.hist+=np.bincount(np.minimum(255,(y*255).astype(np.int32)).ravel(),minlength=256)
            mean=float(y.mean());contrast=float(y.std());edges=(np.mean(np.abs(np.diff(y,axis=0)))+np.mean(np.abs(np.diff(y,axis=1))))/2
            chroma=float((f.max(axis=2)-f.min(axis=2)).mean())
            lap=4*y[1:-1,1:-1]-y[:-2,1:-1]-y[2:,1:-1]-y[1:-1,:-2]-y[1:-1,2:]
            noise=float(np.median(abs(lap)))/4;motion=float(np.mean(abs(y-self.previous))) if self.previous is not None else 0
            flicker=abs(mean-self.last_mean) if self.last_mean is not None else 0
            self.sums+=[mean,contrast,edges,chroma,noise,motion,flicker,float(np.mean((y<.025)|(y>.975)))]
            if motion>.15:
                self.scenes+=1;self.cuts.append({'time':round(start+i/self.info['fps'],3),'change':round(motion,4)})
                self.cuts=sorted(self.cuts,key=lambda x:x['change'],reverse=True)[:24]
            self.max_motion=max(self.max_motion,motion);self.previous=y;self.last_mean=mean;self.frames+=1
    def sound(self,data):
        raw=np.frombuffer(data,'<f4').reshape(-1,2)
        for start in range(0,len(raw),16000):
            f=np.nan_to_num(raw[start:start+16000]);n=len(f)
            if not n:continue
            self.sq+=float(np.sum(f.astype(np.float64)**2));self.peak=max(self.peak,float(abs(f).max()))
            self.silent+=int(np.sum(np.max(abs(f),axis=1)<.003));self.count+=n
            self.cross+=float(np.sum(f[:,0]*f[:,1]));self.left2+=float(np.sum(f[:,0]**2));self.right2+=float(np.sum(f[:,1]**2))
            spec=abs(np.fft.rfft(f.mean(axis=1)*np.hanning(n)))**2;freq=np.fft.rfftfreq(n,1/16000);energy=max(1e-15,float(spec.sum()))
            self.centroid+=float(np.sum(freq*spec)/energy);self.high+=float(spec[freq>4000].sum()/energy);self.low+=float(spec[freq<250].sum()/energy);self.windows+=1
    def result(self):
        if not self.frames:raise ValueError('No video frames decoded')
        metrics=dict(zip(['luma','contrast','detail','saturation','noise_proxy','motion','flicker','clipped_fraction'],(self.sums/self.frames).tolist()))
        metrics.update(dark_fraction=float(self.hist[:45].sum()/self.hist.sum()),bright_fraction=float(self.hist[210:].sum()/self.hist.sum()),
                       max_motion=self.max_motion,cuts_per_minute=self.scenes/max(.001,self.info['duration']/60))
        audio={'present':self.info['audio'],'samples':self.count,'rms':math.sqrt(self.sq/max(1,self.count*2)),'peak':self.peak,
               'silence_fraction':self.silent/max(1,self.count),'spectral_centroid':self.centroid/max(1,self.windows),
               'high_band':self.high/max(1,self.windows),'low_band':self.low/max(1,self.windows),
               'stereo_correlation':self.cross/max(1e-12,math.sqrt(self.left2*self.right2))}
        report={**self.info,'schema':1,'frames_examined':self.frames,'metrics':metrics,'audio':audio,
                'interesting_times':sorted(self.cuts,key=lambda x:x['time']),
                'method':'Full-duration chunked decode, every decoded frame at 160x96 and all audio at 16 kHz. Cut times approximate for VFR. Explained multivariate heuristics.'}
        report['recommendations']=recommend(report);return json.dumps(report)


def analysis_begin(info_json):
    global _stats
    _stats=Analysis(json.loads(info_json))

def analysis_frames(data,start):_stats.pictures(data,start)
def analysis_audio(data):_stats.sound(data)
def analysis_finish():return _stats.result()
