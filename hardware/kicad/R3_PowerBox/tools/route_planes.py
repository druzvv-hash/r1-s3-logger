"""Checkpoint E: explicit domain planes, local returns and thermal stitching.

Builds on immutable D. This is not a signal router.
"""
import subprocess
import pcbnew as k
from route_reva import ROOT, BOARD, line, via, pad, point

D='24a4931'

def zone(b,net,layer,box,priority=0):
    z=k.ZONE(b);z.SetLayer(layer);z.SetNet(b.FindNet(net))
    z.SetZoneName(net+'_'+k.LayerName(layer)+'_RETURN')
    z.SetAssignedPriority(priority)
    z.SetLocalClearance(k.FromMM(.25));z.SetMinThickness(k.FromMM(.2))
    z.SetPadConnection(k.ZONE_CONNECTION_THT_THERMAL)
    z.SetThermalReliefGap(k.FromMM(.25));z.SetThermalReliefSpokeWidth(k.FromMM(.4))
    z.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS)
    x1,y1,x2,y2=box
    p=z.Outline();p.NewOutline()
    for x,y in ((x1,y1),(x2,y1),(x2,y2),(x1,y2)):p.Append(k.FromMM(x),k.FromMM(y))
    b.Add(z)

def main():
    src=ROOT/'tmp'/'stage_E_start.kicad_pcb'
    if not src.exists():src.write_bytes(subprocess.check_output(['git','show',D+
        ':hardware/kicad/R3_PowerBox/R3_power.kicad_pcb'],cwd=ROOT))
    b=k.LoadBoard(str(src))
    for x,y in [(22,22),(22,45),(33,53),(38,70),(38,94),(68,95),(100,95),
                (90,81.5),(96,66),(90,46.5),(90,54),(100,70),(70,29),(90,29),
                (95,32),(120.55,50),(120.55,60),(120.55,83)]:via(b,'DGND',x,y)
    for x,y in [(125,30),(125,55),(125,85),(138,30),(145,55),(154,55),(170,85)]:via(b,'GND_ISO',x,y)
    for net,pin,coords in [('VSYS_PROT',2,[(70.3,68.6),(70.3,70)]),
                         ('VSYS_MAIN',3,[(73.7,68.7),(73.7,70.2),(73.7,71.2)])]:
        for xy in coords:
            via(b,net,*xy)
            choices=[p for p in b.FindFootprintByReference('Q4').Pads() if p.GetNumber()==str(pin)]
            p=min(choices,key=lambda p:sum((a-c)**2 for a,c in zip(point(p),xy)))
            line(b,net,[point(p),xy],.5)
    for xy in [(145,40.5),(145,43.5)]:
        via(b,'GND_ISO',*xy);line(b,'GND_ISO',[point(pad(b,'U4',9)),xy],.3)
    for layer in (k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu):
        zone(b,'DGND',layer,(20.5,20.5,120.8,99.5))
        zone(b,'GND_ISO',layer,(124.2,20.5,179.5,99.5))
    for layer in (k.F_Cu,k.B_Cu):
        zone(b,'BMS_FET_COMMON',layer,(47.1,74.9,53.4,80.2),10)
        zone(b,'VSYS_PROT',layer,(67.5,67.5,71,71.3),10)
        zone(b,'VSYS_MAIN',layer,(73,67.5,76.5,73.3),10)
    b.GetDesignSettings().m_TrackMinWidth=k.FromMM(.13)
    k.ZONE_FILLER(b).Fill(b.Zones())
    k.SaveBoard(str(BOARD),b)
    print('E domain planes filled; tracks/vias',len(b.GetTracks()))

if __name__=='__main__':main()
