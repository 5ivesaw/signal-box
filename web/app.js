import {BrowserEngine} from './engine.js?v=7';
const $=id=>document.getElementById(id), storage='signal-box-project-v1';
const desktopOnly=new Set(['gsm','codec2','formant']);
const defaults=()=>({enabled:false,strength:.5,locked:false,asset:'',start:0,end:null,roi:[.55,.2,.25,.5]});
let catalog=[],byId=new Map(),presets={},focus='chroma_bleed',source=null,sourceURL=null,resultURL=null,result=null,info=null,assets={},busy=false,report=[],toastTimer;
let project={schema:1,source:'',effects:{},seed:1967,width:480,fps:0,threads:2,crf:18};
try{const saved=JSON.parse(localStorage.getItem(storage));if(saved?.schema===1)project={...project,...saved};}catch{}
const engine=new BrowserEngine(({stage,fraction,detail})=>{
  $('job-status').textContent=stage;$('job-detail').textContent=detail||'Processing locally. You can continue browsing effects.';
  $('progress').hidden=fraction===null;$('progress').value=fraction??0;
  if(stage.includes('ready')||stage==='Render complete'||stage==='Analysis complete')$('engine-state').textContent='● LOCAL ENGINE · READY';
  if(stage.includes('Loading'))$('engine-state').textContent='◌ LOADING ENGINE · ~69 MB';
});
function setting(id){return project.effects[id]??=(defaults());}
function selected(){return catalog.filter(e=>project.effects[e.id]?.enabled);}
function persist(){try{localStorage.setItem(storage,JSON.stringify(project));}catch{}}
function toast(text){$('toast').textContent=text;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,5500);}
function addReport(value){report.push(typeof value==='string'?value:JSON.stringify(value,null,2));report=report.slice(-15);$('report').textContent=report.join('\n\n');}
function failure(error){const message=error.message||String(error);$('job-status').textContent=message==='Job cancelled'?'Job cancelled':'Job could not finish';$('job-detail').textContent=message.split('\n')[0];$('progress').hidden=true;addReport(message);$('report-panel').open=true;toast(message.split('\n')[0]);}
function busyState(value){busy=value;$('cancel').hidden=!value;for(const id of ['render','preview-focused','preview-stack','auto','demo','hero-demo','empty-demo'])$(id).disabled=value;for(const id of ['source-file','load-project'])$(id).disabled=value;}
async function task(fn){if(busy){toast('A job is already running. Cancel it before starting another.');return;}busyState(true);try{await fn();}catch(e){failure(e);}finally{busyState(false);}}
function downloadBlob(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);}
function escape(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function filtered(){const terms=$('search').value.toLowerCase().split(/\s+/).filter(Boolean),category=$('category').value;return catalog.filter(e=>(!category||e.category===category)&&(!$('selected-only').checked||project.effects[e.id]?.enabled)&&(!$('heavy-only').checked||e.cost==='heavy'||['error_dither','pixel_sort'].includes(e.id))&&terms.every(t=>(e.id+' '+e.name+' '+e.description+' '+e.category).toLowerCase().includes(t)));}
function renderLibrary(){
  const rows=filtered();$('filter-count').textContent=`${rows.length} / ${catalog.length} shown`;
  $('effect-list').innerHTML=rows.map(e=>{const s=project.effects[e.id]||defaults();return `<div role="listitem" class="effect-row ${e.id===focus?'active':''}" data-id="${e.id}"><input type="checkbox" aria-label="Enable ${escape(e.name)}" ${s.enabled?'checked':''}><button class="effect-focus" aria-label="Inspect ${escape(e.name)}"><strong>${escape(e.name)}</strong><small>${escape(e.category)} · ${e.fidelity}</small></button><span class="status" title="${e.asset?'Needs an asset':e.cost==='heavy'?'Expensive operation':'Built-in operation'}">${s.locked?'L ':''}${e.asset?'◇':e.cost==='heavy'||e.id==='error_dither'?'!':'○'}</span></div>`;}).join('')||'<div class="chain-empty">No effects match. Try a broader search.</div>';
}
function renderChain(){
  const rows=selected();$('selected-count').textContent=rows.length;
  $('chain').innerHTML=rows.map(e=>`<div class="chain-item" data-id="${e.id}"><button aria-label="Inspect selected ${escape(e.name)}">${escape(e.name)}</button><span>${Math.round(setting(e.id).strength*100)}%${setting(e.id).locked?' L':''}</span><button class="remove" aria-label="Remove ${escape(e.name)}">×</button></div>`).join('')||'<div class="chain-empty">Your selected effects appear here.<br>Lock an effect to protect your choice from automatic modes.</div>';
  const heavy=rows.filter(e=>e.cost==='heavy'||['error_dither','pixel_sort'].includes(e.id)).length,missing=rows.filter(e=>e.asset&&!assets[e.id]).length;
  $('cost-summary').textContent=rows.length?`${rows.length} selected${heavy?` · ${heavy} expensive`:''}${missing?` · ${missing} need assets`:''}. ${heavy?'Preview before a long render.':'Original media stays unchanged.'}`:'A clear chain exports the source through the working pipeline.';
}
function inspect(){
  const e=byId.get(focus);if(!e)return;const s=setting(focus);
  $('effect-category').textContent=e.category.toUpperCase();$('effect-name').textContent=e.name;$('effect-description').textContent=e.description;
  $('effect-details').hidden=false;$('effect-toggle').disabled=false;$('effect-toggle').textContent=s.enabled?'Disable effect':'Enable effect';
  $('effect-toggle').classList.toggle('primary',s.enabled);$('strength').value=s.strength;$('strength-value').textContent=Math.round(s.strength*100)+'%';$('effect-lock').checked=s.locked;
  $('effect-badges').innerHTML=`<span class="badge">${e.fidelity.toUpperCase()}</span><span class="badge ${e.cost==='heavy'?'warn':''}">${e.id==='error_dither'?'HEAVY':e.cost.toUpperCase()}</span><span class="badge">${e.temporal?'MOVING PREVIEW':'PICTURE FILTER'}</span>${e.asset?'<span class="badge warn">REQUIRES '+e.asset.toUpperCase()+'</span>':''}${desktopOnly.has(e.id)?'<span class="badge warn">DESKTOP DEPENDENCY</span>':''}`;
  const windowed=['frame','audio','asset_audio','asset_video'].includes(e.kind)||e.recipe==='audio_reverse';
  $('effect-start').disabled=$('effect-end').disabled=!windowed;$('effect-start').value=s.start;$('effect-end').value=s.end??'';$('effect-roi').value=s.roi.join(', ');
  $('asset-label').hidden=!e.asset;$('asset-file').accept=e.asset==='video'?'video/*,image/*':'audio/*,video/*';$('asset-name').textContent=e.asset?(assets[e.id]?.name||(s.asset?`Reselect: ${s.asset}`:'No asset selected.')):'';
}
function update(){persist();renderLibrary();renderChain();inspect();}
function applyPreset(name){if(!presets[name])return;for(const s of Object.values(project.effects))if(!s.locked)s.enabled=false;for(const id of presets[name])if(!setting(id).locked)setting(id).enabled=true;update();toast('Preset applied. Every effect remains individually editable.');}
function random(seed){let a=seed>>>0;return()=>{a+=0x6D2B79F5;let t=a;t=Math.imul(t^t>>>15,t|1);t^=t+Math.imul(t^t>>>7,t|61);return((t^t>>>14)>>>0)/4294967296;};}
function chaos(){project.seed=crypto.getRandomValues(new Uint32Array(1))[0];$('seed').value=project.seed;const rng=random(project.seed);for(const s of Object.values(project.effects))if(!s.locked)s.enabled=false;const candidates=catalog.filter(e=>!e.asset&&!desktopOnly.has(e.id)&&!setting(e.id).locked);for(let i=candidates.length-1;i>0;i--){const j=Math.floor(rng()*(i+1));[candidates[i],candidates[j]]=[candidates[j],candidates[i]];}for(const e of candidates.slice(0,5+Math.floor(rng()*17))){const s=setting(e.id);s.enabled=true;s.strength=Math.round((.2+rng()*.75)*100)/100;}update();toast(`Chaos seed ${project.seed} saved in the project.`);}
function setSource(file){
  if(!file)return;if(busy){toast('Cancel the running job before changing the source.');return;}
  source=file;info=null;project.source=file.name;persist();if(sourceURL)URL.revokeObjectURL(sourceURL);sourceURL=URL.createObjectURL(file);
  $('source-name').textContent=file.name;$('media-info').textContent=`${(file.size/1e6).toFixed(1)} MB · LOCAL FILE`;$('start').value=0;showSource();$('job-status').textContent='Source loaded';$('job-detail').textContent='Choose effects and generate a preview. No media has been uploaded.';
}
function showSource(){if(!sourceURL)return;const v=$('monitor-video');v.src=sourceURL;v.hidden=false;$('empty-monitor').hidden=true;$('view-source').classList.add('active');$('view-result').classList.remove('active');$('monitor-label').textContent='SOURCE / UNPROCESSED';}
function showResult(){if(!resultURL)return;$('monitor-video').src=resultURL;$('monitor-video').hidden=false;$('empty-monitor').hidden=true;$('view-result').classList.add('active');$('view-source').classList.remove('active');$('monitor-label').textContent='PROCESSED / LOCAL RENDER';}
async function demo(){if(busy)return;try{$('job-status').textContent='Loading the test signal';const r=await fetch('examples/test-pattern.mp4');if(!r.ok)throw new Error('Test signal could not be loaded');setSource(new File([await r.blob()],'test-pattern.mp4',{type:'video/mp4'}));if(!selected().length)applyPreset('tape');document.querySelector('#studio').scrollIntoView({behavior:'smooth'});}catch(e){failure(e);}}
async function runRender(mode){
  if(!source){toast('Open a video or load the test signal first.');return;}
  await task(async()=>{
    const start=mode==='full'?0:Number($('start').value),duration=mode==='full'?undefined:Number($('duration').value);
    const snapshot=structuredClone(project),snapshotAssets={...assets};
    result=await engine.render(source,snapshot,snapshotAssets,{start,duration,preview:mode!=='full',effect:mode==='effect'?focus:undefined});
    if(resultURL)URL.revokeObjectURL(resultURL);resultURL=URL.createObjectURL(new Blob([result.bytes],{type:'video/mp4'}));
    $('view-result').disabled=false;showResult();$('download').href=resultURL;$('download').hidden=false;$('download').download=mode==='full'?'signal-box.mp4':'signal-box-preview.mp4';$('download-manifest').hidden=false;
    addReport(result.manifest);$('media-info').textContent=`${result.info.width}×${result.info.height} · ${result.info.duration.toFixed(2)}s`;
  });
}
async function auto(){
  if(!source){toast('Open a video first. Adaptive selection examines your actual source.');return;}
  await task(async()=>{const analysis=await engine.analyze(source);for(const s of Object.values(project.effects))if(!s.locked)s.enabled=false;for(const r of analysis.recommendations){const s=setting(r.id);if(!s.locked){s.enabled=true;s.strength=r.strength;}}update();addReport(analysis);$('report-panel').open=true;toast(`Analyzed ${analysis.frames_examined} frames. Recommendations and reasons are below.`);});
}
function validateLoaded(p){if(p?.schema!==1||typeof p.effects!=='object'||!p.effects)throw new Error('This is not a Signalbox v1 project');for(const [id,s] of Object.entries(p.effects)){if(!byId.has(id))throw new Error('Unknown effect: '+id);if(typeof s.enabled!=='boolean'||!Number.isFinite(s.strength)||s.strength<0||s.strength>1)throw new Error('Invalid effect setting: '+id);}return {...project,...p};}
function syncSettings(){for(const name of ['width','fps','seed','crf'])$(name).value=project[name];}
$('effect-list').addEventListener('click',ev=>{const row=ev.target.closest('.effect-row');if(!row)return;const id=row.dataset.id;if(ev.target.matches('input')){setting(id).enabled=ev.target.checked;update();}else{focus=id;renderLibrary();inspect();}});
$('chain').addEventListener('click',ev=>{const row=ev.target.closest('.chain-item');if(!row)return;if(ev.target.closest('.remove')){setting(row.dataset.id).enabled=false;update();}else{focus=row.dataset.id;inspect();renderLibrary();}});
for(const id of ['search','category','selected-only','heavy-only'])$(id).addEventListener(id==='search'?'input':'change',renderLibrary);
$('filtered-toggle').onclick=()=>{const rows=filtered(),enable=!rows.every(e=>setting(e.id).enabled);for(const e of rows)setting(e.id).enabled=enable;update();};
$('effect-toggle').onclick=()=>{setting(focus).enabled=!setting(focus).enabled;update();};
$('strength').oninput=()=>{setting(focus).strength=Number($('strength').value);$('strength-value').textContent=Math.round(setting(focus).strength*100)+'%';renderChain();persist();};
$('effect-lock').onchange=()=>{setting(focus).locked=$('effect-lock').checked;update();};
for(const id of ['effect-start','effect-end','effect-roi'])$(id).onchange=()=>{const s=setting(focus);if(id==='effect-start')s.start=Number($(id).value);if(id==='effect-end')s.end=$(id).value===''?null:Number($(id).value);if(id==='effect-roi'){const roi=$(id).value.split(',').map(Number);if(roi.length!==4||roi.some(v=>!Number.isFinite(v)||v<0||v>1)||roi[0]+roi[2]>1||roi[1]+roi[3]>1||roi[2]===0||roi[3]===0){toast('Region must be x,y,width,height within 0..1 and fit the picture.');inspect();return;}s.roi=roi;}persist();};
$('asset-file').onchange=()=>{const file=$('asset-file').files[0];if(file){assets[focus]=file;setting(focus).asset=file.name;update();}$('asset-file').value='';};
$('source-file').onchange=()=>{setSource($('source-file').files[0]);$('source-file').value='';};
for(const id of ['demo','hero-demo','empty-demo'])$(id).onclick=demo;
$('view-source').onclick=showSource;$('view-result').onclick=showResult;
$('preview-focused').onclick=()=>runRender('effect');$('preview-stack').onclick=()=>runRender('stack');$('render').onclick=()=>runRender('full');$('auto').onclick=auto;$('chaos').onclick=chaos;
$('select-all').onclick=()=>{for(const e of catalog)setting(e.id).enabled=true;update();toast('All 258 entries enabled. Assign missing assets; unsupported browser codecs will be reported.');};
$('clear').onclick=()=>{for(const s of Object.values(project.effects))s.enabled=false;update();};
$('preset').onchange=()=>{applyPreset($('preset').value);$('preset').value='';};
$('settings-toggle').onclick=()=>{$('settings').hidden=!$('settings').hidden;$('settings-toggle').setAttribute('aria-expanded',String(!$('settings').hidden));};
for(const id of ['width','fps','seed','crf'])$(id).onchange=()=>{const value=Number($(id).value);if(!Number.isFinite(value)||value<0){toast('Choose a nonnegative number.');syncSettings();return;}project[id]=value;persist();};
$('save-project').onclick=()=>downloadBlob(new Blob([JSON.stringify(project,null,2)],{type:'application/json'}),'signal-box-project.json');
$('load-project').onchange=async()=>{try{const file=$('load-project').files[0];if(!file)return;project=validateLoaded(JSON.parse(await file.text()));assets={};source=null;if(sourceURL)URL.revokeObjectURL(sourceURL);sourceURL=null;$('monitor-video').removeAttribute('src');$('monitor-video').hidden=true;$('empty-monitor').hidden=false;$('source-name').textContent='Reselect source video';syncSettings();update();toast('Project loaded. Reselect its source video and effect assets.');}catch(e){failure(e);}finally{$('load-project').value='';}};
$('download-manifest').onclick=()=>{if(result)downloadBlob(new Blob([JSON.stringify(result.manifest,null,2)],{type:'application/json'}),'signal-box-render.json');};
$('cancel').onclick=()=>{engine.cancel();};
$('theme').onclick=()=>{document.body.classList.toggle('night');try{localStorage.setItem('signal-box-theme',document.body.classList.contains('night')?'night':'day');}catch{}};
try{document.body.classList.toggle('night',localStorage.getItem('signal-box-theme')==='night');}catch{}
for(const button of document.querySelectorAll('.guide-jump'))button.onclick=()=>{$('category').value=button.dataset.category;$('search').value='';$('selected-only').checked=false;renderLibrary();$('studio').scrollIntoView({behavior:'smooth'});};
const drop=$('dropzone');drop.addEventListener('dragover',e=>{e.preventDefault();drop.classList.add('dragging');});drop.addEventListener('dragleave',()=>drop.classList.remove('dragging'));drop.addEventListener('drop',e=>{e.preventDefault();drop.classList.remove('dragging');setSource(e.dataTransfer.files[0]);});
$('monitor-video').addEventListener('loadedmetadata',()=>{if($('view-source').classList.contains('active')){const v=$('monitor-video');if(Number.isFinite(v.duration)){$('media-info').textContent=`${v.videoWidth}×${v.videoHeight} · ${v.duration.toFixed(1)}s`;$('start').max=v.duration;$('duration').max=v.duration;}}});
$('monitor-video').addEventListener('error',()=>{if(source)$('job-detail').textContent='This container cannot play natively here. The FFmpeg engine may still decode it for a preview.';});
document.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();$('search').focus();$('studio').scrollIntoView({behavior:'smooth'});}});
window.addEventListener('beforeunload',e=>{if(busy){e.preventDefault();e.returnValue='';}});
try{const response=await fetch('catalog.json');if(!response.ok)throw new Error('Catalog failed to load');const data=await response.json();catalog=data.effects;byId=new Map(catalog.map(e=>[e.id,e]));presets=data.presets;for(const group of new Set(catalog.map(e=>e.category))){const option=document.createElement('option');option.value=option.textContent=group;$('category').append(option);}for(const id of Object.keys(project.effects))if(!byId.has(id))delete project.effects[id];syncSettings();update();}catch(e){failure(e);}
