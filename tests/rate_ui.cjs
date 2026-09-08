/* Real DOM, synthetic device: validation, explicit application, and live draft safety. */
const {chromium}=require('playwright'),fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const {encodeConfig,decodeConfig}=require('../device_ui/codec.js');
const {RATE_PRESETS}=require('../device_ui/rate_profile.js');
const fields=require('../schemas/config-v1.json').fields,root=path.resolve(__dirname,'..');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}}),errors=[],commands=[];
  page.on('pageerror',e=>errors.push(e.message));
  let config=Object.fromEntries(fields.map(f=>[f.name,f.default])),revision=1,tick=0,phase='READY';
  await page.route('**/*',async route=>{
   const req=route.request(),p=new URL(req.url()).pathname;
   if(p==='/')return route.fulfill({contentType:'text/html',body:fs.readFileSync(path.join(root,'device_ui/index.html'),'utf8')});
   if(p==='/api/state')return route.fulfill({json:{ready:true,boot:'12345678',revision,generation:'3',config_hex:encodeConfig(config,fields),settings_status:'UNSAVED',uptime_ms:++tick*500,sample_at_ms:tick*500,requested_hz:config.requested_rate_hz,recording_state:phase,recording_available:true,valid:true,volts:3,amps:3}});
   if(p==='/api/command'){
    const command=req.postData().split(' ');commands.push(command[2]);assert.equal(command[2],'APPLY');
    config=decodeConfig(command[3],fields);revision++;
    return route.fulfill({json:{ok:true,message:'Applied',revision}});
   }
   return route.fulfill({json:{ok:true}});
  });
  await page.goto('http://127.0.0.1:9878/');
  await page.waitForFunction(()=>state?.ready);
  assert.deepEqual(await page.locator('#rate-presets button').allTextContents(),RATE_PRESETS.map(String));
  for(const bad of ['', '0','301','1.5']){
   await page.locator('#quick-rate').fill(bad);assert(await page.locator('#apply-rate').isDisabled());
  }
  await page.locator('#quick-rate').fill('137');await page.waitForTimeout(1200);
  assert.equal(await page.locator('#quick-rate').inputValue(),'137','Polling must preserve unapplied manual input');
  assert.match(await page.locator('#rate-profile').textContent(),/збільшує шум/);
  assert.equal(commands.length,0,'Editing never sends a mutation');
  await page.locator('#apply-rate').click();await page.waitForFunction(()=>state.requested_hz===137&&!busy);
  assert.equal(config.vshunt_ct_code,2);assert.equal(config.shunt_uohm,150);
  await page.locator('[data-hz="1"]').click();await page.locator('#quick-rate').press('Enter');
  await page.waitForFunction(()=>state.requested_hz===1&&!busy);
  assert.equal(config.max_gap_us,2000000);assert.equal(config.vshunt_ct_code,5);
  await page.locator('[data-hz="300"]').click();await page.locator('#apply-rate').click();
  await page.waitForFunction(()=>state.requested_hz===300&&!busy);assert.equal(config.vshunt_ct_code,0);
  phase='RUNNING';await page.waitForFunction(()=>state.recording_state==='RUNNING');
  assert(await page.locator('#quick-rate').isDisabled());assert(await page.locator('[data-hz="100"]').isDisabled());
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Mobile overflow');
  fs.mkdirSync(path.join(root,'data/production-rates'),{recursive:true});
  await page.screenshot({path:path.join(root,'data/production-rates/rates-mobile.png'),fullPage:true});
  assert.deepEqual(commands,['APPLY','APPLY','APPLY']);assert.deepEqual(errors,[]);
  console.log('RATE UI PASS: presets, integers, draft preservation, profiles, no SAVE, recording lock, mobile');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
