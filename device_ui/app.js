/* The hardware owns all mutations. A browser draft is never saved implicitly. */
const $=id=>document.getElementById(id);
const labels={
shunt_uohm:['Опір шунта, µΩ','400 A / 60 mV = 150 µΩ'],
polarity:['Полярність струму','+1 — звичайна; −1 — інвертувати'],
i_zero_uV:['Нуль струму, µV','Зсув вхідної напруги шунта'],
i_gain:['Коефіцієнт струму','1 = без корекції масштабу'],
u_zero_V:['Нуль напруги, V','Віднімається перед коефіцієнтом'],
u_gain:['Коефіцієнт напруги','1 = без корекції масштабу'],
requested_rate_hz:['Частота майбутнього запису, Hz','Поки діагностичний цикл ≈1 Hz'],
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
live_hz:['Майбутній Live, Hz','Ця тестова панель опитує раз на секунду'],
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
function updateDraft(){
  const current=values(),changes=base?REGISTRY.filter(f=>current[f.name]!==base[f.name]):[];
  dirty=changes.length>0;let invalid='';
  try{validateConfig(current,REGISTRY);}catch(e){invalid=e.message;}
  $('changes').textContent=changes.map(f=>labels[f.name][0]+': '+String(base[f.name])+' → '+String(current[f.name])).join('\n');
  $('draft-note').textContent=stale()?'Стан змінився. Прочитай з логера заново.':invalid|| (dirty?'Змін у чернетці: '+changes.length:'Чернетка відповідає логеру');
  $('apply').disabled=!online||busy||!base||stale()||!dirty||!!invalid;
  $('save').disabled=!online||busy||!base||stale()||dirty||state?.settings_status!=='UNSAVED';
  $('export').disabled=!base||!!invalid;
}
function rows(id,items){const dl=$(id);dl.replaceChildren();for(const [label,value] of items){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=String(value);dl.append(dt,dd);}}
function number(v,n=3){return Number.isFinite(v)?v.toFixed(n):'—';}
function setOffline(error){online=false;document.body.classList.add('offline');$('connection').textContent='Немає зв’язку';$('connection').classList.remove('online');for(const id of ['amps','volts','watts'])$(id).textContent='—';$('temperature').textContent='Температура INA228: —';notice(error,true);controls();}
function controls(){for(const el of document.querySelectorAll('[data-command],#sync-time'))el.disabled=busy||!online;updateDraft();}
function render(s){
  if(!s.ready)throw Error('Логер запускається. Очікуємо готовності.');
  // HTTP may still answer from core 0 when the hardware owner's snapshot stops.
  if(!state||s.boot!==state.boot||s.uptime_ms!==state.uptime_ms)lastReceived=Date.now();
  if(Date.now()-lastReceived>5000)throw Error('Знімок стану логера застарів');
  const wasOffline=!online;
  if(state&&s.boot!==state.boot){points=[];lastSample=null;notice('Логер перезапустився. Перевір стан і налаштування.',true);}
  state=s;online=true;document.body.classList.remove('offline');
  $('release-usb').hidden=s.transport!=='usb';
  $('connection').textContent='● Логер підключений';$('connection').classList.add('online');
  const valid=s.valid&&((s.uptime_ms-s.sample_at_ms)>>>0)<3500;
  for(const key of ['amps','volts','watts'])$(key).textContent=valid?number(s[key],key==='watts'?3:4):'—';
  $('temperature').textContent='Температура INA228: '+(valid?number(s.temp_c,2)+' °C':'—');
  $('utc').textContent=s.utc?new Date(s.utc*1000).toISOString().replace('T',' ').replace('.000Z',' UTC'):'RTC: потрібно встановити час';
  $('cadence').textContent='Діагностичний цикл ≈1 Hz · відлік '+s.sample_id;
  if(wasOffline)notice('Логер підключений. Можна змінювати навантаження та запускати тести.');
  rows('health',[['INA228',s.ina],['microSD',s.sd==='READ'?'Читання OK':s.sd],['24C32',s.eeprom==='READ'?'Читання OK':s.eeprom],['DS3231',s.rtc],['OLED',s.oled?'Працює':'Недоступний']]);
  rows('memory',[['FIFO в PSRAM',s.buffer_ready?(s.queue_bytes/1024)+' KiB · підготовлено':'Не виділено'],['Блок SD у внутрішній SRAM',(s.sd_block_bytes/1024)+' KiB'],['Вільна PSRAM',(s.psram_free/1048576).toFixed(2)+' MiB'],['Вільна внутрішня пам’ять',(s.heap_free/1024).toFixed(1)+' KiB']]);
  rows('raw',[['Вхід шунта',valid?number(s.shunt_uv,4)+' µV':'—'],['VSHUNT / VBUS / TEMP raw',valid?[s.shunt_raw,s.bus_raw,s.temp_raw].join(' / '):'—'],['I²C: адрес / помилок',s.i2c_count+' / '+s.i2c_errors],['Ядро апаратних тестів / UI',s.owner_core+' / '+s.ui_core],['Час після запуску',Math.floor(s.uptime_ms/1000)+' s']]);
  rows('network',[['Точка доступу',s.ap_ready?'Увімкнена':'Запуск / недоступна'],['Назва мережі',s.ssid]]);
  $('wifi-password').textContent=s.ap_password;
  $('generation').textContent='EEPROM · покоління '+s.generation;
  $('config-state').textContent=({'SAVED':'Застосовано та збережено','UNSAVED':'Застосовано, ще не збережено','BLOCKED':'EEPROM заблоковано: перевір формат','APPLY FAIL':'Помилка застосування'})[s.settings_status]||s.settings_status;
  $('footer-device').textContent='R1-S3 · прошивка '+s.firmware+' · '+(s.boot||'');
  if(!base)reload();
  // Preserve a dirty draft when another client changes the configuration.
  else if(!dirty&&stale())reload();
  if(lastSample!==s.boot+':'+s.sample_id){
    if(!paused)points.push({t:s.sample_at_ms,i:valid?s.amps:null,u:valid?s.volts:null});
    if(points.length>120)points.shift();lastSample=s.boot+':'+s.sample_id;draw();
  }
  controls();
}
async function api(path,body){
  const options={cache:'no-store',signal:AbortSignal.timeout(14000)};
  if(body!=null){options.method='POST';options.headers={'Content-Type':'text/plain','X-R1-Panel':'1'};options.body=body;}
  const token=new URLSearchParams(location.search).get('token');
  const response=await fetch(path+(token?'?token='+encodeURIComponent(token):''),options),data=await response.json();
  if(!response.ok)throw Error(data.message||'HTTP '+response.status);return data;
}
async function refresh(){render(await api('/api/state'));}
async function command(verb,arg='',useDraft=false){
  if(!online||busy||!state)return;busy=true;controls();notice('Виконується команда…');
  try{
    const boot=useDraft?baseBoot:state.boot,revision=useDraft?baseRevision:state.revision;
    const response=await api('/api/command',boot+' '+revision+' '+verb+(arg?' '+arg:''));
    if(!response.ok)throw Error(response.message);
    // Owner publishes a new snapshot at most 250 ms after the acknowledged command.
    await new Promise(r=>setTimeout(r,350));await refresh();
    if(verb==='APPLY'||verb==='SAVE')reload();
    notice((verb==='APPLY'?'Налаштування застосовано. Збереження в EEPROM — окремо. ':verb==='SAVE'?'EEPROM: запис і перевірка завершені. ':'Тест завершено. ')+response.message);
  }catch(e){notice('Команда: '+e.message+'. Онови стан перед повторенням.',true);try{await refresh();}catch{}}
  finally{busy=false;controls();}
}
function draw(){
  const canvas=$('chart'),rect=canvas.getBoundingClientRect();if(!rect.width)return;
  const dpr=window.devicePixelRatio||1;canvas.width=Math.round(rect.width*dpr);canvas.height=Math.round(rect.height*dpr);
  const c=canvas.getContext('2d');c.scale(dpr,dpr);const w=rect.width,h=rect.height,left=65,right=w-15;
  c.fillStyle='#0b1016';c.fillRect(0,0,w,h);c.font='11px system-ui';
  if(!points.length){c.fillStyle='#8095a5';c.fillText('Очікування вимірів…',left,50);return;}
  const t0=points[0].t,t1=points[points.length-1].t,span=Math.max(1000,(t1-t0)>>>0);
  for(const [index,key,color,unit] of [[0,'i','#00c8ff','A'],[1,'u','#ffd600','V']]){
    const top=18+index*(h/2),height=h/2-43,vals=points.map(p=>p[key]).filter(Number.isFinite);
    let min=vals.length?Math.min(...vals):0,max=vals.length?Math.max(...vals):1,pad=Math.max((max-min)*.15,.005);
    min-=pad;max+=pad;
    for(let j=0;j<3;j++){const y=top+j*height/2;c.strokeStyle='#22303a';c.beginPath();c.moveTo(left,y);c.lineTo(right,y);c.stroke();c.fillStyle='#8294a2';c.fillText((max-j*(max-min)/2).toFixed(3),4,y+4);}
    c.fillStyle=color;c.fillText(unit,4,top+height+17);
    c.strokeStyle=color;c.lineWidth=1.7;c.beginPath();let last=null;
    for(const p of points){if(!Number.isFinite(p[key])){last=null;continue;}const x=left+((p.t-t0)>>>0)/span*(right-left),y=top+(max-p[key])/(max-min)*height;
      if(last&&((p.t-last.t)>>>0)<=2500)c.lineTo(x,y);else c.moveTo(x,y);last=p;
    }c.stroke();
    const tail=points[points.length-1];if(Number.isFinite(tail[key])){c.fillStyle=color;c.beginPath();c.arc(left+((tail.t-t0)>>>0)/span*(right-left),top+(max-tail[key])/(max-min)*height,3,0,Math.PI*2);c.fill();}
  }
  c.fillStyle='#8294a2';c.fillText('-'+(span/1000).toFixed(0)+' s',left,h-4);c.fillText('останній',Math.max(left,right-54),h-4);
}
makeFields();
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
$('pause').onclick=()=>{paused=!paused;$('pause').textContent=paused?'Продовжити графік':'Пауза графіка';};
$('clear-chart').onclick=()=>{points=[];draw();};
$('export').onclick=()=>{try{const v=values();validateConfig(v,REGISTRY);const url=URL.createObjectURL(new Blob([JSON.stringify({schema:'r1s3-config',major:1,minor:0,values:v},null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='r1s3-config-draft.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){notice(e.message,true);}};
$('import').onclick=()=>$('profile-file').click();
$('profile-file').onchange=async()=>{
  try{const file=$('profile-file').files[0];if(!file)return;if(file.size>16000)throw Error('JSON завеликий');const obj=JSON.parse(await file.text());if(!obj||Object.keys(obj).sort().join(',')!=='major,minor,schema,values'||obj.schema!=='r1s3-config'||obj.major!==1||obj.minor!==0)throw Error('Непідтримуваний профіль');validateConfig(obj.values,REGISTRY);fill(obj.values);notice('Профіль імпортовано в чернетку. Перевір різницю перед застосуванням.');}catch(e){notice(e.message,true);}finally{$('profile-file').value='';}
};
window.addEventListener('resize',draw);
setInterval(()=>{if(online&&Date.now()-lastReceived>5000)setOffline('Дані застаріли. Перевір підключення логера.');},1000);
async function poll(){if(!busy&&!polling&&!stopped){polling=true;try{await refresh();}catch(e){setOffline('Немає відповіді: '+e.message);}finally{polling=false;}}setTimeout(poll,1000);}
controls();draw();
if(location.protocol==='file:')setOffline('Це панель пристрою. Запусти device_ui/start.cmd на ПК або відкрий http://192.168.4.1 у мережі логера.');
else poll();
