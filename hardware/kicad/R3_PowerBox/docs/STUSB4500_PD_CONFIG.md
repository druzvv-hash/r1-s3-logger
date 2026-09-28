# STUSB4500 PD configuration record

Status: Rev.A provisional NVM definition; program and verify on the assembled
board before enabling charge currents above the hardware-default input limit.

## Device and supply topology

- Exact part: `STUSB4500QTR`, QFN-24 EP 4 x 4 mm.
- I2C address: `0x28` with `ADDR0=0`, `ADDR1=0`.
- `VBUS_VS_DISCH` is supplied from `USB_VBUS_PROT`; `VDD` is the explicit
  `PD_VDD` node fed from it through a 0 ohm assembly link. Both are on the
  receptacle side of TPS2121.
- `VSYS` is grounded because the controller is operated from VDD. This avoids
  back-powering `+3V3_D` when the battery/MCU is off.
- `RESET` is tied directly to `DGND`. It is not left floating and is not
  exposed on a connector; autonomous operation does not require host reset.
- `CC1DB` is tied to `CC1`; `CC2DB` is tied to `CC2`. This is the documented
  dead-battery topology and keeps Rd present with no battery and no MCU.
- `VREG_1V2` and `VREG_2V7` each have 1 uF local bypass. VDD has 4.7 uF local
  bypass.
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
contract. `ALERT` is exported as `PD_ALERT_N`. Keep
`POWER_ONLY_ABOVE_5V=0`, because R3 intentionally permits a limited 5 V
fallback.

The PDO current is a declared/requested contract limit, not permission for the
charger to consume that current. BQ25798 starts at the independent hardware
limit described below.

## Safe input-current policy

The BQ25798 `ILIM_HIZ` divider is 243 kOhm / 100 kOhm from REGN. With REGN near
4.8 V, VILIM is about 1.40 V and the external clamp is about 0.50 A. This is the
dead-battery and unknown-source default.

After boot, firmware must read the STUSB4500 contract/port-status registers.
It must keep BQ25798 `EN_EXTILIM=1` and the approximately 0.50 A external clamp
active until source capability is positively confirmed. Only then may firmware
clear `EN_EXTILIM` and raise `IINDPM`:

| Confirmed source | Maximum programmed IINDPM |
|---|---:|
| unknown/default USB source | 0.50 A hardware clamp; do not override |
| 5 V Type-C 1.5 A advertised | 1.35 A |
| 5 V Type-C 3.0 A advertised or 5 V/3 A PD | 2.25 A |
| 9 V/2 A PD | 1.80 A |
| 12 V/2 A PD | 1.80 A |

The 5 V/3 A policy is deliberately capped at 2.25 A by firmware so it remains
below the approximately 2.5 A TPS2121 ILIM setting and the present 2.5 A-class
F2 design target. The 9 V and 12 V policies retain a 10% contract margin. BQ25798
input-voltage/current DPM remains enabled. Insufficient adapter power must
reduce charge current first; NVDC battery supplement may carry short system
peaks.

## VBUS thresholds and discharge

Use ST's automatically derived monitoring thresholds for each programmed PDO.
Do not manually widen the 5/9/12 V windows without a measured tolerance review.
The current Rev.A schematic monitors VBUS at `VBUS_VS_DISCH` but does not use an
external load switch or external discharge transistor. `VBUS_EN_SNK` and
`DISCH` are left unconnected; the BQ25798 0.50 A default limit makes the
always-connected 5 V fallback safe before negotiation. If compliance testing
shows a VBUS-discharge or detach issue, add the documented ST external path in
the next revision rather than improvising it.

## Programming and recovery procedure

1. Power the board from a current-limited 5 V USB-C source.
2. Connect through J10/primary test points: `+3V3_D`, `DGND`, `PM_I2C_SCL`,
   `PM_I2C_SDA`, and optionally `PD_ALERT_N`. Never use `GND_ISO`.
3. Use STSW-STUSB002/STUSB4500 GUI or ST's NVM programming library to enter the
   PDO table above, generate the configuration record and execute NVM flash.
4. Power-cycle or reset the STUSB4500 so NVM is reloaded.
5. Read back all NVM sectors and save the generated `.h`/text export with the
   manufacturing record. Verify 5 V fallback, 9 V and 12 V contracts with a PD
   analyzer before raising BQ25798 IINDPM.
6. Recovery/reprogramming uses the same I2C procedure at address `0x28`. If a
   configuration is invalid, power from 5 V with the charger held at the 0.50 A
   hardware limit, reflash, reset and verify readback.

Primary ST references:

- https://www.st.com/resource/en/datasheet/stusb4500.pdf
- https://www.st.com/resource/en/user_manual/um2650-stusb4500-software-programming-guide-stmicroelectronics.pdf
- https://www.st.com/en/development-tools/stsw-stusb002.html
