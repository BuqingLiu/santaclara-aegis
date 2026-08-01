"""Global configuration — tuned for laptop-friendly (low CPU/GPU) operation."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CONFIG = {
    # -- connection --------------------------------------------------------
    "host": os.environ.get("CARLA_HOST", "127.0.0.1"),
    "port": int(os.environ.get("CARLA_PORT", 2000)),
    "tm_port": int(os.environ.get("CARLA_TM_PORT", 8000)),
    "timeout": 30.0,

    # -- determinism / performance (laptop profile) -------------------------
    "sync_mode": True,
    "fixed_delta_seconds": 0.05,      # 20 Hz simulation step
    "tm_seed": 2026,                  # deterministic Traffic Manager
    "map": "Town10HD_Opt",            # urban map closest to Santa Clara grid
    "region": "santa_clara",          # real-road region when --map custom
    "unload_heavy_layers": True,      # strip parked cars/props to save GPU

    # -- ego ----------------------------------------------------------------
    "ego_model": "vehicle.tesla.model3",
    "ego_speed_boost_pct": -5,        # slightly above TM default flow speed
    "max_speed_mps": 16.0,            # global TM cap (m/s) -> ~58 km/h urban.
                                      # Critical on OSM maps where CARLA infers
                                      # no/garbage speed limit and floors it.

    # -- background traffic (richer street life; still laptop-friendly) ------
    "background_vehicles": 22,        # moving ambient traffic
    "background_walkers": 8,          # sidewalk pedestrians (kinematic on OSM)
    "parked_vehicles": 14,            # roadside parked cars: visual richness
                                      # on bare OSM-derived maps (no buildings)

    # -- sensors --------------------------------------------------------------
    "camera": {"width": 960, "height": 540, "fov": 90,
               "x": -7.0, "z": 3.4, "pitch": -14.0,
               "save_every_n_frames": 20},

    # -- compliance thresholds (used by data/postprocess.py) -----------------
    "thresholds": {
        "ttc_pass_s": 1.0,            # min TTC above this => PASS candidate
        "hard_brake_mps2": 4.6,       # decel beyond this counts as hard brake
        "min_gap_review_m": 1.5,      # closest approach below this => REVIEW
    },
}


def load_scenarios():
    with open(ROOT / "config" / "scenarios.json", encoding="utf-8") as f:
        return json.load(f)
