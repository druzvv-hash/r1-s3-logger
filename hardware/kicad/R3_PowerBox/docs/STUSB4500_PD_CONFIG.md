# STUSB4500 PD configuration record

Routing F firmware constraint: preserve BQ25798 PWM_FREQ=0 (1.5 MHz).
R75=6.04 kOhm selects this at POR and L3=SRP7028A-1R0M is 1 uH.
750 kHz requires a different 2.2 uH inductor and is not allowed by this BOM.
Review1 (2026-10-03) supersedes the old nominal 0.50 A startup divider.
Confirmed-source ceilings remain 1.35 / 2.25 / 1.80 / 1.80 A; the unknown-source
hardware default is now approximately 0.30 A nominal. See the tolerance bound below.

## Mandatory first-power interlock

Factory ST NVM is NOT the R3 configuration: it can request 15/20 V. Initial
assembly, replacement or NVM recovery MUST use a verified current-limited
5 V-only, non-PD supply. Do not connect an ordinary PD supply until all NVM
sectors have been programmed/read back, power-cycled on 5 V-only and verified
against this record. D3 is a 13 V TVS, not protection against sustained 20 V.
Mark the programmed board and retain the readback with its serial number.
This is a procedural interlock, not autonomous overvoltage qualification of
an unprogrammed board. Rev.B may add an approved-voltage-window-qualified
VBUS_EN_SNK switch; a generic enable switch alone does not solve factory PDOs.

Status: Rev.A provisional NVM definition; program and verify on the assembled
board before enabling charge currents above the hardware-default input limit.

## Device and supply topology

- Exact part: `STUSB4500QTR`, QFN-24 EP 4 x 4 mm.
- I2C address: `0x28` with `ADDR0=0`, `ADDR1=0`.
- `VBUS_VS_DISCH` is supplied from `USB_VBUS_PROT` through R106=1 kOhm;
  its worst DC discharge estimate is 12.6 mA at 12.6 V, below 50 mA.
  `VDD` is the explicit
  `PD_VDD` node fed from it through a 0 ohm assembly link. Both are on the
  receptacle side of TPS2121.
- `VSYS` is supplied by `+3V3_D` with local C109=1 uF. DS12499 Rev8
  section 2.2.4 says SCL/SDA are pulled down when neither VDD nor VSYS is
  present: the old grounded VSYS blocked the shared bus on battery-only power.
  The documented dual-supply configuration preserves VDD-powered autonomous
  dead-battery negotiation and powers the interface when the battery MCU runs.
- `RESET` is tied directly to `DGND`. It is not left floating and is not
  exposed on a connector; autonomous operation does not require host reset.
- `CC1DB` is tied to `CC1`; `CC2DB` is tied to `CC2`. This is the documented
  dead-battery topology and keeps Rd present with no battery and no MCU.
- `VREG_1V2` and `VREG_2V7` each have 1 uF local bypass. VDD has C106=1 uF;
  C71=4.7 uF is USB input bulk. Their sum is 5.7 uF nominal / 6.84 uF at +20%.
  Downstream mux inrush/capacitance still requires attach testing.
- PM I2C is shared with BQ25798 and BQ28Z610. Their addresses do not conflict.
  Pull-ups remain on `+3V3_D`; with that rail absent the bus is not driven and
  autonomous PD negotiation still runs from VDD.

## NVM PDO definition

Program the following three fixed sink PDOs. Do not add a 15 V or 20 V PDO.

| PDO | Voltage | Operating current | Role |
|---|---:|---:|---|
| PDO1 | 5.0 V | 3.0 A maximum sink capability | mandatory PD/Type-C fallback |
| PDO2 | 9.0 V | 2.0 A | secondary fallback |
| PDO3 | 12.0 V | 2.0 A | preferred R3 contract |

PDO3 is the preferred/highest-priority match. Program `POWER_OK_CFG=10b`
(ST configuration 2). In this mode POWER_OK1/2/3 independently identify the
explicitly negotiated PDO after PS_READY; therefore `POWER_OK3`, exported as
active-low `PD_CONTRACT_12V_N`, is valid only for a successful PDO3 (12 V)
contract while attached. POWER_OK outputs can retain state after detach;
firmware MUST also verify live attach/source/contract status, never infer
current capability from POWER_OK3 alone. `ALERT` is exported as `PD_ALERT_N`. Keep
`POWER_ONLY_ABOVE_5V=0`, because R3 intentionally permits a limited 5 V
fallback.

The PDO current is a declared/requested contract limit, not permission for the
charger to consume that current. BQ25798 starts at the independent hardware
limit described below.

## Safe input-current policy

R76/R77 are 28.7 kOhm / 10.0 kOhm, both 0.1%, from REGN. TI Rev.C gives
Ilimit=(VILIM-1)/0.8. At REGN=4.8 V the nominal clamp is 0.300 A.
Using REGN=5.2 V, adverse resistor tolerance and +1.5 uA pin leakage gives
0.446 A. This is an estimate, not a guaranteed maximum including unspecified
ADC/5 V low-current regulation error. Measure unknown-source startup before
unrestricted use. The old 243k/100k divider had excessive leakage sensitivity.

After boot, firmware must read the STUSB4500 contract/port-status registers.
It must keep BQ25798 `EN_EXTILIM=1` and the conservative external clamp
active until source capability is positively confirmed. Only then may firmware
clear `EN_EXTILIM` and raise `IINDPM`:

| Confirmed source | Maximum programmed IINDPM |
|---|---:|
| unknown/default USB source | ~0.30 A nominal hardware clamp; do not override |
| 5 V Type-C 1.5 A advertised | 1.35 A |
| 5 V Type-C 3.0 A advertised or 5 V/3 A PD | 2.25 A |
| 9 V/2 A PD | 1.80 A |
| 12 V/2 A PD | 1.80 A |

The 5 V/3 A policy is deliberately capped at 2.25 A by firmware so it remains
below the approximately 2.5 A TPS2121 ILIM setting and the present 2.5 A-class
F2 design target at low temperature. F2 is now 2920L260/33DR (33 V); its hold
rating is only 2.24 A at 40 C / 2.02 A at 50 C / 1.81 A at 60 C. A 2.25 A
continuous setting is NOT hot-qualified. Lower charging/current demand as
required by the measured enclosure envelope; there is no F2 temperature sensor
or implemented automatic thermal firmware policy in this hardware repository.
The 9 V and 12 V policies retain a 10% contract margin. BQ25798
input-voltage/current DPM remains enabled. Insufficient adapter power must
reduce charge current first; NVDC battery supplement may carry short system
peaks.

## VBUS thresholds and discharge

Use ST's automatically derived monitoring thresholds for each programmed PDO.
Do not manually widen the 5/9/12 V windows without a measured tolerance review.
The current Rev.A schematic monitors VBUS at `VBUS_VS_DISCH` but does not use an
external load switch or external discharge transistor. `VBUS_EN_SNK` and
`DISCH` are left unconnected; the BQ25798 conservative startup clamp limits
load before negotiation but is NOT USB compliance certification. If compliance testing
shows a VBUS-discharge or detach issue, add the documented ST external path in
the next revision rather than improvising it.

## Programming and recovery procedure

1. Power from a verified current-limited **5 V-only non-PD** source. Ordinary
   PD chargers, even if initially at 5 V, are forbidden at this step. If the
   limited source cannot sustain the programming domain, use a validated
   charged pack for supplement, leave the future R3 loads disconnected and
   switch SW1 ON. Do not bypass the current clamp or inject external 3.3 V
   into the buck output without a separate back-power review.
2. Connect through J10/primary test points: `+3V3_D`, `DGND`, `PM_I2C_SCL`,
   `PM_I2C_SDA`, and optionally `PD_ALERT_N`. Never use `GND_ISO`.
3. Use STSW-STUSB002/STUSB4500 GUI or ST's NVM programming library to enter the
   PDO table above, generate the configuration record and execute NVM flash.
4. Power-cycle or reset the STUSB4500 so NVM is reloaded.
5. Read back all NVM sectors and save the generated `.h`/text export with the
   manufacturing record. Verify 5 V fallback, 9 V and 12 V contracts with a PD
   analyzer before raising BQ25798 IINDPM.
6. Recovery/reprogramming uses the same I2C procedure at address `0x28`. If a
   configuration is invalid, power from a verified 5 V-only source with the charger held at the conservative
   hardware limit, reflash, reset and verify readback.

Primary ST references:

- https://www.st.com/resource/en/datasheet/stusb4500.pdf
- https://www.st.com/resource/en/user_manual/um2650-stusb4500-software-programming-guide-stmicroelectronics.pdf
- https://www.st.com/en/development-tools/stsw-stusb002.html
