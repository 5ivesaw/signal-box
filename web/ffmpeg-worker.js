/* Local-only, single-thread FFmpeg worker. No SharedArrayBuffer/COOP dependency. */
let core, logs = [];
const emit = (type, data) => postMessage({type, ...data});
async function load() {
  if (core) return;
  const local = ['127.0.0.1','localhost','::1'].includes(self.location.hostname);
  const base = local ? new URL('vendor/ffmpeg/', self.location).href : 'https://cdn.jsdelivr.net/npm/@ffmpeg/core@0.12.10/dist/umd/';
  const coreURL = base+'ffmpeg-core.js';
  const wasmURL = base+'ffmpeg-core.wasm';
  importScripts(coreURL);
  core = await createFFmpegCore({mainScriptUrlOrBlob: `${coreURL}#${btoa(JSON.stringify({wasmURL}))}`});
  core.setLogger(({message}) => { logs.push(message); if(logs.length > 2000) logs.shift(); });
  core.setProgress(({progress,time}) => emit('progress', {progress,time}));
}
function exec(args, probe=false) {
  logs=[]; core.setTimeout(1200000);
  if(probe) core.ffprobe(...args); else core.exec('-hide_banner','-nostdin','-y',...args);
  let code=core.ret; core.reset();
  // The bundled ffprobe can return normally without updating the CLI exit slot.
  // Accept that case only when its requested JSON output was actually written.
  if(probe && code===-1){const i=args.indexOf('-o');if(i>=0){try{if(core.FS.stat(args[i+1]).size>0)code=0;}catch{}}}
  if(code && !args.includes('-encoders') && !args.includes('-filters')) throw new Error((probe?"Probe: ":"Command: ")+args.join(" ")+"\n"+logs.slice(-16).join('\n') || `FFmpeg exited ${code}`);
  return {code,logs};
}
self.onmessage = async ({data:msg}) => {
  try {
    await load();let result;
    const {type,data}=msg;
    if(type==='load') {
      const enc=exec(['-encoders']).logs.join('\n'), fil=exec(['-filters']).logs.join('\n');
      const bsf=exec(['-bsfs']).logs.join('\n');
      result={encoders:enc,filters:fil,bsfs:bsf};
    } else if(type==='exec') result=exec(data.args,!!data.probe);
    else if(type==='write') { core.FS.writeFile(data.path,data.bytes);result=true; }
    else if(type==='text') { core.FS.writeFile(data.path,new TextEncoder().encode(data.text));result=true; }
    else if(type==='read') result=core.FS.readFile(data.path);
    else if(type==='readText') result=new TextDecoder().decode(core.FS.readFile(data.path));
    else if(type==='unlink') {try{core.FS.unlink(data.path);}catch{}result=true;}
    else if(type==='mount') {
      try{core.FS.mkdir(data.path);}catch{}
      core.FS.mount(core.FS.filesystems.WORKERFS,{files:[data.file]},data.path);result=data.path+'/'+data.file.name;
    } else if(type==='unmount') {try{core.FS.unmount(data.path);core.FS.rmdir(data.path);}catch{}result=true;}
    else if(type==='list') result=core.FS.readdir('/').filter(x=>!['.','..'].includes(x)).map(name=>{const s=core.FS.stat('/'+name);return {name,size:s.size,file:core.FS.isFile(s.mode)}});
    else throw new Error('Unknown worker command');
    if(result instanceof Uint8Array)postMessage({id:msg.id,result},[result.buffer]);
    else postMessage({id:msg.id,result});
  }catch(error){postMessage({id:msg.id,error:error.message});}
};
