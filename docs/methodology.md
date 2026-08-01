# Methodology

SantaClara Aegis is built so that simulation evidence is **reproducible,
labeled, and defensible** — suitable as supporting material for CA DMV permit
interactions, investor due diligence, and internal safety-case development.

## Determinism

- **Fixed step**: `0.05 s` (20 Hz) synchronous server–client stepping.
- **Seeded Traffic Manager**: ambient traffic is reproducible run-to-run.
- **Topology-driven events**: scenarios are generated from road topology, not
  hardcoded coordinates, so they transfer to client-specific maps.
- Result: every run is reproducible at the scenario-logic level.

## Scenario construction

Each safety event is described relative to the ego vehicle's lane, junction,
and signal state. This makes the same 23 scenarios portable from CARLA's stock
urban map (`Town10HD_Opt`) to a client's actual corridor (e.g. El Camino Real
× Lawrence Expressway) via an OSM → OpenDRIVE export (see `maps/README.md`).

## Metrics

Per scenario, the engine records and scores:

- **Time-To-Collision (TTC)** — minimum over the run.
- **Clearance gap** — minimum distance to the primary threat.
- **Maximum deceleration** — peak braking demand.
- **Hard-braking / AEB activations** — event counts.
- **Collisions** — contact events (ground-truth).

## Scoring

| Verdict | Meaning |
|---|---|
| **PASS** | Event negotiated within safe margins (TTC/gap above policy thresholds). |
| **REVIEW** | TTC or clearance fell below policy thresholds — human review recommended. |
| **FAIL** | Contact event occurred. |

Thresholds are configurable per client ODD. See `docs/data-schema.md` for the
exact per-frame and summary fields.
