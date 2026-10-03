"""Apply explicitly approved passive-footprint ECOs to the current routes."""
import xml.etree.ElementTree as E
import review1_eco_guard  # Prevent accidental replay over the accepted board.
import pcbnew as k
from route_reva import ROOT,BOARD,vec,pad,point,line
from generate_preliminary_placement import footprint_from_id
b=k.LoadBoard(str(BOARD)); root=E.parse(ROOT/'tmp/review1_netlist.xml').getroot()
retained=[]
cs={c.get('ref'):c for c in root.findall('./components/comp')}
assert not b.FindFootprintByReference('R107'), 'ECO already applied'
for z in b.Zones():
    if not z.GetIsRuleArea():z.UnFill()
for ref in ['C23','C24','C40','C41','C42','FB4','FB5']:
    old=b.FindFootprintByReference(ref)
    retained.append(old)
    print('Replacing',ref,flush=True)
    oldpins={p.GetNumber():(k.VECTOR2I(p.GetPosition()),p.GetNetCode()) for p in old.Pads()}
    new=footprint_from_id(cs[ref].findtext('footprint'))
    new.SetReference(ref);new.SetValue(cs[ref].findtext('value'));new.SetPath(old.GetPath())
    new.SetPosition(old.GetPosition());new.SetOrientationDegrees(old.GetOrientationDegrees())
    retained.append(new)
    for p in new.Pads():p.SetNet(b.FindNet(oldpins[p.GetNumber()][1]))
    new.Reference().SetLayer(k.F_Fab);new.Value().SetVisible(False)
    b.Remove(old);b.Add(new)
    for p in new.Pads():
        prev=oldpins[p.GetNumber()][0]
        for t in b.GetTracks():
            if isinstance(t,k.PCB_VIA):continue
            if t.GetStart()==prev:t.SetStart(p.GetPosition())
            if t.GetEnd()==prev:t.SetEnd(p.GetPosition())
    fid=k.LIB_ID();fid.Parse(k.UTF8(cs[ref].findtext('footprint')));new.SetFPID(fid)

old=b.FindFootprintByReference('R40'); points={p.GetNumber():p.GetPosition() for p in old.Pads()}
old.SetPosition(vec(148,47.5));old.Reference().SetLayer(k.F_Fab)
for p in old.Pads():
    for t in b.GetTracks():
        if isinstance(t,k.PCB_VIA):continue
        if t.GetStart()==points[p.GetNumber()]:t.SetStart(p.GetPosition())
        if t.GetEnd()==points[p.GetNumber()]:t.SetEnd(p.GetPosition())
for ref,xy in [('R107',(140,77)),('R108',(140,86))]:
    f=footprint_from_id(cs[ref].findtext('footprint'));f.SetReference(ref)
    f.SetValue(cs[ref].findtext('value'));f.SetPosition(vec(*xy));f.SetDNP(True)
    f.Reference().SetLayer(k.F_Fab);f.Value().SetVisible(False);b.Add(f)
    fid=k.LIB_ID();fid.Parse(k.UTF8(cs[ref].findtext('footprint')));f.SetFPID(fid)
    for net in root.findall('./nets/net'):
        for n in net.findall('node'):
            if n.get('ref')==ref:pad(b,ref,n.get('pin')).SetNet(b.FindNet(net.get('name')))
line(b,'+5V_INA',[point(pad(b,'C60',1)),(132.05,77),point(pad(b,'R107',1))],.35)
line(b,'-5V_INA',[point(pad(b,'C62',2)),point(pad(b,'R108',1))],.35)
k.SaveBoard(str(BOARD),b)
