"""#15 Signal failure + cross traffic: all lights at the junction go dark
(CA CVC 21800(d): treat as all-way stop) while scripted cross traffic keeps
moving - the ego must negotiate the junction unprotected."""
import carla

from scenarios.base_scenario import BaseScenario
from simulation import world_utils as wu


class IntersectionGridlock(BaseScenario):
    NAME = "intersection_gridlock"
    NEEDS = ["junction"]

    def setup(self, ctx):
        self.junction, _entry, _d = wu.find_junction_ahead(ctx.map, ctx.ego)
        if self.junction is None:
            self.finished = True
            return
        self.trigger_point = self.junction.bounding_box.location

        # signal failure: every light at this junction goes dark
        wu.set_lights_near(ctx.world, self.trigger_point, 45.0,
                           carla.TrafficLightState.Off)

        # two scripted cross-traffic vehicles from different approaches
        ego_road = ctx.map.get_waypoint(ctx.ego.get_location()).road_id
        entries = wu.junction_entries(self.junction, ego_road)
        self.pending = []
        for entry, _exit in entries[:2]:
            prev = entry.previous(20.0)
            start_wp = prev[0] if prev else entry
            bp = self._pick_bp(ctx, ("vehicle.seat.leon",
                                     "vehicle.citroen.c3",
                                     "vehicle.audi.tt"))
            v = wu.try_spawn(ctx.world, bp, start_wp.transform)
            if v is not None:
                self.actors.append(v)
                ctx.threats.append(v)
                route = wu.chain_route(start_wp, step=3.0, length=70.0)
                self.pending.append(wu.RouteDriver(v, route, target_speed=6.0))

    def on_tick(self, ctx, frame, sim_time):
        if not hasattr(self, "trigger_point"):
            return
        if self.check_trigger(ctx, self.trigger_point, frame,
                              "dark_signal_cross_traffic"):
            self.drivers.extend(self.pending)
        super().on_tick(ctx, frame, sim_time)
