// Optional real-browser UI check. Usage: node tests/smoke_viewer.cjs <viewer URL>
const {chromium}=require('playwright');
const path=require('path'),fs=require('fs');
const {pathToFileURL}=require('url');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto(pathToFileURL(path.resolve('viewer/index.html')).href);
  if(!(await page.locator('#status').innerText()).includes('start.cmd'))throw Error('Missing direct-file launch help');
  if(!await page.locator('#file').isDisabled())throw Error('Direct-file import should not attempt fetch');
  await page.goto(process.argv[2]);
  await page.locator('#file').setInputFiles(path.resolve('tests/fixtures/native-sign-crossing.csv'));
  await page.locator('.card strong').first().waitFor();
  if(await page.locator('.card').count()!==6)throw Error('Missing statistics cards');
  if(!(await page.locator('#status').innerText()).includes('Контрольні суми'))throw Error('Missing integrity status');
  await page.locator('#start').fill('0.02');await page.locator('#end').fill('0.04');await Promise.all([page.waitForResponse(r=>r.url().includes('/api/window')&&r.ok()),page.locator('#apply').click()]);
  await Promise.all([page.waitForResponse(r=>r.url().includes('/api/window')&&r.ok()),page.locator('#reset').click()]);
  fs.mkdirSync('.pio',{recursive:true});
  await page.screenshot({path:'.pio/viewer-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:'.pio/viewer-mobile.png',fullPage:true});
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile horizontal overflow');
  await page.locator('#file').setInputFiles(path.resolve('tests/fixtures/r1-short.csv'));
  await page.locator('#preview').waitFor({state:'visible'});
  await page.locator('#mapping').selectOption('short');await page.locator('#reload').click();
  await page.locator('#workspace').waitFor({state:'visible'});
  await page.locator('#file').setInputFiles(path.resolve('tests/fixtures/native-bad-crc.csv'));
  await page.locator('#status.error').waitFor();
  if(await page.locator('#workspace').isVisible())throw Error('Corrupt file displayed');
  if(errors.length)throw Error(errors.join('\n'));
  console.log('Browser smoke PASS: import, range/reset, mobile, mapping confirmation, corrupt rejection; no JS errors.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
