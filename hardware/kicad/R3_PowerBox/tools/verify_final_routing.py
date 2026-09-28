"""F acceptance checks against the preserved E board; no production sign-off."""
import json, math, subprocess
from pathlib import Path
import pcbnew as k
from finalize_routing import ROOT, REMOVE

E='b42e73f52d1e8538079f944b93870e21eaef7fe8'
scratch=ROOT/'tmp/F_preserved_E.kicad_pcb'
scratch.write_bytes(subprocess.check_output(['git','show',E+':hardware/kicad/R3_PowerBox/R3_power.kicad_pcb'],cwd=ROOT))
old=k.LoadBoard(str(scratch)); b=k.LoadBoard(str(ROOT/'R3_power.kicad_pcb'))
def pt(p):return (round(k.ToMM(p.x),5),round(k.ToMM(p.y),5))
def record(t):
    return (str(t.GetNetname()),pt(t.GetStart()),pt(t.GetEnd()),t.GetLayer(),
            t.GetWidth(k.F_Cu) if isinstance(t,k.PCB_VIA) else t.GetWidth())
before={t.m_Uuid.AsString():record(t) for t in old.GetTracks()}
after={t.m_Uuid.AsString():record(t) for t in b.GetTracks()}
def anchors(board):
    return {f.GetReference():(pt(f.GetPosition()),f.GetOrientationDegrees(),f.GetLayer()) for f in board.GetFootprints()}
def rules(board):
    return sorted((z.GetZoneName(),str(z.GetNetname()),z.GetLayer(),z.Outline().Format()) for z in board.Zones())
local_sw={'1deab3a7-5e7f-4af3-b785-25a58dad8758','24916ae9-7615-4fca-8a10-908e9fbae25a'}
changed={u:(v,after.get(u)) for u,v in before.items() if after.get(u)!=v}
unexpected={u:v for u,v in changed.items() if u not in REMOVE|local_sw and v[0][0] not in ('N$8','N$6')}
new={u:v for u,v in after.items() if u not in before}
loc_before=anchors(old);loc_after=anchors(b)
checks={
    'all_other_E_routes_preserved':not unexpected and all(v[0] in ('CHG_SW2','N$8') for v in new.values()),
    'all_other_E_footprint_positions_orientations_sides_preserved':all(v==loc_after[r] for r,v in loc_before.items() if r!='C75'),
    'C75_local_correction_position':loc_after['C75'][0]==(54.8,51.8),
    'zone_and_keepout_boundaries_preserved':rules(old)==rules(b),
}
for pin,ref,y,net in [(1,'R94',74.05,'BAT_NEG_RAW'),(2,'R95',67.95,'DGND')]:
    p=next(p for p in b.FindFootprintByReference('R93').Pads() if p.GetNumber()==str(pin))
    root=k.VECTOR2I(k.FromMM(61.4),k.FromMM(y))
    checks[f'R93_{pin}_sense_root_inside_pad']=p.HitTest(root)
    checks[f'{ref}_dedicated_0p2mm_FCu_pickup']=any(
        str(t.GetNetname())==net and t.GetLayer()==k.F_Cu and not isinstance(t,k.PCB_VIA)
        and (t.GetStart()==root or t.GetEnd()==root) and abs(k.ToMM(t.GetWidth())-.2)<1e-6
        for t in b.GetTracks())
    checks[f'R93_{pin}_three_force_vias']=sum(isinstance(t,k.PCB_VIA) and str(t.GetNetname())==net
        and pt(t.GetPosition()) in [(x,75.4 if pin==1 else 66.6) for x in (59.1,60,60.9)]
        for t in b.GetTracks())==3
checks['both_Kelvin_no_pour_rules_present']=all(any(z.GetZoneName()=='KELVIN_'+name+'_NO_POUR'
    and z.GetIsRuleArea() and z.GetDoNotAllowZoneFills() for z in b.Zones()) for name in ('SRP','SRN'))
sw={'CHG_SW1','CHG_SW2','SW_3V3','SW_5V'}
quiet={'PM_I2C_SCL','PM_I2C_SDA','USB_CC1','USB_CC2','BMS_SRP_FILT','BMS_SRN_FILT',
       'BMS_VC1_FILT','BMS_VC2_FILT','NTC_BMS','NTC_CHG'}
def point_segment(p,a,c):
    dx,dy=c[0]-a[0],c[1]-a[1]; denom=dx*dx+dy*dy
    u=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/denom)) if denom else 0
    return math.hypot(p[0]-a[0]-u*dx,p[1]-a[1]-u*dy)
def cross(a,c,p):return (c[0]-a[0])*(p[1]-a[1])-(c[1]-a[1])*(p[0]-a[0])
def distance(a,c,p,q):
    if cross(a,c,p)*cross(a,c,q)<0 and cross(p,q,a)*cross(p,q,c)<0:return 0
    return min(point_segment(p,a,c),point_segment(q,a,c),point_segment(a,p,q),point_segment(c,p,q))
tracks=[t for t in b.GetTracks() if not isinstance(t,k.PCB_VIA)]
overlays=[]
for t in tracks:
    if t.GetNetname() not in sw:continue
    for q in tracks:
        if q.GetNetname() not in quiet:continue
        if distance(pt(t.GetStart()),pt(t.GetEnd()),pt(q.GetStart()),pt(q.GetEnd())) < k.ToMM(t.GetWidth()+q.GetWidth())/2:
            overlays.append({'switch':t.GetNetname(),'quiet':q.GetNetname(),'switch_start':pt(t.GetStart()),
                             'quiet_start':pt(q.GetStart()),'layers':[k.LayerName(t.GetLayer()),k.LayerName(q.GetLayer())]})
checks['no_selected_quiet_trace_projection_over_SW_tracks']=not overlays
lengths={net:round(sum(k.ToMM(t.GetLength()) for t in tracks if t.GetNetname()==net),3) for net in sw|{'BMS_SRP_FILT','BMS_SRN_FILT'}}
report={'preserved_checkpoint':E,'checks':checks,'trace_length_mm_including_branches':lengths,
        'audited_local_route_changes':changed,'unexpected_route_changes':unexpected,
        'quiet_SW_projection_overlaps':overlays,
        'limitations':'Geometrical checks, not impedance/EMC/thermal qualification. Kelvin traces are not length-matched. No powered hardware test.'}
(ROOT/'reports/routing_F_verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
raise SystemExit(0 if all(checks.values()) else 1)
