"""Chunked, disk-backed audio DSP; no whole-track arrays in RAM."""
from pathlib import Path
import hashlib
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from .media import ffmpeg

RATE=48000


def noise(seed,idx):
    # Counter-based deterministic pseudo-noise, stable across chunk boundaries.
    x=np.asarray(idx,dtype=np.uint64)+np.uint64(seed%2**32)
    x=(x^(x>>np.uint64(16)))*np.uint64(0x45d9f3b)
    x=(x^(x>>np.uint64(16)))*np.uint64(0x45d9f3b)
    return ((x & np.uint64(0xffffff)).astype(np.float32)/(0xffffff)*2-1)


def fetch(data,index):
    if len(data)==0:return np.zeros((len(index),2),np.float32)
    base=np.floor(index).astype(np.int64)
    mix=(index-base).astype(np.float32)[:,None]
    return data[base.clip(0,len(data)-1)]*(1-mix)+data[(base+1).clip(0,len(data)-1)]*mix


def synth(k, data, idx, s, seed):
    a=s.strength;t=idx/RATE;f=np.asarray(data[idx.clip(0,len(data)-1)],dtype=np.float32).copy()
    wave=lambda hz:np.sin(2*np.pi*hz*t)
    add=lambda v,g=.03:f+np.asarray(v)[:,None]*g*a
    if k in ('hiss','breathing'):
        v=noise(seed,idx)
        if k=='breathing':v*=np.maximum(0,np.sin(t*1.4))**2
        return add(v,.035)
    if k in ('hum','hum60'):
        hz=50 if k=='hum' else 60
        return add(wave(hz)+.3*wave(hz*3)+.15*wave(hz*5),.035)
    if k=='rf_buzz':return add(np.sign(wave(217))*(wave(1200)+.4*wave(2400)),.02)
    if k=='whine':return add(np.sin(2*np.pi*(3700*t+30*np.sin(t*.4))),.018)
    if k=='crackle':
        events=noise(seed,idx//1200)>.96
        envelope=np.exp(-(idx%1200)/35)
        return add(noise(seed+17,idx)*envelope*events,.4)
    if k in ('audio_dropout','dead_air'):
        period=5 if k=='audio_dropout' else 9
        phase=t%period;length=.08+.5*a if k=='audio_dropout' else 1+4*a
        env=np.clip((phase-length)*300,0,1)
        return f*env[:,None]
    if k in ('underrun','voip','locked_groove','groove_skip','granular'):
        if k=='voip':
            packet=(idx//960);loss=noise(seed,packet)>(1-a*.6)
            mapped=idx-loss.astype(np.int64)*960
        elif k=='locked_groove':mapped=np.floor(t/4)*4*RATE+(idx%24000)
        elif k=='groove_skip':mapped=idx-np.where(t%5>4,int((.2+a*.6)*RATE),0)
        elif k=='underrun':mapped=np.where(t%3<.3+a,idx//(RATE*3)*(RATE*3)+idx%2400,idx)
        else:
            grain=2400;block=idx//grain
            mapped=idx+(np.floor(noise(seed,block)*4)*grain)
        g=fetch(data,mapped)
        if k=='granular':g*=np.sin(np.pi*(idx%2400)/2400)[:,None]**2
        return g
    if k in ('wow','flutter','clock_jitter','tape_stretch','diplacusis'):
        delay=(80*np.sin(2*np.pi*.7*t)+40*np.sin(2*np.pi*.317*t)+20*np.sin(2*np.pi*1.13*t))*a
        if k=='flutter':delay=(9*np.sin(2*np.pi*8.7*t)+4*np.sin(2*np.pi*13.1*t))*a
        if k=='clock_jitter':delay=(2*noise(seed,idx//128)+10*np.sin(t*.2))*a
        if k=='tape_stretch':delay=2000*a*np.maximum(0,np.sin(t*.7))**3
        out=fetch(data,idx-delay)
        if k=='diplacusis':out[:,1]=fetch(data,idx+delay)[:,1]
        return out
    if k=='sticky_shed':return add(np.sin(2*np.pi*(1800*t+150*np.sin(t*2)))*(t%7<1),.06)
    if k=='print_through':
        advance=idx+int(.7*RATE)
        early=fetch(data,advance)*(advance<len(data))[:,None]
        return f+early*(.05+.15*a)
    if k=='ring_mod':return f*wave(35+250*a)[:,None]
    if k=='shepard':
        v=np.zeros(len(t));phase=(t%12)/12
        for octave in range(6):
            hz=55*2**(octave+phase);env=np.exp(-((np.log2(hz/700))/2)**2)
            # Integral of the exponential frequency sweep.
            v+=np.sin(2*np.pi*55*2**octave*12/np.log(2)*(2**phase-1))*env
        return add(v,.012)
    if k=='missing_fundamental':return add(sum(wave(110*j)/j for j in range(2,8)),.06)
    tones={'tinnitus':6000,'flyback':15700,'infrasound':19,'mosquito':17000,'test_tone':1000}
    if k in tones:return add(wave(tones[k]),.018)
    if k=='alert_tone':return add((wave(853)+wave(960))*(t%8<2),.025)
    if k=='dtmf':
        digits=(t.astype(int)%12);lo=np.array([697,770,852,941])[digits//3];hi=np.array([1209,1336,1477])[digits%3]
        return add((np.sin(2*np.pi*lo*t)+np.sin(2*np.pi*hi*t))*(t%1<.3),.025)
    if k=='uvb76':return add(np.sign(wave(462))*(t%1.2<.8),.025)
    if k=='duga':return add(noise(seed,idx)*np.exp(-(t%.1)*250),.09)
    if k=='pirate':return f*(.7+.3*np.sin(t*.6))[:,None]+np.sin(2*np.pi*(1200*t+50*np.sin(t*.2)))[:,None]*a*.015
    if k=='heartbeat':
        p=t%.85;v=np.exp(-p*25)*np.sin(p*2*np.pi*65)+.6*np.exp(-np.maximum(0,p-.16)*30)*np.sin((p-.16)*2*np.pi*55)*(p>.16)
        return add(v,.12)
    if k=='auditory_exclusion':return f*(1-a*.8)+wave(6500)[:,None]*a*.015
    if k=='hyperacusis':return np.tanh(f*(1+a*5))*.8
    if k=='sidechain':return f*(1-a*np.exp(-(t%.5)*10))[:,None]
    if k=='wrong_audio_format':
        q=np.clip(f*32767,-32768,32767).astype('<i2');return q.byteswap().astype(np.float32)/32768*.25
    if k=='wrong_interleave':return f.reshape(-1).reshape(2,-1).T
    if k=='power_click':return add((wave(80)+noise(seed,idx)*.2)*np.exp(-np.maximum(0,t-s.start)*60),.2)
    raise ValueError(f'Unimplemented audio operation {k}')


def process_audio(source, destination, effects, job, seed=1967, offset=0, assets=None):
    """Run effects in series using alternating PCM files, bounded 4 s buffers."""
    source=Path(source);destination=Path(destination);assets=assets or {}
    current=source
    for number,(e,s) in enumerate(effects):
        job.check();job.emit('Audio: '+e.name,number/max(1,len(effects)))
        data=np.memmap(current,dtype='<f4',mode='r').reshape(-1,2)
        out_path=destination.with_name(f'audio-dsp-{number%2}.f32')
        if out_path==current:out_path=destination.with_name('audio-dsp-other.f32')
        salt=int.from_bytes(hashlib.blake2s(e.id.encode(),digest_size=4).digest(),'little')
        asset=None
        if e.kind=='asset_audio':
            asset=np.memmap(assets[e.id],dtype='<f4',mode='r').reshape(-1,2)
        with out_path.open('wb') as out:
            for start in range(0,len(data),RATE*4):
                job.check();end=min(len(data),start+RATE*4);idx=np.arange(start,end);t=idx/RATE+offset
                f=np.array(data[start:end],copy=True)
                active=(t>=s.start)&((t<s.end) if s.end is not None else True)
                if e.recipe=='audio_reverse':g=np.asarray(data[len(data)-end:len(data)-start][::-1])
                elif e.kind=='asset_audio':
                    if e.recipe=='impulse':
                        ir=np.asarray(asset[:RATE*10]);norm=max(1,float(np.sum(np.abs(ir),axis=0).max()));ir=ir/norm
                        lo=max(0,start-len(ir)+1);chunk=np.asarray(data[lo:end]);skip=start-lo
                        g=np.stack([fftconvolve(chunk[:,c],ir[:,c],mode='full')[skip:skip+len(idx)] for c in range(2)],axis=1)
                        g=f*(1-s.strength)+g*s.strength
                    else:
                        local=((t-s.start)*RATE).astype(np.int64)
                        pos=local%max(1,len(asset))
                        if e.recipe=='whisper':pos=len(asset)-1-pos
                        carrier=np.asarray(asset[pos]).copy()
                        if e.recipe=='event':g=carrier*(local<len(asset))[:,None]*s.strength
                        elif e.recipe=='vocoder':
                            # Context keeps filter transients out of most chunk boundaries.
                            lo=max(0,start-RATE//4);context=np.asarray(data[lo:end]);shift=start-lo
                            cp=((np.arange(lo,end)/RATE+offset-s.start)*RATE).astype(np.int64)%len(asset)
                            cc=np.asarray(asset[cp]);v=np.zeros_like(context)
                            for low,high in zip(np.geomspace(100,8000,17)[:-1],np.geomspace(100,8000,17)[1:]):
                                band=butter(2,[low,high],btype='bandpass',fs=RATE,output='sos')
                                speech=sosfilt(band,context,axis=0);car=sosfilt(band,cc,axis=0)
                                env=sosfilt(butter(1,30,fs=RATE,output='sos'),np.abs(speech),axis=0)
                                v+=car*env*12
                            g=f*(1-s.strength)+v[shift:]*s.strength
                        else:g=f+carrier*s.strength*(.08 if e.recipe=='whisper' else .2)
                else:g=synth(e.recipe,data,idx,s,seed+salt)
                f[active]=g[active]
                f=np.nan_to_num(f,nan=0,posinf=1,neginf=-1).clip(-4,4)
                out.write(f.astype('<f4').tobytes())
        del data
        if asset is not None:del asset
        current=out_path
    if current!=destination:
        import shutil
        shutil.copyfile(current,destination)
    return destination
