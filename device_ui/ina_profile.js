/* Match settings::runtimeTimingFeasible; the device remains authoritative. */
const INA_CT_US=[50,84,150,280,540,1052,2074,4120];
const INA_AVERAGES=[1,4,16,64,128,256,512,1024];
const INA_FIELDS=['requested_rate_hz','adc_range','vshunt_ct_code','vbus_ct_code','temp_ct_code','average_code'];
function inaTiming(config,benchmark=false){
  const conversion=INA_CT_US[config.vshunt_ct_code]+INA_CT_US[config.vbus_ct_code]+INA_CT_US[config.temp_ct_code];
  const us=conversion*INA_AVERAGES[config.average_code],hz=config.requested_rate_hz;
  const fits=rate=>Number.isFinite(us)&&us<Math.floor(1000000/rate)&&
    (benchmark||us+(rate>100?2500:4000)<=Math.floor(1000000/rate));
  let maximum=0;for(let rate=1;rate<=300;rate++)if(fits(rate))maximum=rate;
  const rateValid=Number.isInteger(hz)&&hz>=1&&hz<=300;
  return {us,maximum,period:rateValid?1000000/hz:NaN,
    valid:rateValid&&fits(hz)&&us<config.ready_timeout_us,
    averages:INA_AVERAGES[config.average_code],
    limitAmps:(config.adc_range===1?40960:163840)/config.shunt_uohm};
}
function inaWithTiming(config,hz=config.requested_rate_hz){
  const us=inaTiming(config).us;
  return {...config,requested_rate_hz:hz,
    ready_timeout_us:Math.min(1000000,Math.max(config.ready_timeout_us,us+1000)),
    max_gap_us:Math.max(config.max_gap_us,Math.ceil(2000000/hz))};
}
function inaDescription(config){
  const t=inaTiming(config);
  return `Усереднення ×${t.averages}; шунт ${INA_CT_US[config.vshunt_ct_code]} мкс, напруга ${INA_CT_US[config.vbus_ct_code]} мкс, температура ${INA_CT_US[config.temp_ct_code]} мкс.`;
}
if(typeof module!=='undefined')module.exports={INA_CT_US,INA_AVERAGES,INA_FIELDS,inaTiming,inaWithTiming,inaDescription};
