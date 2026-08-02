---
title: "Reproducing a Night Pedestrian-Crossing Edge Case in CARLA (with Telemetry)"
published: true
tags: carla, simulation, autonomousvehicles, python
---

# Reproducing a Night Pedestrian-Crossing Edge Case in CARLA (with Telemetry)

Edge cases are only useful if you can **reproduce them on demand**. Here is a concrete, minimal pattern for one of the highest-risk AV scenarios: a pedestrian stepping into the ego lane at night, from behind a parked vehicle (occlusion).

## Why this case matters
- Night + low contrast → perception latency spikes.
- Occlusion → the pedestrian appears late.
- The combination is exactly where SOTIF unknown-unsafe gaps hide.

## The reproducible skeleton
```python
import carla

def spawn_occluder(world, x, y):
    bp = world.get_blueprint_library().find('static.prop.container')
    t = carla.Transform(carla.Location(x=x, y=y, z=0.0))
    return world.spawn_actor(bp, t)

def spawn_ped(world, x, y, speed):
    bp = world.get_blueprint_library().find('walker.pedestrian.0001')
    t = carla.Transform(carla.Location(x=x, y=y, z=0.0))
    ped = world.spawn_actor(bp, t)
    ped.apply_control(carla.WalkerControl(
        direction=carla.Vector3D(-1, 0, 0), speed=speed))
    return ped

# Record telemetry each tick: ego speed, TTC, ped distance
def record(world, ego, ped, log):
    t = world.get_snapshot().timestamp.elapsed_seconds
    v = ego.get_velocity()
    speed = 3.6 * (v.x**2 + v.y**2 + v.z**2)**0.5
    d = ego.get_location().distance(ped.get_location())
    log.append({"t": round(t,2), "ego_kmh": round(speed,1), "dist_m": round(d,2)})
```

## What good output looks like
- A deterministic seed so the run is identical every time.
- A telemetry CSV: `t, ego_kmh, dist_m, TTC`.
- A pass/fail rule, e.g. *ego reached safe stop before dist_m < 2.0 m*.

## The catch
Writing 23 of these by hand — each tuned for weather, actor behavior, and compliance tags — is 6–10 weeks of engineering. That is the part most teams under-estimate.

---

### Skip the build, keep the evidence
We ship 23 pre-built safety-critical scenarios (telemetry CSV + reproducible CARLA script + compliance tags) including this exact night pedestrian case. Try the free sample:

- Free sample → https://buqingliu.github.io/santaclara-aegis/samples/sample-scenario.html
- Library & pricing → https://buqingliu.github.io/santaclara-aegis/
- Custom scenarios for your ODD → https://t.me/santaclaraaegis_bot

What scenario is blocking your validation right now? Describe it to the bot and we'll scope it.
