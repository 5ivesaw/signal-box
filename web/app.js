import {BrowserEngine} from './engine.js?v=8';
const $=id=>document.getElementById(id), storage='signal-box-project-v1';
const desktopOnly=new Set(['gsm','codec2','formant']);
const defaults=()=>({enabled:false,strength:.5,locked:false,asset:'',start:0,end:null,roi:[.55,.2,.25,.5]});
let highlighted=new Set(),selectionAnchor=null,history=[],historyIndex=-1,restoring=false,commandIndex=0;
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
function persist(){
  const state=JSON.stringify(project);try{localStorage.setItem(storage,state);}catch{}
  if(!restoring&&history[historyIndex]!==state){history=history.slice(0,historyIndex+1);history.push(state);if(history.length>80)history.shift();historyIndex=history.length-1;}
  if($('undo')){$('undo').disabled=historyIndex<=0;$('redo').disabled=historyIndex>=history.length-1;}
}
function toast(text){$('toast').textContent=text;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,5500);}
function addReport(value){report.push(typeof value==='string'?value:JSON.stringify(value,null,2));report=report.slice(-15);$('report').textContent=report.join('\n\n');}
function failure(error){const message=error.message||String(error);$('job-status').textContent=message==='Job cancelled'?'Job cancelled':'Job could not finish';$('job-detail').textContent=message.split('\n')[0];$('progress').hidden=true;addReport(message);$('report-panel').open=true;toast(message.split('\n')[0]);}
function busyState(value){busy=value;$('cancel').hidden=!value;for(const id of ['quick-export','render','preview-focused','preview-stack','auto','demo','hero-demo','empty-demo'])$(id).disabled=value;for(const id of ['source-file','load-project'])$(id).disabled=value;}
async function task(fn){if(busy){toast('A job is already running. Cancel it before starting another.');return;}busyState(true);try{await fn();}catch(e){failure(e);}finally{busyState(false);}}
function downloadBlob(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);}
function escape(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function filtered(){const terms=$('search').value.toLowerCase().split(/\s+/).filter(Boolean),category=$('category').value;return catalog.filter(e=>(!category||e.category===category)&&(!$('selected-only').checked||project.effects[e.id]?.enabled)&&(!$('heavy-only').checked||e.cost==='heavy'||['error_dither','pixel_sort'].includes(e.id))&&terms.every(t=>(e.id+' '+e.name+' '+e.description+' '+e.category).toLowerCase().includes(t)));}
function renderLibrary(){
  $('range-count').textContent=`${highlighted.size} highlighted`;
  const rows=filtered();$('filter-count').textContent=`${rows.length} / ${catalog.length} shown`;
  $('effect-list').innerHTML=rows.map(e=>{const s=project.effects[e.id]||defaults();return `<div role="option" aria-selected="${highlighted.has(e.id)}" class="effect-row ${e.id===focus?'active':''} ${highlighted.has(e.id)?'highlighted':''}" data-id="${e.id}"><input type="checkbox" aria-label="Enable ${escape(e.name)}" ${s.enabled?'checked':''}><button class="effect-focus" aria-label="Inspect ${escape(e.name)}"><strong>${escape(e.name)}</strong><small>${escape(e.category)} · ${e.fidelity}</small></button><span class="status" title="${e.asset?'Needs an asset':e.cost==='heavy'?'Expensive operation':'Built-in operation'}">${s.locked?'L ':''}${e.asset?'◇':e.cost==='heavy'||e.id==='error_dither'?'!':'○'}</span></div>`;}).join('')||'<div class="chain-empty">No effects match. Try a broader search.</div>';
}
function renderChain(){
  const rows=selected();$('selected-count').textContent=rows.length;$('chain-tab-count').textContent=rows.length;
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
  clearResult();source=file;info=null;project.source=file.name;persist();if(sourceURL)URL.revokeObjectURL(sourceURL);sourceURL=URL.createObjectURL(file);
  $('source-name').textContent=file.name;$('media-info').textContent=`${(file.size/1e6).toFixed(1)} MB · LOCAL FILE`;$('start').value=0;showSource();$('job-status').textContent='Source loaded';$('job-detail').textContent='Choose effects and generate a preview. No media has been uploaded.';
}
function clearResult(){
  result=null;if(resultURL)URL.revokeObjectURL(resultURL);resultURL=null;
  $('view-result').disabled=true;$('download').hidden=true;$('download-manifest').hidden=true;$('monitor-download').hidden=true;
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
    $('view-result').disabled=false;showResult();$('download').href=resultURL;$('download').hidden=false;$('download').download=mode==='full'?'signal-box.mp4':'signal-box-preview.mp4';$('download-manifest').hidden=false;$('monitor-download').href=resultURL;$('monitor-download').download=$('download').download;$('monitor-download').hidden=false;showSide('chain');
    addReport(result.manifest);$('media-info').textContent=`${result.info.width}×${result.info.height} · ${result.info.duration.toFixed(2)}s`;
  });
}
async function auto(){
  if(!source){toast('Open a video first. Adaptive selection examines your actual source.');return;}
  await task(async()=>{const analysis=await engine.analyze(source);for(const s of Object.values(project.effects))if(!s.locked)s.enabled=false;for(const r of analysis.recommendations){const s=setting(r.id);if(!s.locked){s.enabled=true;s.strength=r.strength;}}update();addReport(analysis);$('report-panel').open=true;$('activity-dialog').showModal();toast(`Analyzed ${analysis.frames_examined} frames. Recommendations and reasons are below.`);});
}
function validateLoaded(p){if(p?.schema!==1||typeof p.effects!=='object'||!p.effects)throw new Error('This is not a Signalbox v1 project');for(const [id,s] of Object.entries(p.effects)){if(!byId.has(id))throw new Error('Unknown effect: '+id);if(typeof s.enabled!=='boolean'||!Number.isFinite(s.strength)||s.strength<0||s.strength>1)throw new Error('Invalid effect setting: '+id);}return {...project,...p};}
function syncSettings(){for(const name of ['width','fps','seed','crf'])$(name).value=project[name];}
$('effect-list').addEventListener('click',ev=>{
  const row=ev.target.closest('.effect-row');if(!row)return;const id=row.dataset.id;
  selectEffect(id,ev.shiftKey,ev.ctrlKey||ev.metaKey);
  if(ev.target.matches('input')){
    const ids=ev.shiftKey?[...highlighted]:[id];for(const key of ids)setting(key).enabled=ev.target.checked;update();
  }else{renderLibrary();inspect();}
  $('effect-list').focus({preventScroll:true});
});
$('chain').addEventListener('click',ev=>{const row=ev.target.closest('.chain-item');if(!row)return;if(ev.target.closest('.remove')){setting(row.dataset.id).enabled=false;update();}else{focus=row.dataset.id;inspect();renderLibrary();showSide('inspector');}});
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
$('load-project').onchange=async()=>{try{const file=$('load-project').files[0];if(!file)return;project=validateLoaded(JSON.parse(await file.text()));assets={};clearResult();source=null;if(sourceURL)URL.revokeObjectURL(sourceURL);sourceURL=null;$('monitor-video').removeAttribute('src');$('monitor-video').hidden=true;$('empty-monitor').hidden=false;$('source-name').textContent='Reselect source video';syncSettings();update();toast('Project loaded. Reselect its source video and effect assets.');}catch(e){failure(e);}finally{$('load-project').value='';}};
$('download-manifest').onclick=()=>{if(result)downloadBlob(new Blob([JSON.stringify(result.manifest,null,2)],{type:'application/json'}),'signal-box-render.json');};
$('cancel').onclick=()=>{engine.cancel();};
$('theme').onclick=()=>{document.body.classList.toggle('night');try{localStorage.setItem('signal-box-theme',document.body.classList.contains('night')?'night':'day');}catch{}};
try{document.body.classList.toggle('night',localStorage.getItem('signal-box-theme')==='night');}catch{}
for(const button of document.querySelectorAll('.guide-jump'))button.onclick=()=>{$('category').value=button.dataset.category;$('search').value='';$('selected-only').checked=false;renderLibrary();$('studio').scrollIntoView({behavior:'smooth'});};
const drop=$('dropzone');drop.addEventListener('dragover',e=>{e.preventDefault();drop.classList.add('dragging');});drop.addEventListener('dragleave',()=>drop.classList.remove('dragging'));drop.addEventListener('drop',e=>{e.preventDefault();drop.classList.remove('dragging');setSource(e.dataTransfer.files[0]);});
$('monitor-video').addEventListener('loadedmetadata',()=>{if($('view-source').classList.contains('active')){const v=$('monitor-video');if(Number.isFinite(v.duration)){$('media-info').textContent=`${v.videoWidth}×${v.videoHeight} · ${v.duration.toFixed(1)}s`;$('start').max=v.duration;$('duration').max=v.duration;}}});
$('monitor-video').addEventListener('error',()=>{if(source)$('job-detail').textContent='This container cannot play natively here. The FFmpeg engine may still decode it for a preview.';});
window.addEventListener('beforeunload',e=>{if(busy){e.preventDefault();e.returnValue='';}});
try{const response=await fetch('catalog.json');if(!response.ok)throw new Error('Catalog failed to load');const data=await response.json();catalog=data.effects;byId=new Map(catalog.map(e=>[e.id,e]));presets=data.presets;for(const group of new Set(catalog.map(e=>e.category))){const option=document.createElement('option');option.value=option.textContent=group;$('category').append(option);}for(const id of Object.keys(project.effects))if(!byId.has(id))delete project.effects[id];syncSettings();update();}catch(e){failure(e);}


// Workspace interaction model: selection is independent of enabled effects.
function selectEffect(id,extend=false,toggle=false){
  const rows=filtered().map(e=>e.id);const anchor=selectionAnchor&&rows.includes(selectionAnchor)?selectionAnchor:focus;
  if(extend&&rows.includes(anchor)){const a=rows.indexOf(anchor),b=rows.indexOf(id);highlighted=new Set(rows.slice(Math.min(a,b),Math.max(a,b)+1));}
  else if(toggle){highlighted.has(id)?highlighted.delete(id):highlighted.add(id);selectionAnchor=id;}
  else{highlighted=new Set([id]);selectionAnchor=id;}
  focus=id;
}
function actionIds(){return highlighted.size?[...highlighted]:byId.has(focus)?[focus]:[];}
function batch(action){
  const ids=actionIds();if(!ids.length)return;
  const lock=!ids.every(id=>setting(id).locked),enable=!ids.every(id=>setting(id).enabled);
  for(const id of ids){const s=setting(id);if(action==='lock')s.locked=lock;else if(action==='toggle')s.enabled=enable;else s.enabled=action==='enable';}
  update();
}
function undoRedo(delta){
  const next=historyIndex+delta;if(next<0||next>=history.length)return;
  historyIndex=next;restoring=true;project=JSON.parse(history[next]);syncSettings();update();restoring=false;
  toast(delta<0?'Undid project change.':'Redid project change.');
}
function workspace(name){$('studio').dataset.workspace=name;document.querySelectorAll('[data-workspace]').forEach(el=>{if(el.tagName==='BUTTON')el.classList.toggle('active',el.dataset.workspace===name);});}
function showSide(name){
  const isChain=name==='chain';$('inspector').hidden=isChain;document.querySelector('.chain-panel').hidden=!isChain;
  $('inspector-tab').setAttribute('aria-selected',String(!isChain));$('chain-tab').setAttribute('aria-selected',String(isChain));
}
function closeContext(){$('context-menu').hidden=true;}
function openHelp(tab='workflow'){
  document.querySelectorAll('[data-help]').forEach(b=>b.classList.toggle('active',b.dataset.help===tab));
  document.querySelectorAll('[data-help-panel]').forEach(p=>p.hidden=p.dataset.helpPanel!==tab);
  if(!$('help-dialog').open)$('help-dialog').showModal();
}
function playPause(){const v=$('monitor-video');if(v.hidden)return;v.paused?v.play().catch(()=>{}):v.pause();}
function mark(which){
  const v=$('monitor-video');if(v.hidden)return;
  if(!$('view-source').classList.contains('active')){toast('Switch to Source to mark source-time positions.');return;}
  if(which==='start')$('start').value=v.currentTime.toFixed(2);
  else $('duration').value=Math.max(.1,v.currentTime-Number($('start').value)).toFixed(2);
  toast(which==='start'?'Preview start set to playhead.':'Preview end set to playhead.');
}
const commands=[
 ['Open video','Ctrl/⌘ O',()=>$('source-file').click()],
 ['Load test signal','',demo],['Save project','Ctrl/⌘ S',()=>$('save-project').click()],
 ['Load project','',()=>$('load-project').click()],['Undo','Ctrl/⌘ Z',()=>undoRedo(-1)],['Redo','Ctrl/⌘ Shift Z',()=>undoRedo(1)],
 ['Search effects','/',()=>{workspace('library');$('search').focus();}],
 ['Preview inspected effect','P',()=>runRender('effect')],['Preview signal chain','Shift P',()=>runRender('stack')],
 ['Export full video','Ctrl/⌘ Enter',()=>runRender('full')],['Analyze and adapt','Alt A',auto],['Random chaos','Alt C',chaos],
 ['Enable highlighted effects','',()=>batch('enable')],['Disable highlighted effects','Delete',()=>batch('disable')],
 ['Toggle highlighted effects','Space',()=>batch('toggle')],['Lock / unlock highlighted effects','L',()=>batch('lock')],
 ['Enable every effect','',()=>$('select-all').click()],['Clear signal chain','',()=>$('clear').click()],
 ['Highlight all filtered effects','Ctrl/⌘ A',()=>{highlighted=new Set(filtered().map(e=>e.id));renderLibrary();workspace('library');}],
 ['Show library','1',()=>workspace('library')],['Show monitor','2',()=>workspace('monitor')],
 ['Show inspector','3',()=>{workspace('side');showSide('inspector');}],['Show signal chain','4',()=>{workspace('side');showSide('chain');}],
 ['Render settings','',()=>$('settings-toggle').click()],['View activity','',()=>$('report-open').click()],
 ['Switch color theme','',()=>$('theme').click()],['Play / pause video','K',playPause],
 ['Mark preview start','I',()=>mark('start')],['Mark preview end','O',()=>mark('end')],
 ['Keyboard shortcuts','?',()=>openHelp('keys')],['Cancel current job','',()=>{if(busy)engine.cancel();}]
];
function matchingCommands(){const q=$('command-search').value.toLowerCase().trim();return commands.filter(c=>c[0].toLowerCase().includes(q));}
function renderCommands(){const list=matchingCommands();commandIndex=Math.max(0,Math.min(commandIndex,list.length-1));$('command-list').innerHTML=list.map((c,i)=>`<button class="command-item ${i===commandIndex?'active':''}" role="option" aria-selected="${i===commandIndex}" data-command="${commands.indexOf(c)}"><span>${escape(c[0])}</span>${c[1]?`<kbd>${escape(c[1])}</kbd>`:''}</button>`).join('')||'<div class="chain-empty">No matching commands.</div>';}
function openCommands(){$('command-search').value='';commandIndex=0;renderCommands();$('command-dialog').showModal();$('command-search').focus();}
function executeCommand(command){$('command-dialog').close();command?.[2]();}
$('command-open').onclick=openCommands;$('command-search').oninput=()=>{commandIndex=0;renderCommands();};
$('command-list').onclick=e=>{const row=e.target.closest('[data-command]');if(row)executeCommand(commands[Number(row.dataset.command)]);};
$('command-search').onkeydown=e=>{
  if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();const n=matchingCommands().length;commandIndex=(commandIndex+(e.key==='ArrowDown'?1:-1)+n)%Math.max(1,n);renderCommands();$('command-list').querySelector('.active')?.scrollIntoView({block:'nearest'});}
  if(e.key==='Enter'){e.preventDefault();executeCommand(matchingCommands()[commandIndex]);}
};
$('shortcut-list').innerHTML=commands.filter(c=>c[1]).map(c=>`<div><span>${escape(c[0])}</span><kbd>${escape(c[1])}</kbd></div>`).join('')+'<div><span>Select a range</span><kbd>Shift click / Shift ↑ ↓</kbd></div><div><span>Add to selection</span><kbd>Ctrl/⌘ click</kbd></div><div><span>Seek video</span><kbd>J / ;</kbd></div>';
$('help-open').onclick=()=>openHelp();document.querySelectorAll('[data-help]').forEach(b=>b.onclick=()=>openHelp(b.dataset.help));
document.querySelectorAll('[data-dialog-close]').forEach(b=>b.onclick=()=>b.closest('dialog').close());
document.querySelectorAll('dialog').forEach(d=>d.addEventListener('click',e=>{if(e.target===d){const r=d.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)d.close();}}));
$('report-open').onclick=()=>{$('report-panel').open=true;$('activity-dialog').showModal();};
document.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>{$(b.dataset.close).hidden=true;$('settings-toggle').setAttribute('aria-expanded','false');});
$('inspector-tab').onclick=()=>showSide('inspector');$('chain-tab').onclick=()=>showSide('chain');
document.querySelectorAll('button[data-workspace]').forEach(b=>b.onclick=()=>workspace(b.dataset.workspace));
$('quick-export').onclick=()=>runRender('full');$('undo').onclick=()=>undoRedo(-1);$('redo').onclick=()=>undoRedo(1);
$('batch-enable').onclick=()=>batch('enable');$('batch-disable').onclick=()=>batch('disable');$('batch-lock').onclick=()=>batch('lock');
$('mark-start').onclick=()=>mark('start');$('mark-end').onclick=()=>mark('end');
document.addEventListener('contextmenu',e=>{
  if(e.target.closest('input,textarea,pre,video,a,[contenteditable]'))return;
  e.preventDefault();const row=e.target.closest('.effect-row,.chain-item');
  if(row){if(!highlighted.has(row.dataset.id))selectEffect(row.dataset.id);else focus=row.dataset.id;renderLibrary();inspect();}
  const items=row?[
    ['Enable highlighted',()=>batch('enable'),''],['Disable highlighted',()=>batch('disable'),'Del'],['Lock / unlock',()=>batch('lock'),'L'],
    ['Inspect effect',()=>{showSide('inspector');workspace('side');},'3'],['Preview inspected effect',()=>runRender('effect'),'P'],
    ['Preview signal chain',()=>runRender('stack'),'⇧ P'],['Highlight all filtered',()=>{highlighted=new Set(filtered().map(e=>e.id));renderLibrary();},'⌘ A']
  ]:[['Open video',()=>$('source-file').click(),'⌘ O'],['Save project',()=>$('save-project').click(),'⌘ S'],['Undo',()=>undoRedo(-1),'⌘ Z'],['Redo',()=>undoRedo(1),'⇧ ⌘ Z'],['Commands',openCommands,'⌘ K'],['Shortcuts',()=>openHelp('keys'),'?']];
  const menu=$('context-menu');menu.innerHTML=`<div class="context-title">${row?`${actionIds().length} HIGHLIGHTED · SIGNAL BOX`:'SIGNAL BOX / WORKSPACE'}</div>`+items.map((item,i)=>`<button class="context-item" role="menuitem" data-action="${i}"><span>${escape(item[0])}</span><kbd>${escape(item[2])}</kbd></button>`).join('');
  menu.hidden=false;menu.style.left=Math.max(8,Math.min(e.clientX,innerWidth-243))+'px';menu.style.top=Math.max(8,Math.min(e.clientY,innerHeight-menu.offsetHeight-8))+'px';
  menu.onclick=ev=>{const item=ev.target.closest('[data-action]');if(item){closeContext();items[Number(item.dataset.action)][1]();}};menu.querySelector('button')?.focus();
});
document.addEventListener('pointerdown',e=>{if(!e.target.closest('#context-menu'))closeContext();});
window.addEventListener('resize',closeContext);document.addEventListener('scroll',closeContext,true);
document.addEventListener('keydown',e=>{
  const mod=e.ctrlKey||e.metaKey,key=e.key.toLowerCase(),input=e.target.closest('input,textarea,select,[contenteditable]');
  if(e.key==='Escape'){closeContext();$('settings').hidden=true;return;}
  if(mod&&key==='k'){e.preventDefault();if(!$('command-dialog').open)openCommands();return;}
  if(!$('context-menu').hidden){
    if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();const buttons=[...$('context-menu').querySelectorAll('button')],i=buttons.indexOf(document.activeElement);buttons[(i+(e.key==='ArrowDown'?1:-1)+buttons.length)%buttons.length]?.focus();}
    return;
  }
  if(document.querySelector('dialog[open]'))return;
  if(mod&&key==='s'){e.preventDefault();$('save-project').click();return;}
  if(mod&&key==='o'){e.preventDefault();if(!busy)$('source-file').click();return;}
  if(mod&&e.key==='Enter'){e.preventDefault();runRender('full');return;}
  if(input)return;
  if(e.key===' '&&e.target.closest('button,a,summary')&&!e.target.closest('.catalog-panel'))return;
  if(mod&&key==='z'){e.preventDefault();undoRedo(e.shiftKey?1:-1);return;}
  if(mod&&key==='y'){e.preventDefault();undoRedo(1);return;}
  if(mod&&key==='a'){e.preventDefault();highlighted=new Set(filtered().map(x=>x.id));renderLibrary();workspace('library');$('effect-list').focus();return;}
  if(mod)return;
  if(e.altKey){if(key==='a'){e.preventDefault();auto();}if(key==='c'){e.preventDefault();chaos();}return;}
  if(e.key==='ArrowDown'||e.key==='ArrowUp'){
    if(!e.target.closest('.catalog-panel'))return;e.preventDefault();const rows=filtered();if(!rows.length)return;
    const index=Math.max(0,rows.findIndex(x=>x.id===focus)),next=Math.max(0,Math.min(rows.length-1,index+(e.key==='ArrowDown'?1:-1)));
    selectEffect(rows[next].id,e.shiftKey);renderLibrary();inspect();$('effect-list').focus();$('effect-list').querySelector(`[data-id="${focus}"]`)?.scrollIntoView({block:'nearest'});return;
  }
  const actions={'/':()=>{workspace('library');$('search').focus();},' ':()=>batch('toggle'),'delete':()=>batch('disable'),'backspace':()=>batch('disable'),'l':()=>batch('lock'),'p':()=>runRender(e.shiftKey?'stack':'effect'),'k':playPause,'i':()=>mark('start'),'o':()=>mark('end'),'j':()=>{$('monitor-video').currentTime=Math.max(0,$('monitor-video').currentTime-2);},';':()=>{$('monitor-video').currentTime+=2;},'?':()=>openHelp('keys'),'1':()=>workspace('library'),'2':()=>workspace('monitor'),'3':()=>{workspace('side');showSide('inspector');},'4':()=>{workspace('side');showSide('chain');}};
  if(actions[key]){e.preventDefault();actions[key]();}
});
persist();
