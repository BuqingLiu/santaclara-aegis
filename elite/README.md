# SantaClara Aegis — Proprietary Core Module

This directory intentionally contains **only documentation**. The `elite/`
engine — the deterministic scenario runtime, the `SafeDriver` behavior model
(including the queue-hold and longitudinal/lateral safety logic), the radar /
ground-truth perception stack, the metrics and compliance-report generators —
is the proprietary, subscriber-only core of SantaClara Aegis.

## What subscribers receive

- The full `elite/` package (Python, versioned, with the compliance engine
  `v3.0` behavior model).
- The complete runnable pipeline (`core_engine.py`, `run_*.py`, `scenarios/`,
  `simulation/`, `config/`, `tools/`, `data/`, `reports/`) wired to `elite/`.
- Access to the subscription API and the managed simulation service.

## For evaluators

The surrounding repository is the **open reference layer**: scenario
definitions, the CARLA client, sensor rig, map tooling, and sample datasets.
It is published so prospective customers can review engineering quality,
data schema, and methodology. Running the full suite requires the `elite/`
engine, which is delivered under a commercial subscription (see
[the sales page](https://github.com/BuqingLiu/santaclara-aegis) and
`docs/api-reference.md`).

## Licensing

The `elite/` engine is **not open source**. All rights reserved. Use is
governed by a commercial agreement; see `LICENSE` (repository open layer) and
the subscription terms referenced on the sales page.
