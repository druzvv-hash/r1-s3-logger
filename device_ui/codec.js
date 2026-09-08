/* Config v1 TLV, shared by the offline USB and embedded panels. */
function validateConfig(values, registry) {
  if (!values || typeof values !== 'object' || Object.keys(values).length !== registry.length ||
      registry.some(f => !Object.prototype.hasOwnProperty.call(values, f.name))) throw Error('Неповний або невідомий набір параметрів');
  for (const f of registry) {
    const v=values[f.name];
    let ok;
    if(f.type==='utf8') ok=typeof v==='string'&&!v.includes('\0')&&new TextEncoder().encode(v).length<=f.max_bytes;
    else if(f.type==='bool') ok=typeof v==='boolean';
    else ok=typeof v==='number'&&Number.isFinite(v)&&(f.type==='f64'||Number.isInteger(v))&&v>=(f.min??-Infinity)&&v<=(f.max??Infinity)&&(!f.enum||f.enum.includes(v));
    if(!ok) throw Error('Перевір значення: '+f.name);
  }
  const date=values.calibration_utc;
  if(date && (!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$/.test(date)||!Number.isFinite(Date.parse(date))||new Date(date).toISOString().replace('.000','')!==date)) throw Error('Дата калібрування: YYYY-MM-DDTHH:MM:SSZ');
  if(values.calibration_valid&&(!values.calibration_id||!values.calibration_note||!date))throw Error('Заповни походження калібрування, опис і UTC');
}
function encodeConfig(values, registry) {
  validateConfig(values,registry);
  const codes={u32:1,i32:2,f64:3,bool:4,utf8:5}, out=[];
  for(const f of registry){
    const raw=f.type==='utf8'?new TextEncoder().encode(values[f.name]):new Uint8Array(f.type==='f64'?8:f.type==='bool'?1:4);
    const v=new DataView(raw.buffer,raw.byteOffset,raw.byteLength);
    if(f.type==='u32')v.setUint32(0,values[f.name],true);
    if(f.type==='i32')v.setInt32(0,values[f.name],true);
    if(f.type==='f64')v.setFloat64(0,values[f.name],true);
    if(f.type==='bool')raw[0]=values[f.name]?1:0;
    out.push(f.id&255,f.id>>8,codes[f.type],0,raw.length&255,raw.length>>8,0,0,...raw);
  }
  if(out.length>1472)throw Error('Конфігурація завелика');
  return out.map(v=>v.toString(16).padStart(2,'0')).join('');
}
function decodeConfig(hex,registry){
  if(typeof hex!=='string'||!/^([0-9a-fA-F]{2})+$/.test(hex)||hex.length>2944)throw Error('Некоректний пакет конфігурації');
  const bytes=Uint8Array.from(hex.match(/../g),x=>parseInt(x,16)),v=new DataView(bytes.buffer),out={};let p=0;
  const codes={u32:1,i32:2,f64:3,bool:4,utf8:5};
  for(const f of registry){
    if(p+8>bytes.length||v.getUint16(p,true)!==f.id||bytes[p+2]!==codes[f.type]||bytes[p+3]||v.getUint16(p+6,true))throw Error('Невідомий формат TLV');
    const n=v.getUint16(p+4,true);p+=8;
    if(p+n>bytes.length || (f.type!=='utf8'&&n!==(f.type==='f64'?8:f.type==='bool'?1:4)))throw Error('Обрізаний пакет TLV');
    if(f.type==='utf8')out[f.name]=new TextDecoder('utf8',{fatal:true}).decode(bytes.subarray(p,p+n));
    if(f.type==='u32')out[f.name]=v.getUint32(p,true);
    if(f.type==='i32')out[f.name]=v.getInt32(p,true);
    if(f.type==='f64')out[f.name]=v.getFloat64(p,true);
    if(f.type==='bool'){if(bytes[p]>1)throw Error('Некоректне bool');out[f.name]=!!bytes[p];}
    p+=n;
  }
  if(p!==bytes.length)throw Error('Зайві поля TLV');
  validateConfig(out,registry);return out;
}
function configMinor(v){return [10,50,100].includes(v.requested_rate_hz)&&v.max_gap_us<=1000000?0:1;}
function exportProfile(values,registry){validateConfig(values,registry);return {schema:'r1s3-config',major:1,minor:configMinor(values),values};}
function importProfile(obj,registry){
  if(!obj||Object.keys(obj).sort().join(',')!=='major,minor,schema,values'||obj.schema!=='r1s3-config'||obj.major!==1||![0,1].includes(obj.minor))throw Error('Непідтримуваний профіль');
  validateConfig(obj.values,registry);
  if(obj.minor<configMinor(obj.values))throw Error('Розширені значення потребують профілю 1.1');
  return obj.values;
}
if(typeof module!=='undefined')module.exports={encodeConfig,decodeConfig,validateConfig,exportProfile,importProfile};
