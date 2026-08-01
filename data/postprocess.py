"""Compliance metric computation & scoring.

Metrics: min TTC, min gap, max deceleration, hard-brake count, speeds.
Scoring: FAIL   = collision occurred
         REVIEW = min TTC below threshold or extremely small gap
         PASS   = event handled with safe margins
"""


def compute_metrics(collector, thresholds, dt):
    rows = collector.rows
    speeds = [r["ego_speed_mps"] for r in rows]
    ttcs = [r["ttc_s"] for r in rows
            if r["ttc_s"] != "" and r["event_active"]]
    gaps = [r["nearest_threat_gap_m"] for r in rows
            if r["nearest_threat_gap_m"] != ""]

    # deceleration series from speed differences.
    # NOTE: filter physically-impossible spikes (> 12 m/s^2 exceeds any
    # production brake; such values come from simulator velocity resets /
    # collision impulses, not real braking) so DMV metrics stay credible.
    PHYS_MAX_DECEL = 12.0
    max_decel, hard_brakes, in_brake = 0.0, 0, False
    for i in range(1, len(speeds)):
        decel = (speeds[i - 1] - speeds[i]) / dt
        if decel > PHYS_MAX_DECEL:
            in_brake = False
            continue
        max_decel = max(max_decel, decel)
        if decel > thresholds["hard_brake_mps2"]:
            if not in_brake:
                hard_brakes += 1
                in_brake = True
        else:
            in_brake = False

    min_ttc = round(min(ttcs), 2) if ttcs else None
    min_gap = round(min(gaps), 2) if gaps else None
    collisions = len(collector.collision_events)

    if collisions > 0:
        result = "FAIL"
    elif ((min_ttc is not None and min_ttc < thresholds["ttc_pass_s"])
          or (min_gap is not None
              and min_gap < thresholds["min_gap_review_m"])):
        result = "REVIEW"
    else:
        result = "PASS"

    return {
        "scenario": collector.scenario,
        "title": collector.meta.get("title", ""),
        "dmv_ref": collector.meta.get("dmv_ref", ""),
        "frames": len(rows),
        "duration_s": round(len(rows) * dt, 1),
        "avg_speed_mps": round(sum(speeds) / len(speeds), 2) if speeds else 0,
        "max_speed_mps": round(max(speeds), 2) if speeds else 0,
        "min_ttc_s": min_ttc,
        "min_gap_m": min_gap,
        "max_decel_mps2": round(max_decel, 2),
        "hard_brake_count": hard_brakes,
        "collision_count": collisions,
        "events_triggered": [e["label"] for e in collector.events],
        "result": result,
    }
