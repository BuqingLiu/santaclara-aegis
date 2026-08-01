#!/usr/bin/env python
"""Encode captured forensic frames into MP4 demo videos.

Usage (standalone):
    python tools/frames_to_video.py outputs/20260729_2049          # whole run
    python tools/frames_to_video.py outputs/20260729_2049 --fps 10

Also called automatically by  run_sim.py --record .

Each scenario folder (containing frames/frame_*.png) becomes
<run_dir>/videos/<scenario>.mp4 with a title card and a HUD overlay
(scenario name + sim time), ready to use as sales / demo material.
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

# make repo root importable when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.logger import get_logger  # noqa: E402

log = get_logger("video")

FOURCC = cv2.VideoWriter_fourcc(*"mp4v")


def _title_card(size, title, subtitle, frames=20):
    w, h = size
    card = np.zeros((h, w, 3), dtype=np.uint8)
    card[:] = (24, 18, 12)                      # dark navy-ish
    cv2.putText(card, title, (40, h // 2 - 20),
                cv2.FONT_HERSHEY_DUPLEX, 1.1, (255, 255, 255), 2,
                cv2.LINE_AA)
    cv2.putText(card, subtitle, (40, h // 2 + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (180, 200, 255), 1,
                cv2.LINE_AA)
    cv2.putText(card, "CARLA 0.9.x | Santa Clara SafetySim Pipeline",
                (40, h - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                (120, 140, 170), 1, cv2.LINE_AA)
    return [card] * frames


def _hud(img, scenario, sim_t, result=None):
    """Small overlay bar: scenario name + sim time (+ verdict)."""
    h, w = img.shape[:2]
    cv2.rectangle(img, (0, 0), (w, 34), (30, 22, 16), -1)
    text = f"{scenario}   t={sim_t:6.2f}s"
    cv2.putText(img, text, (12, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (255, 255, 255), 1, cv2.LINE_AA)
    if result:
        color = {"PASS": (90, 200, 90), "REVIEW": (60, 190, 255),
                 "FAIL": (70, 70, 230)}.get(result, (200, 200, 200))
        cv2.putText(img, result, (w - 110, 23), cv2.FONT_HERSHEY_DUPLEX,
                    0.65, color, 2, cv2.LINE_AA)
    return img


def encode_scenario(scn_dir: Path, out_path: Path, fps: int = 10,
                    dt: float = 0.05) -> bool:
    # RGB frames live under frames/rgb/ (multi-sensor layout); older runs
    # saved them flat under frames/. Support both.
    frame_dir = scn_dir / "frames" / "rgb"
    if not list(frame_dir.glob("frame_*.png")):
        frame_dir = scn_dir / "frames"
    frames = sorted(frame_dir.glob("frame_*.png"))
    if len(frames) < 5:
        log.warning("%s: only %d frames - skipped", scn_dir.name, len(frames))
        return False

    first = cv2.imread(str(frames[0]))
    if first is None:
        return False
    h, w = first.shape[:2]

    # verdict + title from summary.json if present
    result, title = None, scn_dir.name
    summary = scn_dir / "summary.json"
    if summary.exists():
        try:
            meta = json.loads(summary.read_text(encoding="utf-8"))
            result = meta.get("result")
            title = meta.get("title", scn_dir.name)
        except Exception:  # noqa: BLE001
            pass

    out_path.parent.mkdir(parents=True, exist_ok=True)
    vw = cv2.VideoWriter(str(out_path), FOURCC, fps, (w, h))
    for card in _title_card((w, h), title, scn_dir.name):
        vw.write(card)

    for fp in frames:
        img = cv2.imread(str(fp))
        if img is None:
            continue
        if img.shape[:2] != (h, w):
            img = cv2.resize(img, (w, h))
        sim_frame = int(fp.stem.split("_")[1])
        vw.write(_hud(img, scn_dir.name, sim_frame * dt, result))
    vw.release()
    log.info("Encoded %-24s -> %s (%d frames @ %d fps)",
             scn_dir.name, out_path.name, len(frames), fps)
    return True


def encode_run(run_dir, fps: int = 10):
    """Encode every scenario folder in a run directory; returns video list."""
    run_dir = Path(run_dir)
    videos_dir = run_dir / "videos"
    made = []
    for scn_dir in sorted(run_dir.iterdir()):
        if not scn_dir.is_dir() or not (scn_dir / "frames").exists():
            continue
        out = videos_dir / f"{scn_dir.name}.mp4"
        if encode_scenario(scn_dir, out, fps=fps):
            made.append(out)
    if made:
        log.info("Video pack ready: %s (%d clips)", videos_dir.resolve(),
                 len(made))
    else:
        log.warning("No scenario frame folders found under %s", run_dir)
    return made


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run_dir", help="run folder, e.g. outputs/20260729_2049")
    p.add_argument("--fps", type=int, default=10)
    args = p.parse_args()
    encode_run(args.run_dir, fps=args.fps)


if __name__ == "__main__":
    main()
