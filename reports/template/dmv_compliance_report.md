# AV Safety Scenario Compliance Report

**Corridor:** Santa Clara Tech Park / Downtown San Jose / El Camino Real × Lawrence Expressway
**Simulation platform:** CARLA 0.9.x — deterministic synchronous mode (20 Hz), seeded Traffic Manager
**Date:** {{DATE}}

## 1. Executive Summary

{{N_SCENARIOS}} safety-critical scenario classes were executed end-to-end.
Results: **{{N_PASS}} PASS · {{N_REVIEW}} REVIEW · {{N_FAIL}} FAIL**.

This report is prepared in alignment with California DMV Autonomous Vehicle
Program reporting expectations (13 CCR §227–228, disengagement & collision
reporting context) and NHTSA pre-crash scenario typology. Simulation evidence
is supplied as 20 Hz telemetry (CSV), ground-truth event logs (JSON), and
chase-camera frames (PNG) per scenario.

## 2. Methodology

- **Determinism:** fixed 0.05 s step, synchronous server-client stepping, seeded Traffic Manager — every run is reproducible bit-for-bit at scenario logic level.
- **Scenario construction:** events are generated from road topology (lanes, junctions, signals), making them transferable to client-specific OpenDRIVE maps of the actual corridor.
- **Metrics:** minimum Time-To-Collision (TTC), minimum clearance gap, maximum deceleration, hard-braking count, collision count.
- **Scoring:** FAIL = contact event; REVIEW = TTC/clearance below policy thresholds; PASS = event negotiated with safe margins.

## 3. Results

| Scenario | Regulatory reference | Result | min TTC (s) | min Gap (m) | Collisions |
|---|---|---|---|---|---|
{{RESULTS_TABLE}}

## 4. Data Package Contents

Each scenario folder contains:

| File | Content |
|---|---|
| `telemetry.csv` | 20 Hz ego kinematics, control commands, threat gap, TTC |
| `events.json` | Ground-truth trigger timeline and collision log |
| `frames/*.png` | Chase-camera evidence frames |
| `summary.json` | Scored KPI summary |

## 5. Limitations & Intended Use

Simulation results support — but do not replace — on-road validation. Scenario
parameters (speeds, trigger ranges, weather) are configurable per client ODD.
This package is intended for internal safety-case development, investor/partner
due diligence, and as supporting evidence in CA DMV permit interactions.
