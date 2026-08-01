"""#18 Highway on-ramp merge: a vehicle enters from the right and merges into
the ego lane with insufficient gap (freeway on-ramp merge conflict — a
leading cause of SoCal/NorCal freeway injury crashes).
"""
import carla

from scenarios.base_scenario import BaseScenario
from simulation import world_utils as wu


class HighwayOnrampMerge(BaseScenario):
    NAME = "highway_onramp_merge"
    NEEDS = ["adjacent_lane"]

    def setup(self, ctx):
        wp = wu.forward_waypoint(ctx.map, ctx.ego, 30.0)
        right = wp.get_right_lane()
        if right is not None and right.lane_type == carla.LaneType.Driving:
            wp = right
        start = wu.lateral_offset(wp.transform, 0.0)
        tr = carla.Transform(start, wp.transform.rotation)
        bp = self._pick_bp(ctx, ("vehicle.audi.tt", "vehicle.nissan.micra"))
        self.merger = wu.try_spawn(ctx.world, bp, tr)
        if self.merger is None:
            self.finished = True
            return
        self.actors.append(self.merger)
        ctx.threats.append(self.merger)
        pts = [start]
        cur = wp
        for i in range(6):
            nxt = cur.next(4.0)
            if not nxt:
                break
            cur = nxt[0]
            off = 0.0 if i < 3 else -1.6 * (i - 2) / 3.0  # drift left
            pts.append(wu.lateral_offset(cur.transform, off))
        pts.append(wu.lateral_offset(cur.transform, -3.2))  # into ego lane
        self.driver = wu.RouteDriver(self.merger, pts, target_speed=8.0)
        self.drivers.append(self.driver)

    def on_tick(self, ctx, frame, sim_time):
        super().on_tick(ctx, frame, sim_time)
        if self.merger is None or not self.merger.is_alive:
            self.finished = True
            return
        self.check_trigger(ctx, self.merger, frame, "merge_conflict")
