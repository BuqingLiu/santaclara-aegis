# Getting Started (reference layer)

This guide runs the **open reference layer** against a local CARLA server.
Running the full suite requires the proprietary `elite/` engine, which is
delivered to subscribers — see the [sales page](https://github.com/BuqingLiu/santaclara-aegis).

## Prerequisites

- **CARLA 0.9.14 – 0.9.16** (any package build).
- **Python 3.7 – 3.12** (the `carla` wheel must match your server version).
- Windows / Linux.

## 1. Start CARLA

```bat
CarlaUE4.exe -quality-level=Low -windowed -ResX=960 -ResY=540
```

## 2. Install client dependencies

```bash
pip install -r requirements.txt
```

## 3. Run a scenario (with the engine)

```bash
python run_sim.py --scenario pedestrian_crossing --duration 40
python run_sim.py --all --duration 30 --report      # full suite + report
python run_all.py                                    # auto-starts CARLA too
```

## 4. Real-corridor maps

Scenarios are topology-driven, so they transfer to a client's actual corridor.
To target the Santa Clara corridor (El Camino Real × Lawrence Expressway):

```bash
python tools/osm_to_xodr.py maps/elcamino_lawrence.osm     # OSM -> OpenDRIVE
python tools/osm_to_xodr.py --load maps/elcamino_lawrence.xodr
python run_sim.py --all --report                            # same suite, real corridor
```

See [`maps/README.md`](../maps/README.md) for the OSM extract bounding box and
the photoreal (RoadRunner / UE4) premium path.

## 5. Review the data

Each run writes `outputs/<timestamp>/<scenario>/` with `telemetry.csv`,
`events.json`, `frames/`, and `summary.json`, plus a consolidated
`compliance_report.pdf / .md`. The schema is documented in
[`data-schema.md`](data-schema.md).

## Note on the proprietary core

`core_engine.py` and the scenario runners import `elite`. In this public
repository `elite/` contains documentation only; the runnable engine is
provided under subscription. The reference layer is published so you can review
scenario definitions, the CARLA client, the sensor rig, and sample datasets.
