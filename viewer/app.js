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
 if(!selected||busy)return;file=selected;busy=true;requestVersion++;$('workspace').hidden=true;$('preview').hidden=true;
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
  $('workspace').hidden=false;await resetRange();
 }catch(error){summary=null;status(error.error||error.message||String(error),true);if(error.preview){$('preview').textContent='Перший рядок / попередній перегляд:\n'+JSON.stringify(error.preview,null,2);$('preview').hidden=false;document.querySelector('.import').open=true;}}
 finally{busy=false;$('reload').disabled=false;}
}
async function resetRange(){if(!summary)return;const s=summary.segments[Number($('segment').value)];$('start').value=0;$('end').value=s.duration_s;await update();}
async function update(){
 if(!summary)return;const version=++requestVersion;
 const start=Number($('start').value),end=Number($('end').value),channels=['I_A','P_W','Wh_net',$('channel').value].filter(k=>summary.channels[k]);
 try{const q=new URLSearchParams({segment:$('segment').value,start,end,channels:[...new Set(channels)].join(','),pixels:Math.floor($('current').clientWidth||1000)});
 const result=await api('/api/window?'+q);if(version!==requestVersion)return;latest=result;render();
 }catch(error){if(version===requestVersion)status(error.error||String(error),true);}
}
function card(title,value,detail){const box=document.createElement('div');box.className='card';const label=document.createElement('span'),strong=document.createElement('strong'),small=document.createElement('small');label.textContent=title;strong.textContent=value;small.textContent=detail;box.append(label,strong,small);return box;}
function render(){if(!latest||!summary)return;const current=latest.stats.I_A, key=$('channel').value, second=latest.stats[key], power=latest.stats.P_W, recorded=latest.stats.Wh_net;
 $('cards').replaceChildren(card('Середній струм',number(current?.mean)+' A',`Мін ${number(current?.min)} · Макс ${number(current?.max)}`),card(key,number(second?.mean)+' '+(summary.channels[key]||''),`Мін ${number(second?.min)} · Макс ${number(second?.max)}`),card('Покритий час',number(current?.covered_s)+' с',`Без даних / поза вимірами: ${number(current?.missing_s)} с`),card('Заряд + / −',`${number(current?.positive)} / ${number(current?.negative)} Ah`,'Перераховано лише на покритих інтервалах'),card('Енергія + / −',`${number(power?.positive)} / ${number(power?.negative)} Wh`,'Перераховано за потужністю та фактичним часом'),card('Зміна записаного Wh_net',number(recorded?.last!=null&&recorded?.first!=null?recorded.last-recorded.first:null)+' Wh','Різниця лічильника у файлі; окремо від перерахунку'));
 $('other-title').textContent=key+' · '+summary.channels[key];draw($('current'),latest.envelopes.I_A||[],'#a4e5c3');draw($('other'),latest.envelopes[key]||[],'#a4c9f1');
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
 canvas.dataset.left=left;canvas.dataset.right=right;
}
for(const canvas of [$('current'),$('other')]){let anchor=null;canvas.addEventListener('pointerdown',e=>{if(!latest)return;anchor=e.offsetX;canvas.setPointerCapture(e.pointerId);});canvas.addEventListener('pointerup',e=>{if(anchor===null||!latest)return;const from=anchor;anchor=null;if(Math.abs(e.offsetX-from)<5)return;const left=Number(canvas.dataset.left),right=Number(canvas.dataset.right),t=x=>latest.start+Math.max(0,Math.min(1,(x-left)/(right-left)))*(latest.end-latest.start);$('start').value=t(Math.min(from,e.offsetX));$('end').value=t(Math.max(from,e.offsetX));update();});canvas.addEventListener('dblclick',resetRange);}
$('file').addEventListener('change',e=>openFile(e.target.files[0]));$('reload').onclick=()=>openFile(file);$('apply').onclick=update;$('reset').onclick=resetRange;$('segment').onchange=resetRange;$('channel').onchange=update;
$('drop').addEventListener('dragover',e=>{e.preventDefault();$('drop').classList.add('dragging');});$('drop').addEventListener('dragleave',()=>$('drop').classList.remove('dragging'));$('drop').addEventListener('drop',e=>{e.preventDefault();$('drop').classList.remove('dragging');openFile(e.dataTransfer.files[0]);});
$('report').onclick=()=>{if(!summary)return;const blob=new Blob([JSON.stringify({summary,selection:latest},null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='r1-viewer-report.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
window.addEventListener('resize',()=>{if(latest)render();});
if(directFile){status(launchHelp,true);$('file').disabled=true;$('reload').disabled=true;$('filename').textContent='Відкрито index.html напряму. Для читання записів запусти start.cmd.';}
