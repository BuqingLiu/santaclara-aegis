"""Scenario contract + shared spawn helpers.

Every safety event implements:
    setup(ctx)            spawn threat actors (relative to ego's road topology)
    on_tick(ctx, frame,t) trigger / drive the event
    cleanup(ctx)          handled here (destroys everything it registered)
"""
import math

import carla

from simulation import world_utils as wu
from utils.logger import get_logger

log = get_logger("scenario")


class KinematicWalker:
    """Move a pedestrian along a straight world-space line at constant speed.

    CARLA's AI walker controller needs a pedestrian navmesh, which is NOT
    generated for OpenDRIVE roads built from OSM. This kinematic mover always
    works (real maps + stock maps) and is what makes "pedestrian darts out"
    actually visible on the real Santa Clara / San Jose roads.
    """

    def __init__(self, walker, target, speed=1.6):
        self.walker = walker
        self.target = target
        self.speed = speed
        self.done = False

    def step(self, dt):
        if self.done or not self.walker.is_alive:
            return True
        loc = self.walker.get_location()
        dx = self.target.x - loc.x
        dy = self.target.y - loc.y
        d = math.hypot(dx, dy)
        if d < 0.5:
            self.done = True
            return True
        adv = min(self.speed * dt, d)
        self.walker.set_location(carla.Location(
            x=loc.x + dx / d * adv, y=loc.y + dy / d * adv, z=loc.z))
        return False


class ScenarioContext:
    """Everything a scenario needs, in one bag."""

    def __init__(self, world, client, tm, tm_port, ego, collector, config):
        self.world = world
        self.client = client
        self.tm = tm
        self.tm_port = tm_port
        self.map = world.get_map()
        self.blueprints = world.get_blueprint_library()
        self.ego = ego
        self.collector = collector
        self.config = config
        self.threats = []          # actors tracked for TTC / gap metrics


class BaseScenario:
    NAME = "base"
    NEEDS = []                     # "adjacent_lane" / "junction"

    def __init__(self, meta):
        self.meta = meta           # dict from config/scenarios.json
        self.trigger_dist = float(meta.get("trigger_dist", 20.0))
        self.triggered = False
        self.finished = False
        self.actors = []           # everything to destroy on cleanup
        self.controllers = []      # walker AI controllers (stop before destroy)
        self.drivers = []          # RouteDriver instances stepped each tick
        self.kinematic_walkers = []  # KinematicWalker instances (real-map safe)

    # ------------------------------------------------------------------ #
    # lifecycle
    # ------------------------------------------------------------------ #
    def setup(self, ctx):
        raise NotImplementedError

    def on_tick(self, ctx, frame, sim_time):
        dt = ctx.config.get("fixed_delta_seconds", 0.05)
        for d in self.drivers:
            d.step()
        for w in self.kinematic_walkers:
            w.step(dt)

    def cleanup(self, ctx):
        for c in self.controllers:
            try:
                c.stop()
            except Exception:  # noqa: BLE001
                pass
        for a in reversed(self.controllers + self.actors):
            try:
                if a.is_alive:
                    a.destroy()
            except Exception:  # noqa: BLE001
                pass
        self.actors.clear()
        self.controllers.clear()
        self.drivers.clear()
        self.kinematic_walkers.clear()

    # ------------------------------------------------------------------ #
    # trigger helper
    # ------------------------------------------------------------------ #
    def check_trigger(self, ctx, reference, frame, label):
        """Fire once when ego closes within trigger_dist of reference.

        Defensive: actors on OSM maps can be destroyed asynchronously when
        they leave the road network, and is_alive can briefly lag — so any
        access to a (possibly dead) actor is wrapped.
        """
        if self.triggered:
            return False
        try:
            loc = (reference.get_location()
                   if hasattr(reference, "get_location") else reference)
            dist = ctx.ego.get_location().distance(loc)
        except Exception:  # noqa: BLE001 - actor destroyed off-map
            return False
        if dist <= self.trigger_dist:
            self.triggered = True
            ctx.collector.mark_event(label, frame,
                                     {"trigger_dist_m": self.trigger_dist})
            try:
                ctx.world.debug.draw_string(
                    loc + carla.Location(z=2.5), f"!! {label} !!",
                    color=carla.Color(255, 30, 30), life_time=4.0)
            except Exception:  # noqa: BLE001
                pass
            log.info(">>> EVENT TRIGGERED: %s (frame %s)", label, frame)
            return True
        return False

    # ------------------------------------------------------------------ #
    # spawn helpers (all relative to ego's road topology -> map-agnostic)
    # ------------------------------------------------------------------ #
    def _pick_bp(self, ctx, patterns):
        for pat in patterns:
            found = ctx.blueprints.filter(pat)
            if found:
                return found[0]
        return ctx.blueprints.filter("vehicle.*")[0]

    def spawn_vehicle_ahead(self, ctx, distance, lane="same",
                            patterns=("vehicle.audi.tt",), yaw_offset=0.0,
                            autopilot=False, track=True):
        wp = wu.forward_waypoint(ctx.map, ctx.ego, distance)
        if lane in ("left", "right"):
            adj = wp.get_left_lane() if lane == "left" else wp.get_right_lane()
            if (adj is not None and adj.lane_type == carla.LaneType.Driving
                    and adj.lane_id * wp.lane_id > 0):
                wp = adj
        tr = carla.Transform(wp.transform.location, wp.transform.rotation)
        tr.rotation.yaw += yaw_offset
        vehicle = wu.try_spawn(ctx.world, self._pick_bp(ctx, patterns), tr)
        if vehicle is None:
            log.warning("spawn_vehicle_ahead failed at %.0fm (%s lane)",
                        distance, lane)
            return None, wp
        if autopilot:
            vehicle.set_autopilot(True, ctx.tm_port)
        self.actors.append(vehicle)
        if track:
            ctx.threats.append(vehicle)
        return vehicle, wp

    def spawn_walker_offset(self, ctx, distance_ahead, right_offset,
                            track=True):
        """Spawn a pedestrian beside the road; returns (walker, ctrl, wp)."""
        wp = wu.forward_waypoint(ctx.map, ctx.ego, distance_ahead)
        loc = wu.lateral_offset(wp.transform, right_offset)
        loc.z += 1.0
        bp = ctx.blueprints.filter("walker.pedestrian.*")[0]
        if bp.has_attribute("is_invincible"):
            bp.set_attribute("is_invincible", "false")
        walker = wu.try_spawn(ctx.world, bp, carla.Transform(loc), z_lift=0.0)
        if walker is None:
            log.warning("walker spawn failed at %.0fm ahead", distance_ahead)
            return None, None, wp
        ctrl_bp = ctx.blueprints.find("controller.ai.walker")
        ctrl = ctx.world.spawn_actor(ctrl_bp, carla.Transform(),
                                     attach_to=walker)
        self.actors.append(walker)
        self.controllers.append(ctrl)
        if track:
            ctx.threats.append(walker)
        return walker, ctrl, wp

    @staticmethod
    def send_walker(ctrl, wp, right_offset, speed=2.6):
        """Command a walker to cross toward an offset from lane centre."""
        target = wu.lateral_offset(wp.transform, right_offset)
        ctrl.start()
        ctrl.set_max_speed(speed)
        ctrl.go_to_location(target)

    def send_walker_kinematic(self, walker, wp, right_offset, speed=2.6):
        """Cross a walker using the navmesh-free KinematicWalker.

        Use this instead of send_walker on real OSM maps (no walker navmesh).
        """
        target = wu.lateral_offset(wp.transform, right_offset)
        self.kinematic_walkers.append(
            KinematicWalker(walker, target, speed=speed))
