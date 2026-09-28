"""Incremental manual routing, starting at A0, never the pre-routing board."""
import subprocess
from pathlib import Path
import pcbnew as k
from route_reva import ROOT,BOARD,vec,pad,point,line,via,join

A0='2b4bb5e9568fd3ed68e13147868de63d9654c6fa'

def move(b,ref,x,y,angle=0):
    f=b.FindFootprintByReference(ref)
    assert not any(t.GetStart()==p.GetPosition() or t.GetEnd()==p.GetPosition()
                   for t in b.GetTracks() for p in f.Pads()),f'Already routed: {ref}'
    f.SetPosition(vec(x,y)); f.SetOrientationDegrees(angle)

def back(b,ref,x,y,angle=0):
    move(b,ref,x,y,angle)
    f=b.FindFootprintByReference(ref)
    f.Flip(f.GetPosition(),True)

def remove_segment(b,net,a,z,layer):
    hits=[t for t in b.GetTracks() if not isinstance(t,k.PCB_VIA)
          and t.GetNetname()==net and t.GetLayer()==layer
          and {t.GetStart().x,t.GetEnd().x}=={vec(*a).x,vec(*z).x}
          and {t.GetStart().y,t.GetEnd().y}=={vec(*a).y,vec(*z).y}]
    assert len(hits)==1,(net,a,z,len(hits))
    b.Remove(hits[0])

def charger_finish(b):
    # The A0 BAT link/BTST2 via occupied the only legal escape for PROG and
    # BATP with 0.70 mm vias. Rework only these explicitly identified objects.
    for a,z in [((52.9,50.2),(54,50.2)),((54,50.2),(55,50.875)),
                ((55,50.875),(56.5,50.875))]:
        remove_segment(b,'PACK_POS',a,z,k.F_Cu)
    remove_segment(b,'N$8',(52.8625,51.4),(54,51.4),k.F_Cu)
    remove_segment(b,'N$8',(54,51.4),(54.775,53.8),k.B_Cu)
    hits=[t for t in b.GetTracks() if isinstance(t,k.PCB_VIA)
          and t.GetNetname()=='N$8' and t.GetPosition()==vec(54,51.4)]
    assert len(hits)==1
    b.Remove(hits[0])
    line(b,'PACK_POS',[point(pad(b,'U8',22)),(54,50)],.2)
    via(b,'PACK_POS',54,50)
    # Local BAT escape only on In1: In2 is occupied by the switch-via fanout.
    # DGND must remain connected around this short island, checked at E.
    line(b,'PACK_POS',[(54,50),(57.5,50),(57.5,53)],.8,k.In1_Cu)
    line(b,'N$8',[point(pad(b,'U8',19)),(54.2,51.4),(55,52.2)],.2)
    via(b,'N$8',55,52.2)
    line(b,'N$8',[(55,52.2),(55.8,53),(55.8,53.8),point(pad(b,'C75',1))],.2,k.B_Cu)
    back(b,'R74',55,55.5,180)
    back(b,'R75',53,47.5,180)
    back(b,'R76',62,60,180)
    back(b,'R77',62,62)
    back(b,'R78',66,56)
    back(b,'R79',66,58,180)
    back(b,'C89',58,45.7)
    line(b,'N$6',[point(pad(b,'U8',18)),(53.5,51.8),(54.4,52.7),(54.4,52.8)],.2)
    via(b,'N$6',54.4,52.8)
    line(b,'N$6',[(54.4,52.8),(54,53.2),(54,55.325),point(pad(b,'R74',2))],.15,k.B_Cu)
    line(b,'PACK_POS',[point(pad(b,'R74',1)),(57.5,55.5)],.2,k.B_Cu)
    line(b,'N$10',[point(pad(b,'U8',20)),(54.5,51),(54.8,50.9)],.2)
    via(b,'N$10',54.8,50.9)
    line(b,'N$10',[(54.8,50.9),(52.6,50.9),(52.6,48.5),(53.825,48.5),point(pad(b,'R75',1))],.2,k.B_Cu)
    line(b,'DGND',[point(pad(b,'R75',2)),(52.175,46.575),(51,45.4)],.3,k.B_Cu)
    line(b,'N$9',[point(pad(b,'U8',24)),(53.5,49.4),(54.5,49)],.2)
    via(b,'N$9',54.5,49)
    line(b,'N$9',[(54.5,49),(54.6,48.9),(54.6,45.7),point(pad(b,'C89',1))],.2,k.B_Cu)
    via(b,'DGND',59.5,43)
    line(b,'DGND',[point(pad(b,'C89',2)),(59.5,43)],.3,k.B_Cu)
    line(b,'BQ25798_ILIM',[point(pad(b,'U8',17)),(53.2,52.2),(53.5,52.5),(53.7,52.7),(53.7,56.6)],.2)
    via(b,'BQ25798_ILIM',53.7,56.6)
    line(b,'BQ25798_ILIM',[(53.7,56.6),(60,61.2)],.2,k.In2_Cu)
    via(b,'BQ25798_ILIM',60,61.2)
    join(b,('R76',2),('R77',1),width=.2,layer=k.B_Cu)
    line(b,'BQ25798_ILIM',[(60,61.2),(61.175,61.2),point(pad(b,'R76',2))],.2,k.B_Cu)
    line(b,'NTC_CHG',[point(pad(b,'U8',16)),(53.1,52.6),(53.1,56.2),(52.7,56.6),(52.7,57.5)],.2)
    via(b,'NTC_CHG',52.7,57.5)
    line(b,'NTC_CHG',[(52.7,57.5),(52.7,58.5),(58,63.8),(67,63.8),(69.5,61.3),(69.5,57.5)],.2,k.In2_Cu)
    via(b,'NTC_CHG',69.5,57.5)
    line(b,'NTC_CHG',[(69.5,57.5),(68,57.5),point(pad(b,'R78',2))],.2,k.B_Cu)
    join(b,('R78',2),('R79',1),width=.2,layer=k.B_Cu)
    line(b,'CHG_REGN',[(47.6,53.775),(47.6,55.5)],.2)
    via(b,'CHG_REGN',47.6,55.5)
    line(b,'CHG_REGN',[(47.6,55.5),(48,56),(60,56),(60,58.5)],.2,k.In2_Cu)
    via(b,'CHG_REGN',60,58.5)
    line(b,'CHG_REGN',[(60,58.5),point(pad(b,'R76',1))],.2,k.B_Cu)
    join(b,('R76',1),('R78',1),[(63,59.5),(63,57)],.2,k.B_Cu)
    for ref,x,y in [('R77',65,64.5),('R79',64.5,58)]:
        line(b,'DGND',[point(pad(b,ref,2)),(x,y)],.3,k.B_Cu)
        via(b,'DGND',x,y)
    # VAC1/VAC2 are voltage-sense inputs, not the high-current VBUS pins.
    line(b,'CHARGER_IN',[point(pad(b,'U8',8)),(49.1,54.8)],.2)
    line(b,'CHARGER_IN',[point(pad(b,'U8',9)),(49.6,54),(49.1,54.5)],.2)
    via(b,'CHARGER_IN',49.1,54.8)
    via(b,'CHARGER_IN',43.5,51.7)
    line(b,'CHARGER_IN',[(49.1,54.8),(45,54.8),(43.5,53.3),(43.5,51.7)],.2,k.In2_Cu)
    join(b,('U8',10),('U8',11),width=.2)
    for pin,x in [(10,50),(13,51.2)]:
        line(b,'DGND',[point(pad(b,'U8',pin)),(x,54.8)],.2)
        via(b,'DGND',x,54.8)

def stage_a(b):
    # Unrouted BMS parts only: shorten filtered sense links and keep their
    # inputs at the shunt instead of the earlier generic packing positions.
    move(b,'U9',65.5,76.9)
    move(b,'R95',63.5,67.95)
    move(b,'R94',63.5,74.05)
    move(b,'C94',62,77.5,90)
    move(b,'C93',68,81.5)
    move(b,'TP26',64,70.5)
    move(b,'TP30',90,61)
    # SW2's original pad blocked the gauge's complete right-side fanout.
    # Move this unrouted service button locally; all panel/connectors stay fixed.
    move(b,'SW2',85,78)
    # Five-amp force current enters the lower shunt terminal separately from
    # the quiet side-edge sense pickup. Three parallel through vias.
    line(b,'BAT_NEG_RAW',[point(pad(b,'J8',3)),(34,72),(39,64.5),
                         (54,64.5),(56,66.5),(56,71),(58.5,74.2),(59.1,75.4)],2.5,k.In2_Cu)
    line(b,'BAT_NEG_RAW',[(59.1,75.4),(60.9,75.4)],1.2,k.In2_Cu)
    for x in (59.1,60,60.9):
        via(b,'BAT_NEG_RAW',x,75.4)
        line(b,'BAT_NEG_RAW',[point(pad(b,'R93',1)),(x,75.4)],1.0)
    # Equal force fanout on the DGND side; connects to the plane at stage E.
    for x in (59.1,60,60.9):
        via(b,'DGND',x,66.6)
        line(b,'DGND',[point(pad(b,'R93',2)),(x,66.6)],1.0)
    # Kelvin trace roots are INSIDE the two respective shunt pads. There is
    # no sense via in DGND before R95, preventing L2 from bypassing the pickup.
    line(b,'BAT_NEG_RAW',[(61.4,74.05),point(pad(b,'R94',1))],.2)
    line(b,'DGND',[(61.4,67.95),point(pad(b,'R95',1))],.2)
    for ref,net,y in [('R94','BMS_SRP_FILT',74.05),('R95','BMS_SRN_FILT',67.95)]:
        line(b,net,[point(pad(b,ref,2)),(65.5,y)],.2)
        via(b,net,65.5,y)
    # Filtered pair on B.Cu, away from SW1/SW2 and force traces on In2.Cu.
    line(b,'BMS_SRN_FILT',[(65.5,67.95),(66.3,68.75),(66.3,71.7),
                          (62.8,75.2),(62.8,76.725),(61,76.725)],.2,k.B_Cu)
    line(b,'BMS_SRP_FILT',[(65.5,74.05),(64.6,74.95),(64.6,78.4),
                          (63.7,79.3),(61,79.3),(61,78.275)],.2,k.B_Cu)
    for net,y,pin in [('BMS_SRN_FILT',76.725,2),('BMS_SRP_FILT',78.275,1)]:
        x=61
        via(b,net,x,y)
        line(b,net,[(x,y),point(pad(b,'C94',pin))],.2)
    join(b,('C94',2),('U9',2),[(62,75.4),(63.2,75.4),(63.6,75.8),(63.6,76.3)],.2)
    join(b,('C94',1),('U9',3),[(63,78.275),(63,76.7)],.2)
    # Cell filtering is adjacent to the gauge, on its reverse side. Separate
    # connector-origin sense routes are not extensions of battery force copper.
    back(b,'R90',74,82,180)
    back(b,'R91',78,82,180)
    back(b,'C97',70.5,74.5)
    back(b,'C98',73.5,74.5)
    # VC1 and VC2 escape to local vias above the pin row, not into SW2 pads.
    for pin,x,ex in [(7,68.4,67.4),(8,69.4,67.8),(9,70.4,68.2),
                     (10,71.4,68.6),(11,72.4,69),(12,73.4,69.4)]:
        p=pad(b,'U9',pin); y=point(p)[1]; net=str(p.GetNetname())
        line(b,net,[point(p),(ex,y),(x,79.4)],.2)
        via(b,net,x,79.4)
    line(b,'BMS_VC1_FILT',[(73.4,79.4),(73.4,76),(72.725,75.325),point(pad(b,'C98',1))],.2,k.B_Cu)
    join(b,('C98',1),('C97',2),width=.2,layer=k.B_Cu)
    line(b,'BMS_VC2_FILT',[(72.4,79.4),(72.4,75.8),(69.725,75.8),point(pad(b,'C97',1))],.2,k.B_Cu)
    line(b,'BMS_VC2_FILT',[point(pad(b,'R90',2)),(72.4,81.225),(72.4,79.4)],.2,k.B_Cu)
    line(b,'BMS_VC1_FILT',[point(pad(b,'R91',2)),(76,80.825),(74.825,80.825),(73.4,79.4)],.2,k.B_Cu)
    # Gauge VSS/EP local return, tied only to the battery side of the shunt.
    line(b,'BAT_NEG_RAW',[point(pad(b,'U9',1)),(64.15,75.4),(65.5,75.4),(65.5,76.9)],.2)
    via(b,'BAT_NEG_RAW',65.5,76.9)
    line(b,'BAT_NEG_RAW',[(65.5,76.9),(64.5,76.9),(63,75.4),(60.9,75.4)],.5,k.In2_Cu)
    via(b,'BAT_NEG_RAW',75.8,74.5)
    line(b,'BAT_NEG_RAW',[point(pad(b,'C98',2)),(75.8,74.5)],.3,k.B_Cu)
    line(b,'BAT_NEG_RAW',[(75.8,74.5),(72,73),(68,73),(65.5,76.9)],.5,k.In2_Cu)
    # PBI bypass is bottom-side, directly behind the gauge.
    back(b,'C93',71.4,81.2,90)
    line(b,'BMS_PBI',[(71.4,79.4),point(pad(b,'C93',1))],.2,k.B_Cu)
    line(b,'BAT_NEG_RAW',[point(pad(b,'C93',2)),(71.8,82.375),(71.8,83.3)],.3,k.B_Cu)
    via(b,'BAT_NEG_RAW',71.8,83.3)
    line(b,'BAT_NEG_RAW',[(71.8,83.3),(74,84.5),(79,84.5),(79,74.5),(75.8,74.5)],.3,k.In2_Cu)
    # CHG/DSG gate components retain the TI EVM connectivity. Gate traces
    # leave the gate pad away from the parallel source fingers.
    move(b,'R98',48,81,180)
    move(b,'R99',43,81,180)
    move(b,'R100',58.5,81)
    back(b,'R101',58,84,90)
    move(b,'TP29',39,83)
    back(b,'C95',48,73)
    back(b,'C96',53,73)
    back(b,'R92',63,81)
    back(b,'R96',62,84)
    back(b,'R97',65,84)
    join(b,('Q2',1),('R98',2),[(46.56,80.385)],.2)
    join(b,('R98',2),('R99',1),width=.2)
    line(b,'PACK_POS',[point(pad(b,'R99',2)),(42.175,82.3)],.3)
    via(b,'PACK_POS',42.175,82.3)
    line(b,'PACK_POS',[(42.175,82.3),(42.175,80.3),(45.4,78.4)],.5,k.B_Cu)
    line(b,'BMS_CHG_GATE',[point(pad(b,'Q3',1)),(54.44,75.8),(57.325,75.8),(59.325,77.8),(59.325,81)],.2)
    line(b,'BMS_CHG_GATE',[point(pad(b,'R100',2)),(60.3,81)],.2)
    via(b,'BMS_CHG_GATE',60.3,81)
    line(b,'BMS_CHG_GATE',[(60.3,81),(60.3,83.175),point(pad(b,'R101',1))],.2,k.B_Cu)
    line(b,'BAT_POS_RAW',[point(pad(b,'R101',2)),(54,84.825),(54,81.5)],.3,k.B_Cu)
    for ref,net,x,y in [('R98','N$2',49.8,81),('R100','N$3',57.675,80)]:
        line(b,net,[point(pad(b,ref,1)),(x,y)],.2)
        via(b,net,x,y)
    line(b,'N$2',[(68.4,79.4),(68.4,81.9),(51,81.9),(49.8,81)],.2,k.In2_Cu)
    line(b,'N$3',[(70.4,79.4),(70.4,81.4),(69,82.8),(61.2,82.8),(61.2,80),(57.675,80)],.2,k.B_Cu)
    line(b,'BMS_FET_COMMON',[point(pad(b,'C95',2)),(50.5,74.725),(50.5,77.3)],.3,k.B_Cu)
    line(b,'BMS_FET_COMMON',[point(pad(b,'C96',1)),(50.5,74.725)],.3,k.B_Cu)
    via(b,'PACK_POS',47.225,71.8)
    line(b,'PACK_POS',[point(pad(b,'C95',1)),(47.225,71.8),(45.4,71.8),(45.4,73.5)],.3,k.B_Cu)
    line(b,'BAT_POS_RAW',[point(pad(b,'C96',2)),(55.55,73),(55.55,77.75)],.3,k.B_Cu)
    # PACK sense supply, NTC input and shunt-test terminals.
    line(b,'PACK_POS',[(69.4,79.4),(69.4,80.5),(71,82.1),(71,85),(46,85),(42.175,82.3)],.3,k.In2_Cu)
    line(b,'N$1',[point(pad(b,'U9',4)),(63.45,77.1),(63.45,80.1)],.2)
    via(b,'N$1',63.45,80.1)
    line(b,'N$1',[(63.45,80.1),point(pad(b,'R92',2))],.2,k.B_Cu)
    line(b,'BAT_NEG_RAW',[point(pad(b,'TP26',1)),(60,71.5),(56,71)],.5,k.In2_Cu)
    # Harness sense lines use the quiet lower perimeter, below the charger
    # and battery force corridor. They pick up at J8, not FET force vias.
    join(b,('J8',2),('TP25',1),[(35,75)],.2)
    line(b,'CELL_MID',[point(pad(b,'TP25',1)),(35,85),(40,90),(40,96),
                       (86,96),(86,84),(80,84),(80,82)],.2,k.In2_Cu)
    via(b,'CELL_MID',80,82)
    line(b,'CELL_MID',[(80,82),point(pad(b,'R91',1))],.2,k.B_Cu)
    line(b,'BAT_POS_RAW',[point(pad(b,'J8',1)),(31,80),(31,95),(33,97),
                          (88,97),(88,83)],.2,k.In2_Cu)
    via(b,'BAT_POS_RAW',88,83)
    line(b,'BAT_POS_RAW',[(88,83),(75.5,83),(75.5,82)],.2)
    via(b,'BAT_POS_RAW',75.5,82)
    line(b,'BAT_POS_RAW',[(75.5,82),point(pad(b,'R90',1))],.2,k.B_Cu)
    line(b,'NTC_BMS',[point(pad(b,'J8',4)),(31,69),(31,77)],.2,k.B_Cu)
    via(b,'NTC_BMS',31,77)
    line(b,'NTC_BMS',[(31,77),(31,80),(32.5,81.5),(33,83.5),(38.5,83.5),point(pad(b,'TP29',1))],.2)
    line(b,'NTC_BMS',[point(pad(b,'TP29',1)),(40,84),(49,84),(50,83),
                      (61.2,83),(62.175,82.025),(62.175,80)],.2)
    via(b,'NTC_BMS',62.175,80)
    line(b,'NTC_BMS',[(62.175,80),point(pad(b,'R92',1))],.2,k.B_Cu)
    # A future ground pour must not bypass the Kelvin pickup on the front.
    for name,y in [('SRN',67.95),('SRP',74.05)]:
        z=k.ZONE(b); z.SetIsRuleArea(True); z.SetZoneName('KELVIN_'+name+'_NO_POUR')
        z.SetLayer(k.F_Cu); z.SetDoNotAllowZoneFills(True)
        z.SetDoNotAllowTracks(False); z.SetDoNotAllowVias(False)
        z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
        o=z.Outline(); o.NewOutline()
        for x,yy in [(61.5,y-.75),(64.1,y-.75),(64.1,y+.75),(61.5,y+.75)]:
            o.Append(k.FromMM(x),k.FromMM(yy))
        b.Add(z)

def main():
    # Re-evaluating this stage preserves every A0 track UUID and footprint;
    # the immutable input is the CURRENT USER-SPECIFIED ROUTING CHECKPOINT.
    src=ROOT/'tmp'/'stage_A_start.kicad_pcb'
    src.parent.mkdir(exist_ok=True)
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()!=A0:
        raise RuntimeError('A-stage regeneration is allowed only at A0; use the next checkpoint recipe')
    if not src.exists():
        if subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()!=A0:
            raise RuntimeError('Initialize this stage only at the specified A0 commit')
        src.write_bytes(subprocess.check_output(['git','show',A0+
            ':hardware/kicad/R3_PowerBox/R3_power.kicad_pcb'],cwd=ROOT))
    b=k.LoadBoard(str(src)); stage_a(b); charger_finish(b)
    b.GetDesignSettings().m_TrackMinWidth=k.FromMM(.13)
    k.SaveBoard(str(BOARD),b)
    print('A0 retained; stage A in progress:',len(b.GetTracks()),'copper objects')

if __name__=='__main__': main()
