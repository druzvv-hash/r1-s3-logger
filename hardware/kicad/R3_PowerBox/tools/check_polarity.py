"""Independent physical-pad polarity contract; KiCad Python required."""
import json
import sys
import pcbnew as k
from route_reva import ROOT, BOARD

EXPECTED = {
    'D1': {'1':'SERVICE_IN_REV', '2':'DGND'},
    'D2': {'1':'SERVICE_IN_REV', '2':'Q1_GATE'},
    'D3': {'1':'USB_VBUS_PROT', '2':'DGND'},
    'D4': {'1':'USB_CC1', '2':'USB_CC2', '3':'DGND'},
    'D5': {'1':'BQ_STAT_RAW', '2':'CHARGE_LED_A'},
    'D6': {'1':'DGND', '2':'RUN_LED_A'},
    'D7': {'1':'BQ_STAT_RAW', '2':'CHARGE_STATUS'},
}
b=k.LoadBoard(str(BOARD)); logical=json.loads((ROOT/'tools/logical_nets.json').read_text())
issues=[]; checked=[]
for ref, pins in EXPECTED.items():
    f=b.FindFootprintByReference(ref)
    for pin, net in pins.items():
        pads=[p for p in f.Pads() if p.GetNumber()==pin] if f else []
        actual=[str(p.GetNetname()) for p in pads]
        if not pads or actual!=[net] or logical.get(f'{ref}.{pin}')!=net:
            issues.append(dict(ref=ref,pin=pin,want=net,actual=actual,source=logical.get(f'{ref}.{pin}')))
        checked.append(f'{ref}.{pin}={net}')
uncovered=[f.GetReference() for f in b.GetFootprints() if f.GetReference().startswith('D') and f.GetReference() not in EXPECTED]
issues.extend({'uncovered_diode':r} for r in uncovered)
result=dict(pass_check=not issues,checked=checked,issues=issues,
    scope='Physical footprint pad numbers AND editable-source logical nets. D4 is dual AAC, not a two-pin cathode-1 part. Not an assembly inspection.')
(ROOT/'reports/review1_polarity.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2));sys.exit(bool(issues))
