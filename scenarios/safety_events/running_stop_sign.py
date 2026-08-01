"""#20 Running a stop sign: cross-traffic has the right of way and proceeds
toward the intersection while the ego rolls the stop sign -- a perpendicular
( T-bone ) conflict / near-miss.

Map-agnostic: works on real OSM roads (no navmesh needed).

SAFETY FIX (root cause of the 562 km/h blow-up):
    The original version routed the cross car straight across the ego lane
    (from +9 m to -9 m lateral). On the real map the two vehicles physically
    collided and the collision impulse launched the ego to 562 km/h. CARLA
    0.9.16 has no per-actor `set_collision_enabled`, so the only robust fix
    is geometric: the cross vehicle now brakes and HOLDS at +3.0 m lateral
    -- just outside the ego lane -- so it never contacts the ego. The result
    is a dramatic, physically safe near-miss that can never launch the ego.
"""
import carla

from scenarios.base_scenario import BaseScenario
from simulation import world_utils as wu


class RunningStopSign(BaseScenario):
    NAME = "running_stop_sign"
    NEEDS = ["junction"]

    def setup(self, ctx):
        wp = wu.forward_waypoint(ctx.map, ctx.ego, 22.0)
        # Cross-traffic enters from the right and drives toward the
        # intersection. It brakes and HOLDS at +3.0 m lateral -- the edge of
        # the cross-street, just outside the ego lane -- so it physically
        # cannot hit the ego. This is the fix that removes the 562 km/h launch.
        start = wu.lateral_offset(wp.transform, 9.0)
        tr = carla.Transform(start, wp.transform.rotation)
        tr.rotation.yaw += 90.0
        bp = self._pick_bp(ctx, ("vehicle.nissan.micra", "vehicle.audi.tt"))
        self.cross = wu.try_spawn(ctx.world, bp, tr)
        if self.cross is None:
            self.finished = True
            return
        self.actors.append(self.cross)
        ctx.threats.append(self.cross)
        # hold point sits 3 m to the right of the ego lane centre-line
        hold = wu.lateral_offset(wp.transform, 3.0)
        # fast approach (11 m/s) then a hard brake at the intersection edge
        self.driver = wu.RouteDriver(self.cross, [start, hold],
                                     target_speed=11.0, hold_at_end=True)
        self.drivers.append(self.driver)

    def on_tick(self, ctx, frame, sim_time):
        super().on_tick(ctx, frame, sim_time)
        if self.cross is None or not self.cross.is_alive:
            self.finished = True
            return
        self.check_trigger(ctx, self.cross, frame, "cross_traffic_roll")
