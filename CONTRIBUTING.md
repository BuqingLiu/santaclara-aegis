# Contributing

SantaClara Aegis is a **commercial product**. The open reference layer in this
repository (scenario definitions, CARLA client, sensor rig, map tooling, sample
datasets, and documentation) is published so customers and partners can review
engineering quality and propose improvements.

## What you can contribute

- Corrections and extensions to `docs/` (scenario catalog, data schema,
  methodology, compliance references).
- New **scenario definitions** under `config/scenarios.json` and
  `scenarios/safety_events/` that follow the existing contract (see
  `scenarios/base_scenario.py` and `docs/scenario-catalog.md`).
- Sample datasets and bug reports against the reference layer.
- Translations and clarity improvements to the documentation.

## How to propose changes

1. Open an issue describing the change.
2. Fork, branch (`fix/...`, `docs/...`, `feat/...`), and open a pull request
   against `main`.
3. Keep scenario contracts stable — new scenarios must implement
   `setup / on_tick / cleanup` and emit ground-truth events.

## Proprietary code

The `elite/` engine is **not** part of this repository and is not open to
external contribution. Integration, the behavior model, and the metrics/
reporting stack are developed in-house and delivered to subscribers.

## Code of conduct

Be respectful and constructive. We follow a standard open-source code of
conduct; harassment or hostile behavior will not be tolerated.
