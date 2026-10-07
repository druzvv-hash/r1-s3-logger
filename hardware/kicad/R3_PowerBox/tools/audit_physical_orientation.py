"""Fail-closed physical pin contracts, not a 3D/viewer-based orientation test.

Run with KiCad Python. --negative-controls proves detection of known U4
mirroring, diode reversal, MOS gate remap and USB CC swaps (in memory only).
Manufacturer references and supplier-release limitations: docs/JLC_ORIENTATION_FINAL_AUDIT.md.
"""
import argparse,json,re,math,hashlib,xml.etree.ElementTree as E
from pathlib import Path
import pcbnew as k
ROOT=Path(__file__).resolve().parents[1]
P=argparse.ArgumentParser();P.add_argument('--board',type=Path,default=ROOT/'R3_power.kicad_pcb');P.add_argument('--negative-controls',action='store_true');args=P.parse_args()
LOGICAL=json.loads((ROOT/'tools/logical_nets.json').read_text())
# Number-ordered manufacturer pin functions. EP is a PCB implementation number.
FUNCTIONS={
'U1':('TPS62132','SW SW SW PG FB AGND FSW DEF SS/TR AVIN PVIN PVIN EN VOS PGND PGND EP'),
'U2':('TPS54302','GND SW VIN FB EN BOOT'),
'U4':('ADM7150','VREG VOUT BYP GND REF_SENSE REF EN VIN EP'),
'U5':('TPS7A20','IN GND EN NC OUT'),
'U7':('TPS2121','OUT IN2 CP2 OV2 OV1 PR1 IN1 OUT ST ILIM SS GND'),
'U8':('BQ25798','STAT VBUS VBUS BTST1 REGN D+ D- VAC2 VAC1 ACDRV2 ACDRV1 QON CE SCL SDA TS ILIM_HIZ BATP BTST2 PROG INT BAT BAT SDRV SYS SW2 GND SW1 PMID'),
'U9':('BQ28Z610','VSS SRN SRP TS1 SCL SDA DSG PACK CHG PBI VC2 VC1 EP'),
'U10':('STUSB4500','CC1DB CC1 NC CC2 CC2DB RESET SCL SDA DISCH GND ATTACH ADDR0 ADDR1 POWER_OK3 GPIO VBUS_EN_SNK A_B_SIDE VBUS_VS_DISCH ALERT POWER_OK2 VREG_1V2 VSYS VREG_2V7 VDD GND'),
'Q1':('PMOS','G S D'),'Q4':('PMOS','G S D'),'Q2':('NMOS_POWER','G S D'),'Q3':('NMOS_POWER','G S D'),
}
# Independent functional net contracts. NC = intentionally unused, not a blank pad.
NETS={
'U1':['SW_3V3']*3+['PG_3V3_D']+['DGND']*4+['N$11']+['VSYS_MAIN']*4+['+3V3_D','DGND','DGND','DGND'],
'U2':['DGND','SW_5V','VSYS_MAIN','FB_5V','NC','N$12'],
'U4':['N$13','+3V3_A_ISO','N$14','GND_ISO','ADM7150_REF','ADM7150_REF','EN_3V3_A_ISO','+5V_ISO_A','GND_ISO'],
'U5':['+5V_ISO_D','GND_ISO','+5V_ISO_D','NC','+3V3_D_ISO'],
'U7':['CHARGER_IN','SERVICE_IN_PROT','DGND','DGND','DGND','DGND','USB_VBUS_PROT','CHARGER_IN','INPUT_SOURCE_STATUS','N$4','N$5','DGND'],
'U8':['BQ_STAT_RAW','CHARGER_IN','CHARGER_IN','N$7','CHG_REGN','NC','NC','CHARGER_IN','CHARGER_IN','DGND','DGND','QON_SERVICE','DGND','PM_I2C_SCL','PM_I2C_SDA','NTC_CHG','BQ25798_ILIM','N$6','N$8','N$10','CHARGER_INT_FAULT','PACK_POS','PACK_POS','N$9','VSYS_RAW','CHG_SW2','DGND','CHG_SW1','CHG_PMID'],
'U9':['BAT_NEG_RAW','BMS_SRN_FILT','BMS_SRP_FILT','N$1','PM_I2C_SCL','PM_I2C_SDA','N$2','PACK_POS','N$3','BMS_PBI','BMS_VC2_FILT','BMS_VC1_FILT','BAT_NEG_RAW'],
'U10':['USB_CC1','USB_CC1','NC','USB_CC2','USB_CC2','DGND','PM_I2C_SCL','PM_I2C_SDA','NC','DGND','NC','DGND','DGND','PD_CONTRACT_12V_N','NC','NC','NC','PD_VBUS_SENSE_DISCH','PD_ALERT_N','NC','PD_VREG_1V2','+3V3_D','PD_VREG_2V7','PD_VDD','DGND'],
'Q1':['Q1_GATE','SERVICE_IN_REV','SERVICE_IN_FUSED'],
'Q2':['BMS_DSG_GATE','PACK_POS','BMS_FET_COMMON'],
'Q3':['BMS_CHG_GATE','BAT_POS_RAW','BMS_FET_COMMON'],
'Q4':['SYS_LOAD_GATE','VSYS_PROT','VSYS_MAIN'],
'D1':['SERVICE_IN_REV','DGND'],'D2':['SERVICE_IN_REV','Q1_GATE'],'D3':['USB_VBUS_PROT','DGND'],
'D4':['USB_CC1','USB_CC2','DGND'],'D5':['BQ_STAT_RAW','CHARGE_LED_A'],'D6':['DGND','RUN_LED_A'],'D7':['BQ_STAT_RAW','CHARGE_STATUS'],'C1':['SERVICE_IN_REV','DGND']}
EXPECTED_PACKAGE={'U1':'VQFN-16-1EP_3x3mm_P0.5mm_EP1.45x1.45mm','U2':'SOT-23-6','U4':'LFCSP-8-1EP_3x3mm_P0.5mm_EP1.74x1.45mm','U5':'SOT-23-5','U7':'Texas_VQFN-HR-12_2x2.5mm_P0.5mm','U8':'Texas_RQM0029A_VQFN-29_4x4mm_P0.4mm','U9':'Texas_DRZ0012A_VSON-12','U10':'QFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm','Q1':'DMP3007LSS_SO8_LOGICAL','Q4':'DMP3007LSS_SO8_LOGICAL','Q2':'CSD17577Q3A_VSON-8_3.3x3.3mm','Q3':'CSD17577Q3A_VSON-8_3.3x3.3mm','D1':'D_SMB','D2':'D_SOD-123','D3':'D_SMB','D4':'SOT-323_SC-70','D5':'LED_0603_1608Metric','D6':'LED_0603_1608Metric','D7':'D_SOD-323','C1':'CP_Elec_6.3x5.8','J7':'USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal'}
lib={}
for block in re.split(r'^DEF ',(ROOT/'libraries/R3_POWER.lib').read_text(),flags=re.M)[1:]:
    name=block.split()[0];lib[name]={line.split()[2]:line.split()[1] for line in block.splitlines() if line.startswith('X ')}
netlist=E.parse(ROOT/'tmp/orientation/current_netlist.xml').getroot()
parts={p.attrib['part']:{v.attrib['num']:v.attrib['name'].replace('~{','').replace('}','') for v in p.findall('pins/pin')} for p in netlist.findall('libparts/libpart')}
for name,pins in parts.items():
    if 'STUSB4500' in name:lib['STUSB4500']=pins
def xy(p):return (round(k.ToMM(p.x),5),round(k.ToMM(p.y),5))
def local(p,f):
    # pcbnew local coordinates on Bottom are already flipped. Undo the
    # local Y reflection to compare against manufacturer component top view.
    x,y=xy(p.GetFPRelativePosition());return (x,-y if f.GetLayer()==k.B_Cu else y)
def audit(b):
    errors=[];checks=[]
    def require(ok,label):
        checks.append(label)
        if not ok:errors.append(label)
    for ref,pins in NETS.items():
        f=b.FindFootprintByReference(ref)
        for i,net in enumerate(pins,1):
            pads=[p for p in f.Pads() if p.GetNumber()==str(i)]
            require(bool(pads),f'{ref}.{i}:exists')
            require(all(str(p.GetNetname()).startswith('unconnected-') if net=='NC' else str(p.GetNetname())==net for p in pads),f'{ref}.{i}:net={net}')
            if net!='NC':require(LOGICAL.get(f'{ref}.{i}')==net,f'{ref}.{i}:editable_source={net}')
    for ref,(symbol,funcs) in FUNCTIONS.items():
        for i,func in enumerate(funcs.split(),1):require(lib.get(symbol,{}).get(str(i))==func,f'{ref}.{i}:symbol_function={func}')
    for ref,name in EXPECTED_PACKAGE.items():
        f=b.FindFootprintByReference(ref);fid=f.GetFPID()
        require(str(fid.GetLibItemName())==name,f'{ref}:package_contract')
    # Full physical ordering: left descends, bottom moves right, right ascends,
    # top moves left; unlike mere PCB/schematic parity this catches mirroring.
    sides={'U1':[list(range(1,5)),list(range(5,9)),list(range(9,13)),list(range(13,17))],
        'U4':[list(range(1,5)),[],list(range(5,9)),[]],
        'U9':[list(range(1,7)),[],list(range(7,13)),[]],
        'U10':[list(range(1,7)),list(range(7,13)),list(range(13,19)),list(range(19,25))],
        'U8':[list(range(1,9)),list(range(9,16)),list(range(16,25)),list(range(25,30))],
        'U2':[[1,2,3],[],[4,5,6],[]],'U5':[[1,2,3],[],[4,5],[]],
        'U7':[[1,2],[3,4,5,6],[7,8],[9,10,11,12]]}
    for ref,groups in sides.items():
        f=b.FindFootprintByReference(ref);pads={p.GetNumber():local(p,f) for p in f.Pads()}
        for side,ids in enumerate(groups):
            if not ids:continue
            pts=[pads[str(i)] for i in ids]
            require(all(p[0]<0 if side==0 else p[1]>0 if side==1 else p[0]>0 if side==2 else p[1]<0 for p in pts),f'{ref}:side_{side}')
            vals=[p[1] if side in (0,2) else p[0] for p in pts]
            require(all(a<z if side<2 else a>z for a,z in zip(vals,vals[1:])),f'{ref}:counterclockwise_side_{side}')
    for ref in ['Q1','Q4','Q2','Q3']:
        f=b.FindFootprintByReference(ref);p={n:sorted(local(v,f) for v in f.Pads() if v.GetNumber()==n) for n in ['1','2','3']}
        require(len(p['1'])==1 and len(p['2'])==3,f'{ref}:logical_gate_and_three_sources')
        require(p['1'][0][0]<0 and p['1'][0][1]>max(y for x,y in p['2']),f'{ref}:physical_pin4_gate_below_1to3_sources')
        require(all(x<0 for x,y in p['2']) and all(x>0 for x,y in p['3']),f'{ref}:source_left_drain_right')
    for ref in ['D1','D2','D3','D5','D6','D7','C1']:
        f=b.FindFootprintByReference(ref);p={v.GetNumber():local(v,f) for v in f.Pads()}
        require(p['1'][0]<p['2'][0],ref+':canonical_cathode_or_positive_pad1_left')
    f=b.FindFootprintByReference('J7');p={v.GetNumber():v for v in f.Pads() if v.GetNumber()}
    usb={'A1':(-3.2,'DGND'),'B12':(-3.2,'DGND'),'A4':(-2.4,'USB_VBUS_RAW'),'B9':(-2.4,'USB_VBUS_RAW'),'B8':(-1.75,'NC'),'A5':(-1.25,'USB_CC1'),'B7':(-.75,'NC'),'A6':(-.25,'NC'),'A7':(.25,'NC'),'B6':(.75,'NC'),'A8':(1.25,'NC'),'B5':(1.75,'USB_CC2'),'A9':(2.4,'USB_VBUS_RAW'),'B4':(2.4,'USB_VBUS_RAW'),'A12':(3.2,'DGND'),'B1':(3.2,'DGND')}
    for num,(x,net) in usb.items():
        require(local(p[num],f)==(x,-3.68),f'J7.{num}:GCT_top_view_land_position')
        require(str(p[num].GetNetname()).startswith('unconnected-') if net=='NC' else str(p[num].GetNetname())==net,f'J7.{num}:function={net}')
    require(sorted(local(v,f) for v in f.Pads() if v.GetNumber()=='SH')==[(-4.32,-3.105),(-4.32,1.075),(4.32,-3.105),(4.32,1.075)],'J7:GCT_shell_stake_positions')
    require(xy(f.GetPosition())==(23.675,33.0) and f.GetOrientationDegrees()==-90,'J7:unchanged_body_center_and_mating_left')
    require(all(v.IsMirrored() for fp in b.GetFootprints() for v in [fp.Reference(),fp.Value()] if v.IsVisible() and v.GetLayer()==k.B_SilkS),'all_visible_Bottom_silk_fields_mirrored')
    return {'pass':not errors,'checks':len(checks),'errors':errors}
b=k.LoadBoard(str(args.board));result=audit(b)
if args.negative_controls:
    negative={}
    for case in ['U4_mirror','D3_reverse','Q4_gate_source','J7_CC_swap']:
        fault=k.LoadBoard(str(args.board))
        if case=='U4_mirror':
            f=fault.FindFootprintByReference('U4')
            for p in f.Pads():
                if p.GetNumber() in map(str,range(1,9)):
                    q=p.GetPosition();p.SetPosition(k.VECTOR2I(q.x,2*f.GetPosition().y-q.y))
        else:
            ref,a,c={'D3_reverse':('D3','1','2'),'Q4_gate_source':('Q4','1','2'),'J7_CC_swap':('J7','A5','B5')}[case]
            f=fault.FindFootprintByReference(ref);pa=next(p for p in f.Pads() if p.GetNumber()==a);pc=next(p for p in f.Pads() if p.GetNumber()==c)
            old=pa.GetNet();pa.SetNet(pc.GetNet());pc.SetNet(old)
        negative[case]=not audit(fault)['pass']
    result['negative_controls_rejected']=negative
    result['pass']=result['pass'] and all(negative.values())
result['board_sha256']=hashlib.sha256(args.board.read_bytes()).hexdigest()
result['scope']='Physical pin order, explicit pin/net/source contracts, selected package IDs and mechanical USB mapping. Not supplier model/centroid acceptance, SMT qualification or full production release.'
(ROOT/'reports/orientation_physical_audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2));raise SystemExit(not result['pass'])
