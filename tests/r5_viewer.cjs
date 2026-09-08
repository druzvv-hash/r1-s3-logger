// R5 preservation acceptance: real pointer gestures and original-row lookup.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 const response=()=>page.waitForResponse(r=>r.url().includes('/api/window')&&r.ok());
 async function point(fraction,y=100){await page.locator('#current').scrollIntoViewIfNeeded();const b=await page.locator('#current').boundingBox();return {x:b.x+65+(b.width-80)*fraction,y:b.y+y};}
 async function click(fraction,shift=false,y=100){const p=await point(fraction,y);if(shift)await page.keyboard.down('Shift');await page.mouse.click(p.x,p.y);if(shift)await page.keyboard.up('Shift');}
 try{
  await page.goto(process.argv[2]);
  await page.locator('#file').setInputFiles('tests/fixtures/native-sign-crossing.csv');await page.locator('.card').first().waitFor();
  await click(0);await page.waitForFunction(()=>document.querySelector('#marker-info').textContent.includes('A:'));
  await click(1);await page.waitForFunction(()=>document.querySelector('#marker-info').textContent.includes('Повні дані'));
  const initial=await page.locator('#marker-info').innerText();assert(initial.includes('0,06 с'));assert(initial.includes('t_us='));
  await click(.5,true,60);await click(.5,true,150);assert((await page.locator('#marker-info').innerText()).includes('Δ (D − C)'));
  const p=await point(.5);await page.mouse.move(p.x,p.y);await page.waitForFunction(()=>document.querySelector('#sample-info').textContent.includes('quality='));
  assert((await page.locator('#sample-info').innerText()).includes('рядок'));
  await Promise.all([response(),page.mouse.wheel(0,-300)]);
  assert(Number(await page.locator('#end').inputValue())-Number(await page.locator('#start').inputValue())<.06);
  assert((await page.locator('#marker-info').innerText()).includes('0,06 с'));
  await page.locator('#gesture').selectOption('pan');const a=await point(.65),b=await point(.35);const before=Number(await page.locator('#start').inputValue());await page.mouse.move(a.x,a.y);await page.mouse.down();await page.mouse.move(b.x,b.y);await Promise.all([response(),page.mouse.up()]);assert(Number(await page.locator('#start').inputValue())>before);
  await Promise.all([response(),page.locator('#reset').click()]);
  await page.locator('#gesture').selectOption('zoom');const z1=await point(.25),z2=await point(.75);await page.mouse.move(z1.x,z1.y);await page.mouse.down();await page.mouse.move(z2.x,z2.y);await Promise.all([response(),page.mouse.up()]);assert(Number(await page.locator('#start').inputValue())>.01);
  await Promise.all([response(),page.locator('#zoom-markers').click()]);assert.equal(Number(await page.locator('#start').inputValue()),0);assert.equal(Number(await page.locator('#end').inputValue()),.06);
  await Promise.all([response(),page.locator('#series input[value="P_W"]').check()]);assert.equal(await page.locator('#plots canvas').count(),3);
  await Promise.all([response(),page.locator('#series input[value="I_A"]').uncheck()]);assert.equal(await page.locator('#plots canvas').count(),2);
  await Promise.all([response(),page.locator('#series input[value="I_A"]').check()]);
  await page.screenshot({path:'.pio/viewer-r5-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);await page.screenshot({path:'.pio/viewer-r5-mobile.png',fullPage:true});
  await page.locator('#file').setInputFiles('tests/fixtures/r1-eight.csv');await page.waitForFunction(()=>document.querySelector('#format').textContent==='R1 eight-column CSV');
  assert(!(await page.locator('#marker-info').innerText()).includes('t_us='));
  assert.deepEqual(errors,[]);console.log('R5 interactions PASS: A/B, C/D, exact row, wheel, pan, drag zoom, persistent selection, series, mobile, file reset.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
