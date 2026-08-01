# Real-Road Mapping — El Camino Real × Lawrence Expressway

The pipeline runs out-of-the-box on CARLA's stock urban map (`Town10HD_Opt`),
because every scenario is built from **relative road topology** (lanes,
junctions, signals) — not hardcoded coordinates.

To run the same 15 scenarios on the **actual Santa Clara corridor**:

## 1. Export the OSM extract

Bounding box covering the intersection and approaches:

```
south=37.3661  west=-122.0043  north=37.3749  east=-121.9890
```

Either download from https://www.openstreetmap.org/export with that bbox,
or via Overpass API:

```
https://overpass-api.de/api/map?bbox=-122.0043,37.3661,-121.9890,37.3749
```

Save as `maps/elcamino_lawrence.osm` (not committed — ODbL licensing and
file size; each client receives their own extract).

## 2. Convert to OpenDRIVE

```bash
python tools/osm_to_xodr.py maps/elcamino_lawrence.osm
```

## 3. Load it into the running CARLA server

```bash
python tools/osm_to_xodr.py --load maps/elcamino_lawrence.xodr
python run_sim.py --all --report          # same suite, real corridor
```

For photoreal deliverables (client premium tier), the `.xodr` is imported
into RoadRunner / UE4 with aerial imagery — contact for the managed service.
