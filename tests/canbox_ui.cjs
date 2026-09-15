// Synthetic panel acceptance; physical BLE is qualified separately.
const {chromium}=require('playwright');
const fs=require('fs'),assert=require('node:assert/strict');
const {encodeConfig}=require('../device_ui/codec.js');
const fields=require('../schemas/config-v1.json').fields;
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:1000}}),errors=[],commands=[];
  page.on('pageerror',e=>errors.push(e.message));
  const cfg=Object.fromEntries(fields.map(f=>[f.name,f.default]));
  const can={mode:true,saved:true,connected:true,fresh:true,pending:false,phase:'closed',session:'9007199254740993',detail:0};
  let tick=0;
  const fake={ready:true,firmware:'CANBox fixture',boot:'12345678',revision:7,generation:'4',settings_status:'SAVED',config_hex:encodeConfig(cfg,fields),valid:true,volts:0,amps:0,temp_c:24,shunt_uv:0,sd:'READ',eeprom:'READ',rtc:'TICK OK',ina:'ADC OK',recording_state:'READY',recording_available:true,live_available:true,requested_hz:5,ble:{enabled:true,state:'CANBOX',devices:[],canbox:can}};
  await page.route('http://127.0.0.1:9877/**',async route=>{
   const path=new URL(route.request().url()).pathname;
   if(path==='/')return route.fulfill({contentType:'text/html',body:fs.readFileSync('device_ui/index.html','utf8')});
   if(path==='/api/state')return route.fulfill({json:{...fake,uptime_ms:++tick*500,sample_id:tick}});
   if(path==='/api/live')return route.fulfill({json:{boot:fake.boot,samples:[],lost:false,cursor:0,newest:0}});
   if(path==='/api/command'){commands.push(route.request().postData());can.pending=true;return route.fulfill({json:{ok:true,message:commands.at(-1)}});}
   return route.fulfill({status:404,json:{message:'No fixture'}});
  });
  await page.goto('http://127.0.0.1:9877/');await page.waitForFunction(()=>online);
  await page.locator('[data-tab="ble"]').click();
  assert.equal(await page.locator('#can-start').isEnabled(),true);
  assert.equal(await page.locator('#can-stop').isDisabled(),true);
  assert.match(await page.locator('#can-state').textContent(),/9007199254740993/);
  await page.locator('#can-start').click();await page.waitForFunction(()=>!busy&&state.ble.canbox.pending);
  assert.equal(commands.at(-1),'12345678 7 BLE CAN START');
  assert.equal(await page.locator('#can-start').isDisabled(),true);
  assert.match(await page.locator('#can-state').textContent(),/Очікуємо результат/);
  can.pending=false;can.phase='recording';await page.evaluate(()=>refresh());
  assert.equal(await page.locator('#can-stop').isEnabled(),true);
  await page.locator('#can-stop').click();await page.waitForFunction(()=>!busy&&state.ble.canbox.pending);
  assert.equal(commands.at(-1),'12345678 7 BLE CAN STOP');
  can.pending=false;can.phase='closed';can.fresh=false;await page.evaluate(()=>refresh());
  assert.equal(await page.locator('#can-start').isDisabled(),true);
  assert.match(await page.locator('#can-state').textContent(),/запис може тривати/);
  can.fresh=true;can.saved=false;await page.evaluate(()=>refresh());
  assert.equal(await page.locator('#can-start').isDisabled(),true,'Unsaved peer cannot start');
  await page.locator('#can-peer').fill('11:22:33:44:55:66');await page.locator('#can-pin').fill('012345');
  await page.locator('#can-connect').click();
  assert.equal(await page.locator('#can-pin').inputValue(),'');
  await page.waitForFunction(()=>!busy);
  assert.equal(commands.at(-1),'12345678 7 BLE CAN CONNECT 11:22:33:44:55:66 012345');
  assert.equal((await page.locator('body').textContent()).includes('012345'),false);
  assert.equal(await page.evaluate(()=>localStorage.length),0);
  assert.deepEqual(errors,[]);
  await page.screenshot({path:'C:/Projects/GLL CANBox/local/r1-canbox-panel.png',fullPage:true});
  console.log('PASS CANBox actual/pending/stale/permission/64-bit/PIN panel checks');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
