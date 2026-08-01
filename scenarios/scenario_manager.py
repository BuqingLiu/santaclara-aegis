"""Execution engine: spawns the ego, runs a scenario deterministically,
records telemetry, and guarantees teardown even on Ctrl-C."""
import time

import carla

from data.collector import DataCollector
from data.postprocess import compute_metrics
from scenarios.base_scenario import ScenarioContext
from scenarios.safety_events import REGISTRY
from simulation import world_utils as wu
from simulation.sensors import SensorRig
from utils.logger import get_logger

log = get_logger("manager")


class ScenarioManager:
    def __init__(self, session, config, scenario_meta, output_root):
        self.session = session
        self.cfg = config
        self.meta_all = scenario_meta
        self.output_root = output_root
        self._capture_video = False  # set True when --record is passed
        self._ego_capped = False     # stateful hard speed-cap latch
        self._weather_presets = {
            "Night": carla.WeatherParameters(
                cloudiness=40.0, precipitation=0.0,
                sun_altitude_angle=-25.0, fog_density=4.0),
        }

    # ------------------------------------------------------------------ #
    def _apply_weather(self, name):
        world = self.session.world
        if name in self._weather_presets:
            world.set_weather(self._weather_presets[name])
        else:
            world.set_weather(getattr(carla.WeatherParameters, name,
                                      carla.WeatherParameters.ClearNoon))

    def _spawn_ego(self, needs):
        world, world_map = self.session.world, self.session.world.get_map()
        bp = world.get_blueprint_library().find(self.cfg["ego_model"])
        bp.set_attribute("role_name", "ego")
        cap = float(self.cfg.get("max_speed_mps", 16.0))

        # Try each candidate spawn, keeping the first one where the ego
        # actually drives freely. On OSM-derived OpenDRIVE, CARLA's auto
        # spawn points frequently sit inside malformed junction meshes and
        # eject the vehicle (the 322/562 km/h "mutation"). A waypoint-derived
        # candidate that lets the car move is the fix.
        for tf, _jd in wu.ego_spawn_candidates(world_map, needs):
            ego = wu.try_spawn(world, bp, tf)
            if ego is None:
                continue
            if self._spawn_is_free(world, world_map, ego, cap):
                self._ego_cap = cap
                self._ego_gov = wu.EgoGovernor(ego, world_map, cap * 0.85)
                return ego
            # stuck in malformed mesh -> discard and try the next candidate
            try:
                if ego.is_alive:
                    ego.destroy()
                    world.tick()
            except Exception:  # noqa: BLE001
                pass

        # Last resort: fall back to the first auto spawn point (may be rough,
        # but at least the scenario runs; the hard_clamp net still protects).
        spawn, _ = wu.find_ego_spawn(world_map, needs)
        ego = wu.try_spawn(world, bp, spawn)
        if ego is None:
            for sp in world_map.get_spawn_points():
                ego = wu.try_spawn(world, bp, sp)
                if ego:
                    break
        if ego is None:
            raise RuntimeError("Could not spawn ego vehicle on this map.")
        log.warning("Ego spawned at fallback point (mesh may be imperfect).")
        self._ego_cap = cap
        self._ego_gov = wu.EgoGovernor(ego, world_map, cap * 0.85)
        return ego

    def _spawn_is_free(self, world, world_map, ego, cap):
        """Drive the ego a moment with a probe governor; if it translates,
        the spawn is on clean road. Returns False if it is stuck (would be
        ejected by the physics solver)."""
        try:
            probe = wu.EgoGovernor(ego, world_map, min(cap, 8.0))
            for _ in range(5):
                world.tick()
            start = ego.get_location()
            for _ in range(14):
                world.tick()
                probe.step()
            end = ego.get_location()
            return start.distance(end) > 1.0
        except Exception:  # noqa: BLE001
            return False

    def _spawn_background(self, count, exclude_radius, ego):
        """Light ambient traffic, kept away from the scripted event zone."""
        world = self.session.world
        bps = [b for b in world.get_blueprint_library().filter("vehicle.*")
               if int(b.get_attribute("number_of_wheels")) == 4]
        spawned = []
        for sp in world.get_map().get_spawn_points():
            if len(spawned) >= count:
                break
            if sp.location.distance(ego.get_location()) < exclude_radius:
                continue
            v = world.try_spawn_actor(bps[len(spawned) % len(bps)], sp)
            if v is not None:
                v.set_autopilot(True, self.cfg["tm_port"])
                spawned.append(v)
        log.info("Background traffic: %d vehicles", len(spawned))
        return spawned

    def _spawn_street_life(self, ego):
        """Visual richness for bare OSM maps (no buildings): parked cars
        along the ego's upcoming route + pedestrians standing roadside.
        All static/kinematic — they cannot collide-launch anything."""
        world = self.session.world
        world_map = world.get_map()
        lib = world.get_blueprint_library()
        car_bps = [b for b in lib.filter("vehicle.*")
                   if int(b.get_attribute("number_of_wheels")) == 4]
        walker_bps = list(lib.filter("walker.pedestrian.*"))
        props = []
        n_parked = int(self.cfg.get("parked_vehicles", 0))
        n_walk = int(self.cfg.get("background_walkers", 0))
        try:
            wp = world_map.get_waypoint(ego.get_location())
            for i in range(max(n_parked, n_walk)):
                nxt = wp.next(18.0 + 9.0 * i)
                if not nxt:
                    break
                base = nxt[0]
                # parked car on the right edge (alternate sides a bit)
                if i < n_parked:
                    side = 3.4 if i % 3 else -3.4
                    # lateral_offset returns a Location -> wrap into Transform
                    loc = wu.lateral_offset(base.transform, side)
                    rot = carla.Rotation(
                        pitch=base.transform.rotation.pitch,
                        yaw=base.transform.rotation.yaw
                        + (180.0 if side < 0 else 0.0),
                        roll=base.transform.rotation.roll)
                    tf = carla.Transform(loc, rot)
                    v = wu.try_spawn(world, car_bps[i % len(car_bps)], tf)
                    if v is not None:
                        v.apply_control(carla.VehicleControl(
                            throttle=0.0, brake=1.0, hand_brake=True))
                        props.append(v)
                # pedestrian on the sidewalk
                if i < n_walk and walker_bps:
                    loc = wu.lateral_offset(base.transform, 5.2)
                    tf = carla.Transform(loc, base.transform.rotation)
                    w = wu.try_spawn(world, walker_bps[i % len(walker_bps)],
                                     tf)
                    if w is not None:
                        props.append(w)
        except Exception as exc:  # noqa: BLE001
            log.info("street life partial: %s", exc)
        log.info("Street life: %d parked cars / pedestrians", len(props))
        return props

    # ------------------------------------------------------------------ #
    def run(self, name, duration=35.0):
        if name not in REGISTRY:
            raise KeyError(f"Unknown scenario '{name}'. "
                           f"Available: {', '.join(sorted(REGISTRY))}")
        meta = self.meta_all[name]
        scenario = REGISTRY[name](meta)
        log.info("=" * 62)
        log.info("SCENARIO %-24s | %s", name, meta["title"])
        log.info("=" * 62)

        self._apply_weather(meta.get("weather", "ClearNoon"))
        ego = self._spawn_ego(scenario.NEEDS)
        background = self._spawn_background(
            self.cfg["background_vehicles"], exclude_radius=70.0, ego=ego)
        background += self._spawn_street_life(ego)

        collector = DataCollector(name, meta, self.output_root)
        rig = SensorRig(self.session.world, ego, self.cfg["camera"],
                        collector.frames_dir, collector.on_collision,
                        capture_video=getattr(self, "_capture_video", False))
        ctx = ScenarioContext(self.session.world, self.session.client,
                              self.session.tm, self.cfg["tm_port"],
                              ego, collector, self.cfg)

        dt = self.cfg["fixed_delta_seconds"]
        total_frames = int(duration / dt)
        wall_start = time.time()
        try:
            # settle physics before the event script starts
            for _ in range(10):
                self.session.world.tick()
            scenario.setup(ctx)

            for frame in range(total_frames):
                self.session.world.tick()
                sim_time = frame * dt
                scenario.on_tick(ctx, frame, sim_time)
                collector.record_frame(frame, sim_time, ego, ctx.threats)
                wu.chase_spectator(self.session.world, ego)

                # drive the ego with our deterministic, speed-capped governor
                self._ego_gov.step()

                # absolute safety net (defence in depth): if speed ever
                # exceeds 1.3x the cap, hard-brake AND zero the velocity.
                # The governor already bounds it, so this should never fire --
                # but it is the guarantee that the 322/562 km/h "mutation"
                # can never recur, even if a collision impulse is injected.
                _cap = self._ego_cap
                if wu.speed_of(ego) > _cap * 1.3:
                    wu.hard_clamp(ego, _cap)

                if frame % 100 == 0:
                    log.info("t=%5.1fs | ego %4.1f m/s | threats %d | %s",
                             sim_time, wu.speed_of(ego), len(ctx.threats),
                             "EVENT ACTIVE" if scenario.triggered else "cruise")
                # early stop: collision fully captured, or scenario says done
                if collector.collision_events and \
                        frame > collector.collision_events[-1]["frame"] + 60:
                    log.info("Early stop: collision captured.")
                    break
                if scenario.finished and not scenario.triggered:
                    break
        finally:
            scenario.cleanup(ctx)
            rig.destroy()
            for v in background:
                try:
                    if v.is_alive:
                        v.destroy()
                except Exception:  # noqa: BLE001
                    pass
            try:
                if ego.is_alive:
                    ego.destroy()
            except Exception:  # noqa: BLE001
                pass
            # flush destroys through one tick
            try:
                self.session.world.tick()
            except Exception:  # noqa: BLE001
                pass

        collector.save()
        metrics = compute_metrics(collector, self.cfg["thresholds"], dt)
        collector.save_summary(metrics)
        log.info("RESULT %-24s | %s | minTTC=%s s | minGap=%s m | "
                 "collisions=%d | wall %.0fs",
                 name, metrics["result"], metrics["min_ttc_s"],
                 metrics["min_gap_m"], metrics["collision_count"],
                 time.time() - wall_start)
        return metrics
