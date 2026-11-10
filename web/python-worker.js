let py, bridge;
async function load() {
  if(bridge)return;
  const local=['127.0.0.1','localhost','::1'].includes(self.location.hostname);
  const base=local?new URL('vendor/pyodide/',self.location).href:'https://cdn.jsdelivr.net/pyodide/v0.27.7/full/';
  if(!py){importScripts(base+'pyodide.js');py=await loadPyodide({indexURL:base});}
  await py.loadPackage(['numpy','scipy']);
  const response=await fetch(new URL('engine.zip',self.location),{cache:'no-cache'});
  if(!response.ok)throw new Error('Shared Python engine could not be loaded');
  py.unpackArchive(await response.arrayBuffer(),'zip');
  py.runPython('import signalbox.browser as _bridge');
  bridge=py.globals.get('_bridge');
}
self.onmessage=async({data:msg})=>{
  try{
    await load();let result;const d=msg.data||{};
    if(msg.type==='load')result=true;
    else if(msg.type==='configure')result=JSON.parse(bridge.configure(JSON.stringify(d.project),JSON.stringify(d.info)));
    else {
      const commands={frames:'process_frames',composite:'composite_asset',audioBegin:'begin_audio',audioEffect:'audio_effect',audioFinish:'finish_audio',analysisBegin:'analysis_begin',analysisFrames:'analysis_frames',analysisAudio:'analysis_audio',analysisFinish:'analysis_finish'};
      const name=commands[msg.type];if(!name)throw new Error('Unknown worker command');
      const proxies=[];const binary=bytes=>{const p=py.toPy(bytes);proxies.push(p);return p;};
      try{
        const args={
          frames:()=>[binary(d.bytes),JSON.stringify(d.meta)],
          composite:()=>[binary(d.bytes),binary(d.asset),JSON.stringify(d.meta)],
          audioBegin:()=>[binary(d.bytes)],audioEffect:()=>[d.effect,d.offset||0,d.asset?binary(d.asset):null],audioFinish:()=>[],
          analysisBegin:()=>[JSON.stringify(d.info)],analysisFrames:()=>[binary(d.bytes),d.start],analysisAudio:()=>[binary(d.bytes)],analysisFinish:()=>[]
        };
        const raw=bridge[name](...args[msg.type]());
        if(raw?.toJs){result=raw.toJs();raw.destroy();}else result=raw;
        if(msg.type==='analysisFinish')result=JSON.parse(result);
      }finally{for(const p of proxies)p?.destroy?.();}
    }
    if(result instanceof Uint8Array)postMessage({id:msg.id,result},[result.buffer]);else postMessage({id:msg.id,result});
  }catch(error){postMessage({id:msg.id,error:error.message});}
};
