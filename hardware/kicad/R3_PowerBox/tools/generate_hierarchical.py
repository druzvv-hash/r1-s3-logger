"""Generate a readable hierarchical KiCad 10 schematic for R3 PowerBox."""

import builtins
import json
from pathlib import Path

from skidl import KICAD10, Net, Part, generate_schematic, lib_search_paths, set_default_tool, subcircuit
from skidl.schematics import place
from skidl.tools.kicad10 import gen_schematic, sexp_schematic

ROOT = Path(__file__).resolve().parent.parent
set_default_tool(KICAD10)
lib_search_paths[KICAD10].insert(0, str(ROOT / "libraries"))
sexp_schematic._round_mm.__defaults__ = (3,)

# Give switchers and their external parts enough drawing room. SKiDL's compact
# defaults are useful for logic, but crowd power symbols with many named pins.
_add_placement_bboxes = place.add_placement_bboxes


def _roomy_bboxes(parts, **options):
    options["expansion_factor"] = max(2.5, options.get("expansion_factor", 1.0))
    return _add_placement_bboxes(parts, **options)


place.add_placement_bboxes = _roomy_bboxes
place.LABEL_REACH = 450.0
place.LABEL_BODY_MARGIN = 90.0
gen_schematic._snap_two_pin_parts = lambda node: None


def comp(symbol, ref, value, footprint="", datasheet=""):
    p = Part("R3_POWER_GEN", symbol, ref=ref, value=value, footprint=footprint, tool=KICAD10)
    if datasheet:
        p.datasheet = datasheet
    return p


def stdcomp(library, symbol, ref, value=None, footprint="", datasheet=""):
    """Instantiate a verified KiCad standard-library symbol."""
    p = Part(library, symbol, ref=ref, tool=KICAD10)
    if value:
        p.value = value
    if footprint:
        p.footprint = footprint
    if datasheet:
        p.datasheet = datasheet
    return p


def across(p, a, b):
    a += p[1]
    b += p[2]


def r(ref, value, a, b):
    p = comp("R", ref, value, "Resistor_SMD:R_0603_1608Metric")
    across(p, a, b)
    return p


def c(ref, value, a, b, fp="Capacitor_SMD:C_0603_1608Metric"):
    p = comp("C", ref, value, fp)
    across(p, a, b)
    return p


def tp(ref, net):
    fp = ("R3_Power:TestPoint_CC_D0.6mm" if ref in ("TP31", "TP32") else
          "TestPoint:TestPoint_Pad_D1.0mm" if ref in ("TP27", "TP28") else
          "TestPoint:TestPoint_Plated_Hole_D2.0mm")
    p = comp("TP", ref, net.name, fp)
    net += p[1]


def power_flag(net, ref):
    p = Part("power", "PWR_FLAG", ref=ref, tool=KICAD10)
    net += p[1]


@subcircuit
def input_protection(service_raw, service_prot, dgnd):
    vin_fused, vin_rev, qgate = Net("SERVICE_IN_FUSED"), Net("SERVICE_IN_REV"), Net("Q1_GATE")
    j1 = comp("CONN2", "J1", "SERVICE / BENCH INPUT 6-12V", "Connector_Molex:Molex_Micro-Fit_3.0_43650-0200_1x02_P3.00mm_Horizontal")
    service_raw += j1[1]
    dgnd += j1[2]
    f1 = comp("FUSE", "F1", "MF-R250-0-10 2.5A/30V PPTC", "R3_Power:Fuse_PTC_MF-R250", "https://www.bourns.com/docs/product-datasheets/mf-r.pdf")
    f1.datasheet = "https://www.bourns.com/docs/product-datasheets/mf-r.pdf"
    service_raw += f1[1]
    vin_fused += f1[2]
    # DMP3010LSS is not a valid P-channel choice (the similarly named
    # DMN3010LSS is N-channel). Use the verified 30 V P-channel DMP3007LSS
    # and the project footprint that maps its physical 1-3=S, 4=G, 5-8=D
    # pins onto the three-pin logical PMOS symbol.
    q1 = comp("PMOS", "Q1", "DMP3007LSS-13", "R3_Power:DMP3007LSS_SO8_LOGICAL", "https://www.diodes.com/part/view/DMP3007LSS")
    vin_fused += q1["D"]
    vin_rev += q1["S"]
    qgate += q1["G"]
    r("R1", "100k", qgate, dgnd)
    d2 = comp("DIODE", "D2", "BZT52C10", "Diode_SMD:D_SOD-123")
    qgate += d2["A"]
    vin_rev += d2["K"]
    d1 = comp("DIODE", "D1", "SMBJ13A / 13V VRWM", "Diode_SMD:D_SMB")
    d1.datasheet = "https://www.bourns.com/data/global/pdfs/SMBJ.pdf"
    dgnd += d1["A"]
    vin_rev += d1["K"]
    c("C1", "47uF/25V low-ESR", vin_rev, dgnd, "Capacitor_SMD:CP_Elec_6.3x5.8")
    c("C2", "100nF/25V", vin_rev, dgnd)
    fb = comp("FERRITE", "FB1", "BLM31KN121SN1L / 6A", "Inductor_SMD:L_1206_3216Metric_Pad1.22x1.90mm_HandSolder")
    vin_rev += fb[1]
    service_prot += fb[2]
    c("C3", "22uF/25V", service_prot, dgnd, "Capacitor_SMD:C_1206_3216Metric")
    c("C4", "100nF/25V", service_prot, dgnd)
    tp("TP1", service_raw)
    tp("TP2", service_prot)


@subcircuit
def battery_management(pack_pos, bat_pos, cell_mid, bat_neg, ntc_bms, ntc_chg,
                       pm_scl, pm_sda, v3d, dgnd):
    """2S cell interface, gauge/protection, balancing and Kelvin shunt."""
    j8 = comp("CONN4", "J8", "2S BATTERY / KEYED / NTC_BMS=103AT-2", "Connector_Molex:Molex_Micro-Fit_3.0_43650-0400_1x04_P3.00mm_Horizontal")
    bat_pos += j8[1]
    cell_mid += j8[2]
    bat_neg += j8[3]
    ntc_bms += j8[4]
    j9 = comp("CONN2", "J9", "NTC_CHG=103AT-2 / QUIET DGND RETURN", "Connector_Molex:Molex_Micro-Fit_3.0_43650-0200_1x02_P3.00mm_Horizontal")
    ntc_chg += j9[1]
    dgnd += j9[2]

    u = comp("BQ28Z610", "U9", "BQ28Z610DRZR", "R3_Power:Texas_DRZ0012A_VSON-12", "https://www.ti.com/lit/ds/symlink/bq28z610.pdf")
    bat_neg += u["VSS", "EP"]
    pack_pos += u["PACK"]
    pm_scl += u["SCL"]
    pm_sda += u["SDA"]
    # TI BQ28Z610 typical 2S connection: VC2 is the most-positive cell input,
    # VC1 is the least-positive cell input, and VSS is the stack negative.
    # Therefore Cell1 is VC1-VSS and Cell2 is VC2-VC1.
    vc1_f, vc2_f = Net("BMS_VC1_FILT"), Net("BMS_VC2_FILT")
    r("R90", "100R VC2 / KELVIN", bat_pos, vc2_f)
    vc2_f += u["VC2"]
    r("R91", "100R VC1 / KELVIN", cell_mid, vc1_f)
    vc1_f += u["VC1"]
    c("C97", "100nF VC2-VC1 / CELL2", vc2_f, vc1_f)
    c("C98", "100nF VC1-VSS / CELL1", vc1_f, bat_neg)
    r("R92", "100R TS", ntc_bms, u["TS1"])
    pbi = Net("BMS_PBI")
    pbi += u["PBI"]
    c("C93", "2.2uF PBI", pbi, bat_neg)
    power_flag(bat_neg, "#FLG0601")
    power_flag(vc1_f, "#FLG0602")
    power_flag(pbi, "#FLG0603")
    power_flag(vc2_f, "#FLG0604")

    # TI BQ28Z610EVM Figure 20 high-side pair: PACK+ -> DSG FET -> common
    # drains -> CHG FET -> BAT+. Gate-drive references are the local sources.
    # Preliminary selection: TI CSD17577Q3AT, 30 V, 13 nC typical Qg and
    # 4.8 mOhm maximum RDS(on) at the BQ28Z610's approximately 9.5 V drive.
    # Project footprint maps the physical DQG pins onto this 3-pin symbol.
    fet_common = Net("BMS_FET_COMMON")
    q2 = comp("NMOS_POWER", "Q2", "CSD17577Q3AT 30V NMOS DSG", "R3_Power:CSD17577Q3A_VSON-8_3.3x3.3mm", "https://www.ti.com/lit/ds/symlink/csd17577q3a.pdf")
    q3 = comp("NMOS_POWER", "Q3", "CSD17577Q3AT 30V NMOS CHG", "R3_Power:CSD17577Q3A_VSON-8_3.3x3.3mm", "https://www.ti.com/lit/ds/symlink/csd17577q3a.pdf")
    pack_pos += q2["S"]
    fet_common += q2["D"], q3["D"]
    bat_pos += q3["S"]
    dsg_gate, chg_gate = Net("BMS_DSG_GATE"), Net("BMS_CHG_GATE")
    dsg_gate += q2["G"]
    chg_gate += q3["G"]
    r("R98", "5.1k DSG GATE / TI EVM", u["DSG"], dsg_gate)
    r("R99", "10M DSG G-S / TI EVM", dsg_gate, pack_pos)
    r("R100", "5.1k CHG GATE / TI EVM", u["CHG"], chg_gate)
    r("R101", "10M CHG G-S / TI EVM", chg_gate, bat_pos)
    c("C95", "100nF DSG D-S / TI EVM", pack_pos, fet_common)
    c("C96", "100nF CHG D-S / TI EVM", fet_common, bat_pos)

    # 10 mOhm, 1 W Kelvin shunt: 0.25 W at 5 A, 0.11 W at the 3.3 A
    # design-worst system current. SRP/SRN filter traces are Kelvin routed.
    shunt = comp("R", "R93", "WSL2512R0100FEA 10mR 1W", "Resistor_SMD:R_2512_6332Metric_Pad1.40x3.35mm_HandSolder")
    bat_neg += shunt[1]
    dgnd += shunt[2]
    srp_f, srn_f = Net("BMS_SRP_FILT"), Net("BMS_SRN_FILT")
    r("R94", "100R KELVIN", bat_neg, srp_f)
    r("R95", "100R KELVIN", dgnd, srn_f)
    srp_f += u["SRP"]
    srn_f += u["SRN"]
    c("C94", "100nF SHUNT DIFF", srp_f, srn_f)
    r("R96", "4.7k I2C", pm_scl, v3d)
    r("R97", "4.7k I2C", pm_sda, v3d)

    # FOOTPRINT-SPACE RESERVATION ONLY. This unconnected DNP land pattern is
    # not a functional secondary-OV circuit and must never be populated as-is.
    u11 = stdcomp(
        "Connector_Generic", "Conn_01x07", "U11",
        "BQ294502 SPACE ONLY / NC / DNP",
        "Package_SON:WSON-6-1EP_2x2mm_P0.65mm_EP1x1.6mm",
        "https://www.ti.com/lit/ds/symlink/bq2945.pdf",
    )
    u11.dnp = True
    u11.circuit.NC += u11[1, 2, 3, 4, 5, 6, 7]

    tp("TP24", bat_pos)
    tp("TP25", cell_mid)
    tp("TP26", bat_neg)
    tp("TP27", srp_f)
    tp("TP28", srn_f)
    tp("TP29", ntc_bms)
    tp("TP30", ntc_chg)


@subcircuit
def charger_powerpath(service_prot, pack_pos, ntc_chg, pm_scl, pm_sda,
                      charge_stat, charger_fault, input_status, pd_alert,
                      pd_contract, qon_service, bq_stat_raw, charge_led_a,
                      vsys_raw, vsys_prot, v3d, dgnd):
    """Autonomous USB-C PD sink, protected input mux and 2S NVDC charger."""
    usb_raw, usb_prot, charger_in = Net("USB_VBUS_RAW"), Net("USB_VBUS_PROT"), Net("CHARGER_IN")
    cc1, cc2, shield = Net("USB_CC1"), Net("USB_CC2"), Net("USB_SHIELD")
    j7 = comp("USB_C_PWR", "J7", "USB4105-GF-A", "Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal")
    usb_raw += j7["VBUS"]
    dgnd += j7["GND"]
    cc1 += j7["CC1"]
    cc2 += j7["CC2"]
    shield += j7["SHIELD"]
    j7.circuit.NC += j7["D+", "D-", "SBU1", "SBU2"]
    r("R72", "1M SHIELD", shield, dgnd)
    c("C70", "4.7nF SHIELD", shield, dgnd)
    f2 = comp("FUSE", "F2", "2920L260/33DR 2.6A/33V", "Fuse:Fuse_2920_7451Metric", "https://www.littelfuse.com/~/media/electronics/datasheets/resettable_ptcs/littelfuse_ptc_2920l_datasheet.pdf.pdf")
    usb_raw += f2[1]
    usb_prot += f2[2]
    d3 = comp("DIODE", "D3", "SMBJ13A / 13V VRWM USB VBUS", "Diode_SMD:D_SMB")
    d3.datasheet = "https://www.bourns.com/data/global/pdfs/SMBJ.pdf"
    dgnd += d3["A"]
    usb_prot += d3["K"]
    # 4.7uF + 1uF nominal, <=6.84uF at +20% tolerance before the mux.
    c("C71", "4.7uF/25V USB", usb_prot, dgnd, "Capacitor_SMD:C_1206_3216Metric")

    # STUSB4500QTR autonomous sink. CCxDB-to-CCx enables documented dead-
    # battery Rd presentation; VDD is supplied from connector-side VBUS.
    # VSYS follows switched 3V3 for battery-only PM I2C availability.
    u10 = stdcomp("Interface_USB", "STUSB4500QTR", "U10", "STUSB4500QTR")
    cc1 += u10["CC1", "CC1DB"]
    cc2 += u10["CC2", "CC2DB"]
    pd_vdd = Net("PD_VDD")
    pd_vbus_sense = Net("PD_VBUS_SENSE_DISCH")
    r("R106", "1k VBUS DISCH LIMIT", usb_prot, pd_vbus_sense)
    pd_vbus_sense += u10["VBUS_VS_DISCH"]
    r("R85", "0R PD VDD FEED", usb_prot, pd_vdd)
    pd_vdd += u10["VDD"]
    # RESET is active high; hold it directly at DGND for autonomous operation.
    # ST DS12499 Rev8 section 2.2.4: SCL/SDA are pulled down with neither
    # VDD nor VSYS present. Battery-only common-bus operation needs VSYS.
    v3d += u10["VSYS"]
    dgnd += u10["GND", "RESET", "ADDR0", "ADDR1"]
    pm_scl += u10["SCL"]
    pm_sda += u10["SDA"]
    pd_alert += u10["ALERT"]
    pd_contract += u10["POWER_OK3"]
    pd_v12, pd_v27 = Net("PD_VREG_1V2"), Net("PD_VREG_2V7")
    pd_v12 += u10["VREG_1V2"]
    pd_v27 += u10["VREG_2V7"]
    c("C104", "1uF VREG_1V2", pd_v12, dgnd)
    c("C105", "1uF VREG_2V7", pd_v27, dgnd)
    c("C106", "1uF/25V PD VDD", pd_vdd, dgnd)
    c("C109", "1uF/10V PD VSYS", v3d, dgnd, "Capacitor_SMD:C_0402_1005Metric")
    r("R83", "10k ALERT PU", pd_alert, v3d)
    r("R84", "10k PDO3 OK PU", pd_contract, v3d)
    u10.circuit.NC += u10["NC", "DISCH", "ATTACH", "POWER_OK2", "GPIO", "VBUS_EN_SNK", "A_B_SIDE"]

    # ST's reference design uses ESDA25W on the CC pins. It is a two-line,
    # 25V-min breakdown SOT-323 array; its 65pF typical line capacitance is
    # compatible with the USB-PD CC receiver capacitance budget.
    d4 = stdcomp("Device", "D_TVS_Dual_AAC", "D4", "ESDA25W CC ESD / P1,P2=CC P3=GND",
                 "Package_TO_SOT_SMD:SOT-323_SC-70",
                 "https://www.st.com/resource/en/datasheet/esdaxxxwx.pdf")
    cc1 += d4[1]
    cc2 += d4[2]
    dgnd += d4[3]

    # Use the manufacturer's non-via land pattern at placement stage. The
    # KiCad *ThermalVias variant hard-codes 0.20 mm drills, below the selected
    # standard 4-layer process. Add 0.30/0.70 mm thermal vias during routing.
    u7 = comp("TPS2121", "U7", "TPS2121RUXR", "Package_DFN_QFN:Texas_VQFN-HR-12_2x2.5mm_P0.5mm", "https://www.ti.com/lit/ds/symlink/tps2121.pdf")
    usb_prot += u7["IN1"]
    service_prot += u7["IN2"]
    charger_in += u7["OUT"]
    dgnd += u7["GND", "CP2", "OV1", "OV2", "PR1"]
    input_status += u7["ST"]
    r("R73", "44.2k / ILIM typ 2.5A", u7["ILIM"], dgnd)
    c("C72", "100nF MUX SS", u7["SS"], dgnd)
    c("C73", "10uF/25V MUX OUT", charger_in, dgnd, "Capacitor_SMD:C_1206_3216Metric")

    u8 = comp("BQ25798", "U8", "BQ25798RQM", "Package_DFN_QFN:Texas_RQM0029A_VQFN-29_4x4mm_P0.4mm", "https://www.ti.com/lit/ds/symlink/bq25798.pdf")
    charger_in += u8["VBUS", "VAC1", "VAC2"]
    dgnd += u8["GND", "ACDRV1", "ACDRV2", "CE"]
    u8.circuit.NC += u8["D+", "D-"]
    qon_service += u8["QON"]
    pm_scl += u8["SCL"]
    pm_sda += u8["SDA"]
    bq_stat_raw += u8["STAT"]
    charger_fault += u8["INT"]
    pack_pos += u8["BAT"]
    r("R74", "100R BATP", pack_pos, u8["BATP"])
    vsys_raw += u8["SYS"]

    sw1, sw2, regn, pmid = Net("CHG_SW1"), Net("CHG_SW2"), Net("CHG_REGN"), Net("CHG_PMID")
    sw1 += u8["SW1"]
    sw2 += u8["SW2"]
    regn += u8["REGN"]
    pmid += u8["PMID"]
    # TI BQ25798 Rev.C 8.2.2.2 requires 1uH at 1.5MHz; R75=6.04k
    # selects that frequency and 2S at POR. Do not select 750kHz in firmware.
    l3 = comp("L", "L3", "SRP7028A-1R0M 1uH", "Inductor_SMD:L_Bourns_SRP7028A_7.3x6.6mm", "https://www.bourns.com/data/global/pdfs/SRP7028A.pdf")
    sw1 += l3[1]
    sw2 += l3[2]
    c("C74", "47nF BTST1", u8["BTST1"], sw1)
    c("C75", "47nF BTST2", u8["BTST2"], sw2)
    c("C76", "4.7uF REGN", regn, dgnd)
    for ref in ("C77", "C78", "C79"):
        c(ref, "10uF/25V PMID", pmid, dgnd, "Capacitor_SMD:C_1206_3216Metric")
    c("C80", "100nF PMID", pmid, dgnd)
    for ref in ("C81", "C82", "C83", "C84", "C85"):
        c(ref, "10uF/16V SYS", vsys_raw, dgnd, "Capacitor_SMD:C_1206_3216Metric")
    c("C86", "100nF SYS", vsys_raw, dgnd)
    c("C87", "10uF/16V BAT", pack_pos, dgnd, "Capacitor_SMD:C_1206_3216Metric")
    c("C88", "10uF/16V BAT", pack_pos, dgnd, "Capacitor_SMD:C_1206_3216Metric")
    c("C89", "1nF/50V C0G SDRV", u8["SDRV"], dgnd)
    # BQ25798 Rev.C Figure 10-1 / layout guidance: 100nF immediately at VBUS,
    # plus three 10uF ceramics. C73 remains TPS2121 output bulk and is not
    # counted as charger-local bypass.
    c("C100", "100nF/25V VBUS LOCAL", charger_in, dgnd, "Capacitor_SMD:C_0402_1005Metric")
    for ref in ("C101", "C102", "C103"):
        c(ref, "10uF/25V VBUS LOCAL", charger_in, dgnd, "Capacitor_SMD:C_1206_3216Metric")
    r("R75", "6.04k PROG / 2S PROFILE", u8["PROG"], dgnd)
    ilim = Net("BQ25798_ILIM")
    ilim += u8["ILIM_HIZ"]
    # VILIM=1V+0.8ohm*IIN. Lower divider impedance limits the specified
    # +/-1.5uA ILIM leakage error. Conservative ~0.30A at REGN=4.8V;
    # ~0.45A upper estimate at 5.2V including 0.1% R and leakage, before
    # unspecified ADC/low-current regulation error (bench acceptance gate).
    r("R76", "28.7k 0.1% ILIM TOP / SAFE START", regn, ilim)
    r("R77", "10k 0.1% ILIM BOT", ilim, dgnd)
    ntc_chg += u8["TS"]
    r("R78", "5.24k TS TOP", regn, ntc_chg)
    r("R79", "30.31k TS BOT", ntc_chg, dgnd)
    # Keep the raw BQ25798 STAT drain separate from the MCU/panel logic net.
    # D7 only permits CHARGE_STATUS to pull toward the raw open-drain node;
    # REGN and the hardware LED cannot source current back into +3V3_D.
    r("R80", "10k CHARGE_STATUS PU", charge_stat, v3d)
    d7 = stdcomp("Device", "D_Schottky", "D7", "BAT54WS-7-F STAT ISOLATION",
                 "Diode_SMD:D_SOD-323")
    charge_stat += d7["A"]
    bq_stat_raw += d7["K"]
    r("R81", "10k INT PU", charger_fault, v3d)
    r("R82", "10k MUX ST PU", input_status, v3d)

    # QON is a service/wake input, not the normal user power switch. BQ25798
    # Rev.C provides an internal ~200k pull-up; a momentary contact to DGND
    # exits ship mode (1 s default, or 15 ms with WKUP_DLY=1). A ~10 s hold
    # requests the documented system-power reset behavior.
    sw2 = stdcomp("Switch", "SW_Push", "SW2", "QON SERVICE / TL3305AF160QG",
                  "Button_Switch_SMD:SW_SPST_TL3305A")
    qon_service += sw2[1]
    dgnd += sw2[2]

    # STAT is open-drain and remains usable while the switched main rails are
    # off. REGN -> resistor -> LED -> BQ_STAT_RAW follows TI's hardware
    # indication: LOW=charging, HIGH=complete/disabled, 1 Hz blink=fault.
    r("R104", "2.2k CHG LED / ~1.3mA", regn, charge_led_a)
    d5 = stdcomp("Device", "LED", "D5", "LTST-C190KRKT RED / CHG",
                 "LED_SMD:LED_0603_1608Metric")
    charge_led_a += d5["A"]
    bq_stat_raw += d5["K"]

    f3 = comp("FUSE", "F3", "MF-MSMF250/16X-2 2.5A/16V PPTC", "Fuse:Fuse_1812_4532Metric_Pad1.30x3.40mm_HandSolder", "https://www.bourns.com/docs/product-datasheets/mf-msmf.pdf")
    vsys_raw += f3[1]
    vsys_prot += f3[2]
    power_flag(pack_pos, "#FLG0501")
    power_flag(usb_prot, "#FLG0502")
    power_flag(service_prot, "#FLG0503")
    power_flag(pd_vdd, "#FLG0504")
    tp("TP20", usb_raw)
    tp("TP21", charger_in)
    tp("TP22", vsys_raw)
    tp("TP23", vsys_prot)
    tp("TP31", cc1)
    tp("TP32", cc2)
    tp("TP33", usb_prot)
    tp("TP34", pd_vdd)
    tp("TP35", pd_v27)
    tp("TP36", pd_alert)
    tp("TP37", pm_scl)
    tp("TP38", pm_sda)
    tp("TP39", qon_service)


@subcircuit
def system_power_control(vsys_prot, vsys_main, power_ctrl, dgnd):
    """Low-loss user load switch; charging/BMS/PD stay upstream and alive."""
    sys_gate = Net("SYS_LOAD_GATE")
    # 30 V P-channel SO-8, max 10 mOhm at VGS=-4.5 V. A conservative hot
    # design value of 15 mOhm gives 15/30/49.5 mV drop and 15/60/163 mW at
    # 1/2/3.3 A. Source is upstream so the body diode blocks VSYS_PROT ->
    # VSYS_MAIN while off.
    q4 = comp("PMOS", "Q4", "DMP3007LSS-13 SYSTEM LOAD SWITCH",
              "R3_Power:DMP3007LSS_SO8_LOGICAL",
              "https://www.diodes.com/part/view/DMP3007LSS")
    vsys_prot += q4["S"]
    vsys_main += q4["D"]
    sys_gate += q4["G"]
    r("R102", "100k G-S / DEFAULT OFF", vsys_prot, sys_gate)
    c("C107", "100nF G-S / SOFT START", vsys_prot, sys_gate)
    r("R103", "10k GATE SERIES", sys_gate, power_ctrl)
    sw1 = stdcomp("Switch", "SW_SPST", "SW1", "C&K RS282G05A3 / POWER ON",
                  "Button_Switch_SMD:SW_SPST_CK_RS282G05A3")
    power_ctrl += sw1[1]
    dgnd += sw1[2]
    c("C108", "10uF/16V VSYS_MAIN", vsys_main, dgnd,
      "Capacitor_SMD:C_1206_3216Metric")
    tp("TP40", vsys_main)


@subcircuit
def digital_buck(vsys_main, v3d, pg3d, dgnd):
    power_flag(vsys_main, "#FLG0101")
    power_flag(dgnd, "#FLG0102")
    # Thermal vias are deliberately deferred to routing and must use the
    # approved 0.30 mm drill / 0.70 mm pad geometry.
    u = comp("TPS62132", "U1", "TPS62132RGTR", "Package_DFN_QFN:VQFN-16-1EP_3x3mm_P0.5mm_EP1.45x1.45mm", "https://www.ti.com/lit/ds/symlink/tps62132.pdf")
    vsys_main += u["AVIN", "PVIN", "EN"]
    sw = Net("SW_3V3")
    sw += u["SW"]
    l = comp("L", "L1", "2.2uH XFL4020-222ME", "R3_Power:L_Coilcraft_XFL4020")
    sw += l[1]
    v3d += l[2], u["VOS"]
    # DC power is delivered through L1 (passive). U10 VSYS is now a real
    # power-input consumer on this rail; mark the physical source after L1.
    power_flag(v3d, "#FLG0103")
    dgnd += u["AGND", "PGND", "EP", "FSW", "DEF", "FB"]
    c("C10", "10uF/25V", vsys_main, dgnd, "Capacitor_SMD:C_1206_3216Metric")
    c("C11", "100nF/25V", vsys_main, dgnd)
    c("C12", "22uF/10V", v3d, dgnd, "Capacitor_SMD:C_0805_2012Metric")
    c("C13", "22uF/10V", v3d, dgnd, "Capacitor_SMD:C_0805_2012Metric")
    c("C14", "3.3nF", u["SS/TR"], dgnd)
    r("R10", "100k", pg3d, v3d)
    pg3d += u["PG"]
    tp("TP3", v3d)
    tp("TP4", pg3d)


@subcircuit
def preiso_buck(vsys_main, v5pre, v5pre_ads, v5pre_ina, dgnd):
    u = comp("TPS54302", "U2", "TPS54302DDCR", "Package_TO_SOT_SMD:SOT-23-6", "https://www.ti.com/lit/ds/symlink/tps54302.pdf")
    vsys_main += u["VIN"]
    # TI TPS54302 Rev.C: EN may float (internal pull-up). Never expose
    # this 7V-absolute-maximum pin to the 8.4V/8.6V system rail.
    u.circuit.NC += u["EN"]
    dgnd += u["GND"]
    sw, fb = Net("SW_5V"), Net("FB_5V")
    sw += u["SW"]
    l = comp("L", "L2", "10uH SRP5030TA-100M", "Inductor_SMD:L_Bourns_SRP5030T")
    sw += l[1]
    v5pre += l[2]
    c("C20", "10uF/25V", vsys_main, dgnd, "Capacitor_SMD:C_1206_3216Metric")
    c("C21", "100nF/25V", vsys_main, dgnd)
    c("C22", "100nF BOOT", u["BOOT"], sw)
    c("C23", "22uF/25V GRM32ER71E226KE15L", v5pre, dgnd, "Capacitor_SMD:C_1210_3225Metric")
    c("C24", "22uF/25V GRM32ER71E226KE15L", v5pre, dgnd, "Capacitor_SMD:C_1210_3225Metric")
    fb += u["FB"]
    r("R21", "100k 1%", v5pre, fb)
    r("R22", "13.3k 1%", fb, dgnd)
    c("C25", "75pF C0G", v5pre, fb)
    # The previous 511k/105k divider was the 8-V reference design and blocked
    # startup over part of the fixed 2S range. EN now floats per TI; the
    # BMS owns cell undervoltage cutoff and TPS54302 retains its internal UVLO.
    # Separate primary filters prevent the two isolated converters from sharing
    # one filtered node. Full-load input current at the 4.5 V converter limit is
    # about 0.89 A; the selected bead class must be rated >=1.5 A to retain
    # useful saturation/temperature margin.
    fb_ads = comp("FERRITE", "FB6", "BLM31KN601SH1L", "Inductor_SMD:L_1206_3216Metric_Pad1.22x1.90mm_HandSolder")
    v5pre += fb_ads[1]
    v5pre_ads += fb_ads[2]
    c("C26", "10uF/10V ADS IN", v5pre_ads, dgnd, "Capacitor_SMD:C_0805_2012Metric")
    c("C27", "100nF ADS IN", v5pre_ads, dgnd)
    fb_ina = comp("FERRITE", "FB7", "BLM31KN601SH1L", "Inductor_SMD:L_1206_3216Metric_Pad1.22x1.90mm_HandSolder")
    v5pre += fb_ina[1]
    v5pre_ina += fb_ina[2]
    c("C28", "10uF/10V INA IN", v5pre_ina, dgnd, "Capacitor_SMD:C_0805_2012Metric")
    c("C29", "100nF INA IN", v5pre_ina, dgnd)
    tp("TP5", v5pre)
    tp("TP6", v5pre_ads)
    tp("TP16", v5pre_ina)


@subcircuit
def isolation(v5pre_ads, v5iso_raw, v5iso_a, v5iso_d, ctrl_rs3e_pri, dgnd, gndiso):
    power_flag(v5pre_ads, "#FLG0201")
    u = comp("RS3E", "U3", "RS3E-0505S/H3", "R3_Power:Converter_DCDC_RECOM_RS3E_SIP8", "https://g.recomcdn.com/media/Datasheet/pdf/.fgOwPLnX/.ta93ececc9aa80a1b412c/Datasheet-447/RS3E.pdf")
    # Select RS3E pins by number. SKiDL treats string selectors as patterns,
    # so names beginning with '+' can otherwise match more than one pin.
    v5pre_ads += u[2]
    dgnd += u[1]
    ctrl_rs3e_pri += u["CTRL"]
    u.circuit.NC += u["NC"]
    v5iso_raw += u[6]
    gndiso += u[7]
    # CTRL open = ON. J4 permits an external dry contact or open-drain device
    # to short CTRL to DGND for OFF. Do not drive this pin directly from a
    # push-pull MCU output; see the RECOM CTRL circuit in the review report.
    c("C30", "10uF/10V RAW", v5iso_raw, gndiso, "Capacitor_SMD:C_0805_2012Metric")
    c("C31", "100nF RAW", v5iso_raw, gndiso)
    fba = comp("FERRITE", "FB2", "FB_A / FB-or-0R", "Resistor_SMD:R_0805_2012Metric")
    v5iso_raw += fba[1]
    v5iso_a += fba[2]
    fbd = comp("FERRITE", "FB3", "FB_D / FB-or-0R", "Resistor_SMD:R_0805_2012Metric")
    v5iso_raw += fbd[1]
    v5iso_d += fbd[2]
    c("C32", "10uF A bulk", v5iso_a, gndiso, "Capacitor_SMD:C_0805_2012Metric")
    c("C33", "100nF A", v5iso_a, gndiso)
    c("C34", "10uF D bulk", v5iso_d, gndiso, "Capacitor_SMD:C_0805_2012Metric")
    c("C35", "100nF D", v5iso_d, gndiso)
    tp("TP7", v5iso_raw)
    tp("TP8", v5iso_a)
    tp("TP9", v5iso_d)
    tp("TP10", gndiso)


@subcircuit
def isolated_ldos(v5iso_a, v5iso_d, v3a, v3di, gndiso):
    power_flag(v5iso_a, "#FLG0301")
    power_flag(v5iso_d, "#FLG0302")
    # GND_ISO is already driven by the isolated converter secondary. A
    # PWR_FLAG here creates a false power-output-to-power-output ERC error.
    u4 = comp("ADM7150", "U4", "ADM7150ACPZ-3.3-R7", "R3_Power:LFCSP-8-1EP_3x3mm_P0.5mm_EP1.74x1.45mm", "https://www.analog.com/media/en/technical-documentation/data-sheets/adm7150.pdf")
    v5iso_a += u4["VIN"]
    ena, ref = Net("EN_3V3_A_ISO"), Net("ADM7150_REF")
    ena += u4["EN"]
    r("R40", "10k", v5iso_a, ena)
    v3a += u4["VOUT"]
    gndiso += u4["GND", "EP"]
    ref += u4["REF", "REF_SENSE"]
    # Larger 1210 X7R parts selected to allow DC-bias margin. Ceff/ESR evidence
    # remains an explicit acceptance gate, not an inference from voltage rating.
    c("C40", "22uF/25V GRM32ER71E226KE15L", v5iso_a, gndiso, "Capacitor_SMD:C_1210_3225Metric")
    c("C41", "22uF/25V GRM32ER71E226KE15L", u4["VREG"], gndiso, "Capacitor_SMD:C_1210_3225Metric")
    c("C42", "22uF/25V GRM32ER71E226KE15L", v3a, gndiso, "Capacitor_SMD:C_1210_3225Metric")
    c("C43", "1uF REF", ref, gndiso)
    c("C44", "1uF BYP", u4["BYP"], gndiso)
    u5 = comp("TPS7A20", "U5", "TPS7A2033PDBVR", "Package_TO_SOT_SMD:SOT-23-5", "https://www.ti.com/lit/ds/symlink/tps7a20.pdf")
    v5iso_d += u5["IN", "EN"]
    v3di += u5["OUT"]
    gndiso += u5["GND"]
    u5.circuit.NC += u5["NC"]
    c("C50", "2.2uF IN", v5iso_d, gndiso)
    c("C51", "4.7uF OUT", v3di, gndiso)
    tp("TP11", v3a)
    tp("TP12", v3di)


@subcircuit
def ina_isolation(v5pre_ina, v5ina, v5ina_n, dgnd, gndiso):
    v5p_raw, v5n_raw = Net("+5V_INA_RAW"), Net("-5V_INA_RAW")
    power_flag(v5pre_ina, "#FLG0401")
    u = comp("RS3_DUAL", "U6", "RS3-0505D/H3", "R3_Power:Converter_DCDC_RECOM_RS3_SIP8", "https://g.recomcdn.com/media/Datasheet/pdf/.fc1hzCnZ/.t1305551dee110dff2189/Datasheet-28/RS3.pdf")
    dgnd += u[1]
    v5pre_ina += u[2]
    u.circuit.NC += u["CTRL", "NC"]  # open CTRL is the documented ON state
    v5p_raw += u[6]
    gndiso += u[7]
    v5n_raw += u[8]
    fbp = comp("FERRITE", "FB4", "0R / FB / L BENCH SELECT", "Inductor_SMD:L_1206_3216Metric_Pad1.22x1.90mm_HandSolder")
    v5p_raw += fbp[1]
    v5ina += fbp[2]
    fbn = comp("FERRITE", "FB5", "0R / FB / L BENCH SELECT", "Inductor_SMD:L_1206_3216Metric_Pad1.22x1.90mm_HandSolder")
    v5n_raw += fbn[1]
    v5ina_n += fbn[2]
    c("C60", "10uF +5V bulk", v5ina, gndiso, "Capacitor_SMD:C_0805_2012Metric")
    c("C61", "100nF +5V", v5ina, gndiso)
    c("C62", "10uF -5V bulk", gndiso, v5ina_n, "Capacitor_SMD:C_0805_2012Metric")
    c("C63", "100nF -5V", gndiso, v5ina_n)
    # Do not populate until dual-output regulation/noise tests select the load.
    # 2512 allows a suitably rated preload resistor, not a mandatory value.
    for ref, rail in (("R107", v5ina), ("R108", v5ina_n)):
        preload = comp("R", ref, "DNP PRELOAD / BENCH SELECT", "Resistor_SMD:R_2512_6332Metric")
        across(preload, rail, gndiso)
        preload.dnp = True
    tp("TP13", v5ina)
    tp("TP14", v5ina_n)


@subcircuit
def outputs(v3d, pg3d, v5iso_raw, v3a, v3di, v5ina, v5ina_n,
            ctrl_rs3e_pri, pm_scl, pm_sda, charge_stat, charger_fault,
            input_status, pd_alert, pd_contract, power_ctrl, qon_service,
            bq_stat_raw, dgnd, gndiso):
    j2 = comp("CONN6", "J2", "DIGITAL POWER OUT", "Connector_Molex:Molex_Micro-Fit_3.0_43650-0600_1x06_P3.00mm_Horizontal")
    v3d += j2[1, 2]
    dgnd += j2[3, 4]
    pg3d += j2[5]
    j2.circuit.NC += j2[6]
    j3 = comp("CONN10", "J3", "ISOLATED POWER OUT", "Connector_Molex:Molex_Micro-Fit_3.0_43650-1000_1x10_P3.00mm_Horizontal")
    v5iso_raw += j3[1]
    gndiso += j3[2, 4, 6, 8, 10]
    v3a += j3[3]
    v3di += j3[5]
    v5ina += j3[7]
    v5ina_n += j3[9]
    j4 = comp("CONN4", "J4", "CONTROL / SERVICE", "Connector_Molex:Molex_Micro-Fit_3.0_43650-0400_1x04_P3.00mm_Horizontal")
    dgnd += j4[1]
    pg3d += j4[2]
    ctrl_rs3e_pri += j4[3]
    j4.circuit.NC += j4[4]
    aux_fp = "Connector_JST:JST_GH_SM04B-GHS-TB_1x04-1MP_P1.25mm_Horizontal"
    j5 = comp("CONN4", "J5", "PRIMARY AUX DNP", aux_fp)
    j5.dnp = True
    v3d += j5[1]
    dgnd += j5[2]
    j5.circuit.NC += j5[3, 4]
    j6 = comp("CONN4", "J6", "ISOLATED AUX DNP", aux_fp)
    j6.dnp = True
    v3di += j6[1]
    v3a += j6[2]
    gndiso += j6[3]
    j6.circuit.NC += j6[4]
    j10 = comp("CONN10", "J10", "BATTERY / CHARGER TELEMETRY", "Connector_Molex:Molex_Micro-Fit_3.0_43650-1000_1x10_P3.00mm_Horizontal")
    v3d += j10[1]
    dgnd += j10[2]
    pm_scl += j10[3]
    pm_sda += j10[4]
    charge_stat += j10[5]
    pg3d += j10[6]  # system POWER_GOOD exported as the existing 3V3 power-good
    charger_fault += j10[7]
    input_status += j10[8]
    pd_alert += j10[9]
    pd_contract += j10[10]
    j11 = comp("CONN10", "J11", "USER PANEL / PRIMARY ONLY",
               "Connector_Molex:Molex_Micro-Fit_3.0_43650-1000_1x10_P3.00mm_Horizontal")
    v3d += j11[1]
    dgnd += j11[2]
    power_ctrl += j11[3]
    qon_service += j11[4]
    charge_stat += j11[5]
    pg3d += j11[6]
    pm_scl += j11[7]
    pm_sda += j11[8]
    bq_stat_raw += j11[9]
    j11.circuit.NC += j11[10]

    # Optional prototype board-to-board interfaces. These are deliberately
    # generic 2.54 mm THT patterns so straight/stacking headers or female
    # sockets can use the same holes. Cable/Micro-Fit connectors remain the
    # primary Rev.A assembly; J12/J13 are DNP by default.
    j12 = stdcomp(
        "Connector_Generic", "Conn_02x08_Odd_Even", "J12",
        "PRIMARY B2B 2x8 / DNP",
        "Connector_PinHeader_2.54mm:PinHeader_2x08_P2.54mm_Vertical",
    )
    j12.dnp = True
    v3d += j12[1, 2]
    dgnd += j12[3, 4]
    pm_scl += j12[5]
    pm_sda += j12[6]
    pg3d += j12[7]
    charge_stat += j12[8]
    charger_fault += j12[9]
    input_status += j12[10]
    pd_alert += j12[11]
    pd_contract += j12[12]
    power_ctrl += j12[13]
    qon_service += j12[14]
    j12.circuit.NC += j12[15, 16]

    j13 = stdcomp(
        "Connector_Generic", "Conn_02x05_Odd_Even", "J13",
        "ISOLATED B2B 2x5 / DNP",
        "Connector_PinHeader_2.54mm:PinHeader_2x05_P2.54mm_Vertical",
    )
    j13.dnp = True
    v5iso_raw += j13[1]
    gndiso += j13[2, 4, 6, 8, 10]
    v3a += j13[3]
    v3di += j13[5]
    v5ina += j13[7]
    v5ina_n += j13[9]

    # RUN indicates the actual switched +3V3_D rail; it is necessarily dark
    # when SW1 has disconnected VSYS_MAIN.
    run_led_a = Net("RUN_LED_A")
    r("R105", "2.2k RUN LED / ~0.7mA", v3d, run_led_a)
    d6 = stdcomp("Device", "LED", "D6", "LTST-C190KGKT GREEN / RUN",
                 "LED_SMD:LED_0603_1608Metric")
    run_led_a += d6["A"]
    dgnd += d6["K"]
    tp("TP15", dgnd)


service_raw, service_prot, dgnd = Net("SERVICE_IN_RAW"), Net("SERVICE_IN_PROT"), Net("DGND")
bat_pos, cell_mid, bat_neg = Net("BAT_POS_RAW"), Net("CELL_MID"), Net("BAT_NEG_RAW")
pack_pos, ntc_bms, ntc_chg = Net("PACK_POS"), Net("NTC_BMS"), Net("NTC_CHG")
vsys_raw, vsys_prot, vsys_main = Net("VSYS_RAW"), Net("VSYS_PROT"), Net("VSYS_MAIN")
pm_scl, pm_sda = Net("PM_I2C_SCL"), Net("PM_I2C_SDA")
charge_stat, bq_stat_raw = Net("CHARGE_STATUS"), Net("BQ_STAT_RAW")
charger_fault = Net("CHARGER_INT_FAULT")
input_status = Net("INPUT_SOURCE_STATUS")
pd_alert, pd_contract = Net("PD_ALERT_N"), Net("PD_CONTRACT_12V_N")
qon_service, power_ctrl = Net("QON_SERVICE"), Net("POWER_CTRL")
charge_led_a = Net("CHARGE_LED_A")
v3d, pg3d, v5pre = Net("+3V3_D"), Net("PG_3V3_D"), Net("+5V_PREISO")
v5pre_ads, v5pre_ina = Net("+5V_PREISO_ADS"), Net("+5V_PREISO_INA")
v5iso_raw, v5iso_a, v5iso_d, gndiso = Net("+5V_ISO_RAW"), Net("+5V_ISO_A"), Net("+5V_ISO_D"), Net("GND_ISO")
v3a, v3di = Net("+3V3_A_ISO"), Net("+3V3_D_ISO")
v5ina, v5ina_n, ctrl_rs3e_pri = Net("+5V_INA"), Net("-5V_INA"), Net("CTRL_RS3E_PRI")

input_protection(service_raw, service_prot, dgnd)
battery_management(pack_pos, bat_pos, cell_mid, bat_neg, ntc_bms, ntc_chg,
                   pm_scl, pm_sda, v3d, dgnd)
charger_powerpath(service_prot, pack_pos, ntc_chg, pm_scl, pm_sda,
                  charge_stat, charger_fault, input_status, pd_alert,
                  pd_contract, qon_service, bq_stat_raw, charge_led_a,
                  vsys_raw, vsys_prot, v3d, dgnd)
system_power_control(vsys_prot, vsys_main, power_ctrl, dgnd)
digital_buck(vsys_main, v3d, pg3d, dgnd)
preiso_buck(vsys_main, v5pre, v5pre_ads, v5pre_ina, dgnd)
isolation(v5pre_ads, v5iso_raw, v5iso_a, v5iso_d, ctrl_rs3e_pri, dgnd, gndiso)
isolated_ldos(v5iso_a, v5iso_d, v3a, v3di, gndiso)
ina_isolation(v5pre_ina, v5ina, v5ina_n, dgnd, gndiso)
outputs(v3d, pg3d, v5iso_raw, v3a, v3di, v5ina, v5ina_n,
        ctrl_rs3e_pri, pm_scl, pm_sda, charge_stat, charger_fault,
        input_status, pd_alert, pd_contract, power_ctrl, qon_service,
        bq_stat_raw, dgnd, gndiso)

generate_schematic(
    filepath=str(ROOT),
    top_name="R3_power",
    title="R3 PowerBox — power tree",
    flatness=0.0,
    retries=5,
    auto_stub=True,
    auto_stub_fanout=2,
    auto_stub_max_wire_pins=1,
    label_clearance=True,
    tool=KICAD10,
)

# Preserve the logical SKiDL connectivity independently of the drawing. The
# arranger uses this map to move a label with the exact component pin it belongs
# to, even when the first automatic placement put two labels at one coordinate.
logical_nets = {}
for net in builtins.default_circuit.nets:
    for pin in net.pins:
        if getattr(pin, "part", None) is not None:
            logical_nets[f"{pin.part.ref}.{pin.num}"] = net.name
(ROOT / "tools" / "logical_nets.json").write_text(
    json.dumps(logical_nets, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
