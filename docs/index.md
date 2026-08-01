# SantaClara Aegis — Documentation

> Autonomous-driving **safety simulation & scenario-data subscription platform**.
> Compliant scenario evidence, labeled datasets, and audit-ready reports for
> AV / ADAS teams — built on CARLA.

This is the **open reference layer**. The proprietary `elite/` engine that
runs the scenarios is delivered to subscribers (see the
[sales page](https://github.com/BuqingLiu/santaclara-aegis)).

## Contents

| Document | What it covers |
|---|---|
| [Architecture](architecture.md) | System design, data flow, and the role of the proprietary core. |
| [Scenario Catalog](scenario-catalog.md) | All **23** safety-critical scenario classes, with regulatory references. |
| [Data Schema](data-schema.md) | The per-scenario dataset: `telemetry.csv`, `events.json`, `frames/`, `summary.json`. |
| [API Reference](api-reference.md) | How subscribers retrieve scenarios, datasets, and reports. |
| [Methodology](methodology.md) | Determinism, scenario construction, metrics, and scoring. |
| [Compliance](compliance.md) | Alignment with CA DMV / NHTSA / Euro NCAP / FMVSS expectations. |
| [Getting Started](getting-started.md) | Run the reference layer locally against CARLA. |
| [Roadmap](roadmap.md) | What is planned next. |

## At a glance

- **23** safety-critical scenario classes (VRU, intersection, highway, weather, incident).
- **Deterministic** CARLA simulation — 20 Hz synchronous stepping, seeded Traffic Manager.
- **Labeled data** — 20 Hz telemetry, ground-truth events, chase-camera frames, scored KPIs.
- **Audit-ready** — DMV-style compliance report (PDF/MD) per run.
- **Runs on a laptop** — low-quality profile, capped actors, fixed step.

## Repository layout (open layer)

```
santaclara-aegis/
├── README.md                 # product overview
├── index.html                # sales / landing page
├── docs/                     # this documentation
├── assets/                   # scenario imagery, logo, architecture diagram
├── samples/                  # sample manifest, telemetry, summary
├── scenarios/                # 23 scenario definitions (reference)
├── simulation/               # CARLA client, sensor rig, world utils
├── config/                   # scenario + performance profiles
├── maps/                     # real-corridor (OSM -> OpenDRIVE) tooling
├── tools/                    # record, encode, osm->xodr utilities
├── data/                     # collector + post-processing (reference)
├── reports/                  # compliance report template
├── elite/                    # ⚠ proprietary core — documentation only
└── run_*.py, core_engine.py  # entry points (reference)
```
