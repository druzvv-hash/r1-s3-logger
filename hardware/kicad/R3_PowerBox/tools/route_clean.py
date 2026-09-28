"""Checkpoint C: explicit independent inputs and clean-domain routing."""
import subprocess
import pcbnew as k
from route_reva import ROOT,BOARD,pad,point,line,via,join
from continue_routing import move,back
B='e28cc551cb03bcb958b2d4dc5e7dc65117e721fd'

def clean(b):
    back(b,'FB6',112.5,49)
    back(b,'FB7',112,68.5)
    for ref,x,y in [('C26',116.5,44),('C27',116.5,46.5),
                    ('C28',116.5,68.5),('C29',116.5,71)]: back(b,ref,x,y)
    line(b,'+5V_PREISO',[point(pad(b,'C24',1)),(107.85,56)],.8)
    via(b,'+5V_PREISO',107.85,56)
    line(b,'+5V_PREISO',[(107.85,56),(113.5,56),(113.5,52.2),(110,52.2),(110,49.3)],.8,k.In2_Cu)
    via(b,'+5V_PREISO',110,49.3)
    line(b,'+5V_PREISO',[(110,49.3),point(pad(b,'FB6',1))],.8,k.B_Cu)
    line(b,'+5V_PREISO',[(113.5,56),(113.5,65),(110,65),(110,67)],.8,k.In2_Cu)
    via(b,'+5V_PREISO',110,67)
    for a,z in [((107.85,56),(107,56)),((110,49.3),(109.1,49.3)),((110,67),(110,66.1))]:
        via(b,'+5V_PREISO',*z)
        line(b,'+5V_PREISO',[a,z],.8,k.In2_Cu)
        line(b,'+5V_PREISO',[a,z],.8,k.F_Cu if a==(107.85,56) else k.B_Cu)
    line(b,'+5V_PREISO',[(110,67),(110.3375,67.3375),point(pad(b,'FB7',1))],.8,k.B_Cu)
    join(b,('FB6',2),('C27',1),width=.8,layer=k.B_Cu)
    join(b,('C27',1),('C26',1),width=.8,layer=k.B_Cu)
    join(b,('U3',2),('C26',1),[(117.44,41.5),(115.55,43.39)],.8,k.B_Cu)
    join(b,('FB7',2),('C28',1),width=.8,layer=k.B_Cu)
    join(b,('C28',1),('C29',1),width=.8,layer=k.B_Cu)
    join(b,('C29',1),('U6',2),[(117.44,72.715)],.8,k.B_Cu)
    for ref,x,y in [('C26',118.7,44),('C27',118.5,46.5),
                    ('C28',118.7,68.5),('C29',118.5,71)]:
        line(b,'DGND',[point(pad(b,ref,2)),(x,y)],.35,k.B_Cu); via(b,'DGND',x,y)
    # Raw secondary splits remain physically and electrically isolated.
    back(b,'C30',128.5,43)
    back(b,'C31',132,43)
    join(b,('U3',6),('C30',1),width=.8,layer=k.B_Cu)
    line(b,'+5V_ISO_RAW',[(127.57,41.7),(131.225,41.7),point(pad(b,'C31',1))],.6,k.B_Cu)
    line(b,'+5V_ISO_RAW',[point(pad(b,'C30',1)),(126,44.5)],.8,k.B_Cu)
    via(b,'+5V_ISO_RAW',126,44.5)
    line(b,'+5V_ISO_RAW',[(126,44.5),point(pad(b,'FB2',1))],.8)
    join(b,('FB2',1),('FB3',1),width=.8)
    for fb,bulk,small in [('FB2','C32','C33'),('FB3','C34','C35'),('FB4','C60','C61')]:
        join(b,(fb,2),(bulk,1),width=.8)
        join(b,(bulk,1),(small,1),width=.6)
    # ADM7150 bypasses face their actual pins, not generic symbol ordering.
    move(b,'C40',148.5,44.5)
    move(b,'C41',141.5,44.5,180)
    move(b,'C42',140.5,41.5,180)
    move(b,'C43',148.8,38.3,90)
    move(b,'C44',142,38.5,90)
    back(b,'R40',148,45.5)
    join(b,('U4',8),('C40',1),[(147.55,43.95)],.3)
    join(b,('U4',1),('C41',1),[(142.45,43.95)],.3)
    join(b,('U4',2),('C42',1),[(142.2,42.25)],.3)
    join(b,('U4',3),('C44',1),[(142.5,41.75),(142.5,39.775)],.2)
    join(b,('U4',5),('U4',6),width=.2)
    join(b,('U4',5),('C43',1),[(147.1,41.25),(148.8,39.55)],.2)
    line(b,'EN_3V3_A_ISO',[point(pad(b,'U4',7)),(149,42.25)],.2)
    via(b,'EN_3V3_A_ISO',149,42.25)
    line(b,'EN_3V3_A_ISO',[(149,42.25),(149,44),point(pad(b,'R40',2))],.2,k.B_Cu)
    via(b,'+5V_ISO_A',146.175,44.2)
    line(b,'+5V_ISO_A',[(146.175,44.2),point(pad(b,'C40',1))],.4)
    line(b,'+5V_ISO_A',[(146.175,44.2),point(pad(b,'R40',1))],.3,k.B_Cu)
    line(b,'+5V_ISO_A',[point(pad(b,'C33',1)),(131,50.2)],.5)
    via(b,'+5V_ISO_A',131,50.2)
    line(b,'+5V_ISO_A',[(131,50.2),(140,50.2),(146.175,44.2)],.6,k.In2_Cu)
    line(b,'GND_ISO',[point(pad(b,'U4',4)),(144.4,41.25),(145,42)],.3)
    for x,y in [(144.55,41.55),(145.45,41.55),(144.55,42.45),(145.45,42.45)]: via(b,'GND_ISO',x,y)
    move(b,'C50',140.5,65.5,180)
    move(b,'C51',149,65.5)
    join(b,('U5',1),('C50',1),width=.4)
    join(b,('U5',5),('C51',1),width=.4)
    line(b,'+5V_ISO_D',[point(pad(b,'U5',3)),(142.8,68.7)],.3)
    via(b,'+5V_ISO_D',142.8,68.7)
    via(b,'+5V_ISO_D',141.275,64.2)
    line(b,'+5V_ISO_D',[(141.275,64.2),(142.8,68.7)],.4,k.In2_Cu)
    line(b,'+5V_ISO_D',[(141.275,64.2),point(pad(b,'C50',1))],.4)
    line(b,'+5V_ISO_D',[point(pad(b,'C35',1)),(132.225,58.5),(136,62.3),(136,64),(141.275,64.2)],.6)
    line(b,'GND_ISO',[point(pad(b,'U5',2)),(144.8,67)],.35)
    via(b,'GND_ISO',144.8,67)
    join(b,('U6',6),('FB4',1),width=.8)
    line(b,'-5V_INA_RAW',[point(pad(b,'U6',8)),(137,77.32),(137,84),(127.0875,84),(126,85.0875),(126,86)],.6,k.B_Cu)
    via(b,'-5V_INA_RAW',126,86)
    line(b,'-5V_INA_RAW',[(126,86),point(pad(b,'FB5',1))],.6)
    join(b,('FB5',2),('C62',2),[(128.9125,87.5),(133.95,87.5)],.6)
    line(b,'-5V_INA',[(128.9125,87.5),point(pad(b,'C63',2))],.6)
    for ref,pin,x,y in [('C30',2,130.4,44.3),('C31',2,134,43),
                        ('C32',2,135.2,46),('C33',2,135,49),
                        ('C34',2,135.2,54),('C35',2,135,57),
                        ('C40',2,150.8,44.5),('C41',2,139.2,44.5),
                        ('C42',2,138.2,41.5),('C43',2,148.8,36.3),
                        ('C44',2,142,36.5),('C50',2,138.5,65.5),
                        ('C51',2,151,65.5),('C60',2,135.2,79),
                        ('C61',2,135,82),('C62',1,130.8,86),('C63',1,126,89)]:
        line(b,'GND_ISO',[point(pad(b,ref,pin)),(x,y)],.35,k.B_Cu if ref in ('C30','C31') else k.F_Cu)
        via(b,'GND_ISO',x,y)

def main():
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()!=B:
        raise RuntimeError('C recipe requires B HEAD')
    src=ROOT/'tmp'/'stage_C_start.kicad_pcb'
    if not src.exists(): src.write_bytes(subprocess.check_output(['git','show',B+
        ':hardware/kicad/R3_PowerBox/R3_power.kicad_pcb'],cwd=ROOT))
    b=k.LoadBoard(str(src)); clean(b); b.GetDesignSettings().m_TrackMinWidth=k.FromMM(.13)
    k.SaveBoard(str(BOARD),b); print('B retained; C objects:',len(b.GetTracks()))

if __name__=='__main__': main()
