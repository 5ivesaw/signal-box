import {BrowserEngine} from './engine.js?v=7';
const log=document.querySelector('#log'),out=x=>{log.textContent+='\n'+(typeof x==='string'?x:JSON.stringify(x,null,2));};
let last='',engine=new BrowserEngine(e=>{if(e.stage!==last){out(e.stage);last=e.stage;}});
const setting=(strength=.5)=>({enabled:true,strength,locked:false,asset:'',start:0,end:null,roi:[.55,.2,.25,.5]});
const project=effects=>({schema:1,source:'test-pattern.mp4',effects:Object.fromEntries(effects.map(id=>[id,setting()])),seed:1967,width:96,fps:12,threads:1,crf:18});
async function fixture(){const r=await fetch('examples/test-pattern.mp4');return new File([await r.blob()],'test-pattern.mp4',{type:'video/mp4'});}
function show(result){const url=URL.createObjectURL(new Blob([result.bytes],{type:'video/mp4'}));const v=document.querySelector('#result');v.src=url;v.hidden=false;const a=document.querySelector('#download');a.href=url;a.download='signal-box-browser-test.mp4';a.hidden=false;}
async function run(extended=false){
 document.querySelector('#run').disabled=document.querySelector('#extended').disabled=document.querySelector('#assets').disabled=document.querySelector('#opus').disabled=true;log.textContent='Starting…';
 try{
  const caps=await engine.load();out({encoders:[...caps.encoders],filterCount:caps.filters.size});const file=await fixture();
  if(extended==='opus'){
   const r=await engine.render(file,project(['opus_rot']),{}, {duration:2});show(r);out({opus:'PASS',duration:r.info.duration});
  }else if(extended==='assets'){
   const data=await (await fetch('catalog.json')).json(),entries=data.effects.filter(e=>e.asset),p=project(entries.map(e=>e.id));
   const assets=Object.fromEntries(entries.map(e=>[e.id,file]));
   const r=await engine.render(file,p,assets,{duration:1});show(r);out({assets:'PASS',effects:entries.length,duration:r.info.duration});
  }else if(!extended){
   const rendered=await engine.render(file,project(['composite','tracking','wow','print_through','phone','compression']),{}, {duration:1});
   if(Math.abs(rendered.info.duration-1)>.15)throw new Error('Render duration mismatch '+rendered.info.duration);show(rendered);out({render:'PASS',bytes:rendered.bytes.length,duration:rendered.info.duration});
   const analysis=await engine.analyze(file);if(analysis.frames_examined!==144)throw new Error('Expected 144 frames, got '+analysis.frames_examined);out({analysis:'PASS',frames:analysis.frames_examined,samples:analysis.audio.samples,recommendations:analysis.recommendations});
   const data=await (await fetch('catalog.json')).json();const p=project(data.effects.filter(e=>['frame','vf','audio','af','meta'].includes(e.kind)).map(e=>e.id));
   // Unavailable native filters stay explicit; remove only those for this supported-stack check.
   const unsupported=[];await engine.load();const staged=await engine.py.call('configure',{project:p,info:{width:96,height:54,fps:12}});
   for(const e of staged)if(e.filter){for(const m of e.filter.replace(/'[^']*'/g,"''").matchAll(/(?:^|,)([a-z0-9_]+)(?:=|,|$)/g))if(!caps.filters.has(m[1])){p.effects[e.id].enabled=false;unsupported.push(e.id);}}
   out({unsupportedFilters:[...new Set(unsupported)]});const stack=await engine.render(file,p,{}, {duration:1});out({stack:'PASS',duration:stack.info.duration,effects:Object.values(p.effects).filter(s=>s.enabled).length});
  }else{
   const data=await (await fetch('catalog.json')).json();for(const e of data.effects.filter(e=>['vcodec','acodec'].includes(e.kind))){try{const r=await engine.render(file,project([e.id]),{}, {duration:2});out({id:e.id,status:'PASS',duration:r.info.duration});}catch(err){out({id:e.id,status:'UNAVAILABLE OR FAILED',reason:err.message});}}
  }
  out('ALL REQUESTED DIAGNOSTICS COMPLETED');
 }catch(error){out('FAIL: '+error.message);}finally{document.querySelector('#run').disabled=document.querySelector('#extended').disabled=document.querySelector('#assets').disabled=document.querySelector('#opus').disabled=false;}
}
document.querySelector('#run').onclick=()=>run();document.querySelector('#extended').onclick=()=>run(true);document.querySelector('#cancel').onclick=()=>engine.cancel();

document.querySelector('#assets').onclick=()=>run('assets');

document.querySelector('#opus').onclick=()=>run('opus');
