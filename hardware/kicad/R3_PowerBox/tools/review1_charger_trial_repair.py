"""Remove the DRC-failed charger trial only, preserving all other review ECOs.

The trial's short circuits and overlapping courtyards are recorded in the work
DRC. Recover ONLY its eight changed power/bootstrap nets, then improve locally.
Not a board reset or a replay of an earlier routing stage.
"""
import subprocess
import review1_eco_guard  # Prevent accidental replay over the accepted board.
import pcbnew as k
from route_reva import BOARD,vec
scratch=BOARD.parent/'tmp/review1_charger_reference.kicad_pcb'
scratch.write_bytes(subprocess.check_output(['git','show','ce12ca9:hardware/kicad/R3_PowerBox/R3_power.kicad_pcb']))
b=k.LoadBoard(str(BOARD)); old=k.LoadBoard(str(scratch)); ts=b.GetTracks(); ots=old.GetTracks()
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
for ref in ['L3','C77','C81','C100','C101','C87']:
    f=b.FindFootprintByReference(ref); original=old.FindFootprintByReference(ref)
    prev={p.GetNumber():k.VECTOR2I(p.GetPosition()) for p in f.Pads()}
    f.SetPosition(original.GetPosition());f.SetOrientationDegrees(original.GetOrientationDegrees())
    for p in f.Pads():
        for t in ts:
            if isinstance(t,k.PCB_VIA):continue
            if t.GetStart()==prev[p.GetNumber()]:t.SetStart(p.GetPosition())
            if t.GetEnd()==prev[p.GetNumber()]:t.SetEnd(p.GetPosition())
changed={'CHG_SW1','CHG_SW2','N$7','N$8','CHARGER_IN','PACK_POS','CHG_PMID','VSYS_RAW'}
new_ground={(47.1,48),(47.1,48.8),(44,49.3),(44,50.1),(55.5,48.3),(56.3,48.3)}
for t in list(ts):
    xy=(round(k.ToMM(t.GetPosition().x),4),round(k.ToMM(t.GetPosition().y),4))
    if str(t.GetNetname()) in changed or (isinstance(t,k.PCB_VIA) and str(t.GetNetname())=='DGND' and xy in new_ground):b.Remove(t)
copies=[]
for t in ots:
    if str(t.GetNetname()) in changed:
        c=t.Duplicate();c.SetNet(b.FindNet(str(t.GetNetname())));b.Add(c);copies.append(c)
k.SaveBoard(str(BOARD),b)
