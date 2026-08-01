#!/usr/bin/env python
"""Fault-tolerant batch recorder: runs scenarios one by one with --record,
auto-restarting the CARLA server if it crashes between scenarios.

Usage:
    python tools/record_suite.py                          # all 15 scenarios
    python tools/record_suite.py --only red_light_violation sudden_brake
    python tools/record_suite.py --carla "D:/Carla/CARLA_0.9.16/CarlaUE4.exe"

Produces one outputs/<timestamp>/ folder per scenario (run_sim.py behaviour)
and an MP4 inside each run's videos/ subfolder.
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

DEFAULT_CARLA = r"D:\Carla\CARLA_0.9.16\CarlaUE4.exe"
CARLA_ARGS = ["-quality-level=Low", "-windowed", "-ResX=1280", "-ResY=720",
              "-carla-rpc-port=2000"]


def server_alive(timeout=6.0) -> bool:
    try:
        import carla
        c = carla.Client("127.0.0.1", 2000)
        c.set_timeout(timeout)
        c.get_server_version()
        return True
    except Exception:  # noqa: BLE001
        return False


def start_server(carla_exe: str, wait_s: int = 120) -> bool:
    exe = Path(carla_exe)
    if not exe.exists():
        print(f"[record_suite] CARLA exe not found: {exe}")
        return False
    print("[record_suite] starting CARLA server ...")
    subprocess.Popen([str(exe), *CARLA_ARGS], cwd=str(exe.parent),
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + wait_s
    while time.time() < deadline:
        if server_alive():
            print("[record_suite] server is up.")
            time.sleep(3)          # settle
            return True
        time.sleep(4)
    print("[record_suite] server did not come up in time.")
    return False


def ensure_server(carla_exe: str) -> bool:
    return server_alive() or start_server(carla_exe)


def run_one(name: str, duration: float) -> bool:
    cmd = [sys.executable, "-u", str(REPO / "run_sim.py"),
           "--scenario", name, "--duration", str(duration), "--record"]
    print(f"[record_suite] >>> {name}")
    proc = subprocess.run(cmd, cwd=str(REPO))
    return proc.returncode == 0


def main():
    from config.settings import load_scenarios
    meta = load_scenarios()

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--only", nargs="*", default=None,
                   help="subset of scenario names (default: all)")
    p.add_argument("--duration", type=float, default=30.0)
    p.add_argument("--carla", default=DEFAULT_CARLA,
                   help="path to CarlaUE4.exe for auto-restart")
    p.add_argument("--retries", type=int, default=2,
                   help="max attempts per scenario")
    args = p.parse_args()

    names = args.only if args.only else sorted(meta.keys())
    unknown = [n for n in names if n not in meta]
    if unknown:
        print(f"Unknown scenarios: {unknown}")
        return 1

    ok, failed = [], []
    for name in names:
        done = False
        for attempt in range(1, args.retries + 1):
            if not ensure_server(args.carla):
                print("[record_suite] cannot ensure server - aborting.")
                failed.extend(names[names.index(name):])
                _summary(ok, failed)
                return 1
            if run_one(name, args.duration):
                ok.append(name)
                done = True
                break
            print(f"[record_suite] {name} attempt {attempt} failed "
                  "(server may have crashed) - retrying.")
        if not done:
            failed.append(name)
    _summary(ok, failed)
    return 0 if not failed else 1


def _summary(ok, failed):
    print("=" * 60)
    print(f"[record_suite] OK ({len(ok)}): {', '.join(ok) or '-'}")
    if failed:
        print(f"[record_suite] FAILED ({len(failed)}): {', '.join(failed)}")


if __name__ == "__main__":
    sys.exit(main())
