/* The hardware owns all mutations. A browser draft is never saved implicitly. */
const $=id=>document.getElementById(id);
const labels={
shunt_uohm:['Опір шунта, µΩ','400 A / 60 mV = 150 µΩ'],
polarity:['Полярність струму','+1 — звичайна; −1 — інвертувати'],
i_zero_uV:['Нуль струму, µV','Зсув вхідної напруги шунта'],
i_gain:['Коефіцієнт струму','1 = без корекції масштабу'],
u_zero_V:['Нуль напруги, V','Віднімається перед коефіцієнтом'],
u_gain:['Коефіцієнт напруги','1 = без корекції масштабу'],
requested_rate_hz:['Частота вимірів, Гц','Ціле число 1–300 Гц; має вміщувати конверсії та усереднення'],
adc_range:['Діапазон шунта','Чутливий режим для менших струмів; із шунтом 400 А / 60 мВ він не охоплює всі 400 А'],
vshunt_ct_code:['Час конверсії шунта','Довше вимірювання — менше шуму струму, повільніша реакція'],
vbus_ct_code:['Час конверсії напруги','Довше вимірювання — менше шуму напруги'],
temp_ct_code:['Час конверсії температури','Температура чипа; входить у загальний цикл виміру'],
average_code:['Усереднення INA228','Кількість конверсій на один результат для всіх трьох каналів'],
ready_timeout_us:['Очікування ADC, µs','Має вміщувати конверсії з усередненням'],
max_gap_us:['Межа розриву, µs','Через довші паузи енергія не інтегрується; більше за період відліку'],
flush_interval_ms:['Інтервал збереження, ms','Періодична синхронізація запису з microSD'],
queue_bytes:['Бюфер PSRAM, байти','Нова місткість застосовується перед наступним записом'],
rotation_bytes:['Розмір частини, байти','Після досягнення межі запис переходить у наступний файл'],
reserve_bytes:['Резерв на SD, байти','Вільне місце, яке логер залишає на картці'],
allow_unknown_utc:['Дозволити невідомий UTC','Запис із відносним часом, якщо RTC не налаштований'],
display_hz:['Оновлення OLED, Hz','Оновлення екрана, не частота вимірів'],
live_hz:['Пакети Live, Hz','Базова частота пакетів; Wi-Fi забирає додаткові при відставанні. USB показує свіжі ділянки з позначеними розривами.'],
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
['Аналого-цифрове перетворення',REGISTRY.slice(6,12)],
['Додаткові параметри часу',[REGISTRY[12]]],
['Буфер і запис на microSD',REGISTRY.slice(13,19)],
['Екран і Live',REGISTRY.slice(19,23).concat(REGISTRY.slice(27))],
['Походження калібрування',REGISTRY.slice(23,27)]
];
let state=null,base=null,baseBoot='',baseRevision=0,dirty=false,busy=false,online=false,paused=false,points=[],lastSample=null;
let lastReceived=0,polling=false,stopped=false;
let liveCursor=0,liveBoot='',lastLiveAt=0,clockAt=0,clockDevice=0,streamGaps=0,frameCount=0,fps=0,fpsAt=performance.now(),lastFrame=0;
let nextBreak=false;
const chartNav=new ChartNavigation();
function resetStream(boot=''){points=[];liveCursor=0;liveBoot=boot;clockAt=0;lastLiveAt=0;nextBreak=true;chartNav.live(Number($('chart-window').value)*1000);}
function meters(u,i){$('volts').textContent=number(u,4);$('amps').textContent=number(i,4);$('watts').textContent=number(Number.isFinite(u)&&Number.isFinite(i)?u*i:null,3);}

function notice(text,error=false){$('notice').textContent=text;$('notice').classList.toggle('error',error);}
function makeFields(){
  for(const [title,fields] of groups){
    const fieldset=document.createElement('fieldset'),legend=document.createElement('legend'),grid=document.createElement('div');
    legend.textContent=title;grid.className='field-grid';fieldset.append(legend,grid);
    for(const f of fields){
      const label=document.createElement('label'),name=document.createElement('span'),help=document.createElement('small');
      label.className='field';name.textContent=labels[f.name][0];help.textContent=labels[f.name][1];
      const choices=f.name==='average_code'?INA_AVERAGES.map((n,i)=>[i,n===1?'Без усереднення · ×1':'×'+n]):
        ['vshunt_ct_code','vbus_ct_code','temp_ct_code'].includes(f.name)?INA_CT_US.map((n,i)=>[i,n+' мкс']):
        f.name==='adc_range'?[[0,'Широкий · ±163,84 мВ'],[1,'Чутливий · ±40,96 мВ']]:f.enum?.map(v=>[v,v]);
      let input=document.createElement(choices?'select':'input');input.id='f-'+f.name;input.name=f.name;
      if(choices)for(const [value,text] of choices){const option=document.createElement('option');option.value=value;option.textContent=text;input.append(option);}
      else if(f.type==='bool')input.type='checkbox';
      else if(f.type==='utf8'){input.type='text';input.maxLength=f.max_bytes;}
      else{input.type='number';input.step=f.type==='f64'?'any':'1';if(f.min!=null)input.min=f.min;if(f.max!=null)input.max=f.max;}
      label.append(name,input,help);grid.append(label);
    }
    $(title==='Аналого-цифрове перетворення'?'ina-fields':'config-form').append(fieldset);
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
  try{validateConfig(current,REGISTRY);if(!inaTiming(current,!!state?.benchmark).valid)invalid='Режим INA228 не встигає за частотою або часом очікування.';}catch(e){invalid=e.message;}
  $('changes').textContent=changes.map(f=>labels[f.name][0]+': '+String(base[f.name])+' → '+String(current[f.name])).join('\n');
  $('draft-note').textContent=stale()?'Стан змінився. Прочитай з логера заново.':invalid|| (dirty?'Змін у чернетці: '+changes.length:'Чернетка відповідає логеру');
  $('apply').disabled=recordingBusy()||!online||busy||!base||stale()||!dirty||!!invalid;
  $('save').disabled=state?.benchmark||recordingBusy()||!online||busy||!base||stale()||dirty||state?.settings_status!=='UNSAVED';
  $('export').disabled=!base||!!invalid;
  const timing=inaTiming(current,!!state?.benchmark),locked=recordingBusy()||!online||busy;
  $('ina-timing').textContent=Number.isFinite(timing.us)?`Цикл АЦП: ${number(timing.us/1000,3)} мс · період вимірів: ${number(timing.period/1000,3)} мс. `+
    (timing.maximum?`Розрахункова межа з резервом: ${timing.maximum} Гц.`:'Ця комбінація не вміщується навіть у 1 Гц. Скороти конверсії або усереднення.')+
    (!timing.valid?' Зменш частоту або обери швидший режим.':''):'Вибери коректні параметри INA228.';
  $('ina-timing').classList.toggle('error',!timing.valid);
  $('ina-range').textContent=Number.isFinite(timing.limitAmps)?`Межа АЦП для заданого шунта: ±${number(timing.limitAmps,1)} А.`+(current.adc_range===1?' Чутливий діапазон дає вчетверо менший крок, але зменшує межу вимірювання.':''):'';
  $('ina-fit').hidden=timing.valid||!timing.maximum;
  $('ina-fit').textContent='Узгодити частоту: '+timing.maximum+' Гц';$('ina-fit').disabled=locked||stale();
  $('ina-apply').disabled=$('apply').disabled;$('ina-save').disabled=$('save').disabled;
  $('ina-reload').disabled=busy||!online;
  for(const el of $('ina-fields').querySelectorAll('input,select'))el.disabled=locked;
  $('ina-changes').textContent=$('changes').textContent;
  $('ina-note').textContent=$('draft-note').textContent+' · Застосування змінює всі параметри спільної чернетки. EEPROM зберігається окремою кнопкою.';
  if(state?.config_hex){const applied=decodeConfig(state.config_hex,REGISTRY);$('ina-applied').textContent='Застосовано: '+applied.requested_rate_hz+' Гц · ×'+INA_AVERAGES[applied.average_code];}
}
function editConfig(event){
  if(INA_FIELDS.includes(event.target.name)){
    const adjusted=inaWithTiming(values());
    if(Number.isFinite(adjusted.ready_timeout_us))$('f-ready_timeout_us').value=adjusted.ready_timeout_us;
    if(Number.isFinite(adjusted.max_gap_us))$('f-max_gap_us').value=adjusted.max_gap_us;
  }
  updateDraft();controls();
}
function quickConfig(hz){const applied=decodeConfig(state.config_hex,REGISTRY);return $('rate-mode').value==='auto'?configForRate(applied,hz):inaWithTiming(applied,hz);}
function rows(id,items){const dl=$(id);dl.replaceChildren();for(const [label,value] of items){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=String(value);dl.append(dt,dd);}}
function number(v,n=3){return Number.isFinite(v)?v.toFixed(n):'—';}
let blePeerDirty=false,bleDiscoveryKey='',blePermissionDirty=false;
function canControls(){
  if(!$('can-state'))return;
  const c=state?.ble?.canbox,live=online&&Date.now()-lastReceived<5000;
  const known=!!(live&&c?.mode&&c?.connected&&c?.fresh);
  const locked=busy||!live||stale()||!c;
  const ready=!locked&&known&&c.saved&&c.authorized!==false&&!c.pending;
  const names={idle:'Не записує',closed:'Зупинено · файл закрито',recording:'Запис триває',starting:'Запуск запису',stopping:'Завершення запису',error:'Помилка запису',rejected:'Команду відхилено'};
  let headline='Стан невідомий',note='Немає зв’язку з R1. Запис може тривати; живлення CANBox не підтверджено.',tone='unknown';
  if(live&&!c)note='Ця прошивка R1 не повідомляє стан CANBox. Потрібне оновлення.';
  else if(live&&c&&!c.mode){headline='Нюхалку не підключено';note=c.saved?'Натисни «Підключити нюхалку». Прив’язка збережена, PIN не потрібен.':'Відкрий «Прив’язка та налаштування», щоб додати CANBox.';}
  else if(live&&c&&!known){headline=c.connected?'Стан застарів':'Немає зв’язку з нюхалкою';note='Немає свіжого стану CANBox — запис може тривати. Перевір живлення та відстань між платами.';}
  else if(known){
    headline=names[c.phase]||'Стан невідомий';
    note=c.phase==='recording'?'CANBox підтвердив запис на свою SD. Після зупинки дочекайся закриття файла.':c.phase==='closed'?'CANBox підтвердив зупинку й закриття файла.':c.phase==='idle'?'Нюхалка відповідає; запис ще не запущено.':'Перевір стан перед наступною дією.';
    tone=c.phase==='recording'?'recording':['error','rejected'].includes(c.phase)?'error':['idle','closed'].includes(c.phase)?'ready':'unknown';
    if(c.ready===false&&c.phase==='idle'){headline='Не готова до запису';note='CANBox не підтвердив готовність до нового запису. Перевір SD на нюхалці.';tone='error';}
    if(c.clock_synced!==true&&['idle','closed'].includes(c.phase)){headline='Потрібна синхронізація часу';note='Старт заблоковано. Очікуємо час від R1; перевір RTC або встанови час із телефона у вкладці Огляд.';tone='pending';}
    if(!c.saved||c.authorized===false)note+=' Потрібно завершити прив’язку та дозвіл керування.';
    if(c.pending){headline='Очікуємо результат команди';note+=' Попередній підтверджений стан: '+(names[c.phase]||'невідомий')+'.';tone='pending';}
    if(c.detail)note+=' Код причини: '+c.detail+'.';
  }
  $('can-card').dataset.status=tone;$('can-headline').textContent=headline;
  $('can-link').textContent=known?'● CANBox на зв’язку':live&&c?.mode&&c?.connected?'Стан застарів':'Зв’язок не підтверджено';
  $('can-state').textContent=note;
  $('can-recording').textContent=known?(names[c.phase]||'Невідомо')+(c.pending?' · очікуємо команду':''):'Невідомо';
  $('can-readiness').textContent=!known?'Немає свіжих даних':c.phase==='recording'?'Запис виконується':c.ready===true?'Готова':c.ready===false?'Не готова':'Не повідомляється';
  $('can-association').textContent=!live||!c?'Немає даних':c.saved?'Збережена · без PIN':'Не збережена';
  $('can-session').textContent=known&&c.session&&c.session!=='0'?'Сесія CANBox: '+c.session:'';
  $('can-clock').textContent=!known?'Невідомо':c.clock_synced===true?'Синхронізовано з R1':c.phase==='recording'?'Перевір джерело часу':'Очікуємо час від R1';
  $('can-start').disabled=!ready||c.clock_synced!==true||c.ready===false||!['idle','closed'].includes(c?.phase);
  $('can-stop').disabled=!ready||!['recording','starting','stopping'].includes(c?.phase);
  $('can-query').disabled=!ready;
  $('can-on').disabled=locked||recordingBusy()||!c?.saved||known;
  $('can-save').disabled=locked||!c?.connected;
  $('can-connect').disabled=locked||recordingBusy();
}

function bleControls(){
  canControls();
  const available=!!state?.ble,locked=recordingBusy()||busy||!online||!available;
  const address=$('ble-peer').value.trim(),pin=$('ble-pin').value;
  $('ble-scan').disabled=locked;
  $('ble-connect').disabled=locked||!/^([0-9a-f]{2}:){5}[0-9a-f]{2}$/i.test(address)||!/^\d{6}$/.test(pin);
  $('ble-off').disabled=locked||!state?.ble?.enabled;
  const enrollment=available&&typeof state.ble.enrolled==='boolean';
  $('ble-save').disabled=locked||!enrollment||!state.ble.authenticated||!state.ble.ecosystem;
  $('ble-on').disabled=locked||!enrollment||!state.ble.enrolled||state.ble.authenticated;
  $('ble-forget').disabled=locked||!enrollment||!(state.ble.enrolled||state.ble.peer);
  $('ble-allow-remote').disabled=locked||!enrollment;
  $('ble-peer').disabled=locked;$('ble-pin').disabled=locked;
  if(!online){$('ble-state').classList.remove('online');$('ble-note').textContent='Немає свіжого стану логера. Перевір його підключення.';}
}
function renderBle(ble){
  const names={OFF:'BLE вимкнено',SCANNING:'Пошук R3…',READY:'Вибери R3',CONNECTING:'Підключення…',PAIRING:'Перевірка PIN…',CONNECTED:'R3 підключений',CANBOX:'CANBox вибрано · R3 призупинено',RETRY:'Повторне підключення…',ERROR:'Помилка BLE'};
  $('ble-state').textContent=ble?(names[ble.state]||'Стан BLE невідомий'):'BLE вимкнено';
  $('ble-state').classList.toggle('online',!!(ble?.canbox?.mode?(ble.canbox.connected&&ble.canbox.fresh):(ble?.authenticated&&ble?.fresh)));
  $('ble-note').textContent=ble?.canbox?.mode?'Зараз вибрано CANBox. Канал R3 призупинено; збережена прив’язка залишається.':!ble?'Ця прошивка не повідомляє стан BLE. Потрібне оновлення логера.':
    !ble.enabled?(ble.enrolled?'Збережена прив’язка є. Підключи R3 без повторного PIN.':'Увімкни пошук і вибери R3 для отримання часових маяків.'):
    ble.authenticated&&ble.rtc_synced?'RTC звірено з R3. Точність вирівнювання відліків ще не визначена.':
    ble.authenticated&&ble.fresh?'Маяк отримано; точність синхронізації ще не визначена':
    ble.state==='CONNECTED'?'З’єднання встановлено; очікування свіжого підтвердженого маяка.':
    ble.state==='SCANNING'?'Шукаємо R3 поблизу. Вибери адресу зі списку або введи її вручну.':
    ble.state==='READY'?'Пошук завершено. Вибери R3 та введи PIN для підключення.':
    ble.state==='PAIRING'?'R3 перевіряє PIN. Дочекайся результату підключення.':
    ble.state==='RETRY'?'Зв’язок втрачено. Логер повторює підключення; вимірювання тривають.':
    ble.state==='ERROR'?'Не вдалося встановити зв’язок. Перевір R3, адресу та PIN.':'Підключаємося до вибраного R3…';
  if(!blePeerDirty&&ble?.peer)$('ble-peer').value=ble.peer;
  if(!blePermissionDirty)$('ble-allow-remote').checked=!!ble?.remote_allowed;
  const devices=Array.isArray(ble?.devices)?ble.devices.slice(0,6):[];
  const discoveryKey=JSON.stringify(devices);
  if(discoveryKey!==bleDiscoveryKey){
    bleDiscoveryKey=discoveryKey;$('ble-peers').replaceChildren();
    for(const device of devices){const option=document.createElement('option');option.value=device.address;option.label=device.name||'R3';$('ble-peers').append(option);}
  }
  $('ble-discovery').textContent=devices.length?'Знайдено: '+devices.length+'. Вибери адресу або введи її вручну.':'Запусти пошук або введи адресу R3 вручну.';
  rows('ble-summary',ble?.canbox?.mode?[
    ['Вибраний пристрій','CANBox · '+(ble.canbox.peer||'—')],
    ['З’єднання з CANBox',ble.canbox.connected?'Підтверджено':'Не підтверджено'],
    ['Свіжий стан CANBox',ble.canbox.fresh?'Так':'Ні'],
    ['Час CANBox',ble.canbox.fresh&&ble.canbox.clock_synced?'Синхронізовано з R1':'Очікуємо підтвердження'],
    ['Канал R3','Призупинено, поки вибрано CANBox']
  ]:ble?[
    ['Вибраний R3',ble.peer||'—'],['Підтвердження з’єднання',ble.authenticated?'Підтверджено':'Не підтверджено'],
    ['Свіжий маяк',ble.fresh?'Так':'Ні'],['Вік маяка',Number.isFinite(ble.age_ms)?number(ble.age_ms/1000,1)+' с':'—'],
    ['UTC у маяку',ble.utc_valid?'Валідний за даними R3':'Невідомий / невалідний'],['Точність синхронізації','Ще не визначена'],
    ['Прив’язка після перезапуску',ble.enrolled?'Збережена':'Не збережена'],['Керування записом із R3',ble.remote_allowed?'Дозволено':'Не дозволено'],
    ['Звіряння RTC',ble.rtc_synced?'Виконано для цього запуску R3':ble.enrolled?'Очікує зв’язку, чинного часу або завершення запису':'Потрібна збережена прив’язка']
  ]:[]);
  // Counters are decimal strings: avoid precision loss through Number conversion.
  rows('ble-diagnostics',ble?.canbox?.mode?[
    ['З’єднань із CANBox',ble.canbox.connections??'—'],
    ['Помилки читання стану',ble.canbox.read_errors??'—'],
    ['Відповіді часу / без чинного RTC',(ble.canbox.time_replies??'—')+' / '+(ble.canbox.invalid_time_replies??'—')],
    ['Вік перевірки RTC',Number.isFinite(ble.canbox.rtc_read_age_ms)?number(ble.canbox.rtc_read_age_ms/1000,1)+' с':'Немає чинного часу'],
    ['Остання помилка',ble.last_error||'—']
  ]:ble?[
    ['Запуск R3 / ревізія часу',(ble.source_boot||'—')+' / '+(ble.clock_revision??'—')],['Сегмент',ble.segment||'—'],
    ['Останній номер маяка',ble.last_sequence??'—'],['Отримано / пропущено',(ble.received??'0')+' / '+(ble.missing??'0')],
    ['Некоректні / дублікати / не за порядком',(ble.malformed??'0')+' / '+(ble.duplicates??'0')+' / '+(ble.out_of_order??'0')],
    ['Втрати черги',ble.drops??0],['З’єднання / повторні з’єднання',(ble.connections??0)+' / '+(ble.reconnects??0)],
    ['MTU',ble.mtu||'—'],['Остання помилка',ble.last_error||'—']
  ]:[]);
}
async function submitBle(event){
  event.preventDefault();
  if($('ble-connect').disabled)return;
  const address=$('ble-peer').value.trim().toUpperCase(),pin=$('ble-pin').value;
  $('ble-pin').value='';bleControls();
  await command('BLE','CONNECT '+address+' '+pin);
}
function setOffline(error){online=false;document.body.classList.add('offline');$('connection').textContent='Немає зв’язку';$('connection').classList.remove('online');for(const id of ['amps','volts','watts'])$(id).textContent='—';$('temperature').textContent='Температура INA228: —';notice(error,true);controls();}
function controls(){
  const hz=Number($('quick-rate').value);let validRate=true;
  try{
    rateProfile(hz);
    if(state){const candidate=quickConfig(hz);if(!inaTiming(candidate,!!state.benchmark).valid)throw Error('Ці параметри INA228 не встигають. Зміни їх нижче або вибери «Авто ADC».');}
    $('rate-profile').textContent='Після застосування: '+($('rate-mode').value==='auto'?rateDescription(hz):state?inaDescription(quickConfig(hz)):'параметри INA228 збережуться.');
  }catch(e){validRate=false;$('rate-profile').textContent=e.message;}
  $('rate-profile').classList.toggle('error',!validRate);
  const locked=recordingBusy()||busy||!online;
  $('quick-rate').disabled=locked;
  $('rate-mode').disabled=locked;
  for(const b of $('rate-presets').children){b.disabled=locked;b.setAttribute('aria-pressed',String(Number(b.dataset.hz)===hz));}
  $('apply-rate').disabled=locked||dirty||stale()||!state||!validRate||hz===state.requested_hz;
  $('rate-note').textContent=dirty?'Спочатку застосуй або скинь чернетку в налаштуваннях.':state?.settings_status==='UNSAVED'?'Застосовано. Щоб залишити після перезапуску — збережи в EEPROM у налаштуваннях.':'Частота вимірів і FPS незалежні. Збереження в EEPROM — у налаштуваннях.';
  for(const el of document.querySelectorAll('[data-command],#sync-time'))el.disabled=recordingBusy()||busy||!online;
  $('record-start').disabled=recordingBusy()||busy||!online||dirty||!state?.recording_available;
  $('record-stop').disabled=busy||!online||!['STARTING','RUNNING','STOPPING'].includes(state?.recording_state);
  $('record-files').disabled=recordingBusy()||busy||!online;
  $('files-refresh').disabled=recordingBusy()||!online;fileControls();bleControls();updateDraft();}
function render(s){
  if(!s.ready)throw Error('Логер запускається. Очікуємо готовності.');
  // HTTP may still answer from core 0 when the hardware owner's snapshot stops.
  if(!state||s.boot!==state.boot||s.uptime_ms!==state.uptime_ms)lastReceived=Date.now();
  if(Date.now()-lastReceived>5000)throw Error('Знімок стану логера застарів');
  const wasOffline=!online;
  if(state&&s.boot!==state.boot){resetStream(s.boot);lastSample=null;notice('Логер перезапустився. Перевір стан і налаштування.',true);}
  const previousRate=state?.requested_hz;
  $('benchmark-notice').hidden=!s.benchmark;
  const rateField=REGISTRY.find(f=>f.name==='requested_rate_hz');
  rateField.max=s.benchmark?1000:300;$('f-requested_rate_hz').max=rateField.max;
  state=s;if(previousRate!==s.requested_hz)$('quick-rate').value=s.requested_hz||50;online=true;document.body.classList.remove('offline');
  $('release-usb').hidden=s.transport!=='usb';
  const transport=s.transport==='usb'?'USB через ПК':s.transport==='wifi'?'Wi-Fi напряму':'Підключення до логера';
  $('connection').textContent='● Логер підключений'+(s.transport==='usb'?' · USB':s.transport==='wifi'?' · Wi-Fi':'');$('connection').classList.add('online');
  const valid=s.valid&&((s.uptime_ms-s.sample_at_ms)>>>0)<3500;
  if(!s.live_available)meters(valid?s.volts:null,valid?s.amps:null);
  $('temperature').textContent='Температура INA228: '+(valid?number(s.temp_c,2)+' °C':'—');
  $('utc').textContent=s.utc?new Date(s.utc*1000).toISOString().replace('T',' ').replace('.000Z',' UTC'):'RTC: потрібно встановити час';
  $('cadence').textContent=(s.requested_hz||'—')+' Гц задано · '+number(s.measured_hz,1)+' Гц фактично';
  if(wasOffline)notice('Логер підключений. Можна змінювати навантаження та запускати тести.');
  rows('health',[['INA228',s.ina],['microSD',s.sd==='READ'?'Читання OK':s.sd],['24C32',s.eeprom==='READ'?'Читання OK':s.eeprom],['DS3231',s.rtc],['OLED',s.oled?'Працює':'Недоступний']]);
  rows('memory',[['FIFO в PSRAM',s.buffer_ready?(s.queue_bytes/1024)+' KiB · підготовлено':'Не виділено'],['Блок SD у внутрішній SRAM',(s.sd_block_bytes/1024)+' KiB'],['Вільна PSRAM',(s.psram_free/1048576).toFixed(2)+' MiB'],['Вільна внутрішня пам’ять',(s.heap_free/1024).toFixed(1)+' KiB']]);
  const resetNames=['Невідомо','Живлення / апаратне скидання','Зовнішнє скидання','Програмний перезапуск','Помилка програми','Сторожовий таймер переривань','Сторожовий таймер задач','Сторожовий таймер','Вихід зі сну','Просідання живлення','SDIO'];
  rows('raw',[['Вхід шунта',valid?number(s.shunt_uv,4)+' µV':'—'],['VSHUNT / VBUS / TEMP raw',valid?[s.shunt_raw,s.bus_raw,s.temp_raw].join(' / '):'—'],['I²C: адрес / помилок',s.i2c_count+' / '+s.i2c_errors],['Частота I²C',s.i2c_hz?s.i2c_hz/1000+' кГц':'—'],['Останній запуск',resetNames[s.reset_reason]||'—'],['Ядро апаратних тестів / UI',s.owner_core+' / '+s.ui_core],['Час після запуску',Math.floor(s.uptime_ms/1000)+' s']]);
  rows('timing',[['Задана / виміряна частота',(s.requested_hz||'—')+' / '+number(s.measured_hz,2)+' Hz'],['Коректні / некоректні відліки',s.valid_samples+' / '+s.invalid_samples],['Пропущені періоди',s.missed_samples],['Найбільша затримка старту',(s.max_late_us/1000).toFixed(2)+' ms'],['Читання INA / фрагмент OLED',(s.max_read_us/1000).toFixed(2)+' / '+(s.oled_chunk_us/1000).toFixed(2)+' ms'],['Планові паузи на команди',s.maintenance_count+' · '+s.maintenance_ms+' ms'],['Втрати preview / кадри OLED',s.preview_drops+' / '+s.oled_frames]]);
  rows('network',[['Ця панель',transport],['Точка доступу',s.ap_ready?'Увімкнена':'Запуск / недоступна'],['Назва мережі',s.ssid||'—'],['Пристроїв у Wi-Fi',Number.isInteger(s.ap_clients)?s.ap_clients:'—']]);
  $('wifi-connection-note').textContent=s.transport==='wifi'?'Ти працюєш напряму з логером. USB-сервер на ПК не потрібен.':'Ця панель працює через ПК. На телефоні підключись до мережі логера та відкрий адресу нижче.';
  $('wifi-password').textContent=s.ap_password;
  renderBle(s.ble);
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
    notice(verb==='BLE'?'Команду BLE прийнято. Стеж за станом з’єднання.':verb==='START'?'Запит запису прийнято. Стеж за станом запису.':verb==='STOP'?'Завершуємо запис. Дочекайся закриття файлу.':(verb==='APPLY'?'Налаштування застосовано. Збереження в EEPROM — окремо. ':verb==='SAVE'?'EEPROM: запис і перевірка завершені. ':'Тест завершено. ')+response.message);
  }catch(e){notice(verb==='BLE'?'Команду BLE не виконано. Перевір стан R3 й онови стан перед повторенням.':'Команда: '+e.message+'. Онови стан перед повторенням.',true);try{await refresh();}catch{}}
  finally{busy=false;controls();}
}

let fileDirectory='/',fileSession=0,fileBusy=false,fileJob=null,fileEpoch=0;
let fileEntries=[],fileComplete=false,fileLoaded=false,selectedFile=null;
const fileCollator=new Intl.Collator('uk-UA',{numeric:true,sensitivity:'base'});
function pathHex(path){return Array.from(new TextEncoder().encode(path),b=>b.toString(16).padStart(2,'0')).join('');}
function pathText(hex){return new TextDecoder('utf-8',{fatal:true}).decode(Uint8Array.from(hex.match(/../g),s=>parseInt(s,16)));}
function fileNotice(text){$('files-status').textContent=text;}
async function filesCommand(command){const r=await api('/api/files?command='+encodeURIComponent(command));if(!r.ok)throw Error(r.message||'Помилка читання SD');return r;}
async function closeDirectory(){const id=fileSession;fileSession=0;if(id)await filesCommand('CLOSE '+id);}
async function stopListing(){++fileEpoch;if(fileJob)await fileJob;await closeDirectory();}
function fileControls(){
  const blocked=!online||recordingBusy();
  $('files-up').disabled=blocked||fileDirectory==='/';$('files-records').disabled=blocked;
  $('files-cancel').hidden=!fileJob;
  $('files-download-selected').disabled=blocked||!selectedFile||selectedFile.directory||!selectedFile.path;
  for(const button of document.querySelectorAll('.file-action,.file-name,#files-path button'))button.disabled=blocked||button.dataset.unavailable==='true';
}
function fileSize(size){return size<1024?size+' B':size<1048576?(size/1024).toFixed(1)+' KiB':(size/1048576).toFixed(2)+' MiB';}
function recordingDate(name){
  // Derive only from our session names, never the FAT modification timestamp.
  const match=/^r1s3_(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})-(\d{2})Z_[0-9a-f]{8}_[0-9a-f]{8}_\d{4,}\.(?:csv|part)$/i.exec(name);
  const legacy=/^r1s3_(\d+)_[0-9a-f]{8}_[0-9a-f]{8}_\d{4,}\.(?:csv|part)$/i.exec(name);
  const date=match?new Date(`${match[1]}T${match[2]}:${match[3]}:${match[4]}Z`):legacy&&Number(legacy[1])>0?new Date(Number(legacy[1])*1000):null;
  return date&&Number.isFinite(date.getTime())?date:null;
}
function fileBreadcrumbs(){
  $('files-path').replaceChildren();
  const parts=[['microSD','/']];let path='';
  for(const part of fileDirectory.split('/').filter(Boolean)){path+='/'+part;parts.push([part,path]);}
  for(const [name,path] of parts){const button=document.createElement('button');button.textContent=name;button.onclick=()=>listFiles(path);button.title=path;$('files-path').append(button);}
}
function selectFile(entry){
  selectedFile=entry;
  for(const row of document.querySelectorAll('.file-row'))row.classList.toggle('selected',row.dataset.key===entry?.key);
  $('files-selection').textContent=entry?(entry.directory?'Папка: ':'')+entry.name+(entry.directory?'':' · '+fileSize(entry.size)):'Вибери файл, щоб побачити повну назву.';
  fileControls();
}
function renderFiles(){
  const query=$('files-search').value.trim().toLocaleLowerCase('uk-UA'),type=$('files-type').value,sort=$('files-sort').value;
  const filtered=fileEntries.filter(e=>(!query||(e.name+' '+e.dateText).toLocaleLowerCase('uk-UA').includes(query))&&(e.directory||type==='all'||e.name.toLowerCase().endsWith('.'+type)));
  filtered.sort((a,b)=>{
    if(a.directory!==b.directory)return a.directory?-1:1;
    let order=0;
    if(!a.directory&&sort.startsWith('date'))order=a.date&&b.date?(a.date-b.date)*(sort==='date-desc'?-1:1):a.date?-1:b.date?1:0;
    if(!a.directory&&sort==='size-desc')order=b.size-a.size;
    return order||fileCollator.compare(a.name,b.name)*(sort==='name-desc'?-1:1);
  });
  const fragment=document.createDocumentFragment();
  for(const entry of filtered){
    const row=document.createElement('div'),label=document.createElement('button'),icon=document.createElement('span'),name=document.createElement('span'),date=document.createElement('time'),size=document.createElement('small'),action=document.createElement('button');
    row.className='file-row';row.dataset.key=entry.key;row.classList.toggle('selected',entry.key===selectedFile?.key);
    label.className='file-name';label.title=entry.name;icon.className='file-icon';icon.textContent=entry.directory?'▸':'▤';icon.setAttribute('aria-hidden','true');name.className='file-name-text';name.textContent=entry.name;label.append(icon,name);
    label.onclick=()=>{selectFile(entry);if(entry.directory&&entry.path)listFiles(pathText(entry.path));};
    label.ondblclick=()=>{if(!entry.directory)downloadFile(entry);};
    label.onkeydown=e=>{if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();const next=e.key==='ArrowDown'?row.nextElementSibling:row.previousElementSibling;next?.querySelector('.file-name')?.focus();}if(e.key==='Enter'&&!entry.directory){e.preventDefault();downloadFile(entry);}};
    date.className='file-date';date.textContent=entry.directory?'—':entry.dateText||'—';if(entry.date){date.dateTime=entry.date.toISOString();date.title='Місцевий час браузера. UTC: '+entry.date.toISOString();}else date.title='Час початку невідомий';
    size.className='file-size';size.textContent=entry.directory?'Папка':fileSize(entry.size);
    action.className='file-action';action.textContent=entry.directory?'→':'↓';action.title=entry.directory?'Відкрити':'Завантажити';action.setAttribute('aria-label',action.title);action.dataset.unavailable=String(!entry.path);action.onclick=()=>entry.directory?listFiles(pathText(entry.path)):downloadFile(entry);
    row.onclick=()=>selectFile(entry);row.append(label,date,size,action);fragment.append(row);
  }
  if(!filtered.length){const empty=document.createElement('p');empty.className='files-empty';empty.textContent=fileComplete?(fileEntries.length?'Нічого не знайдено.':'Папка порожня.'):'Читання папки…';fragment.append(empty);}
  $('file-list').replaceChildren(fragment);
  fileNotice(fileComplete?(fileEntries.length?'Показано '+filtered.length+' із '+fileEntries.length+' · усю папку прочитано.':'Папка порожня.'):'Прочитано '+fileEntries.length+' · показано '+filtered.length+' · '+(fileJob?'читаємо далі…':'список неповний. Онови папку.'));
  fileControls();
}
async function listFiles(directory=fileDirectory){
  const epoch=++fileEpoch;if(fileJob)await fileJob;if(epoch!==fileEpoch||fileBusy)return;
  if(!online||!state?.files_available||recordingBusy()){fileNotice('Доступ до файлів — після зупинки запису та підключення логера.');return;}
  fileBusy=true;fileLoaded=true;fileDirectory=directory;fileEntries=[];fileComplete=false;selectedFile=null;
  $('files-search').value='';$('files-scroll').scrollTop=0;fileBreadcrumbs();selectFile(null);
  fileJob=(async()=>{
    try{
      await closeDirectory();let next=false;const seen=new Set();
      do{
        const result=await filesCommand(next?'NEXT '+fileSession:'LIST '+pathHex(directory));
        fileSession=result.more?result.session:0;if(epoch!==fileEpoch)break;
        for(const entry of result.entries){
          entry.key=entry.path||entry.name;if(seen.has(entry.key))continue;seen.add(entry.key);
          entry.date=entry.directory?null:recordingDate(entry.name);entry.dateText=entry.date?entry.date.toLocaleString('uk-UA',{year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'}):'';fileEntries.push(entry);
        }
        next=result.more;fileComplete=!next;renderFiles();
        // Yield between bounded device pages; search, scrolling and cancellation stay responsive.
        if(next)await new Promise(r=>setTimeout(r,20));
      }while(next&&epoch===fileEpoch);
    }catch(e){renderFiles();fileNotice('Список неповний: '+e.message+' · Онови папку.');}
    finally{try{await closeDirectory();}catch{}fileBusy=false;fileJob=null;fileControls();}
  })();
  fileControls();await fileJob;
}
async function downloadFile(entry){
  if(!entry.path||entry.directory||!online||recordingBusy())return;
  await stopListing();if(fileBusy)return;fileBusy=true;
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
  if(points.length){const cutoff=points.at(-1).t-CHART_HISTORY_MS;let first=0;while(first<points.length&&points[first].t<cutoff)first++;
    first=Math.max(first,points.length-CHART_MAX_POINTS);if(first>0)points.splice(0,first);}
}
async function pollLive(){
  const began=performance.now();
  let catchUp=false;
  if(!busy&&!stopped&&online&&!document.hidden){
    try{
      const packet=await api('/api/live?after='+liveCursor);acceptLive(packet);
      const delivery=previewDelivery(packet,state?.transport,state?.requested_hz);
      catchUp=delivery.catchUp;
      if(delivery.resync){liveCursor=0;nextBreak=true;++streamGaps;}
    }
    catch(e){if(!busy){meters(null,null);$('stream-status').textContent='Потік: '+e.message;}}
  }
  // Frequency is a delivery target, not an extra set of ADC conversions.
  let hz=base?.live_hz||5;
  if(state?.config_hex){try{hz=decodeConfig(state.config_hex,REGISTRY).live_hz;}catch{}}
  if(catchUp)hz=Math.max(hz,10);
  setTimeout(pollLive,Math.max(15,1000/hz-(performance.now()-began)));
}
function chartLimits(now=performance.now()){
  const oldest=points[0]?.t||0;
  return {oldest,latest:Math.max(oldest,paused?(points.at(-1)?.t||0):clockDevice+Math.min(Math.max(0,now-clockAt),1000)-300)};
}
function draw(now=performance.now()){
  const canvas=$('chart'),rect=canvas.getBoundingClientRect();if(!rect.width)return false;
  const dpr=window.devicePixelRatio||1,w=rect.width,h=rect.height;
  const pw=Math.round(w*dpr),ph=Math.round(h*dpr);
  if(canvas.width!==pw||canvas.height!==ph){canvas.width=pw;canvas.height=ph;}
  const c=canvas.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);
  const left=65,right=w-15;
  c.fillStyle='#0b1016';c.fillRect(0,0,w,h);c.font='11px system-ui';
  if(!points.length){c.fillStyle='#8095a5';c.fillText('Очікування вимірів…',left,50);return true;}
  // Delay only the viewport, not the samples. Scroll between actual packets at display cadence.
  const limits=chartLimits(now),view=chartNav.range(limits.oldest,limits.latest);
  const {start:t0,end:t1,span}=view,visible=chartVisible(points,t0,t1);
  $('chart-range').textContent=(chartNav.follow?'Наживо':'Перегляд історії')+' · '+number(span/1000,span<1000?2:1)+' с';
  $('chart-live').setAttribute('aria-pressed',String(chartNav.follow&&!paused));
  for(const [index,key,color,unit] of [[0,'i','#00c8ff','A'],[1,'u','#ffd600','V']]){
    const top=18+index*(h/2),height=h/2-43,vals=visible.map(p=>p[key]).filter(Number.isFinite);
    let min=vals.length?Math.min(...vals):0,max=vals.length?Math.max(...vals):1,pad=Math.max((max-min)*.15,.005);
    min-=pad;max+=pad;
    for(let j=0;j<3;j++){const y=top+j*height/2;c.strokeStyle='#22303a';c.beginPath();c.moveTo(left,y);c.lineTo(right,y);c.stroke();c.fillStyle='#8294a2';c.fillText((max-j*(max-min)/2).toFixed(3),4,y+4);}
    c.fillStyle=color;c.fillText(unit,4,top+height+17);
    c.strokeStyle=color;c.lineWidth=1.7;c.beginPath();let last=null;
    for(const p of chartEnvelope(visible,key,t0,span,right-left)){
      if(!p||!Number.isFinite(p[key])){last=null;continue;}
      const x=left+(p.t-t0)/span*(right-left),y=top+(max-p[key])/(max-min)*height;
      if(last&&!p.gap&&p.revision===last.revision)c.lineTo(x,y);else c.moveTo(x,y);
      last=p;
    }c.stroke();
    const tail=visible.at(-1);if(tail&&Number.isFinite(tail[key])){c.fillStyle=color;c.beginPath();c.arc(left+(tail.t-t0)/span*(right-left),top+(max-tail[key])/(max-min)*height,2.5,0,Math.PI*2);c.fill();}
  }
  const age=t=>number((t-limits.latest)/1000,1)+' с';
  c.fillStyle='#8294a2';c.fillText(age(t0),left,h-4);c.fillText(chartNav.follow?'зараз':age(t1),Math.max(left,right-65),h-4);
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
$('ble-form').addEventListener('submit',submitBle);
$('ble-peer').oninput=()=>{blePeerDirty=true;bleControls();};
$('ble-pin').oninput=bleControls;
$('ble-scan').onclick=()=>command('BLE','SCAN');
$('ble-off').onclick=()=>{$('ble-pin').value='';command('BLE','OFF');};
$('ble-allow-remote').onchange=()=>{blePermissionDirty=true;bleControls();};
$('ble-save').onclick=async()=>{await command('BLE','SAVE '+($('ble-allow-remote').checked?'1':'0'));blePermissionDirty=false;};
$('ble-on').onclick=()=>command('BLE','ON');
$('ble-forget').onclick=()=>{$('ble-pin').value='';blePeerDirty=false;blePermissionDirty=false;command('BLE','FORGET');};
$('files-refresh').onclick=()=>listFiles();
$('wifi-from-diagnostics').onclick=()=>document.querySelector('[data-tab="wifi"]').click();
$('record-start').onclick=async()=>{try{await stopListing();await command('START');}catch(e){notice(e.message,true);}};
$('record-stop').onclick=()=>command('STOP');
$('record-files').onclick=()=>{document.querySelector('[data-tab="files"]').click();listFiles('/records');};
$('files-records').onclick=()=>listFiles('/records');
$('files-cancel').onclick=async()=>{await stopListing();renderFiles();};
$('files-search').oninput=()=>{$('files-scroll').scrollTop=0;renderFiles();};
$('files-sort').onchange=$('files-type').onchange=()=>{$('files-scroll').scrollTop=0;renderFiles();};
$('files-download-selected').onclick=()=>{if(selectedFile)downloadFile(selectedFile);};
$('files-up').onclick=()=>listFiles(fileDirectory.slice(0,fileDirectory.lastIndexOf('/'))||'/');
$('file-download').onload=()=>{try{const text=$('file-download').contentDocument.body.textContent;if(text){const r=JSON.parse(text);if(r.message)fileNotice('Не вдалося завантажити: '+r.message);}}catch{}};
$('config-form').addEventListener('submit',e=>e.preventDefault());$('config-form').addEventListener('input',editConfig);
$('ina-fields').addEventListener('input',editConfig);
$('ina-apply').onclick=()=>$('apply').click();$('ina-save').onclick=()=>$('save').click();$('ina-reload').onclick=()=>$('reload-config').click();
$('ina-fit').onclick=()=>{const current=values(),maximum=inaTiming(current,!!state?.benchmark).maximum;if(maximum)fill(inaWithTiming(current,maximum));controls();};
$('ina-from-settings').onclick=()=>{document.querySelector('[data-tab="live"]').click();$('ina-panel').scrollIntoView({behavior:'smooth',block:'start'});};
document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>{document.querySelectorAll('.page').forEach(p=>p.hidden=p.id!==b.dataset.tab);document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active',t===b));if(b.dataset.tab==='files'&&!fileLoaded)listFiles();draw();});
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
for(const hz of RATE_PRESETS){const b=document.createElement('button');b.type='button';b.textContent=hz;b.dataset.hz=hz;
  b.onclick=()=>{$('quick-rate').value=hz;controls();};$('rate-presets').append(b);}
$('quick-rate').oninput=controls;
$('rate-mode').onchange=controls;
$('quick-rate').onkeydown=e=>{if(e.key==='Enter'&&!$('apply-rate').disabled)$('apply-rate').click();};
$('apply-rate').onclick=()=>{if(!state||dirty||stale())return;
  try{const config=quickConfig(Number($('quick-rate').value));if(!inaTiming(config,!!state.benchmark).valid)throw Error('Неприпустимий час конверсії');command('APPLY',encodeConfig(config,REGISTRY));}
  catch(e){notice(e.message,true);}};
function chartGoLive(){paused=false;$('pause').textContent='Пауза графіка';chartNav.live(Number($('chart-window').value)*1000);draw();}
$('pause').onclick=()=>{paused=!paused;$('pause').textContent=paused?'Продовжити графік':'Пауза графіка';if(!paused)chartGoLive();else draw();};
$('clear-chart').onclick=()=>{points=[];chartNav.live(Number($('chart-window').value)*1000);draw();};
$('chart-live').onclick=chartGoLive;
function chartZoom(factor,anchor=.5){const l=chartLimits();chartNav.zoom(factor,anchor,l.oldest,l.latest);draw();}
function chartPan(delta){const l=chartLimits();chartNav.pan(delta,l.oldest,l.latest);draw();}
$('chart-zoom-in').onclick=()=>chartZoom(.5);$('chart-zoom-out').onclick=()=>chartZoom(2);
$('chart-left').onclick=()=>chartPan(-chartNav.span*.25);$('chart-right').onclick=()=>chartPan(chartNav.span*.25);
$('chart').addEventListener('wheel',e=>{e.preventDefault();const r=$('chart').getBoundingClientRect();chartZoom(Math.exp(Math.max(-200,Math.min(200,e.deltaY))*.004),Math.max(0,Math.min(1,(e.clientX-r.left-65)/(r.width-80))));},{passive:false});
let chartDrag=null;
$('chart').onpointerdown=e=>{if(e.button!==0)return;const l=chartLimits();chartNav.range(l.oldest,l.latest);chartNav.follow=false;chartDrag={x:e.clientX,end:chartNav.end};$('chart').setPointerCapture(e.pointerId);$('chart').classList.add('dragging');};
$('chart').onpointermove=e=>{if(!chartDrag)return;const l=chartLimits(),width=$('chart').getBoundingClientRect().width-80;chartNav.end=chartDrag.end-(e.clientX-chartDrag.x)/width*chartNav.span;chartNav.range(l.oldest,l.latest);draw();};
$('chart').onpointerup=$('chart').onpointercancel=$('chart').onlostpointercapture=()=>{chartDrag=null;$('chart').classList.remove('dragging');};
$('chart').ondblclick=chartGoLive;
$('chart').onkeydown=e=>{if(!['ArrowLeft','ArrowRight','+','=','-','Home'].includes(e.key))return;e.preventDefault();if(e.key==='Home')chartGoLive();else if(e.key==='ArrowLeft'||e.key==='ArrowRight')chartPan(chartNav.span*(e.key==='ArrowLeft'?-.25:.25));else chartZoom(e.key==='-'?2:.5);};
$('export').onclick=()=>{try{const v=values();validateConfig(v,REGISTRY);const url=URL.createObjectURL(new Blob([JSON.stringify(exportProfile(v,REGISTRY),null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='r1s3-config-draft.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){notice(e.message,true);}};
$('import').onclick=()=>$('profile-file').click();
$('profile-file').onchange=async()=>{
  try{const file=$('profile-file').files[0];if(!file)return;if(file.size>16000)throw Error('JSON завеликий');const obj=JSON.parse(await file.text());fill(importProfile(obj,REGISTRY));notice('Профіль імпортовано в чернетку. Перевір різницю перед застосуванням.');}catch(e){notice(e.message,true);}finally{$('profile-file').value='';}
};
window.addEventListener('resize',()=>draw());
document.addEventListener('visibilitychange',()=>{if(!document.hidden){liveCursor=0;nextBreak=true;clockAt=0;}});
$('chart-window').onchange=()=>{const l=chartLimits();chartNav.window(Number($('chart-window').value)*1000,l.oldest,l.latest);draw();};
requestAnimationFrame(animate);
setInterval(()=>{if(online&&Date.now()-lastReceived>5000)setOffline('Дані застаріли. Перевір підключення логера.');},1000);
async function poll(){if(!busy&&!polling&&!stopped){polling=true;try{await refresh();}catch(e){setOffline('Немає відповіді: '+e.message);}finally{polling=false;}}setTimeout(poll,1000);}
controls();draw();
if(location.protocol==='file:')setOffline('Це панель пристрою. Запусти device_ui/start.cmd на ПК або відкрий http://192.168.4.1 у мережі логера.');
else {poll();pollLive();}

$('can-manage').onclick=()=>{document.querySelector('[data-tab="ble"]').click();$('can-form').scrollIntoView({behavior:'smooth',block:'center'});};
if($('can-form')){
  $('can-form').onsubmit=async e=>{e.preventDefault();const peer=$('can-peer').value.trim(),pin=$('can-pin').value;if(!/^([0-9a-f]{2}:){5}[0-9a-f]{2}$/i.test(peer)||!/^\d{6}$/.test(pin)){notice('Введи адресу CANBox та PIN із шести цифр.',true);return;}$('can-pin').value='';await command('BLE','CAN CONNECT '+peer+' '+pin);};
  for(const [id,verb] of [['can-save','SAVE'],['can-on','ON'],['can-start','START'],['can-stop','STOP'],['can-query','QUERY']])$(id).onclick=()=>command('BLE','CAN '+verb);
}
