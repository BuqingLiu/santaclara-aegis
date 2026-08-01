# Compliance

SantaClara Aegis produces simulation evidence aligned with recognized
autonomous-vehicle safety and regulatory frameworks. It is positioned as
**supporting material** for safety cases, permit interactions, and due
diligence — not a replacement for on-road validation.

## Framework alignment

| Framework | How Aegis maps to it |
|---|---|
| **California DMV AV Program** (13 CCR §227–228, disengagement/collision context) | Scenario evidence, per-scenario scored KPIs, and a DMV-style compliance report. |
| **NHTSA Pre-Crash Typology** | Cut-in, rear-end (lead decelerating / lead stopped), LTAP/OD, opposite-direction scenarios. |
| **CA Vehicle Code** | CVC 21453 (signals), 21806 (emergency yield), 21760 (cyclist 3-ft), 21800(d) (inoperative signal), 22450 (stop sign), 21658.1 (lane splitting). |
| **CA MUTCD** | Temporary traffic control / construction-zone forced merge. |
| **Euro NCAP CPNC** | Occluded-pedestrian dash-out case. |
| **FMVSS 127** | Low-light pedestrian AEB case. |
| **Caltrans FMS** | Move-over / incident and object-on-roadway cases. |

## What a compliance package contains

- **Executive summary** — scenario count and PASS / REVIEW / FAIL tally.
- **Per-scenario results** — regulatory reference, min TTC, min gap, collisions.
- **Data package** — 20 Hz telemetry, ground-truth events, chase-camera
  frames, and scored summaries per scenario.
- **Methodology & limitations** — determinism, configurability, and intended
  use (see `reports/template/dmv_compliance_report.md` and
  [`methodology.md`](methodology.md)).

## Intended use & limitations

Simulation results support — but do not replace — on-road validation. Scenario
parameters (speeds, trigger ranges, weather) are configurable per client ODD.
The package is intended for internal safety-case development, investor/partner
due diligence, and as supporting evidence in CA DMV permit interactions.
