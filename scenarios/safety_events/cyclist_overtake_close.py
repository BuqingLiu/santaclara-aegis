"""#22 Close-pass of cyclist: a vehicle overtakes a cyclist with unsafe
(<3 ft) lateral clearance — CA Three Feet for Safety Act (V.C. 21760).
"""
import carla

from scenarios.base_scenario import BaseScenario
from simulation import world_utils as wu


class CyclistOvertakeClose(BaseScenario):
    NAME = "cyclist_overtake_close"
    NEEDS = []

    def setup(self, ctx):
        wp = wu.forward_waypoint(ctx.map, ctx.ego, 26.0)
        edge = wu.lateral_offset(wp.transform, 2.2)  # bike on road edge
        tr = carla.Transform(edge, wp.transform.rotation)
        bp = self._pick_bp(ctx, ("vehicle.bh.crossbike",
                                 "vehicle.diamondback.century"))
        self.bike = wu.try_spawn(ctx.world, bp, tr)
        if self.bike is None:
            self.finished = True
            return
        self.actors.append(self.bike)
        ctx.threats.append(self.bike)
        pts = [edge]
        cur = wp
        for _ in range(6):
            nxt = cur.next(4.0)
            if not nxt:
                break
            cur = nxt[0]
            pts.append(wu.lateral_offset(cur.transform, 2.2))
        self.bike_driver = wu.RouteDriver(self.bike, pts, target_speed=3.5)
        self.drivers.append(self.bike_driver)
        # overtaking car spawns behind, in same lane, faster
        self.car, _ = self.spawn_vehicle_ahead(
            ctx, distance=10.0, lane="same",
            patterns=("vehicle.audi.tt", "vehicle.nissan.micra"),
            autopilot=True)
        if self.car is not None:
            ctx.tm.vehicle_percentage_speed_difference(self.car, 15)
        self._min_gap = 99.0

    def on_tick(self, ctx, frame, sim_time):
        super().on_tick(ctx, frame, sim_time)
        if self.bike is None or not self.bike.is_alive:
            self.finished = True
            return
        if self.check_trigger(ctx, self.bike, frame, "cyclist_close_pass"):
            if self.car is not None and self.car.is_alive:
                d = self.car.get_location().distance(self.bike.get_location())
                self._min_gap = min(self._min_gap, d)
                if self._min_gap < 2.0:
                    ctx.collector.mark_event(
                        "unsafe_three_feet", frame,
                        {"min_gap_m": round(self._min_gap, 2)})
