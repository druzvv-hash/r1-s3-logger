/* Hundreds of files, complete search/sort, bounded viewport, cancellation and download. */
const {chromium}=require('playwright'),fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const {encodeConfig}=require('../device_ui/codec.js'),fields=require('../schemas/config-v1.json').fields;
const root=path.resolve(__dirname,'..'),payload=Buffer.from('explorer download bytes\n');
const entries=Array.from({length:600},(_,i)=>{const stamp=new Date(Date.UTC(2026,8,8,10,0,i)).toISOString().slice(0,19).replace('T','_').replace(/:/g,'-');const name=`r1s3_${stamp}Z_00000000_${i.toString(16).padStart(8,'0')}_0000.csv`;return {name,directory:false,size:i+100,path:Buffer.from('/'+name).toString('hex')};});
entries.push({name:'<img onerror=alert(1)>',directory:true,size:0,path:Buffer.from('/nested').toString('hex')});
(async()=>{
 const server=require('http').createServer((req,res)=>{const name=Buffer.from(new URL(req.url,'http://localhost').searchParams.get('path'),'hex').toString().split('/').pop();res.writeHead(200,{'Content-Type':'application/octet-stream','Content-Length':payload.length,'Content-Disposition':"attachment; filename*=UTF-8''"+encodeURIComponent(name)});res.end(payload);});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({channel:'chrome',headless:true}),page=await browser.newPage({viewport:{width:1440,height:1050},acceptDownloads:true,timezoneId:'Europe/Prague'});
 let cursor=0,session=0,closed=0,slow=false,tick=0;const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const config=Object.fromEntries(fields.map(f=>[f.name,f.default]));
 try{
  await page.route('**/*',async route=>{
   const u=new URL(route.request().url());
   if(u.pathname==='/')return route.fulfill({contentType:'text/html',body:fs.readFileSync(path.join(root,'device_ui/index.html'),'utf8')});
   if(u.pathname==='/api/state')return route.fulfill({json:{ready:true,firmware:'fixture',boot:'test',revision:1,generation:'3',config_hex:encodeConfig(config,fields),settings_status:'SAVED',recording_state:'READY',files_available:true,valid:true,uptime_ms:++tick*1000,sample_at_ms:tick*1000,volts:3,amps:1,temp_c:20,live_available:false,transport:'usb'}});
   if(u.pathname==='/api/live')return route.fulfill({json:{boot:'test',samples:[]}});
   if(u.pathname==='/api/files'){
    const c=u.searchParams.get('command');
    if(c.startsWith('CLOSE')){closed++;session=0;return route.fulfill({json:{ok:true}});}
    if(c.startsWith('OPEN'))return route.fulfill({json:{ok:true,session:99,size:payload.length}});
    if(c.startsWith('LIST')&&c!=='LIST 2f')return route.fulfill({json:{ok:true,session:2,more:false,entries:[]}});
    if(c==='LIST 2f'){assert.equal(session,0,'Previous cursor must be closed');cursor=0;session=1;}
    else assert.equal(c,'NEXT 1');
    if(slow)await new Promise(r=>setTimeout(r,70));
    const chunk=entries.slice(cursor,cursor+6);cursor+=chunk.length;const more=cursor<entries.length;if(!more)session=0;
    return route.fulfill({json:{ok:true,session:1,more,entries:chunk}});
   }
   if(u.pathname==='/api/download')return route.continue();return route.fulfill({status:404,body:'Not found'});
  });
  await page.goto('http://127.0.0.1:'+server.address().port+'/');await page.waitForFunction(()=>online);
  await page.getByRole('button',{name:'Файли SD',exact:true}).click();
  await page.waitForFunction(()=>fileComplete&&!fileBusy,{},{timeout:20000});
  assert.equal(await page.locator('.file-row').count(),601);assert.equal(await page.locator('#file-list img').count(),0);
  assert.equal(await page.locator('.file-row').nth(1).locator('.file-name-text').textContent(),entries[599].name,'Newest recording first, folders before files');
  const geometry=await page.locator('#files-scroll').evaluate(el=>({height:el.clientHeight,total:el.scrollHeight}));assert(geometry.height<=600&&geometry.total>20000);
  await page.locator('#files-scroll').evaluate(el=>el.scrollTop=2000);assert(await page.locator('#files-scroll').evaluate(el=>el.scrollTop>1000));
  await page.locator('#files-search').fill(entries[598].name);assert.equal(await page.locator('.file-row').count(),1,'Search covers the complete directory, not one device page');
  await page.locator('.file-name').click();assert.match(await page.locator('#files-selection').textContent(),new RegExp(entries[598].name.replaceAll('.','\\.')));
  const pending=page.waitForEvent('download');await page.locator('#files-download-selected').click();const download=await pending;assert.equal(download.suggestedFilename(),entries[598].name);assert.equal(await download.failure(),null);assert.deepEqual(fs.readFileSync(await download.path()),payload);
  await page.locator('#files-search').fill('');await page.locator('#files-sort').selectOption('date-asc');assert.equal(await page.locator('.file-row').nth(1).locator('.file-name-text').textContent(),entries[0].name);
  await page.locator('#files-type').selectOption('part');assert.equal(await page.locator('.file-row').count(),1,'Folders remain navigable when filtering file type');await page.locator('#files-type').selectOption('csv');assert.equal(await page.locator('.file-row').count(),601);
  fs.mkdirSync(path.join(root,'data/file-explorer'),{recursive:true});await page.locator('#files').screenshot({path:path.join(root,'data/file-explorer/desktop-601.png')});
  await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.locator('#files-scroll').evaluate(el=>el.scrollLeft=el.scrollWidth);assert(await page.locator('#files-scroll').evaluate(el=>el.scrollLeft>100),'Narrow screen uses contained horizontal scrolling');await page.locator('#files-scroll').evaluate(el=>el.scrollLeft=0);await page.locator('#files').screenshot({path:path.join(root,'data/file-explorer/mobile-601.png')});
  slow=true;await page.locator('#files-refresh').click();await page.waitForFunction(()=>fileEntries.length>=12&&!fileComplete);await page.locator('#files-records').click();await page.waitForFunction(()=>fileDirectory==='/records'&&fileComplete&&!fileBusy);assert(closed>0,'Cancellation releases its directory session');assert.equal(await page.locator('.file-row').count(),0);assert.equal(await page.locator('#files-status').textContent(),'Папка порожня.');
  assert.deepEqual(errors,[]);console.log('Explorer: 601 entries, all-page search/sort, scroll, download, cancellation and mobile PASS');
 }finally{await browser.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exit(1);});
