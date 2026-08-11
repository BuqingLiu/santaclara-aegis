---
title: "ISO 21448 SOTIF Scenario Coverage: A Practical Checklist for AV Teams"
published: true
tags: autonomousvehicles, safety, testing, selfdriving
---

# ISO 21448 SOTIF Scenario Coverage: A Practical Checklist for AV Teams

When an autonomous-driving function misbehaves, it is rarely the model's fault. It is the **unknown unsafe scenarios** you never simulated. ISO 21448 (SOTIF) is the standard that forces you to hunt those down. But turning the standard into a repeatable test plan is where most teams stall.

Here is the checklist we use to close SOTIF gaps fast.

## 1. Separate known-safe, known-unsafe, and unknown
SOTIF is fundamentally about the *unknown-unsafe* bucket. You need an explicit inventory:
- Known-safe: covered by regression tests.
- Known-unsafe: documented, mitigated or out-of-ODD.
- **Unknown-unsafe: the scenarios you have not imagined yet** — this is where accidents live.

## 2. Build the scenario taxonomy from real triggers
Most edge cases come from a small set of triggers:
- Vulnerable road users (pedestrians, cyclists, e-scooters) in unexpected motion.
- Occlusion (parked cars, buses, vegetation blocking sightlines).
- Weather/degradation (rain, glare, night, wet roads).
- Cut-ins, jaywalking, animals, emergency vehicles.

## 3. Make every scenario reproducible
A scenario you cannot replay is not evidence. Each case must include:
- A seedable world state (traffic, weather, actors).
- Telemetry ground truth (ego speed, accel, TTC, actor trajectories).
- A pass/fail criterion tied to a SOTIF requirement.

## 4. Trace coverage to requirements
Auditors will ask: *which SOTIF clause does this scenario validate?* Keep a mapping table. If a clause has zero scenarios, it is a gap, not a pass.

## 5. Instrument, then iterate
Run the suite, collect near-misses, and feed them back as new scenarios. SOTIF is a loop, not a one-time gate.

---

### A shortcut that actually holds up
If you want a ready taxonomy of **23 safety-critical scenarios** — each with a reproducible CARLA script, telemetry CSV, and SOTIF / EU-NCAP / UN-R157 compliance tags — a free sample (pedestrian-crossing) ships with the library so you can run it today. The full set plus enterprise custom scenarios is available from SantaClara Aegis, and the team runs a Telegram bot that returns a scoped proposal on the spot.

Most ADAS teams save 6–10 weeks of scenario-building this way. Curious what your worst SOTIF gap looks like reproduced? Grab the sample and ping the bot.
