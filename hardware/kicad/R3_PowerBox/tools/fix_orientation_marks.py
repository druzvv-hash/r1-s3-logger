"""Targeted visible SO8 physical-pin1 marks and critical reference labels.
No pad, net, footprint-anchor, or copper changes.
"""
import pcbnew as k
from route_reva import BOARD,vec
b=k.LoadBoard(str(BOARD))
for ref in ['Q1','Q4']:
    f=b.FindFootprintByReference(ref)
    # The historical cleanup moved the pad-overlapping dot to F.Fab.
    # Place a new unambiguous physical-source-pin1 dot outside the land row.
    for layer,offset in [(k.F_SilkS,(-2.65,-2.95)),(k.F_Fab,(-1.35,-1.85))]:
        s=k.PCB_SHAPE(f);s.SetShape(k.SHAPE_T_CIRCLE)
        p=f.GetPosition()+vec(*offset);s.SetCenter(p);s.SetEnd(p+vec(.15,0))
        s.SetWidth(k.FromMM(.12));s.SetFilled(True);s.SetLayer(layer);f.Add(s)
labels={'Q1':(29,81.4),'Q4':(72,66.4),'D2':(29,91),'D7':(65,37),
        'C1':(37,63.5),'U9':(65.5,74.6),'U8':(51,54.2),'U10':(33,35.8),'J7':(24,37.9)}
for ref,(x,y) in labels.items():
    field=b.FindFootprintByReference(ref).Reference();field.SetPosition(vec(x,y));field.SetLayer(k.F_SilkS);field.SetVisible(True)
    field.SetTextAngle(k.EDA_ANGLE(0,k.DEGREES_T));field.SetTextSize(vec(.7,.7));field.SetTextThickness(k.FromMM(.12))
# A '+' dedicated to C1, not the nearby J1 pin1 label.
f=b.FindFootprintByReference('C1');s=k.PCB_TEXT(b);s.SetText('C1+');s.SetPosition(vec(30.5,62.9));s.SetTextSize(vec(.65,.65));s.SetTextThickness(k.FromMM(.12));s.SetLayer(k.F_SilkS);b.Add(s)
k.SaveBoard(str(BOARD),b)
