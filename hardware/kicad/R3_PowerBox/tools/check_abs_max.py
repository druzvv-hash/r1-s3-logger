"""Selected reviewed pin/net ratings; explicit operating assumptions, not SPICE."""
import json,sys
import pcbnew as k
from route_reva import ROOT,BOARD
b=k.LoadBoard(str(BOARD));logical=json.loads((ROOT/'tools/logical_nets.json').read_text())
def net(ref,pin):return str(next(p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber()==str(pin)).GetNetname())
# pin, required net, operating maximum, absolute maximum, recommended maximum.
cases=[('U7',7,'USB_VBUS_PROT',12.6,24,22),('U7',2,'SERVICE_IN_PROT',12.6,24,22),
 ('U8',2,'CHARGER_IN',12.6,30,24),('U8',3,'CHARGER_IN',12.6,30,24),
 ('U8',1,'BQ_STAT_RAW',5.2,6,6),('U10',24,'PD_VDD',12.6,28,22),
 ('U10',18,'PD_VBUS_SENSE_DISCH',12.6,28,22),('U10',22,'+3V3_D',3.465,6,5.5)]
checks=[]
for ref,pin,want,operating,absolute,recommended in cases:
    actual=net(ref,pin);same=actual==want and logical.get(f'{ref}.{pin}')==want
    checks.append(dict(pin=f'{ref}.{pin}',net=actual,operating_max_V=operating,
        abs_max_V=absolute,recommended_max_V=recommended,pass_check=same and operating<absolute and operating<=recommended))
en=net('U2',5)
checks.append(dict(pin='U2.5',net=en,abs_max_V=7,recommended_max_V=5.5,
    pass_check=en.startswith('unconnected-') and logical.get('U2.5') in ['__NOCONNECT','NOCONNECT','NC'],
    rationale='TPS54302 RevC internal EN pull-up, explicitly permitted floating. No VSYS connection.'))
vmax=5.2*(10000*1.001)/(28700*.999+10000*1.001)
rth=(28700*10000)/(28700+10000)
ilim=(vmax+1.5e-6*rth-1)/.8
report=dict(pass_check=all(c['pass_check'] for c in checks),checks=checks,
    discharge_upper_mA=12.6/1000*1000,discharge_limit_mA=50,
    startup_divider_upper_estimate_A=ilim,
    scope='Selected reviewed DC operating pin limits only. Normal programmed PD <=12V(+5%). No claim to cover every IC pin, negative transients, ringing or firmware faults.',
    open=['Factory ST NVM may request 20V: initial 5V-only programming/readback mandatory; D3 is not continuous-20V rated.',
          'SMBJ13A 21.5V specified clamp is below TPS2121 24V absolute max, but actual surge waveform/current and lead inductance need validation.',
          'ILIM estimate includes resistor tolerance and pin leakage, NOT unspecified ADC/5V low-current regulation error. Measure before unrestricted source use.'],
    sources=['https://www.ti.com/lit/ds/symlink/tps54302.pdf','https://www.ti.com/lit/ds/symlink/tps2121.pdf',
             'https://www.ti.com/lit/ds/symlink/bq25798.pdf','https://www.st.com/resource/en/datasheet/stusb4500.pdf'])
(ROOT/'reports/review1_abs_max.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));sys.exit(not report['pass_check'])
