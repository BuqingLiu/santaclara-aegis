# Changelog

All notable changes to the SantaClara Aegis product are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/), versioning
follows the subscription release train (engine `v3.x`).

## [2026.07] Engine v3.0 — Compliance behavior model

- **Behavior model (`elite.driver`)**: queue-hold memory — once a same-lane
  lead is observed and the vehicle is stopped, the ego holds the brake even
  after the perception track is dropped (no creep, no AEB chatter).
- **Longitudinal/lateral safety**: hard speed clamp on real-road OSM maps
  (Traffic Manager reads no speed limit there), smooth lateral offsets.
- **Determinism**: fixed 20 Hz synchronous stepping, seeded Traffic Manager,
  reproducible scenario logic.
- **Reporting**: DMV-style compliance report (PDF/MD) with per-scenario
  scored KPIs.

## [2026.06] Scenario catalog expansion

- Catalog grew from 15 to **23** safety-critical scenario classes, adding
  motorcycle lane-splitting, bus-stop dart-out, freeway on-ramp merge,
  impaired-driver weave, running stop sign, disabled truck, close-pass cyclist,
  and roadway debris.

## [2026.05] Public reference layer open-sourced

- Scenario definitions, CARLA client, sensor rig, map tooling, and sample
  datasets published for customer review. Proprietary `elite/` engine remains
  subscriber-only.

## [2026.04] First managed-simulation delivery

- Fixed-scope delivery + monthly managed simulation service offered to
  California AV startups.
