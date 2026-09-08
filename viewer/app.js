'use strict';
const $=id=>document.getElementById(id), token=document.querySelector('meta[name=viewer-token]').content;
const directFile=location.protocol==='file:';
const launchHelp='Ця версія потребує локального запуску. Закрий index.html і запусти viewer/start.cmd або python viewer/server.py — браузер відкриється за правильною адресою.';
let file=null, summary=null, latest=null, requestVersion=0, busy=false;
const number=v=>v===null||v===undefined?'—':Number(v).toLocaleString('uk-UA',{maximumFractionDigits:6});
function status(text,error=false){$('status').textContent=text;$('status').classList.toggle('error',error);}
async function api(path,options={}){const response=await fetch(path,{...options,headers:{'X-Viewer-Token':token,...options.headers}});const body=await response.json();if(!response.ok)throw body;return body;}
async function openFile(selected){
 if(directFile){status(launchHelp,true);return;}
 if(!selected||busy)return;file=selected;busy=true;requestVersion++;hoverVersion++;markerVersion++;clearTimeout(hoverTimer);latest=null;$('workspace').hidden=true;$('preview').hidden=true;
 $('filename').textContent=file.name;status('Читаю файл і перевіряю дані…');$('reload').disabled=true;
 const options={mapping:$('mapping').value,delimiter:$('delimiter').value==='tab'?'\t':$('delimiter').value,decimal_comma:$('decimal').value==='comma',max_gap_ms:Number($('gap').value),utc_offset_min:$('zone').value===''?null:Number($('zone').value)};
 try{summary=await api('/api/load',{method:'POST',headers:{'Content-Type':'application/octet-stream','X-Viewer-Options':JSON.stringify(options),'X-Viewer-Name':encodeURIComponent(file.name)},body:file});
  $('format').textContent=summary.format;$('counts').textContent=`${number(summary.rows)} вимірів · ${summary.segments.length} сегм. · ${summary.invalid_rows} непридатних`;
  $('segment').replaceChildren(...summary.segments.map(s=>new Option(`${s.id+1} · ${number(s.duration_s)} с`,s.id)));
  $('channel').replaceChildren(...Object.keys(summary.channels).filter(k=>k!=='I_A').map(k=>new Option(`${k} · ${summary.channels[k]}`,k)));
  if(summary.channels.U_V)$('channel').value='U_V';
  $('metadata').textContent=JSON.stringify(summary.metadata,null,2);$('diagnostics').replaceChildren();
  for(const d of summary.diagnostics){const p=document.createElement('p');p.textContent=(d.line?`Рядок ${d.line}: `:'')+d.message;$('diagnostics').append(p);}
  const integrity=summary.integrity==='verified clean'?'Контрольні суми збігаються.':summary.integrity==='interrupted'?'Файл перерваний. Показано лише перевірену частину.':'Старий формат без контрольних сум.';
  status(`${integrity} Пропущено рядків: ${summary.skipped_rows}; неперевірений хвіст: ${summary.unverified_rows}${summary.partial_line?' + незавершений рядок':''}.`);
  if(!summary.rows){status('Файл прочитано, але перевірених придатних для відображення рядків немає.',true);return;}
  initWorkspace();$('workspace').hidden=false;await resetRange();
 }catch(error){summary=null;status(error.error||error.message||String(error),true);if(error.preview){$('preview').textContent='Перший рядок / попередній перегляд:\n'+JSON.stringify(error.preview,null,2);$('preview').hidden=false;document.querySelector('.import').open=true;}}
 finally{busy=false;$('reload').disabled=false;}
}
async function resetRange(){if(!summary)return;const s=summary.segments[Number($('segment').value)];$('start').value=0;$('end').value=s.duration_s;await update();}
async function update(){
 if(!summary)return;const version=++requestVersion;
 const start=Number($('start').value),end=Number($('end').value),channels=[...new Set(['I_A','P_W','Wh_net',$('channel').value,...selectedChannels()])].filter(k=>summary.channels[k]);
 try{const q=new URLSearchParams({segment:$('segment').value,start,end,channels:[...new Set(channels)].join(','),pixels:Math.floor(document.querySelector('#plots canvas')?.clientWidth||1000)});
 const result=await api('/api/window?'+q);if(version!==requestVersion)return;latest=result;render();
 }catch(error){if(version===requestVersion)status(error.error||String(error),true);}
}
function card(title,value,detail){const box=document.createElement('div');box.className='card';const label=document.createElement('span'),strong=document.createElement('strong'),small=document.createElement('small');label.textContent=title;strong.textContent=value;small.textContent=detail;box.append(label,strong,small);return box;}
function render(){if(!latest||!summary)return;const current=latest.stats.I_A, key=$('channel').value, second=latest.stats[key], power=latest.stats.P_W, recorded=latest.stats.Wh_net;
 $('cards').replaceChildren(card('Середній струм',number(current?.mean)+' A',`Мін ${number(current?.min)} · Макс ${number(current?.max)}`),card(key,number(second?.mean)+' '+(summary.channels[key]||''),`Мін ${number(second?.min)} · Макс ${number(second?.max)}`),card('Покритий час',number(current?.covered_s)+' с',`Без даних / поза вимірами: ${number(current?.missing_s)} с`),card('Заряд + / −',`${number(current?.positive)} / ${number(current?.negative)} Ah`,'Перераховано лише на покритих інтервалах'),card('Енергія + / −',`${number(power?.positive)} / ${number(power?.negative)} Wh`,'Перераховано за потужністю та фактичним часом'),card('Зміна записаного Wh_net',number(recorded?.last!=null&&recorded?.first!=null?recorded.last-recorded.first:null)+' Wh','Різниця лічильника у файлі; окремо від перерахунку'));
 renderPlots();
}
function draw(canvas,bins,color){const ratio=devicePixelRatio||1,w=canvas.clientWidth,h=245;canvas.width=w*ratio;canvas.height=h*ratio;const ctx=canvas.getContext('2d');ctx.scale(ratio,ratio);ctx.clearRect(0,0,w,h);
 const left=65,right=w-15,top=18,bottom=h-35,valid=bins.filter(b=>b.min!==null);let low=valid.length?Math.min(...valid.map(b=>b.min)):0,high=valid.length?Math.max(...valid.map(b=>b.max)):1;
 if(high===low){const pad=Math.max(.01,Math.abs(high)*.05);low-=pad;high+=pad;}const py=v=>bottom-(v-low)/(high-low)*(bottom-top),px=t=>left+(t-latest.start)/Math.max(latest.end-latest.start,1e-12)*(right-left);
 ctx.font='11px system-ui';ctx.lineWidth=1;for(let i=0;i<=4;i++){const y=top+(bottom-top)*i/4;ctx.strokeStyle='#304044';ctx.beginPath();ctx.moveTo(left,y);ctx.lineTo(right,y);ctx.stroke();ctx.fillStyle='#9cacae';ctx.fillText(number(high-(high-low)*i/4),3,y+4);}
 const ticks=w<500?2:4;for(let i=0;i<=ticks;i++){const t=latest.start+(latest.end-latest.start)*i/ticks;ctx.fillStyle='#9cacae';ctx.fillText(number(t)+' с',Math.min(right-42,Math.max(left,px(t)-15)),h-9);}
 ctx.strokeStyle=color;ctx.lineWidth=1.5;let prior=null;for(const b of bins){if(b.min===null){prior=null;continue;}const x=px((b.x0+b.x1)/2);ctx.beginPath();ctx.moveTo(x,py(b.min));ctx.lineTo(x,py(b.max));ctx.stroke();
 // A bin containing a discontinuity is shown as isolated extrema, never a bridge.
 if(!b.broken&&prior){ctx.beginPath();ctx.moveTo(prior.x,prior.y);ctx.lineTo(x,py((b.min+b.max)/2));ctx.stroke();}
 ctx.fillStyle=color;ctx.fillRect(x-1,py((b.min+b.max)/2)-1,2,2);prior=b.broken?null:{x,y:py((b.min+b.max)/2)};}
 canvas.dataset.left=left;canvas.dataset.right=right;canvas.plotScale={left,right,top,bottom,low,high};drawMarkers(canvas,ctx,px,py);
}
$('file').addEventListener('change',e=>openFile(e.target.files[0]));$('reload').onclick=()=>openFile(file);$('apply').onclick=update;$('reset').onclick=resetRange;$('segment').onchange=()=>{hoverVersion++;clearTimeout(hoverTimer);$('sample-info').textContent='Наведи курсор на вимір нового сегмента.';clearMarkers();resetRange();};$('channel').onchange=update;
$('drop').addEventListener('dragover',e=>{e.preventDefault();$('drop').classList.add('dragging');});$('drop').addEventListener('dragleave',()=>$('drop').classList.remove('dragging'));$('drop').addEventListener('drop',e=>{e.preventDefault();$('drop').classList.remove('dragging');openFile(e.dataTransfer.files[0]);});
$('report').onclick=()=>{if(!summary)return;const blob=new Blob([JSON.stringify({summary,selection:latest,markers,markerStats},null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='r1-viewer-report.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
window.addEventListener('resize',()=>{if(latest)render();});
if(directFile){status(launchHelp,true);$('file').disabled=true;$('reload').disabled=true;$('filename').textContent='Відкрито index.html напряму. Для читання записів запусти start.cmd.';}
// R5 interaction state is independent from the viewport and extrema previews.
let markers={times:[],values:[]}, markerStats=null, markerVersion=0, hoverVersion=0, hoverTimer;
const palette=['#a4e5c3','#a4c9f1','#f2be81','#e4a9db','#dce58f','#9bdedc'];
function selectedChannels(){return [...document.querySelectorAll('#series input:checked')].map(el=>el.value);}
function initWorkspace(){
 clearMarkers();hoverVersion++;clearTimeout(hoverTimer);$('sample-info').textContent='Наведи курсор: тут буде точний вимір із файлу.';
 $('series').replaceChildren();
 Object.keys(summary.channels).forEach((key,i)=>{const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.value=key;input.checked=['I_A','U_V'].includes(key);input.onchange=()=>{rebuildPlots();update();};label.append(input,document.createTextNode(key+' · '+summary.channels[key]));$('series').append(label);});
 rebuildPlots();
}
function rebuildPlots(){
 $('plots').replaceChildren();selectedChannels().forEach((key,i)=>{const section=document.createElement('section'),title=document.createElement('h2'),canvas=document.createElement('canvas');section.className='panel plot';title.textContent=key+' · '+summary.channels[key];canvas.dataset.channel=key;canvas.dataset.color=palette[i%palette.length];canvas.id=key==='I_A'?'current':key==='U_V'?'other':'plot-'+i;canvas.setAttribute('aria-label',title.textContent);canvas.setAttribute('role','img');section.append(title,canvas);$('plots').append(section);bindPlot(canvas);});
}
function renderPlots(){document.querySelectorAll('#plots canvas').forEach(canvas=>draw(canvas,latest.envelopes[canvas.dataset.channel]||[],canvas.dataset.color));}
function drawMarkers(canvas,ctx,px,py){
 const s=canvas.plotScale;ctx.save();ctx.beginPath();ctx.rect(s.left,s.top,s.right-s.left,s.bottom-s.top);ctx.clip();ctx.strokeStyle='#ffc989';ctx.fillStyle='#ffc989';ctx.setLineDash([5,4]);
 markers.times.forEach((m,i)=>{const x=px(m.seconds);ctx.beginPath();ctx.moveTo(x,s.top);ctx.lineTo(x,s.bottom);ctx.stroke();ctx.fillText((i?'B':'A')+' '+number(m.seconds)+' с',x+4,s.top+12);});
 markers.values.forEach((m,i)=>{if(m.channel!==canvas.dataset.channel)return;const y=py(m.value);ctx.beginPath();ctx.moveTo(s.left,y);ctx.lineTo(s.right,y);ctx.stroke();ctx.fillText((i?'D':'C')+' '+number(m.value),s.left+4,y-4);});ctx.restore();
}
function markerText(){
 const lines=markers.times.map((m,i)=>`${i?'B':'A'}: ${number(m.seconds)} с · t_us=${m.row.t_us} · ${m.row.timestamp||'час не вказаний'} · quality=${m.row.quality} · рядок ${m.row.line}`);
 if(markers.times.length===2){lines.push('Δt (B − A): '+number(markers.times[1].seconds-markers.times[0].seconds)+' с');}
 markers.values.forEach((m,i)=>lines.push(`${i?'D':'C'}: ${number(m.value)} ${summary?.channels[m.channel]||''} (${m.channel})`));
 if(markers.values.length===2)lines.push('Δ (D − C): '+number(markers.values[1].value-markers.values[0].value)+' '+summary.channels[markers.values[0].channel]);
 if(markerStats){lines.push('Повні дані між A і B:');for(const [key,st] of Object.entries(markerStats.stats))lines.push(`${key}: середнє ${number(st.mean)}, min ${number(st.min)}, max ${number(st.max)}; покрито ${number(st.covered_s)} с, без даних ${number(st.missing_s)} с`);}
 $('marker-info').textContent=lines.join('\n')||'Постав A і B кліками на графіку.';
 $('zoom-markers').disabled=markers.times.length!==2;
}
function clearMarkers(){markers={times:[],values:[]};markerStats=null;markerVersion++;markerText();if(latest)renderPlots();}
async function placeTime(seconds){
 const version=++markerVersion,segment=$('segment').value;
 try{const sample=await api('/api/sample?'+new URLSearchParams({segment,seconds}));if(version!==markerVersion)return;
 markers.times.push(sample);if(markers.times.length>2)markers.times.shift();markerStats=null;markerText();renderPlots();
 if(markers.times.length===2){const [start,end]=markers.times.map(m=>m.seconds).sort((a,b)=>a-b),channels=Object.keys(summary.channels);const result=await api('/api/window?'+new URLSearchParams({segment,start,end,channels:channels.join(','),pixels:50}));if(version!==markerVersion)return;markerStats=result;markerText();}
 }catch(error){if(version===markerVersion)status(error.error||String(error),true);}
}
function viewport(start,end){
 const duration=summary.segments[Number($('segment').value)].duration_s,span=Math.min(duration,Math.max(.000001,end-start));start=Math.max(0,Math.min(start,duration-span));$('start').value=start;$('end').value=start+span;update();
}
function bindPlot(canvas){
 let anchor=null, clickTimer;
 const position=e=>{const r=canvas.getBoundingClientRect(),s=canvas.plotScale,x=e.clientX-r.left,y=e.clientY-r.top;return {x,y,inside:s&&x>=s.left&&x<=s.right&&y>=s.top&&y<=s.bottom,t:latest.start+Math.max(0,Math.min(1,(x-s.left)/(s.right-s.left)))*(latest.end-latest.start),value:s.high-(y-s.top)/(s.bottom-s.top)*(s.high-s.low)};};
 canvas.addEventListener('pointerdown',e=>{if(!latest||!canvas.plotScale||e.button!==0)return;const p=position(e);if(!p.inside)return;anchor={...p,start:latest.start,end:latest.end,mode:$('gesture').value,shift:e.shiftKey};canvas.setPointerCapture(e.pointerId);});
 canvas.addEventListener('pointerup',e=>{if(!anchor||!latest)return;const from=anchor;anchor=null;const p=position(e),drag=Math.abs(p.x-from.x)>=5;
 if(from.mode==='pan'&&drag){const shift=(from.x-p.x)/(canvas.plotScale.right-canvas.plotScale.left)*(from.end-from.start);viewport(from.start+shift,from.end+shift);}
 else if(from.mode==='zoom'&&drag)viewport(Math.min(from.t,p.t),Math.max(from.t,p.t));
 else if(!drag&&from.mode==='markers'){
 if(from.shift){const key=canvas.dataset.channel;if(markers.values[0]?.channel!==key)markers.values=[];markers.values.push({channel:key,value:p.value});if(markers.values.length>2)markers.values.shift();markerText();renderPlots();}
 else {clearTimeout(clickTimer);clickTimer=setTimeout(()=>placeTime(p.t),240);}
 }});
 canvas.addEventListener('pointercancel',()=>{anchor=null;});
 canvas.addEventListener('wheel',e=>{if(!latest||!canvas.plotScale)return;const p=position(e);if(!p.inside)return;e.preventDefault();const factor=e.deltaY>0?1.3:1/1.3;viewport(p.t+(latest.start-p.t)*factor,p.t+(latest.end-p.t)*factor);},{passive:false});
 canvas.addEventListener('dblclick',()=>{clearTimeout(clickTimer);resetRange();});
 canvas.addEventListener('pointermove',e=>{
 if(!latest||!canvas.plotScale||anchor)return;const p=position(e);if(!p.inside)return;clearTimeout(hoverTimer);const version=++hoverVersion,segment=$('segment').value;
 hoverTimer=setTimeout(async()=>{try{const hit=await api('/api/sample?'+new URLSearchParams({segment,seconds:p.t}));if(version!==hoverVersion)return;const r=hit.row;
 $('sample-info').textContent=`Найближчий вимір: ${number(hit.seconds)} с (від курсора ${number(hit.distance_s)} с)\n${r.timestamp||'Час не вказаний'} · t_us=${r.t_us} · рядок ${r.line} · quality=${r.quality}${r.break_before?' · розрив перед виміром':''}${r.quality&1?' · НЕПРИДАТНИЙ':''}\n`+selectedChannels().map(k=>`${k}: ${number(r[k])} ${summary.channels[k]}`).join(' · ');
 }catch(error){if(version===hoverVersion)$('sample-info').textContent=error.error||String(error);}},90);
 });
 canvas.addEventListener('pointerleave',()=>{clearTimeout(hoverTimer);hoverVersion++;});
}
$('clear-markers').onclick=clearMarkers;
$('zoom-markers').onclick=()=>{if(markers.times.length===2){const [a,b]=markers.times.map(m=>m.seconds).sort((a,b)=>a-b);viewport(a,b);}};
