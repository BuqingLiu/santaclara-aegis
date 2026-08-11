---
title: "Stop guessing edge cases: a reproducible AV safety-scenario library (23 classes, CARLA + telemetry)"
published: true
tags: autonomousvehicles, simulation, safety, carla, adas
---

# Stop guessing edge cases: a reproducible AV safety-scenario library

If you work in ADAS / AV verification, you already know the hardest part of a
safety case isn't the model — it's **proving you handled the nasty edge cases**
that regulators (EU NCAP 2026/2030, ISO 21448 SOTIF, UN-R157) actually care about.

Most teams hand-roll 2–3 scenarios, burn weeks in CARLA, and still can't point to
a traceable "this scenario validates that regulation" line.

## What a real edge-case library looks like

For every scenario you want three things that travel together:

1. **Telemetry CSV** — real vehicle trajectories, signals, and events.
2. **A reproducible CARLA script** — one click re-runs the exact situation.
3. **Compliance annotation** — which regulation/requirement the scenario maps to.

Example: a jaywalker "ghost" at night. Telemetry shows AEB triggered at ~6s, full
stop by ~8s, zero contact. The annotation ties it to a specific SOTIF clause. Your
audit team can trace it in one click instead of reverse-engineering a PowerPoint.

## Why 23 classes, not 3

Edge cases cluster: occluded pedestrians, aggressive cut-ins, sensor dropout in
tunnels, two-wheeler weaves, work zones, wrong-way drivers at night, bus-stop
occlusions… Each needs its own reproducible setup. A library that ships
**23 safety-critical classes** gets a verification program from "we hope we
covered it" to "here is the evidence pack."

## Try it before you trust it

A free, fully reproducible sample (pedestrian-crossing, with real telemetry and a
scenario report) ships with the library so you can verify the data is real before
you commit. The full set covers all 23 safety-critical classes plus enterprise
custom scenarios tailored to your vehicle and ODD.

If you want a tailored plan fast, the SantaClara Aegis team runs a Telegram bot
that returns a scoped proposal on the spot.

*Disclosure: I build SantaClara Aegis. The sample above is real run data you can
verify yourself — the original publish links to it.*
