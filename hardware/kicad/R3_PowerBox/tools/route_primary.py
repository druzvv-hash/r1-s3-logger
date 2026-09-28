"""Checkpoint B: explicit local primary-buck routing from committed A."""
import subprocess
import pcbnew as k
from route_reva import ROOT,BOARD,pad,point,line,via,join
from continue_routing import move,back

A='4fed7b328fe3f52b9201013b1988913a9c660c6d'

def primary(b):
    # Rotate the unrouted IC so SW faces its inductor, VIN the input caps.
    move(b,'U1',76,42,180)
    move(b,'L1',80.5,42.3)
    move(b,'C11',72.8,42,90)
    back(b,'C10',73,43.5,90)
    move(b,'C12',85,42.3)
    move(b,'C13',85,45)
    move(b,'C14',73,38.5,180)
    move(b,'R10',80,38)
    for a,z in [(1,2),(2,3)]: join(b,('U1',a),('U1',z),width=.25)
    line(b,'SW_3V3',[point(pad(b,'U1',2)),point(pad(b,'L1',1))],.5)
    for a,z in [(10,11),(11,12)]: join(b,('U1',a),('U1',z),width=.25)
    join(b,('U1',12),('U1',13),[(74.5625,43.4375)],.25)
    join(b,('U1',12),('C11',1),width=.5)
    line(b,'VSYS_MAIN',[point(pad(b,'C11',1)),(71.5,43.5)],.8)
    via(b,'VSYS_MAIN',71.5,43.5)
    line(b,'VSYS_MAIN',[(71.5,43.5),point(pad(b,'C10',1))],.8,k.B_Cu)
    join(b,('L1',2),('C12',1),width=1)
    join(b,('C12',1),('C13',1),width=.8)
    join(b,('U1',14),('C13',1),[(75.75,45)],.2)
    join(b,('U1',9),('C14',1),[(74,41.25),(74,38.5)],.2)
    join(b,('U1',4),('R10',1),[(77.6,41.25),(77.6,39),(79.175,39)],.2)
    join(b,('R10',2),('C12',1),[(84.05,38)],.2)
    for a,z in [(5,6),(6,7),(7,8),(15,16)]: join(b,('U1',a),('U1',z),width=.25)
    line(b,'DGND',[point(pad(b,'U1',15)),(76.25,43),(76,42)],.25)
    line(b,'DGND',[point(pad(b,'U1',6)),(76,42)],.35)
    for x,y in [(75.55,41.5),(76.45,41.5),(75.55,42.4),(76.45,42.4)]:
        via(b,'DGND',x,y)
    for ref,x,y in [('C11',71.8,40.9),
                    ('C12',87.2,42.3),('C13',87.2,45),('C14',71.2,38.5)]:
        line(b,'DGND',[point(pad(b,ref,2)),(x,y)],.35)
        via(b,'DGND',x,y)
    line(b,'DGND',[point(pad(b,'C10',2)),(73,46.3)],.35,k.B_Cu)
    via(b,'DGND',73,46.3)
    # U2: the SW terminal faces L2; sense/BOOT stay out of force copper.
    move(b,'U2',96,52,180)
    move(b,'L2',102,52)
    move(b,'C21',97,48.6)
    move(b,'C20',100,45.4)
    move(b,'C23',108.8,51)
    move(b,'C24',108.8,54)
    back(b,'C22',96,53.8)
    back(b,'R21',94.5,49.2)
    back(b,'R22',91.5,49.2,180)
    back(b,'C25',94.5,47)
    join(b,('U2',2),('L2',1),width=.8)
    join(b,('U2',3),('C21',1),[(97.1375,49.5125)],.6)
    join(b,('C20',1),('C21',1),[(96.225,45.4)],.8)
    line(b,'VSYS_MAIN',[point(pad(b,'U2',5)),(93.7,52)],.2)
    via(b,'VSYS_MAIN',93.7,52)
    via(b,'VSYS_MAIN',96.225,49.5)
    line(b,'VSYS_MAIN',[(93.7,52),(94.5,51.2),(96.225,49.5)],.3,k.In2_Cu)
    line(b,'VSYS_MAIN',[(96.225,49.5),point(pad(b,'C21',1))],.3)
    line(b,'N$12',[point(pad(b,'U2',6)),(94.225,53.5875),(94.225,53.8)],.2)
    via(b,'N$12',94.225,53.8)
    line(b,'N$12',[(94.225,53.8),point(pad(b,'C22',1))],.2,k.B_Cu)
    line(b,'SW_5V',[point(pad(b,'L2',1)),(99.75,54.7)],.2)
    via(b,'SW_5V',99.75,54.7)
    line(b,'SW_5V',[(99.75,54.7),(96.775,54.7),point(pad(b,'C22',2))],.2,k.B_Cu)
    line(b,'+5V_PREISO',[point(pad(b,'L2',2)),(107.85,52),point(pad(b,'C23',1))],1)
    join(b,('C23',1),('C24',1),width=1)
    line(b,'FB_5V',[point(pad(b,'U2',4)),(93.5,51.05)],.2)
    via(b,'FB_5V',93.5,51.05)
    line(b,'FB_5V',[(93.5,51.05),(95.325,51.05),point(pad(b,'R21',2))],.2,k.B_Cu)
    join(b,('R22',1),('R21',2),[(92.325,50.2),(95.325,50.2)],.2,k.B_Cu)
    join(b,('C25',2),('R21',2),width=.2,layer=k.B_Cu)
    join(b,('C25',1),('R21',1),width=.2,layer=k.B_Cu)
    line(b,'+5V_PREISO',[point(pad(b,'C24',1)),(105.9,55.3)],.2)
    via(b,'+5V_PREISO',105.9,55.3)
    line(b,'+5V_PREISO',[(105.9,55.3),(105.9,57.5),(92,57.5),(91,56.5),
                        (91,50.5),(91.5,50),(91.5,47),point(pad(b,'C25',1))],.2,k.B_Cu)
    line(b,'DGND',[point(pad(b,'U2',1)),(97.1375,54.2),(96,55.3375),(96,55.9)],.35)
    via(b,'DGND',96,55.9)
    for ref,pin,x,y,layer in [
                             ('C21',2,98.6,48.6,k.F_Cu),
                             ('C20',2,102.9,45.4,k.F_Cu),
                             ('C23',2,111,51,k.F_Cu),
                             ('C24',2,111,54,k.F_Cu),
                             ('R22',2,89.5,49.2,k.B_Cu)]:
        line(b,'DGND',[point(pad(b,ref,pin)),(x,y)],.35,layer)
        via(b,'DGND',x,y)

def main():
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()!=A:
        raise RuntimeError('B recipe requires committed A HEAD; refusing to erase later work')
    src=ROOT/'tmp'/'stage_B_start.kicad_pcb'
    if not src.exists():
        src.write_bytes(subprocess.check_output(['git','show',A+
            ':hardware/kicad/R3_PowerBox/R3_power.kicad_pcb'],cwd=ROOT))
    b=k.LoadBoard(str(src)); primary(b)
    b.GetDesignSettings().m_TrackMinWidth=k.FromMM(.13)
    k.SaveBoard(str(BOARD),b)
    print('A retained; B copper objects:',len(b.GetTracks()))

if __name__=='__main__': main()
