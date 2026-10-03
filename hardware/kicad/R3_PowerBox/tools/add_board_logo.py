"""Idempotent native silkscreen artwork; no copper or footprint mutation.

Hand-traced monochrome interpretation of the owner supplied Garage Logic Lab
logo. Run using KiCad Python. Do not run placement/routing generators.
"""
from pathlib import Path
import math
import pcbnew as k

ROOT = Path(__file__).resolve().parents[1]
board = k.LoadBoard(str(ROOT / 'R3_power.kicad_pcb'))
NAME = 'GARAGE_LOGIC_LAB_SILK_LOGO'
for group in list(board.Groups()):
    if group.GetName() == NAME:
        for item in list(group.GetItems()):
            board.Remove(item)
        board.Remove(group)
group = k.PCB_GROUP(board)
group.SetName(NAME)
board.Add(group)
CX, CY, SCALE = 162.5, 45.0, 0.012

def point(x, y):
    return k.VECTOR2I(k.FromMM(CX + (x-625)*SCALE), k.FromMM(CY + (y-602)*SCALE))

def line(a, b, width=0.15):
    s = k.PCB_SHAPE(board)
    s.SetShape(k.SHAPE_T_SEGMENT)
    s.SetStart(point(*a)); s.SetEnd(point(*b))
    s.SetWidth(k.FromMM(width)); s.SetLayer(k.F_SilkS)
    board.Add(s); group.AddItem(s)

def polygon(points):
    s = k.PCB_SHAPE(board)
    s.SetShape(k.SHAPE_T_POLY)
    poly = k.SHAPE_POLY_SET(); poly.NewOutline()
    for p in points:
        v = point(*p); poly.Append(v.x, v.y)
    s.SetPolyShape(poly); s.SetFilled(True); s.SetWidth(0)
    s.SetLayer(k.F_SilkS); board.Add(s); group.AddItem(s)

def circle(x,y,r,width=0.15):
    s=k.PCB_SHAPE(board); s.SetShape(k.SHAPE_T_CIRCLE)
    s.SetStart(point(x,y)); s.SetEnd(point(x+r,y))
    s.SetWidth(k.FromMM(width)); s.SetLayer(k.F_SilkS)
    board.Add(s); group.AddItem(s)

# Gear outline retains the distinctive toothed ring without photographic noise.
gear=[]
for tooth in range(16):
    for phase,r in [(0,460),(.18,460),(.25,505),(.75,505),(.82,460)]:
        a=2*math.pi*(tooth+phase)/16
        gear.append((625+r*math.cos(a),602+r*math.sin(a)))
for a,b in zip(gear,gear[1:]+gear[:1]): line(a,b)
circle(625,602,405)
polygon([(650,400),(443,400),(380,409),(332,445),(308,500),(299,544),
 (310,598),(343,641),(386,663),(430,671),(630,671),(630,507),(481,507),
 (433,563),(569,563),(569,607),(435,607),(400,595),(376,570),(372,537),
 (385,503),(412,479),(448,469),(589,469)])
polygon([(708,368),(612,473),(653,473),(653,669),(884,669),(824,603),(708,603)])
for pts,end in [([(730,514),(810,514),(853,468),(910,468)],(932,468)),
                 ([(730,558),(838,558),(875,525),(937,525)],(959,525)),
                 ([(841,585),(892,585)],(914,585))]:
    for a,b in zip(pts,pts[1:]): line(a,b,.16)
    circle(*end,22,.15)
for text,y,size in [('GARAGE',742,.8),('LOGIC LAB',827,.8)]:
    t=k.PCB_TEXT(board); t.SetText(text); t.SetPosition(point(625,y))
    t.SetTextSize(k.VECTOR2I(k.FromMM(size),k.FromMM(size)))
    t.SetTextThickness(k.FromMM(.13)); t.SetLayer(k.F_SilkS)
    board.Add(t); group.AddItem(t)
k.SaveBoard(str(ROOT / 'R3_power.kicad_pcb'),board)
print('Added logo at (162.5,45.0), 12.3 mm envelope, F.SilkS only.')
