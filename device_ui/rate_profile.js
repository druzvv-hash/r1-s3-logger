/* Rate choices change runtime settings only; SAVE is always a separate action. */
const RATE_PRESETS=[1,5,10,25,50,100,150,200,250,300];
function rateProfile(hz){
  if(!Number.isInteger(hz)||hz<1||hz>300)throw Error('Введи ціле число від 1 до 300 Гц');
  if(hz<=100)return {code:5,us:1052,bus:100000,label:'Звичайний'};
  if(hz<=200)return {code:2,us:150,bus:400000,label:'Швидкий'};
  return {code:0,us:50,bus:400000,label:'Максимальна швидкість'};
}
function configForRate(config,hz){
  const p=rateProfile(hz);
  return {...config,requested_rate_hz:hz,vshunt_ct_code:p.code,vbus_ct_code:p.code,
    temp_ct_code:p.code,average_code:0,max_gap_us:Math.max(config.max_gap_us,Math.ceil(2000000/hz))};
}
function rateDescription(hz){
  const p=rateProfile(hz);
  return `${p.label}: ADC ${p.us} мкс на канал, без усереднення; I²C ${p.bus/1000} кГц.`+
    (hz>100?' Коротша конверсія збільшує шум показників.':'');
}
if(typeof module!=='undefined')module.exports={RATE_PRESETS,rateProfile,configForRate};
