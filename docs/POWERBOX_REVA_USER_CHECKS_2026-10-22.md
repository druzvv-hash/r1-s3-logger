# R3 PowerBox Rev.A — user-reported physical checks, 2026-10-22

Recorded in external memory on 2026-10-23. Evidence class: **USER-REPORTED
physical measurements / preliminary bring-up**, not independently repeated by
the agent and **not full hardware acceptance**. The owner requested this
correction after the external-memory audit. No firmware, NVM, CAD or hardware
was changed during this documentation task.

## Evidence and chronology

Source: the owner's messages in the earlier “Діагностика PowerBox” conversation
on 2026-10-22, checked against the owner's explicit 2026-10-23 memory addendum.
Text messages were retrievable; attached photos/oscilloscope images were not
returned by the history reader. No image-derived numbers are reconstructed.

The private programmer report documents U10 write/readback and a fixed-5-V
restart. The owner subsequently reported **operation from PD 12 V**. These are
different evidence scopes: the old report alone does not demonstrate a 12-V
contract, but the project's memory now includes the later physical user report.
No independent PD protocol capture, current-limit or sustained-load verification
is supplied by this update. Preserve the already programmed U10 profile.

| Measurement | User-reported value | Context / limitation |
|---|---|---|
| Supply after U10 programming | PD 12 V operation | Explicit owner report; no protocol trace independently reviewed |
| SYS | 7.594 V / 7.327 V | The 7.594-V text explicitly says button released; the 7.327-V message does not itself restate button state or probe points |
| Outputs after PD report | 3.3062 V / 4.9965 V | Paired output readings; no quantified load or duration supplied |
| Isolated rails, earlier that day | TP13 +5.037 V; TP14 -5.037 V | Earlier than U10 programming / the later PD-12-V report; do not claim a repeat under PD 12 V |
| Other earlier isolated readings | TP12 3.308 V; TP11 3.302 V; TP7/8/9 5.023 V | User text; does not prove isolation withstand or loaded regulation |
| Earlier TP5 static reading | 5.0 V | SW1 held, L1 not yet installed; TP40 7.6 V and TP3 0 V in the same report |

The earlier private fixed-5-V test's 3.3062/4.7740-V readings remain historical;
do not substitute 4.7740 V for the later 4.9965-V user reading.

## Preliminary TP5 load observations — incomplete numeric evidence

On Oct 22 the owner supplied two scope images and clarified “Обидва тп5”
(both TP5), then six images with “Перших 3 без резистора” (first three without
the resistor). This establishes a preliminary TP5 comparison with/without a
resistor. On Oct 23 the owner explicitly clarified **100 ohms**. This value is
user-reported; resistor power rating is not given. The returned history omits
image pixels. Measured load current,
loaded voltage, ripple amplitude, transient depth and scope settings cannot be
verified from that text; numeric load/ripple results remain **UNCONFIRMED** until
the original images or explicit values are available. The earlier 5.0-V TP5
reading above is not a numerical result of this later load comparison.

## Mechanical / assembly problems reported by the owner

- Converter modules do not sit fully down on the PCB because they hit a
  capacitor. Reported physical interference; exact module/capacitor references,
  clearance and remedy are not established by the accessible text.
- Ground contacts were difficult to solder with the large copper pours.
  Reported assembly difficulty; solder-joint quality is not thereby accepted
  or declared failed, and no thermal-relief CAD change is made here.

Keep these observations separate from the Oct 8 source/package audit (U9 DRZ
land mismatch; U1/U4 thermal-land and Q2/Q3 paste warnings; J7 placement open)
and the separate local RevB candidate. Those reports do not resolve the
assembled Rev.A unit's fit or solder-quality questions.

## Unfinished checks and unresolved causes

- Quantified TP5 load/ripple/transient evaluation, scope settings and safe
  sustained-load/temperature limits remain unaccepted; electronic-load testing
  was still deferred in the owner's following conversation.
- SYS/button/power-control behavior needs a bounded test. The owner questioned
  U11 routing; this is an unresolved concern, not a verified root cause.
- Earlier bring-up lacked L1; the owner later reported a temporary “2.2” part.
  Exact rating and final replacement state are not verified here. C1 was
  reported absent; the owner's suggestion that it caused a dip is a hypothesis,
  not a confirmed diagnosis or proof of its current population state.
- Charger/battery/BMS, protection, power transitions, full-load rail regulation,
  isolation safety and mechanical/assembly acceptance remain open.
- A reported 12-V startup does not establish all PD profiles, maximum currents,
  long-duration stability or whole-board acceptance. No repeat U10 programming
  is required by this record.

Next session: read this addendum before interpreting the older 5-V-only report;
recover numeric TP5 evidence, then plan separately authorized bounded hardware
checks. Retain prior reports and the frozen Rev.A / separate RevB distinction.
