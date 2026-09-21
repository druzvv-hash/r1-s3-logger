/* Explicit synthetic device fixture; does not write a physical RTC. */
const {chromium}=require('playwright');
const fs=require('fs'),assert=require('node:assert/strict');
const {encodeConfig}=require('../device_ui/codec.js');
const fields=require('../schemas/config-v1.json').fields;
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const page=await browser.newPage({timezoneId:'Europe/Prague',viewport:{width:390,height:844}});
  let authority=false,phase='READY',tick=0;const commands=[],errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',async route=>{
   const req=route.request(),p=new URL(req.url()).pathname;
   if(p==='/')return route.fulfill({contentType:'text/html',body:fs.readFileSync('device_ui/index.html','utf8')});
   if(p==='/api/state')return route.fulfill({json:{ready:true,boot:'fixture',revision:1,generation:'3',
    config_hex:encodeConfig(Object.fromEntries(fields.map(f=>[f.name,f.default])),fields),
    settings_status:'SAVED',uptime_ms:++tick*500,recording_state:phase,utc:1789981200,
    time_authority_available:authority}});
   if(p==='/api/command'){commands.push(req.postData());return route.fulfill({json:{ok:true,message:'Fixture RTC verified'}});}
   return route.fulfill({json:{ok:true}});
  });
  await page.goto('http://127.0.0.1:9892/');await page.waitForFunction(()=>online);
  await page.locator('#manual-time').fill('2026-09-21T12:34:56');
  assert.equal(commands.length,0,'Editing must not set time');
  await page.locator('#set-manual-time').click();await page.waitForFunction(()=>!busy);
  assert.equal(commands[0],'fixture 1 TIME '+Date.parse('2026-09-21T10:34:56Z')/1000,'Local Prague summer time converts to UTC');
  await page.evaluate(()=>{$('manual-time').value='2026-03-29T02:30:00';controls();});
  await page.locator('#set-manual-time').click();assert.equal(commands.length,1,'Nonexistent DST time is rejected');
  await page.locator('#manual-time').fill('2000-01-02T12:00');
  await page.locator('#set-manual-time').click();await page.waitForFunction(()=>!busy);
  assert.equal(commands[1],'fixture 1 TIME '+Date.parse('2000-01-02T11:00:00Z')/1000);
  authority=true;await page.waitForFunction(()=>state.time_authority_available);
  assert(await page.locator('#sync-time').isDisabled());assert(await page.locator('#set-manual-time').isDisabled());
  authority=false;phase='RUNNING';await page.waitForFunction(()=>state.recording_state==='RUNNING');
  assert(await page.locator('#sync-time').isDisabled());assert(await page.locator('#manual-time').isDisabled());
  phase='READY';await page.waitForFunction(()=>state.recording_state==='READY');
  assert(await page.locator('#sync-time').isEnabled());
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Mobile overflow');
  fs.mkdirSync('data/time-ui-tests',{recursive:true});await page.locator('#time-panel').screenshot({path:'data/time-ui-tests/mobile.png'});
  assert.deepEqual(errors,[]);console.log('PASS: manual UTC conversion, DST rejection, no implicit write, R3 priority, recording lock, mobile layout');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
