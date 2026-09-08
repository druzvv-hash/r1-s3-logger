/* Opt-in physical AP test. Join the logger network first; this never changes PC networking. */
const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict'),crypto=require('crypto');
if(!process.argv.includes('--hardware'))throw Error('Explicit --hardware required; this test starts an SD recording.');
const root=path.resolve(__dirname,'..'),out=path.join(root,'data/wifi-tests');
const base='http://192.168.4.1',report={};
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function api(route,body){
 const r=await fetch(base+route,{signal:AbortSignal.timeout(4000),...(body?{method:'POST',headers:{'Content-Type':'text/plain','X-R1-Panel':'1'},body}:{})});
 assert(r.ok,'HTTP '+r.status);return r.json();
}
(async()=>{
 fs.mkdirSync(out,{recursive:true});
 const baseline=JSON.parse(fs.readFileSync(path.join(out,'baseline.json'),'utf8'));
 const initial=await api('/api/state');
 assert.equal(initial.ssid,baseline.ssid);assert.equal(initial.transport,'wifi');
 assert.equal(initial.firmware,'0.20');assert.equal(initial.recording_state,'READY');
 assert.equal(initial.config_hex,baseline.config_hex);assert(initial.ap_clients>=1);
 const browser=await chromium.launch({channel:'chrome',headless:true});let owned='';
 const errors=[];
 async function page(){
  const p=await browser.newPage({viewport:{width:390,height:844},acceptDownloads:true});
  p.on('pageerror',e=>errors.push(e.message));await p.goto(base);
  await p.waitForFunction(()=>online&&state?.transport==='wifi');return p;
 }
 try{
  let p=await page();
  await p.getByRole('button',{name:'Wi-Fi',exact:true}).click();
  assert.match(await p.locator('#network').textContent(),/Wi-Fi напряму/);
  assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await p.locator('#wifi').screenshot({path:path.join(out,'native-wifi-mobile.png')});
  await p.getByRole('button',{name:'Огляд',exact:true}).click();
  await p.locator('#record-start').click();
  await p.waitForFunction(()=>state?.recording_state==='RUNNING'&&!busy);
  const started=await p.evaluate(()=>state);owned=started.recording_path;
  fs.writeFileSync(path.join(out,'native-owned.json'),JSON.stringify({boot:started.boot,path:owned}));
  await p.close(); // No browser or API polling during this interval.
  await delay(10000);
  p=await page();const resumed=await p.evaluate(()=>state);
  assert.equal(resumed.boot,started.boot);assert.equal(resumed.recording_state,'RUNNING');
  assert.equal(resumed.recording_path,owned);assert(resumed.recording_rows>=started.recording_rows+8*initial.requested_hz);
  report.disconnected_browser_seconds=10;report.rows_while_closed=resumed.recording_rows-started.recording_rows;
  await p.locator('#record-stop').click();await p.waitForFunction(()=>state?.recording_state==='READY'&&!busy);
  const end=await p.evaluate(()=>state);owned='';assert.equal(end.recording_error,'');
  assert.equal(end.config_hex,initial.config_hex);assert.equal(end.generation,initial.generation);
  report.file=path.basename(end.recording_path);report.rows=end.recording_rows;report.bytes=end.recording_bytes;
  report.boot=end.boot;report.firmware=end.firmware;report.ap_clients=end.ap_clients;report.generation=end.generation;
  report.missed=end.missed_samples-initial.missed_samples;report.invalid=end.invalid_samples-initial.invalid_samples;
  report.fifo_high_water=end.recording_high_water;report.fifo_overflows=end.recording_overflows;
  await p.locator('#record-files').click();await p.waitForFunction(()=>!fileBusy&&document.querySelectorAll('.file-row').length>0);
  while(await p.locator('#files-more').isVisible()){await p.locator('#files-more').click();await p.waitForFunction(()=>!fileBusy);}
  const row=p.locator('.file-row').filter({hasText:report.file});
  const pending=p.waitForEvent('download');await row.getByRole('button',{name:'Завантажити',exact:true}).click();
  const download=await pending;assert.equal(await download.failure(),null);assert.equal(download.suggestedFilename(),report.file);
  await download.saveAs(path.join(out,report.file));assert.equal(fs.statSync(path.join(out,report.file)).size,report.bytes);
  report.download_url_port=new URL(download.url()).port||'80';
  // Compare a previously verified larger SD file while querying the independent UI server.
  const referenceIndex=process.argv.indexOf('--reference');
  if(referenceIndex>=0){
   const ref=process.argv[referenceIndex+1],local=fs.readFileSync(ref),name=path.basename(ref);
   const began=performance.now(),r=await fetch(base+'/api/download?path='+Buffer.from('/records/'+name).toString('hex'),{signal:AbortSignal.timeout(15000)});
   assert(r.ok);assert.equal(new URL(r.url).port,'81');
   const reading=r.arrayBuffer().then(b=>({bytes:Buffer.from(b),at:performance.now()}));
   const status=await api('/api/state'),statusAt=performance.now(),received=await reading;
   assert.equal(status.transport,'wifi');assert.equal(status.boot,initial.boot);
   assert.equal(crypto.createHash('sha256').update(received.bytes).digest('hex'),crypto.createHash('sha256').update(local).digest('hex'));
   report.reference_bytes=local.length;report.download_ms=received.at-began;
   report.status_ms=statusAt-began;report.state_during_download=statusAt<received.at;
  }
  assert.deepEqual(errors,[]);report.pass=true;
 }finally{
  // Never stop another client's recording. Preserve a failed test's data for inspection.
  if(owned){try{const s=await api('/api/state');if(s.boot===initial.boot&&s.recording_state==='RUNNING'&&s.recording_path===owned)await api('/api/command',`${s.boot} ${s.revision} STOP`);}catch(e){report.cleanup_error=e.message;}}
  await browser.close();fs.writeFileSync(path.join(out,'native-report.json'),JSON.stringify(report,null,2));
 }
 console.log(JSON.stringify(report));
})().catch(e=>{console.error(e.message);process.exit(1);});
