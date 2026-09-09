/* Synthetic browser acceptance only: no board, serial port or Bluetooth adapter. */
const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const {encodeConfig}=require('../device_ui/codec.js');
const fields=require('../schemas/config-v1.json').fields,root=path.resolve(__dirname,'..');
const read=name=>fs.readFileSync(path.join(root,name),'utf8');
// Assemble in memory so this isolated test does not rewrite firmware assets.
const html=read('device_ui/index.template.html').replace('/*STYLE*/',()=>read('device_ui/style.css'))
 .replace('/*SCHEMA*/',()=>JSON.stringify(fields)).replace('/*CODEC*/',()=>read('device_ui/codec.js'))
 .replace('/*RATE_PROFILE*/',()=>read('device_ui/rate_profile.js')).replace('/*APP*/',()=>read('device_ui/app.js'));
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:1000}}),errors=[],commands=[];
  page.on('pageerror',error=>errors.push(error.message));
  const config=Object.fromEntries(fields.map(field=>[field.name,field.default]));
  let tick=0;
  const fake={ready:true,firmware:'BLE fixture',boot:'12345678',revision:7,generation:'3',settings_status:'SAVED',
   config_hex:encodeConfig(config,fields),valid:true,volts:0,amps:0,temp_c:24,shunt_uv:0,sd:'READ',eeprom:'READ',rtc:'TICK OK',
   oled:true,i2c_count:4,i2c_errors:0,utc:1788840000,owner_core:1,ui_core:0,psram_free:16000000,heap_free:130000,
   queue_bytes:65536,buffer_ready:true,sd_block_bytes:8192,ap_ready:true,ssid:'fixture',ap_password:'fixture',
   transport:'usb',recording_state:'READY',recording_available:true,requested_hz:50,measured_hz:50};
  const ble={enabled:false,state:'OFF',peer:'AA:BB:CC:DD:EE:FF',authenticated:false,fresh:false,utc_valid:false,
   synchronized:false,source_boot:'11223344',clock_revision:1,segment:'4',last_sequence:17,age_ms:null,
   enrolled:false,ecosystem:true,remote_allowed:false,rtc_synced:false,
   received:'9007199254740993',missing:'1',malformed:'0',duplicates:'0',out_of_order:'0',drops:0,
   reconnects:0,connections:0,last_error:'',mtu:185,devices:[]};
  await page.route('**/*',async route=>{
   const request=route.request(),pathname=new URL(request.url()).pathname;
   if(pathname==='/')return route.fulfill({contentType:'text/html',body:html});
   if(pathname==='/api/state')return route.fulfill({json:{...fake,uptime_ms:++tick*1000,sample_at_ms:tick*1000}});
   if(pathname==='/api/live')return route.fulfill({json:{boot:fake.boot,samples:[],lost:false,cursor:0,newest:0}});
   if(pathname==='/api/command'){
    const body=request.postData();commands.push(body);
    if(body.endsWith(' BLE SCAN')){ble.enabled=true;ble.state='SCANNING';ble.devices=[{address:'11:22:33:44:55:66',name:'R3 <img src=x onerror=alert(1)>'}];}
    if(body.includes(' BLE CONNECT ')){ble.peer=body.split(' ')[4];ble.enabled=true;ble.state='CONNECTED';ble.authenticated=true;ble.fresh=true;ble.utc_valid=true;ble.age_ms=250;ble.connections=1;}
    if(body.endsWith(' BLE OFF')){ble.enabled=false;ble.state='OFF';ble.fresh=false;ble.authenticated=false;}
    if(/ BLE SAVE [01]$/.test(body)){ble.enrolled=true;ble.remote_allowed=body.endsWith('1');}
    if(body.endsWith(' BLE ON')){ble.enabled=true;ble.state='RETRY';ble.authenticated=false;ble.fresh=false;}
    if(body.endsWith(' BLE FORGET')){ble.enrolled=false;ble.remote_allowed=false;ble.peer='';ble.enabled=false;ble.state='OFF';ble.authenticated=false;ble.fresh=false;ble.rtc_synced=false;}
    if(body.endsWith(' STOP'))fake.recording_state='STOPPING';
    // A careless backend echo must not reveal the pairing PIN in the page.
    return route.fulfill({json:{ok:true,message:body}});
   }
   return route.fulfill({status:404,json:{message:'Fixture route missing'}});
  });
  await page.goto('http://127.0.0.1:9877/');
  await page.waitForFunction(()=>online);
  await page.getByRole('button',{name:'BLE · R3',exact:true}).click();
  assert.equal(await page.locator('#ble-scan').isDisabled(),true,'Older firmware must disable BLE commands');
  for(const id of ['ble-save','ble-on','ble-forget'])assert.equal(await page.locator('#'+id).isDisabled(),true,'No enrollment commands without firmware capability');
  assert.match(await page.locator('#ble-note').textContent(),/прошивка не повідомляє/);
  fake.ble=ble;
  await page.evaluate(()=>refresh());
  assert.equal(await page.locator('#ble-scan').isEnabled(),true);
  assert.equal(await page.locator('#ble-peer').inputValue(),ble.peer);
  assert.equal(await page.locator('#ble-off').isDisabled(),true);
  await page.locator('#ble-scan').click();await page.waitForFunction(()=>!busy&&state.ble.state==='SCANNING');
  assert.equal(commands.at(-1),'12345678 7 BLE SCAN');
  assert.equal(await page.locator('#ble-peers option').count(),1);
  assert.equal(await page.locator('#ble img').count(),0,'Discovery names must be text, never HTML');
  ble.state='READY';await page.evaluate(()=>refresh());
  assert.equal(await page.locator('#ble-state').textContent(),'Вибери R3');
  assert.match(await page.locator('#ble-note').textContent(),/Пошук завершено/);
  await page.locator('#ble-peer').fill('11:22:33:44:55:66');
  await page.locator('#ble-pin').fill('01234');assert.equal(await page.locator('#ble-connect').isDisabled(),true);
  await page.locator('#ble-pin').fill('012345');
  await page.evaluate(()=>refresh());
  assert.equal(await page.locator('#ble-peer').inputValue(),'11:22:33:44:55:66','Polling must preserve peer input');
  await page.locator('#ble-connect').click();
  assert.equal(await page.locator('#ble-pin').inputValue(),'','PIN must clear as soon as submitted');
  await page.waitForFunction(()=>!busy&&state.ble.fresh);
  assert.equal(commands.at(-1),'12345678 7 BLE CONNECT 11:22:33:44:55:66 012345');
  assert.match(await page.locator('#ble-note').textContent(),/Маяк отримано; точність синхронізації ще не визначена/);
  assert.equal((await page.locator('body').textContent()).includes('012345'),false,'Never display echoed PIN');
  assert.equal(await page.evaluate(()=>localStorage.length),0,'Do not persist PIN or peer in browser storage');
  assert.match(await page.locator('#ble-diagnostics').textContent(),/9007199254740993/,'Keep decimal counter precision');
  assert.equal(await page.locator('#ble-save').isEnabled(),true,'Authenticated ecosystem peer can be explicitly enrolled');
  assert.equal(await page.locator('#ble-allow-remote').isChecked(),false,'Clock enrollment does not imply recording permission');
  await page.locator('#ble-save').click();await page.waitForFunction(()=>!busy&&state.ble.enrolled);
  assert.equal(commands.at(-1),'12345678 7 BLE SAVE 0','Time-only enrollment saves an explicit disabled remote-control policy');
  assert.equal(ble.remote_allowed,false);
  await page.locator('#ble-allow-remote').check();await page.evaluate(()=>refresh());
  assert.equal(await page.locator('#ble-allow-remote').isChecked(),true,'Polling preserves unsaved permission choice');
  await page.locator('#ble-save').click();await page.waitForFunction(()=>!busy&&state.ble.remote_allowed);
  assert.equal(commands.at(-1),'12345678 7 BLE SAVE 1','Explicit permission is sent only on Save');
  assert.match(await page.locator('#ble-summary').textContent(),/Збережена/);
  assert.equal(await page.evaluate(()=>localStorage.length),0,'Enrollment policy belongs to the device, not browser storage');
  await page.getByRole('button',{name:'Налаштування',exact:true}).click();
  await page.locator('#f-oled_contrast').fill('100');
  fake.revision++;
  await page.evaluate(()=>refresh());
  assert.equal(await page.locator('#f-oled_contrast').inputValue(),'100','BLE polling must preserve settings draft');
  assert.equal(await page.locator('#apply').isDisabled(),true,'Revision conflicts still guard settings apply');
  await page.getByRole('button',{name:'BLE · R3',exact:true}).click();
  fake.recording_state='RUNNING';await page.evaluate(()=>refresh());
  for(const id of ['ble-scan','ble-connect','ble-off','ble-peer','ble-pin','ble-save','ble-on','ble-forget','ble-allow-remote'])assert.equal(await page.locator('#'+id).isDisabled(),true,'STOP-only '+id);
  fake.recording_state='STARTING';await page.evaluate(()=>refresh());
  assert.equal(await page.locator('#record-stop').isEnabled(),true,'Local Stop is available during STARTING');
  assert.equal(await page.locator('#record-start').isDisabled(),true,'No second Start during STARTING');
  for(const id of ['ble-save','ble-on','ble-forget'])assert.equal(await page.locator('#'+id).isDisabled(),true,'Enrollment locked while starting');
  await page.getByRole('button',{name:'Огляд',exact:true}).click();
  await page.locator('#record-stop').click();await page.waitForFunction(()=>!busy&&state.recording_state==='STOPPING');
  assert.equal(commands.at(-1),'12345678 8 STOP','STARTING Stop uses latest owner revision');
  assert.match(await page.locator('#record-note').textContent(),/закриття|Збереження|Дописування/);
  await page.getByRole('button',{name:'BLE · R3',exact:true}).click();
  fake.recording_state='READY';ble.fresh=false;ble.state='RETRY';await page.evaluate(()=>refresh());
  assert.match(await page.locator('#ble-note').textContent(),/Зв’язок втрачено/);
  assert.equal(await page.locator('#ble-state').evaluate(node=>node.classList.contains('online')),false);
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'BLE mobile layout overflow');
  const output=path.join(root,'data/ble-tests');fs.mkdirSync(output,{recursive:true});
  await page.locator('#ble').screenshot({path:path.join(output,'panel-mobile-fixture.png')});
  await page.locator('#ble-off').click();await page.waitForFunction(()=>!busy&&!state.ble.enabled);
  assert.equal(commands.at(-1),'12345678 8 BLE OFF','Use latest owner revision');
  assert.equal(ble.enrolled,true,'Turning BLE off does not forget trusted R3');
  assert.equal(await page.locator('#ble-on').isEnabled(),true);
  await page.locator('#ble-on').click();await page.waitForFunction(()=>!busy&&state.ble.enabled);
  assert.equal(commands.at(-1),'12345678 8 BLE ON','Saved enrollment reconnect needs no PIN');
  const beforeReload=commands.length;await page.reload();await page.waitForFunction(()=>online);
  assert.equal(commands.length,beforeReload,'Reload only reads state; it does not replay any BLE or logging command');
  await page.getByRole('button',{name:'BLE · R3',exact:true}).click();
  assert.match(await page.locator('#ble-summary').textContent(),/Збережена/);
  assert.equal(await page.locator('#ble-pin').inputValue(),'','Saved trust never repopulates PIN');
  await page.locator('#ble-forget').click();await page.waitForFunction(()=>!busy&&!state.ble.enrolled);
  assert.equal(commands.at(-1),'12345678 8 BLE FORGET');
  assert.equal(await page.locator('#ble-on').isDisabled(),true,'Forgotten peer cannot use saved reconnect');
  assert.equal(await page.locator('#ble-allow-remote').isChecked(),false,'Forget removes remote-control permission');
  await page.evaluate(()=>setOffline('Fixture disconnected'));
  assert.equal(await page.locator('#ble-scan').isDisabled(),true);
  assert.match(await page.locator('#ble-note').textContent(),/Немає свіжого стану/);
  assert.deepEqual(errors,[]);
  console.log('BLE UI fixture PASS: discovery, PIN privacy, SAVE0/SAVE1 enrollment, saved ON/FORGET, STARTING Stop, no reload replay, owner commands, recording guard, time uncertainty, counters, draft preservation, mobile layout.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
