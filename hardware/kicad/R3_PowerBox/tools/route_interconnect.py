"""Checkpoint D explicit interconnect recipes, never a generic autorouter."""
import subprocess
import pcbnew as k
from route_reva import ROOT,BOARD,pad,point,line,via,join
from continue_routing import move,back
from generate_preliminary_placement import footprint_from_id
C='543b85faf09133c03d7adfbf37dc448e01271e6b'

def pd_local(b):
    # GCT USB4105 drawing: mating/PCB edge is local +Y=3.675 mm.
    # The previous 90-degree anchor faced into the PCB, not out of it.
    move(b,'J7',23.675,33,270)
    move(b,'TP36',63,24,0)
    move(b,'TP35',30.8,43,0)
    back(b,'D4',29.2,33,180)
    for ref,x,y in [('TP31',29.2,31.75),('TP32',29.2,34.75)]:
        old=b.FindFootprintByReference(ref)
        f=footprint_from_id('R3_Power:TestPoint_CC_D0.6mm')
        f.SetReference(ref); f.SetValue(old.GetValue()); f.SetPath(old.GetPath())
        f.SetFPID(k.LIB_ID('R3_Power','TestPoint_CC_D0.6mm'))
        b.Add(f)
        # Resolve the original net before removal: duplicate ref lookup is ambiguous.
        next(iter(f.Pads())).SetNet(next(iter(old.Pads())).GetNet())
        b.Remove(old); f.SetPosition(k.VECTOR2I(k.FromMM(x),k.FromMM(y)))
    for n in (1,2):
        net='USB_CC'+str(n)
        jp='A5' if n==1 else 'B5'
        up=(1,2) if n==1 else (4,5)
        y=31.75 if n==1 else 34.75
        end=point(pad(b,'U10',up[0] if n==1 else up[1]))
        path=[point(pad(b,'J7',jp)),(29.4,y)]
        path += [(29.8,34.35),(29.8,33.75)] if n==2 else [(30.2,y)]
        line(b,net,path+[end],.2)
        join(b,('U10',up[0]),('U10',up[1]))
        via(b,net,29.4,y)
        line(b,net,[(29.4,y),point(pad(b,'D4',n))],.2,k.B_Cu)
    via(b,'DGND',29,33)
    line(b,'DGND',[point(pad(b,'D4',3)),(29,33)],.3,k.B_Cu)
    # Autonomous PD supplies: short top fanout, capacitors immediately below.
    for ref,x,y,a in [('C104',34.5,32,0),('C105',36.5,36,0),
                      ('C106',39.5,31,0),('R85',40,28,180)]:
        back(b,ref,x,y,a)
    for pin,ref,vx,vy in [(21,'C104',33.25,29.95),(23,'C105',32.25,29.95),
                           (24,'C106',31.25,29.95)]:
        net=str(pad(b,'U10',pin).GetNetname())
        line(b,net,[point(pad(b,'U10',pin)),(vx,30.4),(vx,vy)],.2)
        via(b,net,vx,vy)
        path={21:[(33.725,31)],
              23:[(32.25,31.2),(32.25,34),(35,35)],
              24:[]}[pin]
        if pin==24:
            line(b,net,[(vx,vy),(vx,30.6),(37.825,30.6),(38.725,30)],.2,k.In2_Cu)
            via(b,net,38.725,30)
            line(b,net,[(38.725,30),point(pad(b,ref,1))],.2,k.B_Cu)
        else:
            line(b,net,[(vx,vy),*path,point(pad(b,ref,1))],.2,k.B_Cu)
    join(b,('R85',2),('C106',1),[(39.6,28.425),(39.6,30.125)],.2,k.B_Cu)
    # RESET and exposed pad share quiet DGND; ground plane stitches at E.
    join(b,('U10',22),('U10',25),[(32.75,32.4)],.2)
    via(b,'DGND',33,33)
    for pin,xy in [(6,(30.2,35.4)),(10,(33.25,36.4)),
                   (12,(34.25,36.4)),(13,(36.4,34.25))]:
        line(b,'DGND',[point(pad(b,'U10',pin)),xy],.2)
        via(b,'DGND',*xy)
    # USB current remains limited by the existing fuse/mux/firmware policy.
    back(b,'C71',49,29,0)
    for pin,xy in [('A4',(28.2,30.6)),('B4',(28.2,35.4))]:
        line(b,'USB_VBUS_RAW',[point(pad(b,'J7',pin)),xy],.5)
        via(b,'USB_VBUS_RAW',*xy)
    line(b,'USB_VBUS_RAW',[(28.2,30.6),(28,30.8),(28,35.4)],.7,k.In2_Cu)
    line(b,'USB_VBUS_RAW',[(28,30.8),(29.2,29.6),(29.2,20.95),(40.775,20.95),(40.775,25.175)],.7,k.In2_Cu)
    via(b,'USB_VBUS_RAW',40.775,25.175)
    line(b,'USB_VBUS_RAW',[(28.2,35.4),(28,35.4)],.7,k.In2_Cu)
    line(b,'USB_VBUS_RAW',[(40.775,25.175),point(pad(b,'F2',1))],1)
    line(b,'USB_VBUS_PROT',[point(pad(b,'F2',2)),(47.525,24),
                          (47.525,27),(53.15,27),point(pad(b,'D3',2))],.9)
    via(b,'USB_VBUS_PROT',47.525,27)
    line(b,'USB_VBUS_PROT',[(47.525,27),point(pad(b,'C71',1)),
                          (47.525,32.8),(47.2,33.35)],.7,k.B_Cu)
    via(b,'USB_VBUS_PROT',47.2,33.35)
    line(b,'USB_VBUS_PROT',[(47.2,33.35),point(pad(b,'U7',7))],.5)
    line(b,'USB_VBUS_PROT',[(47.525,27),(47.525,26),(42.5,26),(42.5,27),point(pad(b,'R85',1))],.2,k.B_Cu)
    via(b,'USB_VBUS_PROT',36.7,31.5)
    line(b,'USB_VBUS_PROT',[point(pad(b,'U10',18)),(36.45,31.75),(36.7,31.5)],.2)
    line(b,'USB_VBUS_PROT',[(36.7,31.5),(37.4,31.75),(38,32.35),
                          (38,36.8),(43.4,36.8),(47.2,33.35)],.2,k.B_Cu)

def clean_connectors(b):
    # Odd J13 rail contacts fan out away from its even ground column.
    line(b,'+5V_ISO_RAW',[point(pad(b,'U3',6)),(127.6,29),(133,23.6),
                          (150,23.6),point(pad(b,'J13',1))],.6,k.B_Cu)
    line(b,'+5V_ISO_RAW',[point(pad(b,'J13',1)),(154,22.3),(160,22.3),
                          (164,26.3),(164,81),point(pad(b,'J3',1))],.8,k.B_Cu)
    via(b,'+3V3_A_ISO',140.8,39.8)
    line(b,'+3V3_A_ISO',[point(pad(b,'C42',1)),(141.45,40.45),(140.8,39.8)],.4)
    line(b,'+3V3_A_ISO',[(140.8,39.8),(140.8,30),(144.26,26.54),(151,26.54),point(pad(b,'J13',3))],.6,k.In2_Cu)
    line(b,'+3V3_A_ISO',[point(pad(b,'J13',3)),(151,26.54),(151,36.5),
                         (160,45.5),(160,75),point(pad(b,'J3',3))],.6,k.In2_Cu)
    line(b,'+3V3_D_ISO',[point(pad(b,'J13',5)),(152,29.08),(152,36),
                         (161,45),(161,69),point(pad(b,'J3',5))],.6)
    line(b,'+3V3_D_ISO',[point(pad(b,'C51',1)),(148.225,63.5),(158,63.5),
                         (161,66.5),(161,69)],.6)
    line(b,'+3V3_D_ISO',[(161,45),(168,45),(169.125,43.875),point(pad(b,'J6',1))],.3)
    via(b,'+3V3_A_ISO',171.8,42.625)
    via(b,'+3V3_A_ISO',160,45.5)
    line(b,'+3V3_A_ISO',[(160,45.5),(163,42.5),(171.8,42.625)],.4,k.In1_Cu)
    line(b,'+3V3_A_ISO',[(171.8,42.625),point(pad(b,'J6',2))],.3)
    line(b,'+5V_INA',[point(pad(b,'J13',7)),(152.5,31.62),(152.5,35),(162,44.5),
                     (162,63),point(pad(b,'J3',7))],.6,k.In2_Cu)
    via(b,'+5V_INA',131,77.5)
    line(b,'+5V_INA',[point(pad(b,'C60',1)),(131,77.5)],.6)
    line(b,'+5V_INA',[(131,77.5),(142,77.5)],.6)
    via(b,'+5V_INA',142,77.5)
    line(b,'+5V_INA',[(142,77.5),(156,63.5),(162,63.5),(162,63)],.6,k.B_Cu)
    via(b,'+5V_INA',162,63)
    line(b,'-5V_INA',[point(pad(b,'J13',9)),(154,36),(163,45),(163,57)],.6,k.B_Cu)
    via(b,'-5V_INA',163,57)
    line(b,'-5V_INA',[(163,57),(167,57),(169.5,59.5),(172.5,59.5),point(pad(b,'J3',9))],.6,k.In2_Cu)
    line(b,'-5V_INA',[point(pad(b,'C62',2)),(136,86)],.6)
    via(b,'-5V_INA',136,86)
    line(b,'-5V_INA',[(136,86),(138.2,86),(139,84),(148,84),(159,73),(163,69),(163,57)],.6,k.B_Cu)
    # Isolated service TPs stay on the isolated edge, with no DGND copper.
    line(b,'+5V_ISO_RAW',[(164,81),(164,85),(147,85)],.6,k.B_Cu)
    via(b,'+5V_ISO_RAW',147,85)
    line(b,'+5V_ISO_RAW',[(147,85),point(pad(b,'TP7',1))],.6)
    line(b,'+3V3_A_ISO',[(160,75),(160,91),(143,91),point(pad(b,'TP11',1))],.6,k.In2_Cu)
    line(b,'+3V3_D_ISO',[(161,69),(161,92),(148,92),point(pad(b,'TP12',1))],.6)
    line(b,'+5V_INA',[(142,77.5),(145,80.5),(145,88.9)],.6,k.In2_Cu)
    via(b,'+5V_INA',145,88.9)
    line(b,'+5V_INA',[(145,88.9),(145,90),point(pad(b,'TP13',1))],.6,k.B_Cu)
    line(b,'-5V_INA',[(163,69),(163,83)],.6,k.B_Cu)
    for y in (83,87): via(b,'-5V_INA',163,y)
    line(b,'-5V_INA',[(163,83),(163,87)],.6)
    line(b,'-5V_INA',[(163,87),(163,91.5),point(pad(b,'TP14',1))],.6,k.B_Cu)
    line(b,'+5V_ISO_A',[(140,50.2),(140,90),(148,90),point(pad(b,'TP8',1))],.6,k.In2_Cu)
    line(b,'+5V_ISO_D',[(142.8,68.7),(146,72),(146,86),(151,86),point(pad(b,'TP9',1))],.6,k.In2_Cu)

def mux_local(b):
    back(b,'R73',45,28.2,270)
    back(b,'C72',42.5,29.7,180)
    for n,ref,xy in [(10,'R73',(45.25,30.5)),(11,'C72',(44.25,30.5))]:
        net=str(pad(b,'U7',n).GetNetname())
        line(b,net,[point(pad(b,'U7',n)),(point(pad(b,'U7',n))[0],31.25),xy],.2)
        via(b,net,*xy)
        line(b,net,[xy,point(pad(b,ref,1))],.2,k.B_Cu)
    join(b,('U7',1),('U7',8),width=.5)
    line(b,'CHARGER_IN',[point(pad(b,'U7',8)),(46.2,32.65),(46.65,32.2),(46.65,32)],.5)
    via(b,'CHARGER_IN',46.65,32)
    line(b,'CHARGER_IN',[(46.65,32),(48.3,32),(48.3,38.9),(42.525,38.9)],.8,k.In1_Cu)
    line(b,'CHARGER_IN',[point(pad(b,'C73',1)),(42.525,38.9)],.8)
    via(b,'CHARGER_IN',42.525,38.9)
    line(b,'CHARGER_IN',[(42.525,38.9),(33.5,38.9),(33.5,50.875),(35.9,50.875)],1.2,k.B_Cu)
    via(b,'CHARGER_IN',35.9,50.875)
    line(b,'CHARGER_IN',[(35.9,50.875),point(pad(b,'C103',1))],1.2)
    for n in (3,4,5): join(b,('U7',n),('U7',n+1),width=.3)
    for pin,xy in [(3,(44.8,34.5)),(6,(46.9,34.5)),(12,(43,31.85))]:
        middle=[(45.75,34.5)] if pin==6 else []
        line(b,'DGND',[point(pad(b,'U7',pin)),*middle,xy],.2)
        via(b,'DGND',*xy)

def system_power(b):
    # Fuse is part of the SYS/Q4 loop, not an input-edge component.
    # Its old y=24 placement forced a long high-current detour past the bucks.
    move(b,'F3',70,61.5,0)
    move(b,'TP22',69,54.3,0)
    move(b,'TP23',75,58,0)
    move(b,'D1',54,60.3,0)
    move(b,'FB1',58,65,0)
    for x in (68,69,70): via(b,'VSYS_RAW',x,46.2)
    line(b,'VSYS_RAW',[(68,46.2),(70,46.2)],1.5,k.In2_Cu)
    line(b,'VSYS_RAW',[(69,46.2),point(pad(b,'TP22',1))],1.2,k.In2_Cu)
    line(b,'VSYS_RAW',[point(pad(b,'TP22',1)),(67.775,56.225),point(pad(b,'F3',1))],1.2)
    line(b,'VSYS_PROT',[point(pad(b,'F3',2)),(72.225,62.4),(70.225,64.4),point(pad(b,'C107',1))],1.2)
    via(b,'VSYS_PROT',73.8,61.5)
    line(b,'VSYS_PROT',[point(pad(b,'F3',2)),(73.8,61.5)],.3)
    line(b,'VSYS_PROT',[(73.8,61.5),point(pad(b,'TP23',1))],.3,k.B_Cu)
    for x in (68.35,69.35):
        via(b,'VSYS_PROT',x,66.5)
        line(b,'VSYS_PROT',[(x,66.5),(69.35,68.095),(69.35,70.635)],.8)
    line(b,'VSYS_PROT',[(68.35,66.5),(69.35,66.5)],1.2,k.In2_Cu)
    join(b,('C107',1),('R102',1),[(70.225,63.5),(66.175,63.5)],.3)
    line(b,'VSYS_PROT',[point(pad(b,'C107',1)),(69.35,66.5)],.5)
    line(b,'SYS_LOAD_GATE',[point(pad(b,'Q4',1)),(67.8,71.7),(66.7,70.6),(66.7,66.125),point(pad(b,'R102',2))],.2)
    for xy in [(67.8,71.7),(73.3,65),(83.175,63.9)]:via(b,'SYS_LOAD_GATE',*xy)
    line(b,'SYS_LOAD_GATE',[point(pad(b,'Q4',1)),(67.8,71.7)],.2)
    line(b,'SYS_LOAD_GATE',[point(pad(b,'C107',2)),(73.3,65)],.2)
    line(b,'SYS_LOAD_GATE',[point(pad(b,'R103',1)),(83.175,63.9)],.2)
    line(b,'SYS_LOAD_GATE',[(67.8,71.7),(68.2,72.1),(82.5,72.1),(82.5,64.575),(83.175,63.9)],.2,k.B_Cu)
    line(b,'SYS_LOAD_GATE',[(73.3,65),(73.3,62.3),(81.575,62.3),(83.175,63.9)],.2,k.In2_Cu)
    join(b,('R103',2),('SW1',1),width=.2)
    line(b,'VSYS_MAIN',[(74.65,68.095),(74.65,71.905)],.8)
    line(b,'VSYS_MAIN',[(74.65,68.095),(77.525,68.095),point(pad(b,'C108',1))],1.2)
    line(b,'VSYS_MAIN',[(74.65,69.365),point(pad(b,'TP40',1))],1.2)
    for x in (76.5,77.525):
        via(b,'VSYS_MAIN',x,64.6)
        line(b,'VSYS_MAIN',[point(pad(b,'C108',1)),(x,64.6)],.8)
    line(b,'VSYS_MAIN',[(76.5,64.6),(77.525,64.6),(77.525,48.5),(71.2,48.5),(71.2,43.5),(71.5,43.5)],1.2,k.B_Cu)
    line(b,'VSYS_MAIN',[(76.5,64.6),(77.525,64.6),(80.625,67.7),(90,67.7),(98,59.7),(98,50.5),(96.225,49.5)],1.2,k.In2_Cu)

def service_power(b):
    # Keep the fixed service MOSFET and fuse; do not disturb A battery copper.
    # The mux input bypass pair sits locally below U7.
    back(b,'C3',47.5,38,0); back(b,'C4',46,40,0)
    move(b,'U11',38,89,0); move(b,'R1',25,89,0)
    line(b,'SERVICE_IN_RAW',[point(pad(b,'J1',1)),(28.5,55),(28.5,65.5),
                           (39,65.5),point(pad(b,'F1',1))],1)
    line(b,'SERVICE_IN_FUSED',[point(pad(b,'F1',2)),(56.6,74),(56.6,84.4),(54,87),(33.5,87),(33.5,85)],1,k.In1_Cu)
    via(b,'SERVICE_IN_FUSED',33.5,85)
    line(b,'SERVICE_IN_FUSED',[(33.5,85),(31.65,85),(31.65,83.095),(31.65,86.905)],.8)
    line(b,'SERVICE_IN_REV',[(26.35,83.095),(26.35,85.635),(24.8,84.365)],.8)
    via(b,'SERVICE_IN_REV',24.8,84.365)
    line(b,'SERVICE_IN_REV',[(24.8,84.365),(21.3,80.865),(21.3,64),
                           (23.3,66),(31.3,66),(31.3,62)],1.2,k.In1_Cu)
    via(b,'SERVICE_IN_REV',31.3,62)
    line(b,'SERVICE_IN_REV',[(31.3,62),point(pad(b,'C1',1))],.8)
    line(b,'SERVICE_IN_REV',[(31.3,62),(39,59),(58,59),(58,61.8)],1.2,k.In1_Cu)
    via(b,'SERVICE_IN_REV',58,61.8)
    line(b,'SERVICE_IN_REV',[(58,61.8),point(pad(b,'D1',2)),point(pad(b,'FB1',1))],.8)
    via(b,'SERVICE_IN_REV',42,60)
    line(b,'SERVICE_IN_REV',[(42,60),point(pad(b,'C2',1))],.3)
    line(b,'SERVICE_IN_REV',[(42,60),(42,59)],.4,k.In1_Cu)
    join(b,('Q1',1),('R1',1),[(24,86.905),(24,89)],.2)
    via(b,'SERVICE_IN_PROT',61.5,65)
    line(b,'SERVICE_IN_PROT',[point(pad(b,'FB1',2)),(61.5,65)],.8)
    line(b,'SERVICE_IN_PROT',[(61.5,65),(63.2,63.3),(63.2,53.2),(62.5,52.5),
                             (62.5,38),(60,35.5),(50,35.5)],1,k.In1_Cu)
    via(b,'SERVICE_IN_PROT',50,35.5)
    line(b,'SERVICE_IN_PROT',[(50,35.5),(50,37),(47,40),(44,40),(43.6,39.6),(43.6,33.5)],.8,k.In2_Cu)
    via(b,'SERVICE_IN_PROT',43.6,33.5)
    line(b,'SERVICE_IN_PROT',[(43.6,33.5),point(pad(b,'U7',2))],.4)
    via(b,'SERVICE_IN_PROT',44,40)
    line(b,'SERVICE_IN_PROT',[(44,40),point(pad(b,'C3',1))],.6,k.B_Cu)
    join(b,('C3',1),('C4',1),width=.4,layer=k.B_Cu)
    move(b,'D2',29,89,0)
    join(b,('Q1',1),('D2',1),[(27.35,87.905)],.2)
    via(b,'SERVICE_IN_REV',32.3,90.5)
    line(b,'SERVICE_IN_REV',[(24.8,84.365),(32.3,90.5)],.3,k.In1_Cu)
    line(b,'SERVICE_IN_REV',[(32.3,90.5),point(pad(b,'D2',2))],.3)

def primary_distribution(b):
    back(b,'R72',24,40,0); back(b,'C70',24,42.5,0)
    line(b,'+3V3_D',[(84.05,38),(89,38),(88.7,37.7),(88.7,31),(76.5,31),(75,29.5),point(pad(b,'J2',2))],1)
    join(b,('J2',1),('J2',2),width=1.5)
    line(b,'+3V3_D',[(84.175,31),point(pad(b,'R105',1))],.4)
    join(b,('R105',2),('D6',2),[(85.825,26.8),(82.7875,26.8)],.2)
    for x in (88,89):via(b,'+3V3_D',x,38)
    line(b,'+3V3_D',[(88,38),(88,33),(92,29),(92,27),(101,27),point(pad(b,'J12',1)),point(pad(b,'J12',2))],1,k.In2_Cu)
    line(b,'+3V3_D',[(88,38),(89,38),(88.3,38.7),(88.3,56),(87.5,58),(87.5,74),
                   (85,76.5),(85,96),(55,96),point(pad(b,'J10',1))],.8,k.B_Cu)
    line(b,'+3V3_D',[(85,96),(91,96),point(pad(b,'J11',1))],.8,k.B_Cu)
    line(b,'+3V3_D',[(87.5,74),(101.8,74),(104.5,71.3)],.5,k.B_Cu)
    via(b,'+3V3_D',104.5,71.3)
    line(b,'+3V3_D',[(104.5,71.3),point(pad(b,'J5',1))],.4)
    via(b,'+3V3_D',67.825,38.5)
    line(b,'+3V3_D',[(89,38),(86,35),(68.5,35),(67.825,38.5)],.3,k.B_Cu)
    line(b,'+3V3_D',[(67.825,38.5),point(pad(b,'R80',2))],.3)
    via(b,'+3V3_D',66.825,50.5)
    line(b,'+3V3_D',[(67.825,38.5),(65.5,38.5),(65.5,50.5),(66.825,50.5)],.3,k.In2_Cu)
    line(b,'+3V3_D',[(66.825,50.5),point(pad(b,'R81',2))],.3)
    move(b,'R83',77,33.5,0)
    move(b,'R84',85.5,33.5,0)
    for xy in [(49.825,31.5),(39.6,37.4)]:via(b,'+3V3_D',*xy)
    line(b,'+3V3_D',[(67.825,38.5),(66.5,37.175),(66.5,22),(50,22),(49.825,31.5)],.3,k.In2_Cu)
    line(b,'+3V3_D',[(49.825,31.5),(49.2,30),(46,29.3),(39.6,29.3),(39.6,37.4)],.3,k.In2_Cu)
    line(b,'+3V3_D',[(77.825,31),point(pad(b,'R83',2))],.2)
    line(b,'+3V3_D',[(86.325,31),point(pad(b,'R84',2))],.2)
    for ref,xy in [('R82',(39.6,37.4))]:
        line(b,'+3V3_D',[xy,point(pad(b,ref,2))],.2)

def bms_i2c(b):
    # A's NTC vertical escape blocked both adjacent I2C pads. Rework only
    # its four N$1 objects; Kelvin/force copper and cell filters stay intact.
    old_ntc=pad(b,'R92',1).GetPosition()
    for t in list(b.GetTracks()):
        if str(t.GetNetname())=='N$1' or (str(t.GetNetname())=='NTC_BMS'
                and (t.GetStart()==old_ntc or t.GetEnd()==old_ntc)): b.Remove(t)
    move(b,'R92',65.5,82,0)
    line(b,'NTC_BMS',[(62.175,80),(62.175,80.8),(64.725,81.3),point(pad(b,'R92',1))],.2,k.B_Cu)
    # 0.15 mm is needed only in this three-pin QFN escape throat.
    line(b,'N$1',[point(pad(b,'U9',4)),(63.32,77.1),(63.32,78.8),(63.45,80.1)],.15)
    via(b,'N$1',63.45,80.1)
    line(b,'N$1',[(63.45,80.1),(63.95,80.6),(66.275,80.6),point(pad(b,'R92',2))],.2,k.B_Cu)
    for pin,xy,way in [(5,(64.8,79.6),[(63.615,77.5),(63.615,78.9)]),
                       (6,(66,79.1),[(64.15,78.6)])]:
        net=str(pad(b,'U9',pin).GetNetname())
        line(b,net,[point(pad(b,'U9',pin)),*way,xy],.15 if pin==5 else .2)
        via(b,net,*xy)
    line(b,'PM_I2C_SCL',[(64.8,79.6),(64.8,80.5),(67.5,81.8),(67.5,88.5),(61,88.5),point(pad(b,'J10',3))],.2)
    line(b,'PM_I2C_SDA',[(66,79.1),(66.5,79.6),(66.5,80.2),(68.3,81.8),(68.3,89.3),(64,89.3),point(pad(b,'J10',4))],.2)
    join(b,('J10',3),('J11',7),[(61,97),(109,97)],.2)
    join(b,('J10',4),('J11',8),[(64,97),(112,97)],.2,k.In1_Cu)
    line(b,'PM_I2C_SCL',[point(pad(b,'J12',5)),(104.5,33.08),(104.5,31.8),
                       (110.5,31.8),(118.71,33.8),(118.71,41.4),(119.9,42.59),
                       (119.9,71),(118.71,72),(118.71,85),(110,85),(109,86),point(pad(b,'J11',7))],.2,k.In2_Cu)
    line(b,'PM_I2C_SDA',[point(pad(b,'J12',6)),(111,33.08),(118.71,34.8),
                       (118.71,41.4),(119.9,42.59),(119.9,71),(118.71,72),
                       (118.71,84.2),(113,84.2),(112,85.2),point(pad(b,'J11',8))],.2,k.B_Cu)

def charger_i2c(b):
    # Remove only the redundant bottom GND escape, joining the same GND
    # pin to the main ground land inside U8 instead (DRC checks pad geometry).
    old=k.VECTOR2I(k.FromMM(51.2),k.FromMM(54.8))
    for t in list(b.GetTracks()):
        if str(t.GetNetname())=='DGND' and (t.GetStart()==old or t.GetEnd()==old):b.Remove(t)
    line(b,'DGND',[point(pad(b,'U8',13)),(51.2,54.2),(51,54.4)],.2)
    via(b,'DGND',51,54.4)
    line(b,'PM_I2C_SCL',[point(pad(b,'U8',14)),(51.65,53.7),(51.75,53.8),(51.75,55.1)],.2)
    line(b,'PM_I2C_SDA',[point(pad(b,'U8',15)),(52,53.55),(52.4,53.95),(52.4,55.9),(51.85,56.45),(51.85,57.8)],.2)
    for net,xy in [('PM_I2C_SCL',(51.75,55.1)),('PM_I2C_SDA',(51.85,57.8)),
                   ('PM_I2C_SCL',(62,57)),('PM_I2C_SDA',(61,57.8)),
                   ('PM_I2C_SCL',(72,56.9)),('PM_I2C_SDA',(73,56.2)),
                   ('PM_I2C_SCL',(76.5,80.5)),('PM_I2C_SDA',(77.5,80.5))]:via(b,net,*xy)
    line(b,'PM_I2C_SCL',[(51.75,55.1),(58,55.1),(61.1,57),(62,57)],.2,k.In1_Cu)
    line(b,'PM_I2C_SDA',[(51.85,57.8),(51.85,58.15),(54,58.15),(54.3,57.85),(61,57.85),(61,57.8)],.2,k.In1_Cu)
    line(b,'PM_I2C_SCL',[(62,57),(64,56.9),(72,56.9)],.2,k.In2_Cu)
    line(b,'PM_I2C_SDA',[(61,57.8),(61,56.2),(73,56.2)],.2,k.In2_Cu)
    line(b,'PM_I2C_SCL',[(72,56.9),(72,58.5),(76.8,63.3),(82,63.3),(82,74),
                       (78,74),(76.5,75.5),(76.5,80.5)],.2)
    line(b,'PM_I2C_SDA',[(73,56.2),(78,56.2),(82.35,60.55),(82.35,74.5),
                       (78.5,74.5),(77.5,75.5),(77.5,80.5)],.2)
    # Short back-layer bridges clear the analogue VSS return without moving it.
    for net,x in [('PM_I2C_SCL',76.5),('PM_I2C_SDA',77.5)]:
        for y in (83.6,86):via(b,net,x,y)
        line(b,net,[(x,80.5),(x,83.6)],.2,k.In2_Cu)
        line(b,net,[(x,83.6),(x,86)],.2,k.B_Cu)
    line(b,'PM_I2C_SCL',[(76.5,86),(76.5,89.5),(61,89.5),point(pad(b,'J10',3))],.2,k.In2_Cu)
    line(b,'PM_I2C_SDA',[(77.5,86),(77.5,90),(64,90),point(pad(b,'J10',4))],.2,k.In2_Cu)

def pd_i2c(b):
    line(b,'PM_I2C_SCL',[point(pad(b,'U10',7)),(31.4,35.5),(31.4,36.1)],.2)
    line(b,'PM_I2C_SDA',[point(pad(b,'U10',8)),(32.25,37)],.2)
    via(b,'PM_I2C_SCL',31.4,36.1);via(b,'PM_I2C_SDA',32.25,37)
    line(b,'PM_I2C_SCL',[(31.4,36.1),(31.4,30.85),(40,30.85),(40,22),(48.6,22),
                       (48.6,29.8),(59.5,29.8),(60.6,30.9),(65.4,30.9),(65.4,25.8),
                       (88,25.8),(96,31),(104.5,31.8),point(pad(b,'J12',5))],.2,k.In1_Cu)
    line(b,'PM_I2C_SDA',[(32.25,37),(32.25,32.4),(38.8,32.4)],.2,k.In2_Cu)
    via(b,'PM_I2C_SDA',38.8,32.4)
    line(b,'PM_I2C_SDA',[(38.8,32.4),(41.4,31.25),(41.4,22.4),(48.2,22.4),
                       (48.2,30.15),(59.3,30.15),(60.4,31.25),(65.8,31.25),(65.8,26.15),(87.8,26.15),(96,31.5),
                       (101.4,32.6)],.2,k.In1_Cu)
    via(b,'PM_I2C_SDA',101.4,32.6)
    line(b,'PM_I2C_SDA',[(101.4,32.6),(101.4,34.5),(108.54,34.5),point(pad(b,'J12',6))],.2,k.B_Cu)
    line(b,'PM_I2C_SCL',[(31.4,36.1),(31.4,38.2),(34,40.8),(34,41),point(pad(b,'TP37',1))],.2,k.In1_Cu)
    line(b,'PM_I2C_SDA',[(62,31.25),point(pad(b,'TP38',1))],.2,k.In1_Cu)

def i2c_pullups(b):
    # Move the bus pullups out of the cell/shunt analogue group.
    move(b,'R96',95,60,0);move(b,'R97',101,60,0)
    line(b,'+3V3_D',[(87.5,64),(101.825,64),point(pad(b,'R97',2))],.3,k.B_Cu)
    line(b,'+3V3_D',[(95.825,64),point(pad(b,'R96',2))],.3,k.B_Cu)
    via(b,'PM_I2C_SCL',94.175,58.7);via(b,'PM_I2C_SDA',100.175,58.7)
    via(b,'PM_I2C_SCL',72,54)
    line(b,'PM_I2C_SCL',[(72,56.9),(72,54)],.2)
    line(b,'PM_I2C_SCL',[(72,54),(84,54),(86,58.7),(94.175,58.7)],.2,k.In2_Cu)
    line(b,'PM_I2C_SDA',[(73,56.2),(93,56.2),(95.3,58.5),(100.175,58.5),(100.175,58.7)],.2)
    for ref,xy in [('R96',(94.175,58.7)),('R97',(100.175,58.7))]:
        line(b,str(pad(b,ref,1).GetNetname()),[xy,point(pad(b,ref,1))],.2,k.B_Cu)

def status_trunks(b):
    move(b,'TP15',104,78,0)
    # Consolidate the two capacitor ground stubs outside the control lanes.
    for t in list(b.GetTracks()):
        if str(t.GetNetname())=='DGND' and any(t.GetStart()==k.VECTOR2I(k.FromMM(111),k.FromMM(y)) or
                t.GetEnd()==k.VECTOR2I(k.FromMM(111),k.FromMM(y)) for y in (51,54)):b.Remove(t)
    via(b,'DGND',109,52.5)
    for r in ('C23','C24'):line(b,'DGND',[point(pad(b,r,2)),(109,52.5)],.4)
    # Explicit nested fanout: upper contacts use outer lanes. All lanes stay
    # left of module primary pins and never enter the isolation corridor.
    recipes=[(7,113.45,34.35,84.45,70),(8,113.1,35.62,84.1,66.5),
             (9,112.75,36.89,83.75,73),(10,112.4,38.16,83.4,74.5),
             (11,112.05,39.43,83.05,83),(12,111.7,40.7,82.7,84),
             (13,111.35,41.97,82.35,97),(14,111,43.24,82,100)]
    for pn,x,top,bot,left in recipes:
        net=str(pad(b,'J12',pn).GetNetname());p=point(pad(b,'J12',pn))
        way=[(104.5,p[1]),(104.5,top)] if pn%2 else []
        tail=[(left,bot)]
        if pn<13:
            # Stagger the diagonal turns to retain true perpendicular gap.
            sx=91+(12-pn)*.2
            tail=[(sx,bot),(sx-.9,bot+.9),(left,bot+.9)]
        line(b,net,[p,*way,(x,top),(x,bot),*tail],.2,k.In1_Cu)
    for net,xy in [('PG_3V3_D',(70,86.5)),('PG_3V3_D',(106,86)),
        ('CHARGE_STATUS',(66.5,87)),
        ('CHARGER_INT_FAULT',(73,81)),('INPUT_SOURCE_STATUS',(74.5,78)),
        ('PD_ALERT_N',(83,81.5)),('PD_CONTRACT_12V_N',(84,81.5)),
        ('POWER_CTRL',(97,81.1)),('QON_SERVICE',(100,80.8))]:via(b,net,*xy)
    line(b,'PG_3V3_D',[(70,85.35),(70,86.5)],.2,k.In1_Cu)
    line(b,'PG_3V3_D',[(106,84.45),(106,86)],.2,k.In1_Cu)
    line(b,'PG_3V3_D',[(70,86.5),point(pad(b,'J10',6))],.2)
    line(b,'PG_3V3_D',[(106,86),point(pad(b,'J11',6))],.2)
    line(b,'CHARGE_STATUS',[(66.5,85),(66.5,87)],.2,k.In1_Cu)
    line(b,'CHARGE_STATUS',[(66.5,87),(67,88),point(pad(b,'J10',5))],.2,k.B_Cu)
    join(b,('J10',5),('J11',5),[(67,94),(103,94)],.2)
    line(b,'CHARGER_INT_FAULT',[(73,84.65),(73,81)],.2,k.In1_Cu)
    line(b,'CHARGER_INT_FAULT',[(73,81),point(pad(b,'J10',7))],.2)
    line(b,'INPUT_SOURCE_STATUS',[(74.5,84.3),(74.5,78)],.2,k.In1_Cu)
    line(b,'INPUT_SOURCE_STATUS',[(74.5,78),(74.5,85),(76,86.5),point(pad(b,'J10',8))],.2)
    line(b,'PD_ALERT_N',[(83,83.95),(83,81.5)],.2,k.In1_Cu)
    line(b,'PD_ALERT_N',[(83,81.5),(83,89),(79,90.5),point(pad(b,'J10',9))],.2,k.B_Cu)
    line(b,'PD_CONTRACT_12V_N',[(84,83.6),(84,81.5)],.2,k.In1_Cu)
    line(b,'PD_CONTRACT_12V_N',[(84,81.5),(84,90),point(pad(b,'J10',10))],.2,k.B_Cu)
    line(b,'POWER_CTRL',[(97,82.35),(97,81.1)],.2,k.In1_Cu)
    line(b,'QON_SERVICE',[(100,82),(100,80.8)],.2,k.In1_Cu)
    line(b,'POWER_CTRL',[(97,81.1),point(pad(b,'J11',3))],.2)
    line(b,'QON_SERVICE',[(100,80.8),point(pad(b,'J11',4))],.2)
    line(b,'POWER_CTRL',[(97,81.1),(97,76),(95,74),(85.1,74),point(pad(b,'SW1',1))],.2,k.In2_Cu)
    line(b,'QON_SERVICE',[(100,80.8),(100,75),(98,73),(88.6,73)],.2,k.In2_Cu)
    via(b,'QON_SERVICE',88.6,73)
    line(b,'QON_SERVICE',[(88.6,73),(88.6,76.5)],.2)
    line(b,'QON_SERVICE',[(88.6,76.5),(81.4,76.5)],.2,k.In2_Cu)
    via(b,'PG_3V3_D',79.175,36.5)
    line(b,'PG_3V3_D',[point(pad(b,'R10',1)),(79.175,36.5)],.2)
    line(b,'PG_3V3_D',[(79.175,36.5),(79.175,34),(104.5,34),(104.5,34.35)],.2,k.In1_Cu)
    line(b,'PG_3V3_D',[point(pad(b,'J2',5)),(82,26),(80,29),(79.175,34),(79.175,36.5)],.2,k.In2_Cu)
    line(b,'PG_3V3_D',[(79.175,34),(75,34),point(pad(b,'TP4',1))],.2,k.In2_Cu)
    via(b,'PG_3V3_D',99.5,30.5)
    line(b,'PG_3V3_D',[point(pad(b,'J4',2)),(99.5,30.5)],.2)
    line(b,'PG_3V3_D',[(99.5,30.5),(100.5,31.5),(104,32.5),(104,35.62),point(pad(b,'J12',7))],.2,k.In2_Cu)

def pd_alert(b):
    via(b,'PD_ALERT_N',35,29.95)
    line(b,'PD_ALERT_N',[point(pad(b,'U10',19)),(34.75,30.1),(35,29.95)],.2)
    line(b,'PD_ALERT_N',[(35,29.95),(38,29.95),(38,31.8),(42,31.85)],.2,k.B_Cu)
    via(b,'PD_ALERT_N',42,31.85)
    line(b,'PD_ALERT_N',[(42,31.85),(42,22),(63,22),point(pad(b,'TP36',1))],.2)
    line(b,'PD_ALERT_N',[(42,31.85),(42,35.2),(48.8,35.2),(49.2,34.8),(51,34.8),
                       (51.4,35.2),(80,35.2),(84,35.8)],.2)
    via(b,'PD_ALERT_N',84,35.8)
    line(b,'PD_ALERT_N',[point(pad(b,'R83',1)),(76.175,35.2)],.2)
    line(b,'PD_ALERT_N',[(84,35.8),(87,38.8),(98,38.8),(103,40.7),point(pad(b,'J12',11))],.2,k.In1_Cu)

def final_local(b):
    line(b,'USB_SHIELD',[(22.6,28.68),(22.6,37.32)],.3,k.B_Cu)
    line(b,'USB_SHIELD',[(22.6,28.68),(26.78,28.68)],.3,k.B_Cu)
    line(b,'USB_SHIELD',[(22.6,37.32),(26.78,37.32)],.3,k.B_Cu)
    line(b,'USB_SHIELD',[(22.6,37.32),(23.175,40),(23.225,42.5)],.3,k.B_Cu)
    via(b,'POWER_CTRL',85.1,74)
    line(b,'POWER_CTRL',[(85.1,74),point(pad(b,'SW1',1))],.2)
    for x in (81.4,88.6):
        via(b,'QON_SERVICE',x,75.5)
        line(b,'QON_SERVICE',[(x,75.5),(x,76.5)],.2)
        line(b,'QON_SERVICE',[(x,75.5),(x,76.5)],.2,k.In2_Cu)
    line(b,'CTRL_RS3E_PRI',[point(pad(b,'J4',3)),(102.5,26),(110,26),(110,20.7),(119.98,20.7),(119.98,40)],.2,k.B_Cu)
    # POWER_OK3 crosses only quiet input copper, never charger SW copper.
    via(b,'PD_CONTRACT_12V_N',36.2,33.3)
    line(b,'PD_CONTRACT_12V_N',[point(pad(b,'U10',14)),(35.5,33.75),(36.2,33.3)],.2)
    line(b,'PD_CONTRACT_12V_N',[(36.2,33.3),(35.4,34.1),(35.4,38.2),(45.5,38.2),(47.4,36.1)],.2,k.In1_Cu)
    via(b,'PD_CONTRACT_12V_N',47.4,36.1)
    line(b,'PD_CONTRACT_12V_N',[(47.4,36.1),(65,36.1)],.2,k.B_Cu)
    via(b,'PD_CONTRACT_12V_N',65,36.1)
    line(b,'PD_CONTRACT_12V_N',[(65,36.1),(75.5,36.1),(75.5,37.8)],.2,k.In1_Cu)
    via(b,'PD_CONTRACT_12V_N',75.5,37.8)
    line(b,'PD_CONTRACT_12V_N',[(75.5,37.8),(85,37.8),(87,38.8),(98,38.8),(102,42),(108.54,42),(108.54,40.7)],.2,k.In2_Cu)
    via(b,'PD_CONTRACT_12V_N',86,36.6)
    line(b,'PD_CONTRACT_12V_N',[(86,36.6),(85,37.8)],.2,k.In2_Cu)
    line(b,'PD_CONTRACT_12V_N',[(86,36.6),(84.675,34.5),point(pad(b,'R84',1))],.2)

def mux_status(b):
    n='INPUT_SOURCE_STATUS'
    via(b,n,46.1,30.5)
    line(b,n,[point(pad(b,'U7',9)),(46.1,31.2),(46.1,30.5)],.2)
    line(b,n,[(46.1,30.5),(45.8,31.1),(45.8,36.1),(41,36.7),(38,36.7),(37.175,37.5)],.2,k.In1_Cu)
    via(b,n,37.175,37.5)
    line(b,n,[(37.175,37.5),point(pad(b,'R82',1))],.2)
    line(b,n,[(45.8,36.1),(46.1,36.1)],.2,k.In1_Cu)
    via(b,n,46.1,36.1)
    line(b,n,[(46.1,36.1),(46.1,36.7),(65.5,36.7),(65.5,37.3)],.2,k.B_Cu)
    via(b,n,65.5,37.3)
    line(b,n,[(65.5,37.3),(74.8,37.3),(74.8,39),(85,40),(91,43.4),(100,43.4)],.2,k.In1_Cu)
    via(b,n,100,43.4)
    line(b,n,[(100,43.4),(103,39.43),(108.54,39.43),point(pad(b,'J12',10))],.2,k.B_Cu)

def charger_status(b):
    n='CHARGER_INT_FAULT'
    line(b,n,[point(pad(b,'U8',21)),(53.3,50.6),(54.3,50.6),(55.8,49.1),(56,49)],.15)
    via(b,n,56,49)
    line(b,n,[(56,49),(63,49),(64.5,50.9)],.2,k.In2_Cu)
    via(b,n,64.5,50.9)
    line(b,n,[(64.5,50.9),point(pad(b,'R81',1))],.2)
    line(b,n,[(64.5,50.9),(66.5,51.5),(71.5,51.5),(80.5,55),(80.5,76),
               (73.8,76),(73.8,78.6),(74.1,79),(74.1,80.5),(73,81)],.2,k.In1_Cu)
    # Hardware LED and isolated-to-switched-logic diode remain independent.
    join(b,('R104',2),('D5',2),[(55.825,38.5),(59.7875,38.5)],.2)
    join(b,('D5',1),('D7',1),[(58.2125,35.8),(61.95,35.8)],.2)
    join(b,('D7',2),('R80',1),[(65,38.5),(66.175,38.5)],.2)
    n='BQ_STAT_RAW'
    line(b,n,[point(pad(b,'U8',1)),(48.3,49.4),(47.6,49)],.2)
    via(b,n,47.6,49)
    line(b,n,[(47.6,49),(46.4,47.4),(46.4,44.5),(43.5,43.5),(42.8,42),(42.8,40.8),(40.7,40.2)],.2,k.In1_Cu)
    via(b,n,40.7,40.2)
    line(b,n,[(40.7,40.2),(40.7,27)],.2)
    via(b,n,40.7,27);via(b,n,43.5,27)
    line(b,n,[(40.7,27),(43.5,27)],.2,k.In2_Cu)
    line(b,n,[(43.5,27),(46.3,28),(46.3,27.4)],.2)
    via(b,n,46.3,27.4)
    line(b,n,[(46.3,27.4),(46.9,27.8),(47.8,28),(47.8,30.8),(48.7,31.2)],.2,k.In1_Cu)
    via(b,n,48.7,31.2)
    line(b,n,[(48.7,31.2),(48.7,33.5),(52,33.5),(53,34)],.2)
    via(b,n,53,34)
    line(b,n,[(53,34),(53,37.8)],.2,k.In2_Cu)
    via(b,n,53,37.8);via(b,n,57.2,37.8)
    line(b,n,[(53,37.8),(53.5,38.1),(56.5,38.1),(57.2,37.8)],.2,k.B_Cu)
    line(b,n,[(57.2,37.8),point(pad(b,'D5',1))],.2)
    n='CHARGE_STATUS'
    via(b,n,64,39.5)
    line(b,n,[point(pad(b,'R80',1)),(64,39.5)],.2)
    line(b,n,[(64,39.5),(62.8,40),(62.8,48),(66,47.5),(70.1,47.5)],.2,k.B_Cu)
    via(b,n,70.1,47.5)
    line(b,n,[(70.1,47.5),(90,47.5),(104,48)],.2,k.In1_Cu)
    via(b,n,104,48)
    line(b,n,[(104,48),(103.5,47.5),(103.5,37.5),(105.1,37.5),(105.3,36.89),(108.54,36.89),point(pad(b,'J12',8))],.2)
    n='BQ_STAT_RAW'
    via(b,n,61.4,38.5)
    line(b,n,[point(pad(b,'D7',1)),(61.4,38.5)],.2)
    line(b,n,[(61.4,38.5),(62.1,40),(62.1,48.6),(66,48.6),(70.1,49.7)],.2,k.B_Cu)
    via(b,n,70.1,49.7)
    line(b,n,[(70.1,49.7),(88,50.4),(91,50.4),(92,50.1),(97,50.1),(100,49),(106,49)],.2,k.In1_Cu)
    via(b,n,106,49);via(b,n,104,56);via(b,n,104,59);via(b,n,110,89)
    line(b,n,[(106,49),(104,53),(104,56)],.2,k.B_Cu)
    line(b,n,[(104,56),(104,59)],.2,k.In1_Cu)
    line(b,n,[(104,59),(105.5,62),(105.5,72),(107,75),(107,80),(109,82),(110,89)],.2,k.B_Cu)
    line(b,n,[(110,89),point(pad(b,'J11',9))],.2)
    n='CHG_REGN'
    via(b,n,54.5,37.3);via(b,n,60.7,39.5);via(b,n,61.5,48)
    line(b,n,[point(pad(b,'R104',1)),(54.175,37.3),(54.5,37.3)],.2)
    line(b,n,[(54.5,37.3),(55,37.15),(58,37.15),(60.7,39.5)],.2,k.B_Cu)
    line(b,n,[(60.7,39.5),(62.5,40.2),(62.5,47.2),(61.5,48)],.2,k.In2_Cu)
    line(b,n,[(61.5,48),(60.7,53),(63.9,56),(63.9,60),point(pad(b,'R76',1))],.2,k.B_Cu)

def qon_service(b):
    # The original GND pin-10 escape occupied QON's only external throat.
    for t in list(b.GetTracks()):
        if str(t.GetNetname())=='DGND' and (t.GetStart()==k.VECTOR2I(k.FromMM(50),k.FromMM(54.8)) or
            t.GetEnd()==k.VECTOR2I(k.FromMM(50),k.FromMM(54.8))):b.Remove(t)
    via(b,'DGND',49.7,56.8)
    line(b,'DGND',[point(pad(b,'U8',10)),(50,54.5),(49.7,55.2),(49.7,56.8)],.2)
    n='QON_SERVICE'
    line(b,n,[point(pad(b,'U8',12)),(50.8,53.3),(50.35,53.8),(50.35,55.2),(50.6,55.6),(50.6,57)],.15)
    via(b,n,50.6,57)
    line(b,n,[(50.6,57),(50.6,58),(57,64.4),(63.8,64.4)],.2,k.In2_Cu)
    via(b,n,63.8,64.4)
    line(b,n,[(63.8,64.4),(64.3,65.6),(66,66),(70,65.6),(73,63.9),(76,61),(79,61)],.2,k.In1_Cu)
    via(b,n,79,61);via(b,n,86,72.5)
    line(b,n,[(79,61),(83,61),(86,66),(86,72.5)],.2,k.B_Cu)
    line(b,n,[(86,72.5),(88.6,73)],.2,k.In2_Cu)
    move(b,'TP39',94,78,0)
    via(b,n,98,73)
    line(b,n,[(98,73),(94,78)],.2)

def test_access(b):
    for ref,x,y in [('TP6',115.8,53),('TP16',115.8,80),('TP20',28,23)]:move(b,ref,x,y,0)
    line(b,'+5V_PREISO_ADS',[(117.44,40),(116,41.5),(116,53),(115.8,53)],.3,k.In2_Cu)
    line(b,'+5V_PREISO_INA',[(117.44,73),(117.44,76),(115.8,80)],.3,k.B_Cu)
    line(b,'USB_VBUS_RAW',[(29.2,22.5),(28,23)],.3,k.In2_Cu)
    line(b,'+5V_PREISO',[point(pad(b,'TP5',1)),(91,45),(91.5,47),(91.5,50)],.3,k.B_Cu)
    line(b,'USB_VBUS_PROT',[(53.15,27),(55,27),point(pad(b,'TP33',1))],.3)
    n='NTC_CHG'
    line(b,n,[point(pad(b,'J9',1)),(52,22.6),(56,22.6),(56,24),(59,27),(60,29),(60,30.5),(64,30.5),(64,34)],.2)
    via(b,n,64,34);via(b,n,64.5,54)
    line(b,n,[(64,34),(64.6,38),(65.3,40.3),(65.3,42.5),(63.6,43.5),(63.6,49.5),(63.7,50.2),(63.7,52.2),(64.5,54)],.2,k.In1_Cu)
    line(b,n,[(64.5,54),(64.5,54.5),(66.825,54.5),point(pad(b,'R78',2))],.2,k.B_Cu)
    via(b,n,79.5,59)
    line(b,n,[(69.5,57.5),(73,60),(76,60.5),(79.5,59)],.2,k.In1_Cu)
    line(b,n,[(79.5,59),point(pad(b,'TP30',1))],.2,k.In2_Cu)
    n='PD_VDD'
    line(b,n,[(31.25,29.95),(30.2,30.9),(30.2,33.9),(30.6,34.5),(31.2,35.1),(30.8,35.9),
        (30.8,37.5),(31,39)],.2,k.In2_Cu)
    via(b,n,31,39)
    line(b,n,[(31,39),(33.1,40.3),(33.1,46),point(pad(b,'TP34',1))],.2)
    n='PD_VREG_2V7'
    via(b,n,36.2,37.4)
    line(b,n,[point(pad(b,'C105',1)),(36.2,37.4)],.2,k.B_Cu)
    line(b,n,[(36.2,37.4),(34.5,38),(34.5,41),point(pad(b,'TP35',1))],.2,k.In2_Cu)
    for ref,x,y in [('TP27',61,78.8),('TP28',62.8,75.7)]:
        old=b.FindFootprintByReference(ref)
        f=footprint_from_id('TestPoint:TestPoint_Pad_D1.0mm')
        f.SetReference(ref);f.SetValue(old.GetValue());f.SetPath(old.GetPath())
        b.Add(f);next(iter(f.Pads())).SetNet(next(iter(old.Pads())).GetNet());b.Remove(old)
        f.SetPosition(k.VECTOR2I(k.FromMM(x),k.FromMM(y)));f.Flip(f.GetPosition(),True)
    line(b,'BMS_SRP_FILT',[(61,79.3),(61,78.8)],.2,k.B_Cu)
    line(b,'BMS_SRN_FILT',[(62.8,76.725),(62.8,75.7)],.2,k.B_Cu)
    line(b,'CHARGER_IN',[(48.3,33),(51,33),(55,32),point(pad(b,'TP21',1))],.3,k.In1_Cu)
    via(b,'BAT_POS_RAW',41,88.5)
    line(b,'BAT_POS_RAW',[point(pad(b,'TP24',1)),(41,80),(41,88.5)],.3,k.In2_Cu)
    line(b,'SERVICE_IN_PROT',[point(pad(b,'TP2',1)),(42.5,53),(42.5,50.5),(43,49.5),(43,44),(42.5,42),(42.5,40),(43.6,39.6)],.3,k.In2_Cu)

def main():
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()!=C:
        raise RuntimeError('D recipe requires C HEAD')
    src=ROOT/'tmp'/'stage_D_start.kicad_pcb'
    if not src.exists(): src.write_bytes(subprocess.check_output(['git','show',C+
        ':hardware/kicad/R3_PowerBox/R3_power.kicad_pcb'],cwd=ROOT))
    b=k.LoadBoard(str(src)); clean_connectors(b); pd_local(b); mux_local(b); system_power(b); service_power(b); primary_distribution(b); bms_i2c(b); charger_i2c(b); pd_i2c(b); i2c_pullups(b); status_trunks(b); pd_alert(b); final_local(b); mux_status(b); charger_status(b); qon_service(b); test_access(b)
    for f in b.GetFootprints():
        if f.GetReference().startswith('H'):
            for z in f.Zones(): z.SetZoneName('M3_'+f.GetReference())
    b.GetDesignSettings().m_TrackMinWidth=k.FromMM(.13)
    k.SaveBoard(str(BOARD),b); print('C retained; D objects:',len(b.GetTracks()))

if __name__=='__main__': main()
