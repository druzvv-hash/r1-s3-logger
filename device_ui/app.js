/* The hardware owns all mutations. A browser draft is never saved implicitly. */
const $=id=>document.getElementById(id);
const labels={
shunt_uohm:['Опір шунта, µΩ','400 A / 60 mV = 150 µΩ'],
polarity:['Полярність струму','+1 — звичайна; −1 — інвертувати'],
i_zero_uV:['Нуль струму, µV','Зсув вхідної напруги шунта'],
i_gain:['Коефіцієнт струму','1 = без корекції масштабу'],
u_zero_V:['Нуль напруги, V','Віднімається перед коефіцієнтом'],
u_gain:['Коефіцієнт напруги','1 = без корекції масштабу'],
requested_rate_hz:['Частота вимірів, Hz','Реальна частота INA228: 10, 50 або 100 Hz'],
adc_range:['Діапазон шунта','0: ±163.84 mV · 1: ±40.96 mV; вузький не охоплює 400 A'],
vshunt_ct_code:['Час конверсії шунта','Код 0–7: 50, 84, 150, 280, 540, 1052, 2074, 4120 µs'],
vbus_ct_code:['Час конверсії VBUS','Код 0–7: 50 … 4120 µs'],
temp_ct_code:['Час конверсії температури','Код 0–7: 50 … 4120 µs'],
average_code:['Усереднення ADC','Код 0–7: 1, 4, 16, 64, 128, 256, 512, 1024'],
ready_timeout_us:['Очікування ADC, µs','Має вміщувати конверсії з усередненням'],
max_gap_us:['Межа розриву, µs','Для майбутнього записувача'],
flush_interval_ms:['Інтервал flush, ms','Для майбутнього записувача'],
queue_bytes:['Бюджет FIFO, байти','Виділяється при запуску; зміна потребує перезапуску'],
rotation_bytes:['Розмір частини, байти','Для майбутнього записувача'],
reserve_bytes:['Резерв на SD, байти','Для майбутнього записувача'],
allow_unknown_utc:['Дозволити невідомий UTC','Для майбутнього записувача'],
display_hz:['Оновлення OLED, Hz','Оновлення екрана, не частота вимірів'],
live_hz:['Пакети Live, Hz','В одному пакеті кілька вимірів; USB може обмежувати частоту доставки'],
display_filter_tau_ms:['Фільтр OLED, ms','0 = без фільтра; графік панелі показує нефільтровані дані'],
display_utc_offset_min:['Зсув від UTC, хвилини','Для майбутнього UI; панель показує UTC'],
calibration_id:['Ідентифікатор калібрування','Назва процедури або еталона'],
calibration_note:['Примітка калібрування','Умови та прилади'],
calibration_utc:['UTC калібрування','YYYY-MM-DDTHH:MM:SSZ або порожньо'],
calibration_valid:['Калібрування підтверджено','Вмикати лише після перевірки еталоном'],
oled_contrast:['Контраст OLED','0–255']
};
const groups=[
['Вимірювання та коефіцієнти',REGISTRY.slice(0,6)],
['Аналого-цифрове перетворення',REGISTRY.slice(6,13)],
['Буфер і майбутній запис',REGISTRY.slice(13,19)],
['Екран і Live',REGISTRY.slice(19,23).concat(REGISTRY.slice(27))],
['Походження калібрування',REGISTRY.slice(23,27)]
];
let state=null,base=null,baseBoot='',baseRevision=0,dirty=false,busy=false,online=false,paused=false,points=[],lastSample=null;
let lastReceived=0,polling=false,stopped=false;
let liveCursor=0,liveBoot='',lastLiveAt=0,clockAt=0,clockDevice=0,streamGaps=0,frameCount=0,fps=0,fpsAt=performance.now(),lastFrame=0;
let nextBreak=false;
function resetStream(boot=''){points=[];liveCursor=0;liveBoot=boot;clockAt=0;lastLiveAt=0;nextBreak=true;}
function meters(u,i){$('volts').textContent=number(u,4);$('amps').textContent=number(i,4);$('watts').textContent=number(Number.isFinite(u)&&Number.isFinite(i)?u*i:null,3);}

function notice(text,error=false){$('notice').textContent=text;$('notice').classList.toggle('error',error);}
function makeFields(){
  for(const [title,fields] of groups){
    const fieldset=document.createElement('fieldset'),legend=document.createElement('legend'),grid=document.createElement('div');
    legend.textContent=title;grid.className='field-grid';fieldset.append(legend,grid);
    for(const f of fields){
      const label=document.createElement('label'),name=document.createElement('span'),help=document.createElement('small');
      label.className='field';name.textContent=labels[f.name][0];help.textContent=labels[f.name][1];
      let input=document.createElement(f.enum?'select':'input');input.id='f-'+f.name;input.name=f.name;
      if(f.enum)for(const value of f.enum){const option=document.createElement('option');option.value=value;option.textContent=value;input.append(option);}
      else if(f.type==='bool')input.type='checkbox';
      else if(f.type==='utf8'){input.type='text';input.maxLength=f.max_bytes;}
      else{input.type='number';input.step=f.type==='f64'?'any':'1';if(f.min!=null)input.min=f.min;if(f.max!=null)input.max=f.max;}
      label.append(name,input,help);grid.append(label);
    }
    $('config-form').append(fieldset);
  }
}
function values(){const out={};for(const f of REGISTRY){const el=$('f-'+f.name);out[f.name]=f.type==='bool'?el.checked:f.type==='utf8'?el.value:el.value.trim()===''?NaN:Number(el.value);}return out;}
function fill(config){for(const f of REGISTRY){const el=$('f-'+f.name);if(f.type==='bool')el.checked=config[f.name];else el.value=config[f.name];}updateDraft();}
function reload(){if(!state)return;base=decodeConfig(state.config_hex,REGISTRY);baseBoot=state.boot;baseRevision=state.revision;fill(base);}
function stale(){return !!state&&(baseBoot!==state.boot||baseRevision!==state.revision);}
function recordingBusy(){return ['STARTING','RUNNING','STOPPING'].includes(state?.recording_state);}
function updateDraft(){
  const current=values(),changes=base?REGISTRY.filter(f=>current[f.name]!==base[f.name]):[];
  dirty=changes.length>0;let invalid='';
  try{validateConfig(current,REGISTRY);}catch(e){invalid=e.message;}
  $('changes').textContent=changes.map(f=>labels[f.name][0]+': '+String(base[f.name])+' → '+String(current[f.name])).join('\n');
  $('draft-note').textContent=stale()?'Стан змінився. Прочитай з логера заново.':invalid|| (dirty?'Змін у чернетці: '+changes.length:'Чернетка відповідає логеру');
  $('apply').disabled=recordingBusy()||!online||busy||!base||stale()||!dirty||!!invalid;
  $('save').disabled=recordingBusy()||!online||busy||!base||stale()||dirty||state?.settings_status!=='UNSAVED';
  $('export').disabled=!base||!!invalid;
}
function rows(id,items){const dl=$(id);dl.replaceChildren();for(const [label,value] of items){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=String(value);dl.append(dt,dd);}}
function number(v,n=3){return Number.isFinite(v)?v.toFixed(n):'—';}
function setOffline(error){online=false;document.body.classList.add('offline');$('connection').textContent='Немає зв’язку';$('connection').classList.remove('online');for(const id of ['amps','volts','watts'])$(id).textContent='—';$('temperature').textContent='Температура INA228: —';notice(error,true);controls();}
function controls(){
  $('apply-rate').disabled=recordingBusy()||busy||!online||dirty||stale()||!state||Number($('quick-rate').value)===state.requested_hz;
  $('rate-note').textContent=dirty?'Спочатку застосуй або скинь чернетку в налаштуваннях.':state?.settings_status==='UNSAVED'?'Застосовано. Щоб залишити після перезапуску — збережи в EEPROM у налаштуваннях.':'Частота вимірів і FPS незалежні. Збереження в EEPROM — у налаштуваннях.';
  for(const el of document.querySelectorAll('[data-command],#sync-time'))el.disabled=recordingBusy()||busy||!online;
  $('record-start').disabled=recordingBusy()||busy||!online||dirty||!state?.recording_available;
  $('record-stop').disabled=busy||!online||state?.recording_state!=='RUNNING';
  $('record-files').disabled=recordingBusy()||busy||!online;
  $('files-refresh').disabled=recordingBusy()||!online;updateDraft();}
function render(s){
  if(!s.ready)throw Error('Логер запускається. Очікуємо готовності.');
  // HTTP may still answer from core 0 when the hardware owner's snapshot stops.
  if(!state||s.boot!==state.boot||s.uptime_ms!==state.uptime_ms)lastReceived=Date.now();
  if(Date.now()-lastReceived>5000)throw Error('Знімок стану логера застарів');
  const wasOffline=!online;
  if(state&&s.boot!==state.boot){resetStream(s.boot);lastSample=null;notice('Логер перезапустився. Перевір стан і налаштування.',true);}
  const previousRate=state?.requested_hz;
  state=s;if(previousRate!==s.requested_hz)$('quick-rate').value=s.requested_hz||50;online=true;document.body.classList.remove('offline');
  $('release-usb').hidden=s.transport!=='usb';
  $('connection').textContent='● Логер підключений';$('connection').classList.add('online');
  const valid=s.valid&&((s.uptime_ms-s.sample_at_ms)>>>0)<3500;
  if(!s.live_available)meters(valid?s.volts:null,valid?s.amps:null);
  $('temperature').textContent='Температура INA228: '+(valid?number(s.temp_c,2)+' °C':'—');
  $('utc').textContent=s.utc?new Date(s.utc*1000).toISOString().replace('T',' ').replace('.000Z',' UTC'):'RTC: потрібно встановити час';
  $('cadence').textContent=(s.requested_hz||'—')+' Гц задано · '+number(s.measured_hz,1)+' Гц фактично';
  if(wasOffline)notice('Логер підключений. Можна змінювати навантаження та запускати тести.');
  rows('health',[['INA228',s.ina],['microSD',s.sd==='READ'?'Читання OK':s.sd],['24C32',s.eeprom==='READ'?'Читання OK':s.eeprom],['DS3231',s.rtc],['OLED',s.oled?'Працює':'Недоступний']]);
  rows('memory',[['FIFO в PSRAM',s.buffer_ready?(s.queue_bytes/1024)+' KiB · підготовлено':'Не виділено'],['Блок SD у внутрішній SRAM',(s.sd_block_bytes/1024)+' KiB'],['Вільна PSRAM',(s.psram_free/1048576).toFixed(2)+' MiB'],['Вільна внутрішня пам’ять',(s.heap_free/1024).toFixed(1)+' KiB']]);
  rows('raw',[['Вхід шунта',valid?number(s.shunt_uv,4)+' µV':'—'],['VSHUNT / VBUS / TEMP raw',valid?[s.shunt_raw,s.bus_raw,s.temp_raw].join(' / '):'—'],['I²C: адрес / помилок',s.i2c_count+' / '+s.i2c_errors],['Ядро апаратних тестів / UI',s.owner_core+' / '+s.ui_core],['Час після запуску',Math.floor(s.uptime_ms/1000)+' s']]);
  rows('timing',[['Задана / виміряна частота',(s.requested_hz||'—')+' / '+number(s.measured_hz,2)+' Hz'],['Коректні / некоректні відліки',s.valid_samples+' / '+s.invalid_samples],['Пропущені періоди',s.missed_samples],['Найбільша затримка старту',(s.max_late_us/1000).toFixed(2)+' ms'],['Читання INA / фрагмент OLED',(s.max_read_us/1000).toFixed(2)+' / '+(s.oled_chunk_us/1000).toFixed(2)+' ms'],['Планові паузи на команди',s.maintenance_count+' · '+s.maintenance_ms+' ms'],['Втрати preview / кадри OLED',s.preview_drops+' / '+s.oled_frames]]);
  rows('network',[['Точка доступу',s.ap_ready?'Увімкнена':'Запуск / недоступна'],['Назва мережі',s.ssid]]);
  $('wifi-password').textContent=s.ap_password;
  $('generation').textContent='EEPROM · покоління '+s.generation;
  $('config-state').textContent=({'SAVED':'Застосовано та збережено','UNSAVED':'Застосовано, ще не збережено','BLOCKED':'EEPROM заблоковано: перевір формат','APPLY FAIL':'Помилка застосування'})[s.settings_status]||s.settings_status;
  $('footer-device').textContent='R1-S3 · прошивка '+s.firmware+' · '+(s.boot||'');
  $('file-transfer').textContent=s.file_transfer?'Передача / читання SD':s.files_available?'Готово до читання':'Потрібна прошивка v0.16+';
  const phase=s.recording_state||'UNAVAILABLE';
  $('record-state').textContent=({READY:'Готовий',STARTING:'Відкриття файлу…',RUNNING:'● ЗАПИС',STOPPING:'Збереження…',ERROR:'Помилка запису'})[phase]||'Потрібна прошивка v0.18+';
  $('record-state').classList.toggle('recording',phase==='RUNNING');
  $('record-path').textContent=s.recording_path||'';
  $('record-note').textContent=phase==='ERROR'?(s.recording_error+' · Незавершений файл залишено для перевірки.'):
    phase==='RUNNING'?'Виміри записуються на картку. Можна закрити браузер.':phase==='STOPPING'?'Дописування буфера й закриття файлу — зачекай.':phase==='STARTING'?'Перевірка картки та створення нового файлу.':s.recording_path?'Файл збережено. Можна завантажити його у вкладці «Файли SD».':'Почни новий запис, коли навантаження готове.';
  rows('record-stats',[['Тривалість',number(s.recording_seconds,1)+' с'],['Відліків / записано байтів',(s.recording_rows||0)+' / '+fileSize(s.recording_bytes||0)],['Енергія / заряд',number(s.recording_wh,6)+' Wh / '+number(s.recording_ah,6)+' Ah'],['FIFO: зараз / максимум',(s.recording_queued||0)+' / '+(s.recording_high_water||0)],['Переповнення FIFO',s.recording_overflows||0],['Найдовший запис / синхронізація',number(s.recording_write_us/1000,2)+' / '+number(s.recording_sync_us/1000,2)+' ms']]);
  if(recordingBusy())$('file-transfer').textContent='Доступ після Stop';
  if(!base)reload();
  // Preserve a dirty draft when another client changes the configuration.
  else if(!dirty&&stale())reload();
  controls();
}
async function api(path,body){
  const options={cache:'no-store',signal:AbortSignal.timeout(14000)};
  if(body!=null){options.method='POST';options.headers={'Content-Type':'text/plain','X-R1-Panel':'1'};options.body=body;}
  const token=new URLSearchParams(location.search).get('token');
  const response=await fetch(path+(token?(path.includes('?')?'&':'?')+'token='+encodeURIComponent(token):''),options),data=await response.json();
  if(!response.ok)throw Error(data.message||'HTTP '+response.status);return data;
}
async function refresh(){render(await api('/api/state'));}
async function command(verb,arg='',useDraft=false){
  if(!online||busy||!state)return;busy=true;controls();notice('Виконується команда…');
  try{
    const boot=useDraft?baseBoot:state.boot,revision=useDraft?baseRevision:state.revision;
    const response=await api('/api/command',boot+' '+revision+' '+verb+(arg?' '+arg:''));
    if(!response.ok)throw Error(response.message);
    // Owner publishes a new snapshot at most 500 ms after the acknowledged command.
    await new Promise(r=>setTimeout(r,600));await refresh();
    if(verb==='APPLY'||verb==='SAVE')reload();
    notice(verb==='START'?'Запит запису прийнято. Стеж за станом запису.':verb==='STOP'?'Завершуємо запис. Дочекайся закриття файлу.':(verb==='APPLY'?'Налаштування застосовано. Збереження в EEPROM — окремо. ':verb==='SAVE'?'EEPROM: запис і перевірка завершені. ':'Тест завершено. ')+response.message);
  }catch(e){notice('Команда: '+e.message+'. Онови стан перед повторенням.',true);try{await refresh();}catch{}}
  finally{busy=false;controls();}
}

let fileDirectory='/',fileSession=0,fileBusy=false;
function pathHex(path){return Array.from(new TextEncoder().encode(path),b=>b.toString(16).padStart(2,'0')).join('');}
function pathText(hex){return new TextDecoder('utf-8',{fatal:true}).decode(Uint8Array.from(hex.match(/../g),s=>parseInt(s,16)));}
function fileNotice(text){$('files-status').textContent=text;}
async function filesCommand(command){const r=await api('/api/files?command='+encodeURIComponent(command));if(!r.ok)throw Error(r.message||'Помилка читання SD');return r;}
async function closeDirectory(){const id=fileSession;fileSession=0;$('files-more').hidden=true;if(id)await filesCommand('CLOSE '+id);}
function fileSize(size){return size<1024?size+' B':size<1048576?(size/1024).toFixed(1)+' KiB':(size/1048576).toFixed(2)+' MiB';}
async function listFiles(directory=fileDirectory,more=false){
  if(fileBusy)return;
  if(!online||!state?.files_available){fileNotice('Потрібне підключення до логера з прошивкою v0.16+.');return;}
  fileBusy=true;$('files-refresh').disabled=true;$('files-more').disabled=true;
  try{
    fileNotice('Читання картки…');
    if(!more){await closeDirectory();fileDirectory=directory;$('files-path').textContent=directory;$('file-list').replaceChildren();}
    const result=await filesCommand(more?'NEXT '+fileSession:'LIST '+pathHex(directory));
    fileSession=result.more?result.session:0;
    for(const entry of result.entries){
      const row=document.createElement('div'),name=document.createElement('span'),size=document.createElement('small'),button=document.createElement('button');
      row.className='file-row';name.textContent=(entry.directory?'📁 ':'')+entry.name;
      size.textContent=entry.directory?'Папка':fileSize(entry.size);button.textContent=entry.directory?'Відкрити':'Завантажити';
      button.disabled=!entry.path;
      button.onclick=()=>entry.directory?listFiles(pathText(entry.path)):downloadFile(entry);
      row.append(name,size,button);$('file-list').append(row);
    }
    $('files-more').hidden=!result.more;$('files-up').disabled=directory==='/';
    fileNotice($('file-list').children.length?'Файлів і папок: '+$('file-list').children.length+(result.more?' · є наступна сторінка':''):'Папка порожня.');
  }catch(e){fileSession=0;$('files-more').hidden=true;fileNotice(e.message+' · Спробуй оновити список.');}
  finally{fileBusy=false;$('files-refresh').disabled=false;$('files-more').disabled=false;}
}
async function downloadFile(entry){
  if(fileBusy)return;fileBusy=true;
  try{
    await closeDirectory();
    // Check access now so card/busy errors appear in the panel, before starting a browser download.
    const opened=await filesCommand('OPEN '+entry.path);
    await filesCommand('CLOSE '+opened.session);
    const token=new URLSearchParams(location.search).get('token');
    const a=document.createElement('a');a.href='/api/download?path='+entry.path+(token?'&token='+encodeURIComponent(token):'');
    a.download=entry.name;a.target='file-download';document.body.append(a);a.click();a.remove();
    fileNotice('Завантаження «'+entry.name+'» запитано. Прогрес і результат — у завантаженнях браузера.');
  }catch(e){fileNotice('Не вдалося завантажити: '+e.message);}
  finally{fileBusy=false;}
}

function acceptLive(batch){
  if(!state || batch.boot!==state.boot)return; // State/configuration must belong to this boot.
  if(liveBoot!==batch.boot)resetStream(batch.boot);
  if(!Array.isArray(batch.samples))throw Error('Потрібна прошивка з потоком Live');
  if(batch.lost){streamGaps++;nextBreak=true;liveCursor=0;return;} // Resume from the live tail.
  for(const row of batch.samples){
    if(!Array.isArray(row)||row.length!==6||!row.every(Number.isFinite)||!Number.isSafeInteger(row[0])||!Number.isSafeInteger(row[1]))throw Error('Некоректний пакет Live');
    const [id,tUs,u,i,q,revision]=row;
    if(id<=liveCursor)continue;
    const gap=nextBreak || (liveCursor>0&&id!==liveCursor+1) || !!(q&2);
    if(liveCursor&&((q&2)||(id!==liveCursor+1&&!batch.lost)))streamGaps++;
    liveCursor=id;nextBreak=false;
    if(!paused)points.push({id,t:tUs/1000,u:q&5?null:u,i:q&5?null:i,gap,revision});
    else nextBreak=true;
    if(tUs/1000>clockDevice || !clockAt){clockDevice=tUs/1000;clockAt=performance.now();}
    lastLiveAt=performance.now();
    const recent=((state.uptime_ms-Math.floor(tUs/1000))|0)<2500;
    if(online)meters((q&5)||!recent?null:u,(q&5)||!recent?null:i);
  }
  if(points.length>6000)points.splice(0,points.length-6000);
}
async function pollLive(){
  const began=performance.now();
  if(!busy&&!stopped&&online&&!document.hidden){
    try{acceptLive(await api('/api/live?after='+liveCursor));}
    catch(e){if(!busy){meters(null,null);$('stream-status').textContent='Потік: '+e.message;}}
  }
  // Frequency is a delivery target, not an extra set of ADC conversions.
  let hz=base?.live_hz||5;
  if(state?.config_hex){try{hz=decodeConfig(state.config_hex,REGISTRY).live_hz;}catch{}}
  setTimeout(pollLive,Math.max(15,1000/hz-(performance.now()-began)));
}
function draw(now=performance.now()){
  const canvas=$('chart'),rect=canvas.getBoundingClientRect();if(!rect.width)return false;
  const dpr=window.devicePixelRatio||1,w=rect.width,h=rect.height;
  const pw=Math.round(w*dpr),ph=Math.round(h*dpr);
  if(canvas.width!==pw||canvas.height!==ph){canvas.width=pw;canvas.height=ph;}
  const c=canvas.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);
  const left=65,right=w-15,span=Number($('chart-window').value)*1000;
  c.fillStyle='#0b1016';c.fillRect(0,0,w,h);c.font='11px system-ui';
  if(!points.length){c.fillStyle='#8095a5';c.fillText('Очікування вимірів…',left,50);return true;}
  // Delay only the viewport, not the samples. Scroll between actual packets at display cadence.
  const t1=paused?points.at(-1).t:clockDevice+Math.min(Math.max(0,now-clockAt),1000)-300;
  const t0=t1-span,visible=points.filter(p=>p.t>=t0&&p.t<=t1);
  for(const [index,key,color,unit] of [[0,'i','#00c8ff','A'],[1,'u','#ffd600','V']]){
    const top=18+index*(h/2),height=h/2-43,vals=visible.map(p=>p[key]).filter(Number.isFinite);
    let min=vals.length?Math.min(...vals):0,max=vals.length?Math.max(...vals):1,pad=Math.max((max-min)*.15,.005);
    min-=pad;max+=pad;
    for(let j=0;j<3;j++){const y=top+j*height/2;c.strokeStyle='#22303a';c.beginPath();c.moveTo(left,y);c.lineTo(right,y);c.stroke();c.fillStyle='#8294a2';c.fillText((max-j*(max-min)/2).toFixed(3),4,y+4);}
    c.fillStyle=color;c.fillText(unit,4,top+height+17);
    c.strokeStyle=color;c.lineWidth=1.7;c.beginPath();let last=null;
    for(const p of visible){
      if(!Number.isFinite(p[key])){last=null;continue;}
      const x=left+(p.t-t0)/span*(right-left),y=top+(max-p[key])/(max-min)*height;
      if(last&&!p.gap&&p.revision===last.revision)c.lineTo(x,y);else c.moveTo(x,y);
      last=p;
    }c.stroke();
    const tail=visible.at(-1);if(tail&&Number.isFinite(tail[key])){c.fillStyle=color;c.beginPath();c.arc(left+(tail.t-t0)/span*(right-left),top+(max-tail[key])/(max-min)*height,2.5,0,Math.PI*2);c.fill();}
  }
  c.fillStyle='#8294a2';c.fillText('-'+span/1000+' s',left,h-4);c.fillText('зараз',Math.max(left,right-40),h-4);
  return true;
}
function animate(now){
  const target=Number($('frame-rate').value);
  if(!document.hidden&&!$('live').hidden&&!paused&&now-lastFrame>=1000/target-.25){
    if(draw(now))frameCount++;
    lastFrame+=Math.max(1,Math.floor((now-lastFrame+.25)/(1000/target)))*(1000/target);
  }
  if(now-fpsAt>=1000){
    fps=frameCount*1000/(now-fpsAt);frameCount=0;fpsAt=now;
    const fresh=lastLiveAt&&now-lastLiveAt<2500&&((state.uptime_ms-Math.floor(clockDevice))|0)<2500;
    $('stream-status').textContent=(paused?'Графік на паузі':number(fps,0)+' FPS')+' · '+(fresh?'потік наживо':'немає нових відліків')+' · розривів: '+streamGaps;
    if(!fresh&&state?.live_available)meters(null,null);
  }
  requestAnimationFrame(animate);
}
makeFields();
$('files-refresh').onclick=()=>listFiles();
$('record-start').onclick=async()=>{try{await closeDirectory();await command('START');}catch(e){notice(e.message,true);}};
$('record-stop').onclick=()=>command('STOP');
$('record-files').onclick=()=>{document.querySelector('[data-tab="files"]').click();listFiles('/records');};
$('files-more').onclick=()=>listFiles(fileDirectory,true);
$('files-up').onclick=()=>listFiles(fileDirectory.slice(0,fileDirectory.lastIndexOf('/'))||'/');
$('file-download').onload=()=>{try{const text=$('file-download').contentDocument.body.textContent;if(text){const r=JSON.parse(text);if(r.message)fileNotice('Не вдалося завантажити: '+r.message);}}catch{}};
$('config-form').addEventListener('submit',e=>e.preventDefault());$('config-form').addEventListener('input',updateDraft);
document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>{document.querySelectorAll('.page').forEach(p=>p.hidden=p.id!==b.dataset.tab);document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active',t===b));draw();});
document.querySelectorAll('[data-command]').forEach(b=>b.onclick=()=>command(b.dataset.command));
$('sync-time').onclick=()=>command('TIME',String(Math.floor(Date.now()/1000)));
$('release-usb').onclick=async()=>{
  if(busy)return;stopped=true;
  try{await api('/api/shutdown','');setOffline('USB-сервер зупинено. Можна прошивати. Для повернення до панелі запусти device_ui/start.cmd.');}
  catch(e){stopped=false;notice(e.message,true);}
};
$('apply').onclick=()=>{try{command('APPLY',encodeConfig(values(),REGISTRY),true);}catch(e){notice(e.message,true);}};
$('save').onclick=()=>command('SAVE','',true);
$('reload-config').onclick=async()=>{try{await refresh();reload();notice('Конфігурацію прочитано з логера.');}catch(e){notice(e.message,true);}};
$('defaults').onclick=()=>{fill(Object.fromEntries(REGISTRY.map(f=>[f.name,f.default])));notice('Типові значення лише в чернетці.');};
$('quick-rate').onchange=controls;
$('apply-rate').onclick=()=>{if(!state||dirty||stale())return;const config=decodeConfig(state.config_hex,REGISTRY);config.requested_rate_hz=Number($('quick-rate').value);config.max_gap_us=Math.max(config.max_gap_us,2*1000000/config.requested_rate_hz);command('APPLY',encodeConfig(config,REGISTRY));};
$('pause').onclick=()=>{paused=!paused;$('pause').textContent=paused?'Продовжити графік':'Пауза графіка';};
$('clear-chart').onclick=()=>{points=[];draw();};
$('export').onclick=()=>{try{const v=values();validateConfig(v,REGISTRY);const url=URL.createObjectURL(new Blob([JSON.stringify({schema:'r1s3-config',major:1,minor:0,values:v},null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='r1s3-config-draft.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){notice(e.message,true);}};
$('import').onclick=()=>$('profile-file').click();
$('profile-file').onchange=async()=>{
  try{const file=$('profile-file').files[0];if(!file)return;if(file.size>16000)throw Error('JSON завеликий');const obj=JSON.parse(await file.text());if(!obj||Object.keys(obj).sort().join(',')!=='major,minor,schema,values'||obj.schema!=='r1s3-config'||obj.major!==1||obj.minor!==0)throw Error('Непідтримуваний профіль');validateConfig(obj.values,REGISTRY);fill(obj.values);notice('Профіль імпортовано в чернетку. Перевір різницю перед застосуванням.');}catch(e){notice(e.message,true);}finally{$('profile-file').value='';}
};
window.addEventListener('resize',()=>draw());
document.addEventListener('visibilitychange',()=>{if(!document.hidden){liveCursor=0;nextBreak=true;clockAt=0;}});
$('chart-window').onchange=()=>draw();
requestAnimationFrame(animate);
setInterval(()=>{if(online&&Date.now()-lastReceived>5000)setOffline('Дані застаріли. Перевір підключення логера.');},1000);
async function poll(){if(!busy&&!polling&&!stopped){polling=true;try{await refresh();}catch(e){setOffline('Немає відповіді: '+e.message);}finally{polling=false;}}setTimeout(poll,1000);}
controls();draw();
if(location.protocol==='file:')setOffline('Це панель пристрою. Запусти device_ui/start.cmd на ПК або відкрий http://192.168.4.1 у мережі логера.');
else {poll();pollLive();}
