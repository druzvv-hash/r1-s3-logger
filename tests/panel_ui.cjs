/* Browser acceptance. Default uses explicit synthetic fixtures; --hardware uses COM5 bridge. */
const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const {encodeConfig}=require('../device_ui/codec.js');
const fields=require('../schemas/config-v1.json').fields;
const root=path.resolve(__dirname,'..'),hardware=process.argv.includes('--hardware');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const config=Object.fromEntries(fields.map(f=>[f.name,f.default]));
  let offline=false, frozen=false, sample=0, liveId=0;
  const fake={ready:true,firmware:'fixture',boot:'12345678',revision:1,generation:'3',settings_status:'SAVED',config_hex:encodeConfig(config,fields),uptime_ms:1000,sample_at_ms:1000,valid:true,volts:4.906,amps:3.995,watts:19.59947,temp_c:27.25,shunt_uv:599.25,shunt_raw:1918,bus_raw:25119,temp_raw:3488,sd:'READ',eeprom:'READ',rtc:'TICK OK',oled:true,i2c_count:4,i2c_errors:0,utc:1788840000,owner_core:1,ui_core:0,psram_free:16000000,heap_free:130000,queue_bytes:65536,buffer_ready:true,sd_block_bytes:8192,ap_ready:true,ssid:'R1-S3-TEST',ap_password:'synthetic-fixture'};
  let url;
  if(hardware)url=JSON.parse(fs.readFileSync(path.join(root,'data/device-panel/session.json'),'utf8')).url;
  else{
   url='http://127.0.0.1:9876/';
   await page.route('**/*',async route=>{
    const req=route.request(),p=new URL(req.url()).pathname;
    if(p==='/')return route.fulfill({contentType:'text/html',body:fs.readFileSync(path.join(root,'device_ui/index.html'),'utf8')});
    if(p==='/api/live'){
     if(offline)return route.fulfill({status:503,json:{message:'Fixture disconnected'}});
     const samples=[];
     if(!frozen)for(let j=0;j<10;j++){liveId++;samples.push([liveId,liveId*20000,4.906,3.995,0,fake.revision]);}
     return route.fulfill({json:{boot:fake.boot,samples,lost:false,cursor:liveId,newest:liveId}});
    }
    if(p==='/api/state'){
     if(offline)return route.fulfill({status:503,json:{message:'Fixture disconnected'}});
     if(!frozen)sample++;return route.fulfill({json:{...fake,live_available:true,requested_hz:50,measured_hz:50,ina:'ADC OK',sample_id:sample,uptime_ms:sample*1000,sample_at_ms:sample*1000}});
    }
    return route.fulfill({json:{ok:true,message:'Fixture OK'}});
   });
  }
  await page.goto(url);
  await page.waitForFunction(()=>document.getElementById('connection').textContent.includes('підключений'),{timeout:20000});
  await page.waitForTimeout(2200);
  assert.notEqual(await page.locator('#amps').textContent(),'—');
  const animation=await page.evaluate(()=>({fps,count:points.length}));
  if(!hardware){
   fake.transport='usb';fake.ap_clients=0;
   await page.getByRole('button',{name:'Wi-Fi',exact:true}).click();
   await page.waitForFunction(()=>document.getElementById('network').textContent.includes('USB через ПК'));
   assert.match(await page.locator('#wifi-connection-note').textContent(),/через ПК/);
   assert.equal(await page.locator('#wifi-password').isVisible(),false);
   fake.transport='wifi';fake.ap_clients=1;
   await page.waitForFunction(()=>document.getElementById('connection').textContent.includes('Wi-Fi'));
   assert.match(await page.locator('#network').textContent(),/Wi-Fi напряму/);
   assert.match(await page.locator('#network').textContent(),/Пристроїв у Wi-Fi1/);
   assert.match(await page.locator('#wifi-connection-note').textContent(),/напряму/);
   assert.equal(await page.locator('#release-usb').isVisible(),false);
   await page.setViewportSize({width:390,height:844});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Wi-Fi mobile overflow');
   fs.mkdirSync(path.join(root,'data/wifi-tests'),{recursive:true});
   await page.locator('#wifi').screenshot({path:path.join(root,'data/wifi-tests/panel-mobile-fixture.png')});
   await page.setViewportSize({width:1440,height:1100});
   await page.getByRole('button',{name:'Огляд',exact:true}).click();
  }
  assert(animation.count>20,'Real samples must enter the graph');
  assert(animation.fps>=45&&animation.fps<=65,'60 FPS requestAnimationFrame rendering');
  if(!hardware){
   // Invalid records remain null, and a sequence/configuration gap is not joined.
   await page.evaluate(()=>{
    acceptLive({boot:state.boot,samples:[[liveCursor+2,clockDevice*1000+20000,0,0,1,state.revision]]});
    if(points.at(-1).i!==null||!points.at(-1).gap)throw Error('Invalid/gap record lost');
   });
   await page.locator('#pause').click();
   const count=await page.evaluate(()=>points.length);
   await page.waitForTimeout(450);
   assert.equal(await page.evaluate(()=>points.length),count,'Paused chart must stay frozen');
   await page.locator('#pause').click();
   await page.locator('#frame-rate').selectOption('30');
   await page.waitForTimeout(2200);
   const slow=await page.evaluate(()=>fps);
   assert(slow>=25&&slow<=33,'30 FPS limiter');
   await page.locator('#frame-rate').selectOption('60');
  }
  await page.getByRole('button',{name:'Налаштування',exact:true}).click();
  const contrast=await page.locator('#f-oled_contrast').inputValue();
  await page.locator('#f-oled_contrast').fill(contrast==='100'?'101':'100');
  assert.equal(await page.locator('#apply').isEnabled(),true);
  assert.equal(await page.locator('#save').isEnabled(),false);
  await page.locator('#f-i_gain').fill('0');
  assert.equal(await page.locator('#apply').isEnabled(),false);
  await page.getByRole('button',{name:'Прочитати з логера',exact:true}).click();
  await page.waitForFunction(()=>document.getElementById('draft-note').textContent==='Чернетка відповідає логеру');
  if(!hardware){
   await page.locator('#f-oled_contrast').fill('100');fake.revision++;
   await page.waitForFunction(()=>document.getElementById('draft-note').textContent.includes('Стан змінився'));
   assert.equal(await page.locator('#apply').isEnabled(),false);
   await page.getByRole('button',{name:'Прочитати з логера',exact:true}).click();
  }else{
   // A reversible display-only change proves the real browser-to-INA/settings owner path.
   await page.locator('#f-oled_contrast').fill(contrast==='100'?'101':'100');
   await page.locator('#apply').click();
   await page.waitForFunction(()=>document.getElementById('notice').textContent.startsWith('Налаштування застосовано'),{timeout:20000});
   await page.locator('#f-oled_contrast').fill(contrast);
   await page.locator('#apply').click();
   await page.waitForFunction(()=>document.getElementById('notice').textContent.startsWith('Налаштування застосовано')&&document.getElementById('draft-note').textContent==='Чернетка відповідає логеру',{timeout:20000});
   assert.match(await page.locator('#config-state').textContent(),/збережено/);
  }
  await page.getByRole('button',{name:'Огляд',exact:true}).click();
  if(hardware)await page.waitForFunction(()=>document.getElementById('amps').textContent!=='—',{timeout:10000});
  if(hardware){
   const baselineRate=await page.evaluate(()=>state.requested_hz);
   await page.locator('#quick-rate').selectOption('100');
   await page.locator('#apply-rate').click();
   await page.waitForFunction(()=>state.requested_hz===100&&!busy,{timeout:20000});
   try{
    await page.waitForTimeout(8000);
    // Headless Chrome can lower its own rAF cadence when occluded/backgrounded.
    // Check the application against delivered callbacks, not an assumed display clock.
    await page.evaluate(()=>{
     window.rafProbe={count:0,start:performance.now(),active:true};
     requestAnimationFrame(function probe(){if(!rafProbe.active)return;rafProbe.count++;requestAnimationFrame(probe);});
    });
    const frames=[];
    for(let n=0;n<5;n++){await page.waitForTimeout(1100);frames.push(await page.evaluate(()=>fps));}
    const browserFps=await page.evaluate(()=>{rafProbe.active=false;return rafProbe.count*1000/(performance.now()-rafProbe.start);});
    const stream=await page.evaluate(()=>({requested:state.requested_hz,measured:state.measured_hz,invalid:state.invalid_samples,missed:state.missed_samples,preview_drops:state.preview_drops,gaps:streamGaps,points:points.length}));
    stream.fps=frames.reduce((a,b)=>a+b,0)/frames.length;
    stream.browser_callbacks_hz=browserFps;
    console.log('Live 100 Hz / browser:',JSON.stringify(stream));
    assert(Math.abs(stream.measured-100)<1);
    assert(stream.fps>=Math.min(60,browserFps)*.8&&stream.fps<=65);
    assert.equal(stream.preview_drops,0);
   }finally{
    await page.locator('#quick-rate').selectOption(String(baselineRate));
    await page.locator('#apply-rate').click();
    await page.waitForFunction(hz=>state.requested_hz===hz&&!busy,baselineRate,{timeout:20000});
   }
  }
  fs.mkdirSync(path.join(root,'data/device-panel'),{recursive:true});
  await page.screenshot({path:path.join(root,'data/device-panel',hardware?'panel-live.png':'panel-fixture.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.waitForTimeout(200);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'Mobile overflow');
  await page.screenshot({path:path.join(root,'data/device-panel',hardware?'panel-mobile-live.png':'panel-mobile-fixture.png'),fullPage:true});
  if(!hardware){
   frozen=true;await page.waitForFunction(()=>document.getElementById('amps').textContent==='—',{timeout:10000});
   frozen=false;await page.waitForFunction(()=>document.getElementById('amps').textContent!=='—');
   offline=true;await page.waitForFunction(()=>document.getElementById('amps').textContent==='—');
  }
  assert.deepEqual(errors,[]);
  console.log(hardware?'Live panel: readings, contrast apply/restore, EEPROM state and mobile layout PASS':'Fixture panel: draft validation, stale revision, disconnect and mobile layout PASS');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
