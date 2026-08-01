"""#16 Motorcycle lane-splitting: a rider filters through the gap between
lanes beside the ego (CA V.C. 21658.1 permits lane splitting). Tests the
AV's lateral awareness when a motorcycle passes in the adjacent seam.
"""
import carla

from scenarios.base_scenario import BaseScenario
from simulation import world_utils as wu


class MotorcycleLaneSplitting(BaseScenario):
    NAME = "motorcycle_lane_splitting"
    NEEDS = []

    def setup(self, ctx):
        wp = wu.forward_waypoint(ctx.map, ctx.ego, 10.0)
        # ride the seam between ego lane and right lane (toward centre = neg)
        gap = wu.lateral_offset(wp.transform, -1.8)
        tr = carla.Transform(gap, wp.transform.rotation)
        bp = self._pick_bp(ctx, ("vehicle.yamaha.yzf",
                                 "vehicle.kawasaki.ninja",
                                 "vehicle.harley-davidson.low_rider"))
        self.bike = wu.try_spawn(ctx.world, bp, tr)
        if self.bike is None:
            self.finished = True
            return
        self.actors.append(self.bike)
        ctx.threats.append(self.bike)
        pts = [gap]
        cur = wp
        for _ in range(8):
            nxt = cur.next(4.0)
            if not nxt:
                break
            cur = nxt[0]
            pts.append(wu.lateral_offset(cur.transform, -1.8))
        self.driver = wu.RouteDriver(self.bike, pts, target_speed=9.0)
        self.drivers.append(self.driver)

    def on_tick(self, ctx, frame, sim_time):
        super().on_tick(ctx, frame, sim_time)
        if self.bike is None or not self.bike.is_alive:
            self.finished = True
            return
        self.check_trigger(ctx, self.bike, frame, "motorcycle_lane_split")
