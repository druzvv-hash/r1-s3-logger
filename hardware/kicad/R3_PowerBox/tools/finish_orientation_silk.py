"""Complete local reference-label clearances after DRC feedback."""
import pcbnew as k
from route_reva import BOARD,vec
b=k.LoadBoard(str(BOARD))
for ref in ['Q1','Q4','D2','D7','C1','U9','U8','U10','J7']:
    f=b.FindFootprintByReference(ref).Reference();f.SetTextSize(vec(.8,.8))
for ref,xy in [('U10',(33,36.7)),('J7',(24,27)),('D7',(65.7,37))]:b.FindFootprintByReference(ref).Reference().SetPosition(vec(*xy))
for g in b.GetDrawings():
    if isinstance(g,k.PCB_TEXT) and g.GetText()=='C1+':g.SetTextSize(vec(.8,.8))
f=b.FindFootprintByReference('U1')
if not any(isinstance(g,k.PCB_SHAPE) and g.GetLayer()==k.F_SilkS and g.GetShape()==k.SHAPE_T_CIRCLE for g in f.GraphicalItems()):
    s=k.PCB_SHAPE(f);s.SetShape(k.SHAPE_T_CIRCLE);s.SetCenter(vec(78,44.2));s.SetEnd(vec(78.15,44.2));s.SetWidth(k.FromMM(.12));s.SetFilled(True);s.SetLayer(k.F_SilkS);f.Add(s)
f=b.FindFootprintByReference('U9')
if not any(isinstance(g,k.PCB_SHAPE) and g.GetLayer()==k.F_Fab and g.GetShape()==k.SHAPE_T_CIRCLE for g in f.GraphicalItems()):
    s=k.PCB_SHAPE(f);s.SetShape(k.SHAPE_T_CIRCLE);s.SetCenter(vec(64.55,76.1));s.SetEnd(vec(64.7,76.1));s.SetWidth(k.FromMM(.1));s.SetFilled(True);s.SetLayer(k.F_Fab);f.Add(s)
k.SaveBoard(str(BOARD),b)
