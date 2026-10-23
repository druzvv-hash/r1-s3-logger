const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('device_ui/app.js','utf8');
const scope={};vm.createContext(scope);
vm.runInContext(source.slice(source.indexOf('class MeterAverage'),source.indexOf('function acceptLive'))+';globalThis.avg=meterAverage;',scope);
const a=scope.avg;
for(let n=0;n<20;n++)assert.equal(a.add(n*10000,n,2*n,1,5,false),null);
assert.deepEqual(Array.from(a.add(200000,20,40,1,5,false)),[9.5,19,247]);
assert.equal(a.add(400000,1,1,2,5,false),null); // revision discards old window
assert.equal(a.add(600000,1,1,2,5,true),null); // gap discards old window
a.reset();a.add(0,3,4,1,5,false);
assert.deepEqual(Array.from(a.add(1000000,3,4,1,5,false)),[3,4,12]); // 1 Hz acquisition
console.log('Display averaging: PASS');
