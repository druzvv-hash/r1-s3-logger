/* Read-only browser acceptance; --hardware downloads actual SD files over the USB bridge. */
const {chromium}=require('playwright'),fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const {encodeConfig}=require('../device_ui/codec.js');
const fields=require('../schemas/config-v1.json').fields;
const hardware=process.argv.includes('--hardware'),root=path.resolve(__dirname,'..');
const data=Buffer.from([0,255,10,13,35,34,65,66,67]);
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});let fixtureServer;
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1050},acceptDownloads:true,timezoneId:'Europe/Prague'});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  let url;
  if(hardware)url=JSON.parse(fs.readFileSync(path.join(root,'data/device-panel/session.json'),'utf8')).url;
  else{
   fixtureServer=require('http').createServer((req,res)=>{res.writeHead(200,{'Content-Type':'application/octet-stream','Content-Length':data.length,'Content-Disposition':"attachment; filename*=UTF-8''%D1%82%D0%B5%D1%81%D1%82%20%231.csv"});res.end(data);});
   await new Promise(r=>fixtureServer.listen(0,'127.0.0.1',r));
   url='http://127.0.0.1:'+fixtureServer.address().port+'/';let tick=0;
   const config=Object.fromEntries(fields.map(f=>[f.name,f.default]));
   await page.route('**/*',async route=>{
    const u=new URL(route.request().url());
    if(u.pathname==='/')return route.fulfill({contentType:'text/html',body:fs.readFileSync(path.join(root,'device_ui/index.html'),'utf8')});
    if(u.pathname==='/api/state')return route.fulfill({json:{ready:true,firmware:'fixture',boot:'test',revision:1,generation:'3',config_hex:encodeConfig(config,fields),settings_status:'SAVED',files_available:true,valid:true,uptime_ms:++tick*1000,sample_at_ms:tick*1000,volts:3,amps:1,temp_c:20,live_available:false,transport:'usb'}});
    if(u.pathname==='/api/live')return route.fulfill({json:{boot:'test',samples:[]}});
    if(u.pathname==='/api/files'){
     const c=u.searchParams.get('command');
     if(c==='LIST 2f')return route.fulfill({json:{ok:true,session:1,more:false,entries:[{name:'<img onerror=alert(1)>',directory:true,path:Buffer.from('/logs').toString('hex'),size:0},{name:'тест #1.csv',directory:false,path:Buffer.from('/тест #1.csv').toString('hex'),size:data.length}]}});
     if(c.startsWith('LIST'))return route.fulfill({json:{ok:true,session:1,more:false,entries:[]}});
     return route.fulfill({json:{ok:true,session:1,size:data.length}});
    }
    if(u.pathname==='/api/download')return route.continue();
    return route.fulfill({status:404,body:'Not found'});
   });
  }
  await page.goto(url);
  await page.waitForFunction(()=>state?.files_available&&online);
  assert.deepEqual(await page.evaluate(()=>[
   recordingDate('r1s3_1788864937_4ee24d5b_9ebc8459_0000.csv')?.toISOString(),
   recordingDate('r1s3_2026-09-08_10-55-37Z_4ee24d5b_9ebc8459_0001.part')?.toISOString(),
   recordingDate('r1s3_time-unknown_00000000_00000001_0000.csv'),
   recordingDate('r1s3_0_00000000_00000001_0000.csv'),
   recordingDate('unrelated.csv')
  ]),['2026-09-08T10:55:37.000Z','2026-09-08T10:55:37.000Z',null,null,null]);
  await page.getByRole('button',{name:'Файли SD',exact:true}).click();
  await page.locator('#files-refresh').click();
  await page.waitForFunction(()=>!fileBusy&&document.querySelectorAll('.file-row').length>0);
  assert.equal(await page.locator('#file-list img').count(),0,'Filenames must be text, never HTML');
  const button=page.locator('.file-row').filter({has:page.getByRole('button',{name:'Завантажити',exact:true})}).first();
  const filename=await button.locator('.file-name-text').textContent();
  const pending=page.waitForEvent('download');await button.getByRole('button',{name:'Завантажити',exact:true}).click();
  const download=await pending;assert.equal(await download.failure(),null);
  assert.equal(download.suggestedFilename(),filename);
  const bytes=fs.readFileSync(await download.path());
  if(!hardware)assert.deepEqual(bytes,data);
  else{
   const ref=new URL(download.url());ref.searchParams.set('token',new URL(url).searchParams.get('token'));
   const response=await fetch(ref);assert(response.ok);assert.deepEqual(Buffer.from(await response.arrayBuffer()),bytes,'Two real downloads must be byte-identical');
   await download.saveAs(path.join(root,'data/device-panel',path.basename(filename)));
  }
  if(!hardware){
   await page.getByRole('button',{name:'Відкрити',exact:true}).first().click();
   await page.waitForFunction(()=>document.getElementById('files-status').textContent==='Папка порожня.');
   await page.locator('#files-up').click();await page.waitForFunction(()=>document.querySelectorAll('.file-row').length===2);
  }
  fs.mkdirSync(path.join(root,'data/device-panel'),{recursive:true});
  await page.locator('#files').screenshot({path:path.join(root,'data/device-panel/files-desktop.png')});
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Mobile overflow');
  await page.locator('#files').screenshot({path:path.join(root,'data/device-panel/files-mobile.png')});
  assert.deepEqual(errors,[]);console.log(JSON.stringify({result:'FILES UI PASS',hardware,filename,bytes:bytes.length}));
 }finally{await browser.close();if(fixtureServer)await new Promise(r=>fixtureServer.close(r));}
})().catch(e=>{console.error(e);process.exit(1);});
