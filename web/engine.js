/* Browser pipeline. Media is mounted read-only; every output is local WASM memory. */
class RPC {
  constructor(url, event) {this.worker=new Worker(url);this.next=0;this.pending=new Map();this.worker.onmessage=({data:m})=>{if(m.id){const p=this.pending.get(m.id);if(!p)return;this.pending.delete(m.id);m.error?p.reject(new Error(m.error)):p.resolve(m.result);}else event?.(m);};this.worker.onerror=e=>{for(const p of this.pending.values())p.reject(new Error(e.message||'Worker failed'));this.pending.clear();};}
  call(type,data={},transfer=[]) {return new Promise((resolve,reject)=>{const id=++this.next;this.pending.set(id,{resolve,reject});this.worker.postMessage({id,type,data},transfer);});}
  stop(){this.worker.terminate();for(const p of this.pending.values())p.reject(new Error('Job cancelled'));this.pending.clear();}
}
const defaults=()=>({enabled:true,strength:.5,locked:false,asset:'',start:0,end:null,roi:[.55,.2,.25,.5]});
export class BrowserEngine {
  constructor(progress=()=>{}) {this.progress=progress;this.ff=null;this.py=null;this.capabilities=null;this.mounts=[];this.busy=false;}
  status(stage,fraction=null,detail=''){this.progress({stage,fraction,detail});}
  async load(){
    if(this.capabilities)return this.capabilities;
    this.status('Loading the local engine',null,'First use downloads about 69 MB. Your media stays on this device.');
    this.ff??=new RPC(new URL('ffmpeg-worker.js?v=7',import.meta.url));this.py??=new RPC(new URL('python-worker.js?v=7',import.meta.url));
    let caps;try{[caps]=await Promise.all([this.ff.call('load'),this.py.call('load')]);}catch(error){this.ff?.stop();this.py?.stop();this.ff=null;this.py=null;throw error;}
    const names=(text,n)=>new Set(text.split('\n').map(x=>x.trim().split(/\s+/)).filter(x=>x.length>=2&&x[1]!=='='&&(n===6?/^[VAS][A-Z.]{5}$/:/^[TSC.]{3}$/).test(x[0])).map(x=>x[1]));
    this.capabilities={encoders:names(caps.encoders,6),filters:names(caps.filters,3),bsfs:caps.bsfs};
    this.status('Local engine ready',1);return this.capabilities;
  }
  cancel(){this.ff?.stop();this.py?.stop();this.ff=null;this.py=null;this.capabilities=null;this.mounts=[];this.busy=false;this.status('Job cancelled',0,'Your source and project are unchanged. The engine will reload for the next job.');}
  async command(args,probe=false){try{return await this.ff.call('exec',{args,probe});}catch(error){throw new Error(error.message+'\nStage arguments: '+args.join(' '));}}
  async recycleFFmpeg(){
    // Native CLI libraries retain allocations between invocations. Recreate the
    // WASM worker between jobs so memory cannot accumulate across exports.
    if(this.ff){this.ff.stop();this.ff=null;this.capabilities=null;this.mounts=[];}
  }
  async read(path){return this.ff.call('read',{path});}
  async write(path,bytes){return this.ff.call('write',{path,bytes},[bytes.buffer]);}
  async remove(path){return this.ff.call('unlink',{path});}
  async mount(file,key){const path='/mount-'+key;const result=await this.ff.call('mount',{path,file});this.mounts.push(path);return result;}
  async cleanup(){if(!this.ff)return;for(const path of this.mounts){await this.ff.call('unmount',{path});}this.mounts=[];const files=await this.ff.call('list');for(const file of files)if(file.file)await this.remove('/'+file.name);}
  async probe(path){
    await this.command(['-v','error','-show_streams','-show_format','-of','json','-o','/probe.json',path],true);
    const all=JSON.parse(await this.ff.call('readText',{path:'/probe.json'}));await this.remove('/probe.json');
    const v=all.streams?.find(s=>s.codec_type==='video'&&!s.disposition?.attached_pic),a=all.streams?.some(s=>s.codec_type==='audio');
    const fraction=s=>{const [n,d]=String(s||'0/1').split('/').map(Number);return n/(d||1);};
    const duration=Number(v?.duration||all.format?.duration||0);
    return {duration,width:v?.width||0,height:v?.height||0,fps:fraction(v?.avg_frame_rate)||25,audio:!!a,video:!!v,video_index:v?.index||0,stream:v,streams:all.streams};
  }
  dimensions(info,p){let w=info.width,h=info.height;const sar=String(info.stream?.sample_aspect_ratio||'1:1').split(':').map(Number);if(sar[1]&&sar[0])w*=sar[0]/sar[1];const rotation=info.stream?.side_data_list?.find(x=>x.rotation!==undefined)?.rotation||0;if(Math.abs(rotation)%180===90)[w,h]=[h,w];const width=Math.max(2,Math.floor((p.width||w)/2)*2),height=Math.max(2,Math.floor(h/w*width/2)*2);return {width,height,fps:p.fps||Math.min(info.fps,30)};}
  async inspect(source){await this.load();await this.cleanup();const path=await this.mount(source,'source');try{return await this.probe(path);}finally{await this.cleanup();}}
  async preflight(selected,assets){
    const errors=[],warnings=[];
    for(const e of selected){
      const s=e.setting;
      if(e.asset&&!assets[e.id])errors.push(`${e.name}: choose a ${e.asset} asset in the inspector.`);
      if((s.start>0||s.end!==null)&&['vf','af','vcodec','acodec','meta'].includes(e.kind))errors.push(`${e.name}: this whole-stream stage cannot have a time window.`);
      const requested=e.encoder||e.codec?.[0],encoder=requested==='libopus'?'opus':requested;if(encoder&&!this.capabilities.encoders.has(encoder))errors.push(`${e.name}: ${encoder} is not in this browser's FFmpeg build. Use the desktop engine for this codec.`);
      if(e.filter){for(const match of e.filter.replace(/'[^']*'/g,"''").matchAll(/(?:^|,)([a-z0-9_]+)(?:=|,|$)/g))if(!this.capabilities.filters.has(match[1]))errors.push(`${e.name}: filter ${match[1]} is unavailable in this browser build.`);}
      if(e.cost==='heavy'||['pixel_sort','error_dither'].includes(e.id))warnings.push(`${e.name}: potentially much slower than real time.`);
    }
    if(errors.length)throw new Error('Cannot render this selection:\n'+errors.join('\n'));
    return warnings;
  }
  async guardMemory(){const files=await this.ff.call('list');const bytes=files.filter(x=>x.file).reduce((a,b)=>a+b.size,0);if(bytes>420_000_000)throw new Error('This job exceeded the browser scratch-memory allowance (420 MB). Try a shorter interval or use the desktop engine for this full render.');}
  async processVideo(p,selected,input,assetPaths,assetInfo,start,duration,dim){
    const {width:w,height:h,fps}=dim,frameBytes=w*h*3;
    if(frameBytes>32_000_000)throw new Error('Working raster is too large for browser processing. Lower the width.');
    const step=Math.max(1,Math.min(Math.round(fps*2),Math.floor(24_000_000/frameBytes))),total=Math.ceil(duration*fps-1e-5);
    const custom=selected.some(e=>e.kind==='frame'||e.recipe==='databend'),authored=selected.filter(e=>e.kind==='asset_video');
    const chunks=[];
    for(let base=0;base<total;base+=step){
      const count=Math.min(step,total-base),t=start+base/fps,seconds=count/fps;
      this.status('Processing picture',base/total,`${base} / ${total} frames · ${w}×${h}`);
      await this.command(['-ss',String(t),'-i',input,'-map','0:v:0','-an','-vf',`scale=${w}:${h}:flags=bicubic,fps=${fps},setsar=1`,'-frames:v',String(count),'-pix_fmt','rgb24','-f','rawvideo','/raw.rgb']);
      let bytes=await this.read('/raw.rgb');await this.remove('/raw.rgb');
      if(!bytes.length)break;
      if(custom)bytes=await this.py.call('frames',{bytes,meta:{start:t}},[bytes.buffer]);
      for(const e of authored){
        const s=e.setting;if(t+seconds<=s.start||(s.end!==null&&t>=s.end))continue;
        const origin=Math.max(t,s.start),offset=Math.max(0,t-s.start)%Math.max(.1,assetInfo[e.id].duration||duration);
        await this.command(['-stream_loop','-1','-ss',String(offset),'-i',assetPaths[e.id],'-an','-vf',`scale=${w}:${h},fps=${fps},setsar=1`,'-frames:v',String(count),'-pix_fmt','rgb24','-f','rawvideo','/asset.rgb']);
        const asset=await this.read('/asset.rgb');await this.remove('/asset.rgb');
        bytes=await this.py.call('composite',{bytes,asset,meta:{id:e.id,start:t,asset_origin:origin}},[bytes.buffer,asset.buffer]);
      }
      const chunk='/chunk-'+chunks.length+'.mkv';chunks.push(chunk);await this.write('/processed.rgb',bytes);
      await this.command(['-f','rawvideo','-pixel_format','rgb24','-video_size',`${w}x${h}`,'-framerate',String(fps),'-i','/processed.rgb','-an','-c:v','libx264','-preset','ultrafast','-crf','14','-pix_fmt','yuv444p',chunk]);
      await this.remove('/processed.rgb');await this.guardMemory();
    }
    if(!chunks.length)throw new Error('No frames decoded in this interval.');
    await this.ff.call('text',{path:'/chunks.txt',text:chunks.map(x=>`file '${x}'`).join('\n')});
    const filters=selected.filter(e=>e.kind==='vf').map(e=>e.filter);
    filters.push(`setpts=PTS-STARTPTS,fps=${fps},tpad=stop_mode=clone:stop_duration=2`);
    this.status('Applying native picture filters');
    await this.command(['-f','concat','-safe','0','-i','/chunks.txt','-an','-vf',filters.join(','),'-t',String(duration),'-c:v','libx264','-preset','veryfast','-crf',String(p.crf),'-pix_fmt','yuv420p','/picture.mkv']);
    for(const path of chunks)await this.remove(path);await this.remove('/chunks.txt');
    return '/picture.mkv';
  }
  async videoCodecs(current,selected,p,dim,duration){
    const {width:w,height:h,fps}=dim;
    for(const e of selected.filter(e=>e.kind==='vcodec'&&e.recipe!=='databend')){
      const k=e.recipe,a=e.setting.strength,passes=k==='generations'?Math.max(2,Math.floor(2+3*a)):k==='platform'?3:1;
      for(let turn=0;turn<passes;turn++){
        this.status('Codec generation: '+e.name,null,`${turn+1} / ${passes}`);
        const codec=k==='platform'?(turn%2?'libx264':'mpeg4'):e.encoder;
        const raw='/codec.'+(codec==='gif'?'gif':codec==='libx264'?'mkv':'avi');let vf=[];
        const args=['-i',current,'-an','-c:v',codec];
        if(codec==='libx264')args.push('-preset','veryfast','-crf',String(Math.round(30+18*a)));
        else if(['mpeg4','flv','h263'].includes(codec))args.push('-q:v',String(Math.round(6+23*a)));
        if(k==='dark_mud')vf.push('eq=brightness=-.08:contrast=1.3');
        if(codec==='cinepak'){vf.push('scale=320:240');args.push('-q:v','20');}
        if(codec==='h263')vf.push('scale=352:288');if(codec==='gif')vf.push('scale=320:-2','fps=12');
        if(['datamosh','packet_loss','bit_rot','bad_sectors'].includes(k))args.push('-g',String(Math.max(2,Math.floor(fps))),'-bf','0');
        if(vf.length)args.push('-vf',vf.join(','));await this.command([...args,raw]);
        let damaged=raw;
        if(['datamosh','packet_loss','bit_rot'].includes(k)){
          damaged='/damaged.avi';const bsf=k==='datamosh'?"noise=amount=0:drop='key*gt(n,0)'":k==='packet_loss'?`noise=amount=0:drop='not(key)*eq(mod(n,${Math.max(3,Math.floor(15-10*a))}),0)'`:`noise=amount=${Math.floor(8000-6500*a)}`;
          await this.command(['-i',raw,'-c','copy','-bsf:v',bsf,damaged]);
        }else if(k==='bad_sectors'){
          await this.command(['-v','error','-select_streams','v:0','-show_packets','-show_entries','packet=pos,size,flags','-of','json','-o','/packets.json',raw],true);
          const packets=JSON.parse(await this.ff.call('readText',{path:'/packets.json'})).packets,bytes=await this.read(raw);
          packets.forEach((v,i)=>{if(i%7===4&&!v.flags?.includes('K')){const n=Math.min(Math.floor(10+60*a),Math.max(0,Number(v.size)-64));bytes.fill(0,Number(v.pos)+32,Number(v.pos)+32+n);}});
          damaged='/damaged.avi';await this.write(damaged,bytes);await this.remove('/packets.json');
        }
        const next=current==='/recovered-a.mkv'?'/recovered-b.mkv':'/recovered-a.mkv';
        await this.command(['-err_detect','ignore_err','-i',damaged,'-an','-vf',`scale=${w}:${h},fps=${fps},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration=${duration}`,'-t',String(duration),'-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p',next]);
        await this.remove(current);await this.remove(raw);if(raw!==damaged)await this.remove(damaged);current=next;
      }
    }
    return current;
  }
  async audio(p,selected,input,assetPaths,start,duration,hasAudio){
    this.status('Processing audio');
    const af=selected.filter(e=>e.kind==='af'&&e.recipe!=='audio_reverse').map(e=>e.filter);af.push('aresample=48000','apad');
    const inargs=hasAudio?['-ss',String(start),'-i',input,'-map','0:a:0']:['-f','lavfi','-i','anullsrc=r=48000:cl=stereo'];
    const dsp=selected.filter(e=>['audio','asset_audio'].includes(e.kind)||e.recipe==='audio_reverse');
    if(duration*48000*8>128_000_000)throw new Error('This selection needs an audio buffer larger than the browser allowance (128 MB). Render a shorter interval, or use the desktop app for the full source.');
    let pcm='/audio-source.f32';
    await this.command([...inargs,'-t',String(duration),'-vn','-af',af.join(','),'-ar','48000','-ac','2','-f','f32le',pcm]);
    if(dsp.length){
      const bytes=await this.read(pcm);await this.remove(pcm);await this.py.call('audioBegin',{bytes},[bytes.buffer]);
      for(let i=0;i<dsp.length;i++){
        const e=dsp[i];this.status('Audio: '+e.name,i/dsp.length);let asset;
        if(e.kind==='asset_audio'){
          await this.command(['-i',assetPaths[e.id],'-t',String(e.recipe==='impulse'?10:duration),'-vn','-ar','48000','-ac','2','-f','f32le','/audio-asset.f32']);
          asset=await this.read('/audio-asset.f32');await this.remove('/audio-asset.f32');
        }
        await this.py.call('audioEffect',{effect:e.id,offset:start,asset},asset?[asset.buffer]:[]);
      }
      await this.write(pcm,await this.py.call('audioFinish'));
    }
    for(const e of selected.filter(e=>e.kind==='acodec')){
      const [nativeCodec,suffix,rate,channels]=e.codec;
      // This WASM distribution's libopus encoder traps; FFmpeg's native Opus
      // encoder provides an actual Opus round trip at the same bitrate.
      const codec=nativeCodec==='libopus'?'opus':nativeCodec;
      for(let turn=0;turn<(e.recipe==='generations'?3:1);turn++){
        this.status('Audio codec: '+e.name);const path='/encoded-audio.'+suffix;
        const args=['-f','f32le','-ar','48000','-ac','2','-i',pcm,'-c:a',codec,'-ar',String(rate),'-ac',String(channels)];
        if(['aac','libmp3lame','opus'].includes(codec))args.push('-b:a',String(Math.floor(48000-32000*e.setting.strength)));
        if(codec==='opus')args.push('-strict','-2');
        if(e.recipe==='joint_stereo')args.push('-joint_stereo','1');if(codec==='libcodec2')args.push('-mode','3200');
        await this.command([...args,path]);await this.remove(pcm);
        await this.command(['-i',path,'-ar','48000','-ac','2','-af','apad','-t',String(duration),'-f','f32le',pcm]);await this.remove(path);
      }
    }
    const final=['alimiter=limit=.89:level=0:latency=1'];let audioDuration=duration;
    for(const e of selected){const a=e.setting.strength;if(e.recipe==='av_offset')final.push(`adelay=${Math.floor(2000*a)}:all=1`);if(e.recipe==='av_drift')final.push(`asetrate=${Math.floor(48000*(1+.03*a))}`,'aresample=48000');if(e.recipe==='track_mismatch')audioDuration=Math.max(.1,duration*(1-.5*a));}
    await this.command(['-f','f32le','-ar','48000','-ac','2','-i',pcm,'-af',final.join(','),'-t',String(audioDuration),'-c:a','aac','-b:a','160k','/final-audio.m4a']);await this.remove(pcm);
    return '/final-audio.m4a';
  }
  async render(source,project,assets={},options={}){
    if(this.busy)throw new Error('A job is already running');this.busy=true;
    try{
      await this.load();await this.cleanup();const input=await this.mount(source,'source'),info=await this.probe(input);
      if(!info.video||!Number.isFinite(info.duration)||info.duration<=0)throw new Error('A seekable video with a finite duration is required.');
      const p=structuredClone(project);p.source=source.name;
      if(options.effect){p.effects={[options.effect]:{...defaults(),...p.effects[options.effect],enabled:true}};}
      if(options.preview)p.width=Math.min(p.width||480,480);
      const start=Number(options.start||0),duration=Math.min(options.duration??info.duration,info.duration-start);
      if(!Number.isFinite(start)||!Number.isFinite(duration)||start<0||duration<=0)throw new Error('Choose a valid interval inside the video.');
      const dim=this.dimensions(info,p);if(dim.height>4096||dim.width>4096)throw new Error('Please lower the browser working resolution to 4096 pixels or less.');
      const selected=await this.py.call('configure',{project:p,info:dim}),warnings=await this.preflight(selected,assets);
      const assetPaths={},assetInfo={};
      for(const e of selected.filter(e=>e.asset)){assetPaths[e.id]=await this.mount(assets[e.id],'asset-'+e.id);assetInfo[e.id]=await this.probe(assetPaths[e.id]);if(!assetInfo[e.id][e.asset])throw new Error(e.name+': the supplied asset has no '+e.asset+' stream.');}
      let video=await this.processVideo(p,selected,input,assetPaths,assetInfo,start,duration,dim);
      video=await this.videoCodecs(video,selected,p,dim,duration);
      const needsAudio=info.audio||selected.some(e=>['af','audio','acodec','asset_audio'].includes(e.kind));
      const audio=needsAudio?await this.audio(p,selected,input,assetPaths,start,duration,info.audio):null;
      this.status('Finishing MP4');const args=['-i',video];if(audio)args.push('-i',audio,'-map','0:v:0','-map','1:a:0');else args.push('-map','0:v:0');
      args.push('-c','copy','-map_metadata','-1','-movflags','+faststart');
      for(const e of selected)if(e.recipe==='aspect_flag')args.push('-aspect',String(dim.width/dim.height*(.6+e.setting.strength)));
      await this.command([...args,'/result.mp4']);const final=await this.probe('/result.mp4');if(!final.video||final.duration<=0)throw new Error('Final media validation failed.');
      const bytes=await this.read('/result.mp4');const manifest={application:'Signal Box',version:'0.2.0',runtime:'Browser / Pyodide 0.27.7 / FFmpeg WASM 0.12.10',project:p,interval:{start,duration},dimensions:dim,warnings,
        source:{name:source.name,size:source.size,lastModified:source.lastModified},assets:Object.fromEntries(Object.entries(assets).map(([id,f])=>[id,{name:f.name,size:f.size,lastModified:f.lastModified}])),
        notes:['Media processed locally; no server upload.','Opus round trips use FFmpeg native Opus in this browser runtime.','Video uses short H.264 intermediate chunks (CRF 14, 4:4:4) to bound raw-frame memory.','Models and authored-input requirements retain their catalog labels.']};
      this.status('Render complete',1,`${(bytes.byteLength/1e6).toFixed(2)} MB · ${final.duration.toFixed(2)} seconds`);return {bytes,manifest,info:final};
    }finally{try{await this.cleanup();}catch{}await this.recycleFFmpeg();this.busy=false;}
  }
  async analyze(source){
    if(this.busy)throw new Error('A job is already running');this.busy=true;
    try{
      await this.load();await this.cleanup();const input=await this.mount(source,'source'),info=await this.probe(input);
      if(!info.video||!info.duration)throw new Error('A finite-duration source video is required');
      await this.py.call('analysisBegin',{info});const chunk=8;
      for(let start=0;start<info.duration;start+=chunk){
        const duration=Math.min(chunk,info.duration-start);this.status('Analyzing the whole source',start/info.duration,`${start.toFixed(0)} / ${info.duration.toFixed(0)} seconds · every decoded frame`);
        await this.command(['-ss',String(start),'-i',input,'-t',String(duration),'-an','-vf','scale=160:96','-vsync','0','-pix_fmt','rgb24','-f','rawvideo','/analysis.rgb']);
        const bytes=await this.read('/analysis.rgb');await this.remove('/analysis.rgb');await this.py.call('analysisFrames',{bytes,start},[bytes.buffer]);
        if(info.audio){await this.command(['-ss',String(start),'-i',input,'-t',String(duration),'-vn','-ar','16000','-ac','2','-f','f32le','/analysis.f32']);const audio=await this.read('/analysis.f32');await this.remove('/analysis.f32');await this.py.call('analysisAudio',{bytes:audio},[audio.buffer]);}
      }
      const result=await this.py.call('analysisFinish');this.status('Analysis complete',1,`${result.frames_examined} frames examined`);return result;
    }finally{try{await this.cleanup();}catch{}await this.recycleFFmpeg();this.busy=false;}
  }
}
