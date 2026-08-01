# Data Schema

Every scenario produces a self-contained dataset plus a rolled-up summary.
This is the contract subscribers receive through the API and the managed
service. Sample files live in [`samples/`](../samples).

## `telemetry.csv` — 20 Hz ego kinematics

One row per simulation frame.

| Column | Unit | Description |
|---|---|---|
| `frame` | — | Simulation frame index |
| `t_s` | s | Elapsed scenario time |
| `v_kmh` / `v_mps` | km/h / m/s | Ego speed |
| `accel_mps2` | m/s² | Longitudinal acceleration (braking negative) |
| `steer` | — | Steering command [−1, 1] |
| `throttle` / `brake` | — | Control commands [0, 1] |
| `threat_class` | — | Primary threat class (`none`, `pedestrian`, `vehicle`, …) |
| `threat_dist_m` | m | Distance to primary threat |
| `ttc_s` | s | Time-To-Collision (0 if imminent/none) |
| `gap_m` | m | Clearance gap to lead |
| `aeb` | — | AEB activation flag (0/1) |
| `collision` | — | Collision flag (0/1) |

## `events.json` — ground-truth timeline

```json
{
  "scenario": "pedestrian_crossing",
  "triggers": [ { "frame": 80, "t_s": 4.0, "event": "pedestrian_detected", "dist_m": 23.8 } ],
  "collisions": []
}
```

## `frames/*.png` — chase-camera evidence

One PNG per captured frame (configurable cadence), suitable for review clips
and customer deliverables.

## `summary.json` — scored KPIs

```json
{
  "scenario": "pedestrian_crossing",
  "verdict": "PASS",
  "risk_level": "low",
  "max_speed_kmh": 48.6,
  "min_ttc_s": 1.49,
  "min_gap_m": 9.4,
  "max_decel_mps2": 4.10,
  "aeb_activations": 1,
  "collisions": 0,
  "regulatory_ref": "CA DMV AV Program - VRU Interaction"
}
```

See [`samples/summary.sample.json`](../samples/summary.sample.json) and
[`samples/telemetry.sample.csv`](../samples/telemetry.sample.csv) for full
examples.
