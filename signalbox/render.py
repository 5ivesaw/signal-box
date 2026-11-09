from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import copy
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import numpy as np
from .media import Job, probe, capabilities, ffmpeg, local_file, read_exact
from .filters import video_filter, audio_filter
from .frame import FrameEngine
from .audio import process_audio, RATE
from .model import Project

VIDEO_ENCODERS={'h264':'libx264','dark_mud':'libx264','generations':'libx264','platform':'mpeg4',
 'mpeg4':'mpeg4','flv':'flv','cinepak':'cinepak','h263':'h263','gif':'gif',
 'datamosh':'mpeg4','packet_loss':'mpeg4','bit_rot':'mpeg4','bad_sectors':'mpeg4','databend':'libx264'}
AUDIO_CODECS={'aac':('aac','m4a',48000,2),'mp3':('libmp3lame','mp3',48000,2),
 'joint_stereo':('libmp3lame','mp3',48000,2),'opus':('libopus','opus',48000,2),
 'gsm':('libgsm','gsm',8000,1),'mulaw':('pcm_mulaw','wav',8000,1),
 'codec2':('libcodec2','c2',8000,1),'sbc':('sbc','sbc',48000,2),
 'generations':('libmp3lame','mp3',48000,2)}


def dimensions(info,p):
    w,h=info['width'],info['height']
    v=next(x for x in info['streams'] if x['index']==info['video_index'])
    sar=v.get('sample_aspect_ratio','1:1')
    try:
        x,y=map(float,sar.split(':'));w*=x/y if y else 1
    except ValueError:pass
    rotation=next((x.get('rotation',0) for x in v.get('side_data_list',[]) if 'rotation' in x),0)
    if abs(rotation)%180==90:w,h=h,w
    ow=max(2,int((p.width or w)/2)*2)
    oh=max(2,int(h/w*ow/2)*2)
    return ow,oh,p.fps or min(info['fps'],120)


def preflight(p, info=None):
    p.validate();info=info or probe(p.source)
    if not info['video']:raise ValueError('The source must contain video')
    if not math.isfinite(info['duration']) or info['duration']<=0:raise ValueError('A finite-duration video is required')
    caps=capabilities();errors=[];warnings=[]
    if 'libx264' not in caps['encoders']:errors.append('FFmpeg needs the libx264 encoder')
    if 'aac' not in caps['encoders']:errors.append('FFmpeg needs the AAC encoder')
    w,h,fps=dimensions(info,p)
    for e,s in p.enabled():
        if s.strength==0:continue
        if e.asset:
            if not s.asset:errors.append(f'{e.id}: supply {e.asset} asset (Edit effect), or disable it')
            else:
                try:
                    ai=probe(s.asset)
                    if not ai.get(e.asset):errors.append(f'{e.id}: asset has no {e.asset} stream')
                except Exception as ex:errors.append(f'{e.id}: {ex}')
        if (s.start>0 or s.end is not None) and e.kind in ('vf','af','vcodec','acodec','meta'):
            errors.append(f'{e.id}: this whole-stream stage cannot have a time window; use frame/DSP/asset effects for windows')
        if e.kind=='vf':
            names=re.findall(r'(?:^|,)([a-z0-9_]+)=',video_filter(e.recipe,s,w,h,fps))
            for name in names:
                if name not in caps['filters']:errors.append(f'{e.id}: FFmpeg filter {name} unavailable')
        if e.kind=='af' and e.recipe!='audio_reverse':
            for name in re.findall(r'(?:^|,)([a-z0-9_]+)=',audio_filter(e.recipe,s)):
                if name not in caps['filters']:errors.append(f'{e.id}: FFmpeg filter {name} unavailable')
        if e.kind=='vcodec' and VIDEO_ENCODERS[e.recipe] not in caps['encoders']:
            errors.append(f'{e.id}: encoder {VIDEO_ENCODERS[e.recipe]} unavailable')
        if e.kind=='acodec' and AUDIO_CODECS[e.recipe][0] not in caps['encoders']:
            errors.append(f'{e.id}: encoder {AUDIO_CODECS[e.recipe][0]} unavailable')
        if e.recipe in ('datamosh','packet_loss','bit_rot') and 'noise' not in caps['bsfs']:
            errors.append(f'{e.id}: FFmpeg noise bitstream filter unavailable')
        if e.cost=='heavy' or e.id in ('error_dither','pixel_sort'):
            warnings.append(f'{e.name}: potentially much slower than real time; benchmark a preview')
        if e.id in ('datamosh','bit_rot','bad_sectors','packet_loss'):
            warnings.append(f'{e.name}: recovery depends on decoder and source; damaged intermediate may not decode')
    if not info['audio'] and any(e.kind in ('af','audio','acodec','asset_audio') for e,s in p.enabled()):
        warnings.append('Source has no audio: selected audio effects will process an explicit silent stereo bed')
    if len(p.enabled())>40:warnings.append('Large stack: many effects can mask or overwhelm earlier effects; every enabled stage is still run')
    # 128 MiB history, working float rasters, plus FFmpeg and audio/convolution overhead.
    memory_mb=256+w*h*4*3*12/1024**2
    seconds=info['duration'];disk_mb=seconds*(w*h*fps*.03+RATE*8*4)/1024**2
    if w*h>1920*1080:warnings.append('Large working raster: use a smaller width on an 8 GB laptop')
    return {'errors':errors,'warnings':warnings,'width':w,'height':h,'fps':fps,
            'estimated_memory_mb':round(memory_mb),'scratch_estimate_mb':round(disk_mb),
            'note':'Resource estimates are rough, not measured speed promises. Asset convolution and codecs add cost.'}


class AssetReader:
    def __init__(self,path,w,h,fps,start,job,log):
        self.job=job;self.w=w;self.h=h
        self.p=job.spawn(ffmpeg()+['-stream_loop','-1','-ss',str(max(0,start)),'-i',str(local_file(path)),
             '-an','-vf',f'scale={w}:{h},fps={fps},setsar=1','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],stdout=subprocess.PIPE,stderr=log)
    def read(self):
        b=read_exact(self.p.stdout,self.w*self.h*3)
        if len(b)!=self.w*self.h*3:raise RuntimeError('Asset video decoder ended early')
        return np.frombuffer(b,np.uint8).reshape(self.h,self.w,3).astype(np.float32)/255
    def close(self):self.job.reap(self.p);self.p.stdout.close()


def video_stage(p,info,out,job,start,duration,w,h,fps,work):
    frame_effects=[(e,s) for e,s in p.enabled() if e.kind=='frame' or e.recipe=='databend']
    engine=FrameEngine(frame_effects,w,h,fps,p.seed)
    vf=[video_filter(e.recipe,s,w,h,fps) for e,s in p.enabled() if e.kind=='vf' and s.strength>0]
    # PTS remains relative to the rendered interval. Frame and asset windows use absolute source time.
    args=ffmpeg(p.threads)+['-ss',str(start),'-i',info['path'],'-t',str(duration),'-map',f'0:{info["video_index"]}','-an',
          '-vf',f'scale={w}:{h}:flags=bicubic,fps={fps},setsar=1','-pix_fmt','rgb24','-f','rawvideo','pipe:1']
    enc=ffmpeg(p.threads)+['-f','rawvideo','-pixel_format','rgb24','-video_size',f'{w}x{h}','-framerate',str(fps),'-i','pipe:0']
    if vf:enc+=['-vf',','.join(vf)+f',setpts=PTS-STARTPTS,fps={fps},tpad=stop_mode=clone:stop_duration=2','-t',str(duration)]
    enc+=['-an','-c:v','libx264','-preset','veryfast','-crf',str(p.crf),'-threads',str(p.threads),'-pix_fmt','yuv420p',str(out)]
    readers={};frames=0
    with (work/'decode.log').open('wb+') as dl,(work/'encode.log').open('wb+') as el,(work/'assets.log').open('wb+') as al:
        decoder=job.spawn(args,stdout=subprocess.PIPE,stderr=dl)
        encoder=None
        try:
            encoder=job.spawn(enc,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=el)
            while True:
                job.check();b=read_exact(decoder.stdout,w*h*3)
                if not b:break
                if len(b)!=w*h*3:raise RuntimeError('Truncated raw video frame')
                t=start+frames/fps;n=round(t*fps)
                raw=np.frombuffer(b,np.uint8).reshape(h,w,3)
                if frame_effects:raw=engine.process(raw,n,t)
                for e,s in p.enabled():
                    if e.kind!='asset_video' or not s.strength or t<s.start or (s.end is not None and t>=s.end):continue
                    if e.recipe=='single' and abs(t-s.start)>=1/fps:continue
                    if e.id not in readers:readers[e.id]=AssetReader(s.asset,w,h,fps,t-s.start,job,al)
                    asset=readers[e.id].read();f=raw.astype(np.float32)/255
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
                    raw=np.clip(f*255,0,255).astype(np.uint8)
                encoder.stdin.write(raw.tobytes());frames+=1
                if frames%max(1,int(fps/2))==0:job.emit('Picture processing',min(1,frames/(fps*duration)),frames=frames)
            encoder.stdin.close();decoder.wait();encoder.wait();job.check()
            if decoder.returncode or encoder.returncode:
                dl.seek(0);el.seek(0)
                raise RuntimeError('Video stage failed:\n'+(dl.read()+el.read()).decode(errors='replace')[-5000:])
            if not frames:raise RuntimeError('No video frames decoded')
        except BrokenPipeError:
            el.seek(0);raise RuntimeError('Video encoder stopped:\n'+el.read().decode(errors='replace')[-5000:]) from None
        finally:
            for reader in readers.values():reader.close()
            job.reap(decoder);decoder.stdout.close()
            if encoder is not None:
                job.reap(encoder)
                if encoder.stdin and not encoder.stdin.closed:encoder.stdin.close()
    return frames


def codec_video(current,e,s,index,p,work,job,w,h,fps,duration):
    k=e.recipe;a=s.strength
    if k=='databend':return current
    passes=max(2,int(2+3*a)) if k=='generations' else 3 if k=='platform' else 1
    for turn in range(passes):
        codec=VIDEO_ENCODERS[k]
        if k=='platform':codec='mpeg4' if turn%2==0 else 'libx264'
        suffix='gif' if codec=='gif' else 'mkv' if codec=='libx264' else 'avi'
        raw=work/f'codec-{index}-{turn}.{suffix}'
        args=ffmpeg(p.threads)+['-i',str(current),'-an','-c:v',codec,'-threads',str(p.threads)]
        vf=[]
        if codec=='libx264':args+=['-preset','veryfast','-crf',str(round(30+18*a))]
        elif codec in ('mpeg4','flv','h263'):args+=['-q:v',str(round(6+23*a))]
        if k=='dark_mud':vf+=['eq=brightness=-.08:contrast=1.3']
        if codec=='cinepak':vf+=['scale=320:240'];args+=['-q:v','20']
        if codec=='h263':vf+=['scale=352:288']
        if codec=='gif':vf+=['scale=320:-2','fps=12']
        if k in ('datamosh','packet_loss','bit_rot','bad_sectors'):
            args+=['-g',str(max(2,int(fps))),'-bf','0']
        if vf:args+=['-vf',','.join(vf)]
        job.run(args+[str(raw)],'Codec: '+e.name)
        damaged=raw
        if k in ('datamosh','packet_loss','bit_rot'):
            damaged=work/f'damaged-{index}.avi'
            if k=='datamosh':bsf="noise=amount=0:drop='key*gt(n,0)'"
            elif k=='packet_loss':bsf=f"noise=amount=0:drop='not(key)*eq(mod(n,{max(3,int(15-10*a))}),0)'"
            else:bsf=f'noise=amount={int(8000-6500*a)}'
            job.run(ffmpeg(p.threads)+['-i',str(raw),'-c','copy','-bsf:v',bsf,str(damaged)],'Damage: '+e.name)
        if k=='bad_sectors':
            # MPEG-4 VOP bytes in a disposable AVI copy; preserve container headers.
            damaged=work/f'damaged-{index}.avi';shutil.copyfile(raw,damaged)
            packet_info=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_packets','-show_entries','packet=pos,size,flags','-of','json',str(raw)],capture_output=True,text=True,check=True)
            packets=json.loads(packet_info.stdout)['packets']
            with damaged.open('r+b') as handle:
                for j,packet in enumerate(packets):
                    if j%7==4 and 'K' not in packet.get('flags',''):
                        size=int(packet['size']);count=min(int(10+60*a),max(0,size-64))
                        if count:handle.seek(int(packet['pos'])+32);handle.write(bytes(count))
        recovered=work/f'recovered-{index}-{turn}.mkv'
        job.run(ffmpeg(p.threads)+['-err_detect','ignore_err','-i',str(damaged),'-an','-vf',
             f'scale={w}:{h},fps={fps},tpad=stop_mode=clone:stop_duration={duration}',
             '-t',str(duration),'-c:v','libx264','-preset','veryfast','-crf','18','-threads',str(p.threads),'-pix_fmt','yuv420p',str(recovered)],'Recover: '+e.name)
        if probe(recovered)['duration']<duration-.25:raise RuntimeError(f'{e.name}: recovery produced too few frames')
        if current.parent==work and current.name.startswith('recovered-'):current.unlink(missing_ok=True)
        raw.unlink(missing_ok=True)
        if damaged!=raw:damaged.unlink(missing_ok=True)
        current=recovered
    return current


def audio_stage(p,info,work,job,start,duration):
    selected=p.enabled();pcm=work/'source.f32'
    if info['audio']:
        args=ffmpeg(p.threads)+['-ss',str(start),'-i',info['path'],'-map','0:a:0']
    else:args=ffmpeg(p.threads)+['-f','lavfi','-i','anullsrc=r=48000:cl=stereo']
    af=[audio_filter(e.recipe,s) for e,s in selected if e.kind=='af' and e.recipe!='audio_reverse' and s.strength>0]
    af+=['aresample=48000','apad']
    args+=['-t',str(duration),'-vn','-af',','.join(af),'-ar','48000','-ac','2','-f','f32le',str(pcm)]
    job.run(args,'Audio filters')
    if pcm.stat().st_size==0:raise RuntimeError('Audio decode produced no samples')
    assets={}
    for e,s in selected:
        if e.kind=='asset_audio' and s.strength:
            path=work/f'asset-{e.id}.f32';assets[e.id]=path
            job.run(ffmpeg(p.threads)+['-i',str(local_file(s.asset)),'-t',str(10 if e.recipe=='impulse' else duration),'-vn','-ar','48000','-ac','2','-f','f32le',str(path)],'Decode asset: '+e.name)
            if not path.stat().st_size:raise RuntimeError(f'Empty audio asset: {e.id}')
    dsp=[(e,s) for e,s in selected if (e.kind in ('audio','asset_audio') or e.recipe=='audio_reverse') and s.strength]
    if dsp:pcm=process_audio(pcm,work/'processed.f32',dsp,job,p.seed,offset=start,assets=assets)
    for i,(e,s) in enumerate(selected):
        if e.kind!='acodec' or not s.strength:continue
        codec,suffix,rate,channels=AUDIO_CODECS[e.recipe]
        for turn in range(3 if e.recipe=='generations' else 1):
            encoded=work/f'audio-{i}-{turn}.{suffix}'
            args=ffmpeg(p.threads)+['-f','f32le','-ar','48000','-ac','2','-i',str(pcm),'-c:a',codec,'-ar',str(rate),'-ac',str(channels)]
            if codec in ('aac','libmp3lame','libopus'):args+=['-b:a',str(int(48000-32000*s.strength))]
            if e.recipe=='joint_stereo':args+=['-joint_stereo','1']
            if codec=='libcodec2':args+=['-mode','3200']
            job.run(args+[str(encoded)],'Audio codec: '+e.name)
            newpcm=work/f'decoded-audio-{i}-{turn}.f32'
            job.run(ffmpeg(p.threads)+['-i',str(encoded),'-ar','48000','-ac','2','-af','apad','-t',str(duration),'-f','f32le',str(newpcm)],'Decode audio: '+e.name)
            if pcm.name.startswith('decoded-audio-'):pcm.unlink(missing_ok=True)
            encoded.unlink(missing_ok=True);pcm=newpcm
    af=['alimiter=limit=.89:level=0:latency=1']
    for e,s in selected:
        if e.recipe=='av_offset':af.append(f'adelay={int(2000*s.strength)}:all=1')
        if e.recipe=='av_drift':af+= [f'asetrate={int(RATE*(1+.03*s.strength))}','aresample=48000']
    audio_duration=duration
    for e,s in selected:
        if e.recipe=='track_mismatch':audio_duration=max(.1,duration*(1-.5*s.strength))
    result=work/'audio.m4a'
    job.run(ffmpeg(p.threads)+['-f','f32le','-ar','48000','-ac','2','-i',str(pcm),'-af',','.join(af),'-t',str(audio_duration),'-c:a','aac','-b:a','160k',str(result)],'Final audio / peak ceiling')
    return result


def render(project:Project, output, *, start=0.,duration=None,job=None,overwrite=False,scratch=None):
    """Public API. Atomic output + reproducible manifest. Never mutates the source."""
    p=copy.deepcopy(project);job=job or Job();info=probe(p.source);report=preflight(p,info)
    if report['errors']:raise ValueError('Preflight failed:\n'+'\n'.join(report['errors']))
    if not math.isfinite(start) or start<0 or start>=info['duration']:raise ValueError('Start must be inside the source')
    duration=info['duration']-start if duration is None else min(duration,info['duration']-start)
    if not math.isfinite(duration) or duration<=0:raise ValueError('Duration must be positive')
    output=Path(output).expanduser().resolve()
    if output.suffix.lower() not in ('.mp4','.mkv'):raise ValueError('Output must end in .mp4 or .mkv')
    source=Path(info['path'])
    protected={source}|{Path(s.asset).expanduser().resolve() for e,s in p.enabled() if s.asset}
    if output in protected:raise ValueError('Output cannot replace a source or asset')
    if output.exists() and not overwrite:raise FileExistsError(f'Output exists: {output}; choose a new name or --overwrite')
    output.parent.mkdir(parents=True,exist_ok=True)
    manifest_path=output.with_suffix(output.suffix+'.signalbox.json')
    if manifest_path.exists() and not overwrite:raise FileExistsError(f'Manifest exists: {manifest_path}')
    if scratch:Path(scratch).mkdir(parents=True,exist_ok=True)
    free=shutil.disk_usage(scratch or tempfile.gettempdir()).free
    estimated=report['scratch_estimate_mb']*1024**2*duration/info['duration']
    if free<max(32*1024**2,estimated):raise ValueError('Insufficient scratch disk space for estimated intermediates; choose --scratch on a larger disk')
    job.emit('Preflight complete',0,warnings=report['warnings'],resources=report)
    fd,tempname=tempfile.mkstemp(prefix='.signalbox-',suffix=output.suffix,dir=output.parent);os.close(fd)
    stageout=Path(tempname)
    try:
        with tempfile.TemporaryDirectory(prefix='signalbox-',dir=scratch) as temp:
            work=Path(temp);w,h,fps=report['width'],report['height'],report['fps']
            current=work/'picture.mkv';frames=video_stage(p,info,current,job,start,duration,w,h,fps,work)
            actual_duration=frames/fps
            for i,(e,s) in enumerate(p.enabled()):
                if e.kind=='vcodec' and s.strength:current=codec_video(current,e,s,i,p,work,job,w,h,fps,actual_duration)
            has_audio=info['audio'] or any(e.kind in ('audio','af','acodec','asset_audio') for e,s in p.enabled())
            audio=audio_stage(p,info,work,job,start,actual_duration) if has_audio else None
            args=ffmpeg(p.threads)+['-i',str(current)]
            if audio:args+=['-i',str(audio),'-map','0:v:0','-map','1:a:0']
            else:args+=['-map','0:v:0']
            args+=['-c','copy','-map_metadata','-1']
            for e,s in p.enabled():
                if e.recipe=='aspect_flag' and s.strength:args+=['-aspect',str((w/h)*(.6+s.strength))]
            if output.suffix.lower()=='.mp4':args+=['-movflags','+faststart']
            job.run(args+[str(stageout)],'Mux final output')
            final_info=probe(stageout)
            if not final_info['video'] or final_info['duration']<=0:raise RuntimeError('Final validation failed')
            job.check()
            # No-clobber publication is atomic even if another job created the target meanwhile.
            if overwrite:os.replace(stageout,output)
            else:os.link(stageout,output);stageout.unlink()
            manifest={'application':'Signalbox','version':'0.1.0','project':p.to_dict(),
                'source_stat':{'size':source.stat().st_size,'mtime_ns':source.stat().st_mtime_ns},
                'interval':{'start':start,'duration':duration},'output':str(output),'preflight':report,
                'frames':frames,'actual_duration':actual_duration,
                'stages':['FFmpeg decode/resize','frame models + authored picture slots','FFmpeg picture filters',
                          'codec generations / damage and recovery','audio filters','audio DSP / authored audio','audio codec generations','mux'],
                'ffmpeg_version':subprocess.run(['ffmpeg','-version'],capture_output=True,text=True,timeout=10).stdout.splitlines()[0],
                'numpy_version':np.__version__,
                'notes':['Models are approximations unless labeled process.','A selected effect may visually mask another.']}
            manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
            job.emit('Complete',1,output=str(output),manifest=str(manifest_path))
            return manifest
    finally:stageout.unlink(missing_ok=True)


def preview(project, cache_dir, *, effect_id=None,start=0,duration=8,width=480,job=None):
    p=copy.deepcopy(project);info=probe(p.source)
    if effect_id:
        if effect_id not in p.effects:
            from .model import Setting
            p.effects[effect_id]=Setting()
        s=copy.deepcopy(p.effects[effect_id]);s.enabled=True
        p.effects={effect_id:s}
    p.width=min(width,p.width) if p.width else width
    source=Path(info['path']);asset_stats={}
    for e,s in p.enabled():
        if s.asset:
            asset=local_file(s.asset);asset_stats[str(asset)]=(asset.stat().st_size,asset.stat().st_mtime_ns)
    key={'version':'0.1.0','project':p.to_dict(),'source':(source.stat().st_size,source.stat().st_mtime_ns),
         'assets':asset_stats,'start':start,'duration':duration}
    digest=hashlib.sha256(json.dumps(key,sort_keys=True).encode()).hexdigest()[:24]
    cache=Path(cache_dir);cache.mkdir(parents=True,exist_ok=True);target=cache/f'{digest}.mp4'
    if target.exists():
        if job:job.emit('Preview cache hit',1,output=str(target))
        return target
    render(p,target,start=start,duration=duration,job=job)
    return target
