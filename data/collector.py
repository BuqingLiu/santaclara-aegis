"""20 Hz telemetry + ground-truth event recorder.

Per frame: ego kinematics + control, nearest-threat gap, TTC.
Outputs:  telemetry.csv | events.json | summary.json | frames/*.png
"""
import csv
import json
import math
from pathlib import Path

from utils.logger import get_logger

log = get_logger("collector")

FIELDS = ["frame", "sim_time_s", "ego_x", "ego_y", "ego_speed_mps",
          "throttle", "brake", "steer", "nearest_threat_gap_m", "ttc_s",
          "event_active", "collision"]


class DataCollector:
    def __init__(self, scenario_name, meta, output_root):
        self.scenario = scenario_name
        self.meta = meta
        self.dir = Path(output_root) / scenario_name
        self.frames_dir = self.dir / "frames"
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self.rows = []
        self.events = []
        self.collision_events = []
        self._prev_gap = {}
        self._event_active = False

    # ------------------------------------------------------------------ #
    def mark_event(self, label, frame, data=None):
        self._event_active = True
        self.events.append({"label": label, "frame": frame,
                            "data": data or {}})

    def on_collision(self, event):
        # ignore static props (cones, debris) - they don't represent a real
        # safety outcome, they only inflate the collision count
        other = event.other_actor
        if other is None or other.type_id.startswith("static."):
            return
        imp = event.normal_impulse
        rec = {"frame": event.frame, "other_actor": other.type_id,
               "impulse": round(math.sqrt(imp.x ** 2 + imp.y ** 2
                                          + imp.z ** 2), 1)}
        self.collision_events.append(rec)
        log.warning("COLLISION with %s (frame %s)", other.type_id, event.frame)

    # ------------------------------------------------------------------ #
    def record_frame(self, frame, sim_time, ego, threats):
        v = ego.get_velocity()
        speed = math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)
        ctrl = ego.get_control()
        ego_loc = ego.get_location()

        gap, ttc = float("nan"), float("nan")
        for t in threats:
            if not t.is_alive:
                continue
            d = ego_loc.distance(t.get_location()) - 4.0  # bumper allowance
            d = max(d, 0.05)
            if math.isnan(gap) or d < gap:
                gap = d
                # closing speed along the line-of-sight
                tv = t.get_velocity()
                rel = t.get_location() - ego_loc
                rng = max(ego_loc.distance(t.get_location()), 0.1)
                ux, uy = rel.x / rng, rel.y / rng
                closing = (v.x - tv.x) * ux + (v.y - tv.y) * uy
                ttc = d / closing if closing > 0.25 else float("nan")

        self.rows.append({
            "frame": frame, "sim_time_s": round(sim_time, 3),
            "ego_x": round(ego_loc.x, 2), "ego_y": round(ego_loc.y, 2),
            "ego_speed_mps": round(speed, 3),
            "throttle": round(ctrl.throttle, 3),
            "brake": round(ctrl.brake, 3),
            "steer": round(ctrl.steer, 3),
            "nearest_threat_gap_m": (round(gap, 3)
                                     if not math.isnan(gap) else ""),
            "ttc_s": round(ttc, 3) if not math.isnan(ttc) else "",
            "event_active": int(self._event_active),
            "collision": int(any(c["frame"] >= frame - 1
                                 for c in self.collision_events)),
        })

    # ------------------------------------------------------------------ #
    def save(self):
        with open(self.dir / "telemetry.csv", "w", newline="",
                  encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(self.rows)
        with open(self.dir / "events.json", "w", encoding="utf-8") as f:
            json.dump({"scenario": self.scenario,
                       "title": self.meta.get("title", ""),
                       "dmv_ref": self.meta.get("dmv_ref", ""),
                       "events": self.events,
                       "collisions": self.collision_events}, f, indent=2)
        log.info("Saved %d telemetry rows, %d events -> %s",
                 len(self.rows), len(self.events), self.dir)

    def save_summary(self, metrics):
        with open(self.dir / "summary.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
