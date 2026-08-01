#!/usr/bin/env python
"""OpenStreetMap -> OpenDRIVE converter for the real Santa Clara corridor.

Workflow (see maps/README.md):
  1. Export OSM XML of the corridor, e.g. bbox
     37.3661,-122.0043 -> 37.3749,-121.9890  (El Camino Real x Lawrence Expy)
  2. python tools/osm_to_xodr.py maps/elcamino_lawrence.osm
  3. python tools/osm_to_xodr.py --load maps/elcamino_lawrence.xodr
     (generates the road network live in the running CARLA server)
"""
import argparse
from pathlib import Path

import carla


def convert(osm_path: Path) -> Path:
    settings = carla.Osm2OdrSettings()
    settings.generate_traffic_lights = True
    settings.center_map = True
    xodr = carla.Osm2Odr.convert(osm_path.read_text(encoding="utf-8"),
                                 settings)
    out = osm_path.with_suffix(".xodr")
    out.write_text(xodr, encoding="utf-8")
    print(f"OpenDRIVE written: {out}")
    return out


def load(xodr_path: Path, host="127.0.0.1", port=2000):
    client = carla.Client(host, port)
    client.set_timeout(120.0)
    params = carla.OpendriveGenerationParameters(
        vertex_distance=2.0, max_road_length=200.0, wall_height=0.0,
        additional_width=0.6, smooth_junctions=True, enable_mesh_visibility=True)
    client.generate_opendrive_world(
        xodr_path.read_text(encoding="utf-8"), params)
    print("Custom El Camino x Lawrence world loaded in CARLA.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("path", type=Path, help=".osm to convert or .xodr to load")
    p.add_argument("--load", action="store_true",
                   help="load the .xodr into the running server")
    a = p.parse_args()
    if a.load or a.path.suffix == ".xodr":
        load(a.path)
    else:
        load(convert(a.path)) if a.load else convert(a.path)
