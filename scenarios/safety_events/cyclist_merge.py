"""#6 Cyclist merging into lane: a cyclist riding the road edge swerves into
the ego lane (CA Three Feet for Safety Act interaction)."""
import carla

from scenarios.base_scenario import BaseScenario
from simulation import world_utils as wu


class CyclistMerge(BaseScenario):
    NAME = "cyclist_merge"
    NEEDS = []

    def setup(self, ctx):
        wp = wu.forward_waypoint(ctx.map, ctx.ego, 38.0)
        edge = wu.lateral_offset(wp.transform, 2.6)   # road edge
        tr = carla.Transform(edge, wp.transform.rotation)
        bp = self._pick_bp(ctx, ("vehicle.bh.crossbike",
                                 "vehicle.diamondback.century",
                                 "vehicle.gazelle.omafiets"))
        self.bike = wu.try_spawn(ctx.world, bp, tr)
        if self.bike is None:
            self.finished = True
            return
        self.actors.append(self.bike)
        ctx.threats.append(self.bike)
        # route: long road-edge stretch (~30m), then merge in last 8m
        edge_pts = [wp.transform.location]
        cur = wp
        for i in range(6):       # ~30m ride along the curb
            nxt = cur.next(5.0)
            if not nxt:
                break
            cur = nxt[0]
            edge_pts.append(wu.lateral_offset(cur.transform, 2.6 - i * 0.15))
        merge = cur.next(8.0)     # final approach into ego lane
        if merge:
            edge_pts.append(merge[0].transform.location)
        self.driver = wu.RouteDriver(self.bike, edge_pts, target_speed=3.5)
        self.drivers.append(self.driver)   # cyclist rides from the start

    def on_tick(self, ctx, frame, sim_time):
        super().on_tick(ctx, frame, sim_time)
        if self.bike is None or not self.bike.is_alive:
            self.finished = True
            return
        self.check_trigger(ctx, self.bike, frame, "cyclist_in_lane")
