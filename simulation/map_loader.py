"""Real-road map pipeline: download OSM -> convert to OpenDRIVE -> load.

This is the bridge between "a real intersection in Santa Clara / San Jose"
and CARLA's road-network engine. Everything downstream (spawn helpers,
scenarios, sensors) is already map-agnostic, so once the real road is
loaded the same 15+ scenarios run on it unchanged.

Design choices (reliability first):
  * Download uses the public Overpass API (no API key, no manual click).
    A client only needs to give a bounding box (or an OSM export URL).
  * Conversion uses CARLA's built-in carla.Osm2Odr.convert -- no third-party
    toolchain, no RoadRunner, nothing to break.
  * Loading uses generate_opendrive_world with a tuned OpendriveGenerationParameters
    that is known to render cleanly on 0.9.16.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import carla

from utils.logger import get_logger

log = get_logger("map_loader")

# Preset regions. Swap these for any client's coordinates later.
REGIONS = {
    "santa_clara": {
        "label": "Santa Clara - Central Expressway x Lawrence Expy",
        "center": (37.3562, -121.9531),
        "bbox": (-121.9601, 37.3512, -121.9461, 37.3612),  # minlon,minlat,maxlon,maxlat (~1.3 km^2)
        "note": "Central Expressway + Lawrence Expy corridor, Santa Clara.",
    },
    "san_jose": {
        "label": "San Jose Downtown",
        "center": (37.3382, -121.8826),
        "bbox": (-121.8896, 37.3332, -121.8756, 37.3432),
        "note": "Dense downtown grid, high intersection density.",
    },
}

OVERPASS_ENDPOINTS = (
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
    "https://overpass-api.de/api/interpreter",
)


def _overpass_query(bbox) -> str:
    minlon, minlat, maxlon, maxlat = bbox
    # Full map data (not just highways) so junctions + traffic lights come through.
    return f"""
[out:xml][timeout:120];
(
  way["highway"]({minlat},{minlon},{maxlat},{maxlon});
  node["highway"="traffic_signals"]({minlat},{minlon},{maxlat},{maxlon});
  relation["type"="restriction"]({minlat},{minlon},{maxlat},{maxlon});
);
out body;
>;
out skel qt;
"""


def auto_download_osm(target: Path, *, bbox=None, url: Optional[str] = None,
                      timeout: float = 90.0) -> bool:
    """Fetch an OSM extract. Returns True on success.

    target: where to write the .osm file.
    bbox:   (minlon, minlat, maxlon, maxlat) or a REGIONS key.
    url:    an Overpass/export URL (overrides bbox when provided).
    """
    import requests

    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)

    if url:
        log.info("Downloading OSM from URL: %s", url)
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            target.write_text(r.text, encoding="utf-8")
            log.info("Saved OSM (%d bytes) -> %s", len(r.text), target)
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("URL download failed: %s", exc)
            return False

    if isinstance(bbox, str):
        bbox = REGIONS[bbox]["bbox"]

    query = _overpass_query(bbox)
    headers = {"Accept": "application/xml; charset=utf-8"}
    last_err = None
    for attempt in range(2):  # one retry after a backoff
        for ep in OVERPASS_ENDPOINTS:
            try:
                log.info("Querying Overpass %s for bbox %s (attempt %d)",
                         ep, bbox, attempt + 1)
                r = requests.post(ep, data={"data": query}, headers=headers,
                                  timeout=timeout)
                r.raise_for_status()
                if "<way" not in r.text and "<node" not in r.text:
                    raise ValueError("response contained no OSM primitives")
                target.write_text(r.text, encoding="utf-8")
                log.info("Saved OSM (%d bytes) -> %s", len(r.text), target)
                return True
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                log.warning("Overpass %s failed: %s", ep, exc)
                time.sleep(3.0)
    log.error("All Overpass endpoints failed: %s", last_err)
    return False


def convert_osm_to_xodr(osm_path: Path, xodr_path: Optional[Path] = None) -> Path:
    """Convert .osm -> .xodr using CARLA's built-in OSM2ODR."""
    osm_path = Path(osm_path)
    xodr_path = Path(xodr_path) if xodr_path else osm_path.with_suffix(".xodr")

    settings = carla.Osm2OdrSettings()
    settings.generate_traffic_lights = True
    settings.center_map = True
    settings.default_lane_width = 3.5

    log.info("Converting %s -> OpenDRIVE ...", osm_path.name)
    xodr_text = carla.Osm2Odr.convert(osm_path.read_text(encoding="utf-8"),
                                      settings)
    xodr_path.write_text(xodr_text, encoding="utf-8")
    log.info("OpenDRIVE written -> %s", xodr_path)
    return xodr_path


def load_xodr_world(client, xodr_path: Path, *, vertex_distance: float = 2.0,
                    wall_height: float = 0.0, additional_width: float = 0.6):
    """Generate the road network live in the running CARLA server."""
    xodr_path = Path(xodr_path)
    params = carla.OpendriveGenerationParameters(
        vertex_distance=vertex_distance,
        max_road_length=200.0,
        wall_height=wall_height,
        additional_width=additional_width,
        smooth_junctions=True,
        enable_mesh_visibility=True,
    )
    log.info("Generating real-road world in CARLA from %s ...", xodr_path.name)
    world = client.generate_opendrive_world(
        xodr_path.read_text(encoding="utf-8"), params)
    log.info("Real-road world loaded. Actors present: %d",
             len(world.get_actors()))
    return world


def load_real_map(session, region: str = "santa_clara",
                  osm_path: Optional[Path] = None,
                  force_download: bool = False) -> object:
    """Full automated flow: ensure .osm (download if missing) -> .xodr -> world.

    Returns the loaded CARLA world. Falls back to the stock map only if
    every conversion/load step fails (so a demo never hard-crashes).
    """
    root = Path(__file__).resolve().parent.parent
    region_key = region if region in REGIONS else "santa_clara"
    meta = REGIONS[region_key]

    if osm_path is None:
        osm_path = root / "maps" / f"{region_key}.osm"
    osm_path = Path(osm_path)
    xodr_path = osm_path.with_suffix(".xodr")

    if not osm_path.exists() or force_download:
        ok = auto_download_osm(osm_path, bbox=region_key)
        if not ok:
            log.warning("OSM download failed -> falling back to stock map.")
            return session.load_map()  # existing stock loader

    try:
        if not xodr_path.exists() or force_download:
            convert_osm_to_xodr(osm_path, xodr_path)
        world = load_xodr_world(session.client, xodr_path)
        # mark the loaded map name so downstream sync/restore works
        session.world = world
        return world
    except Exception as exc:  # noqa: BLE001
        log.error("Real-map load failed (%s) -> falling back to stock map.",
                  exc)
        return session.load_map()
