const {chromium}=require('playwright'),fs=require('fs'),assert=require('node:assert/strict');
const {encodeConfig}=require('../device_ui/codec.js');
const fields=require('../schemas/config-v1.json').fields;
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}});let phase='READY',tick=0;const commands=[],errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',async route=>{
   const req=route.request(),path=new URL(req.url()).pathname;
   if(path==='/')return route.fulfill({contentType:'text/html',body:fs.readFileSync('device_ui/index.html','utf8')});
   if(path==='/api/state')return route.fulfill({json:{ready:true,boot:'fixture',revision:1,generation:'1',settings_status:'SAVED',
    uptime_ms:++tick*500,recording_state:phase,config_hex:encodeConfig(Object.fromEntries(fields.map(f=>[f.name,f.default])),fields),
    station:{connected:true,ssid:'Home fixture',ip:'192.168.0.50',hostname:'r1-s3-7455',rssi:-55,profiles:3}}});
   if(path==='/api/command'){commands.push(req.postData());return route.fulfill({json:{ok:true,message:'Wi-Fi change queued'}});}
   return route.fulfill({json:{ok:true}});
  });
  await page.goto('http://127.0.0.1:9893/');await page.waitForFunction(()=>online);
  await page.locator('[data-tab=wifi]').click();
  assert.equal(await page.locator('#lan-url').getAttribute('href'),'http://192.168.0.50/');
  assert.equal(await page.locator('#lan-name').getAttribute('href'),'http://r1-s3-7455.local/');
  await page.locator('#lan-ssid').fill('Home fixture');await page.locator('#lan-password').fill('fixture-password');
  assert.equal(commands.length,0);await page.locator('#lan-save').click();await page.waitForFunction(()=>!busy);
  assert.equal(commands[0],'fixture 1 WIFI '+Buffer.from('Home fixture').toString('hex')+' '+Buffer.from('fixture-password').toString('hex'));
  assert.equal(await page.locator('#lan-password').inputValue(),'');
  assert(!await page.locator('body').textContent().then(t=>t.includes('fixture-password')));
  phase='RUNNING';await page.waitForFunction(()=>recordingBusy());assert(await page.locator('#lan-save').isDisabled());
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.deepEqual(errors,[]);
  console.log('PASS: LAN links, explicit network save, password clearing, recording lock, mobile layout');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
