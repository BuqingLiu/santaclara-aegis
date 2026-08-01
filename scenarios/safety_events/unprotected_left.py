"""#4 Unprotected left turn across path (LTAP/OD): an oncoming vehicle turns
left across the ego's path inside the junction ahead - the classic highest
severity urban conflict for CA DMV review."""
import carla

from scenarios.base_scenario import BaseScenario
from simulation import world_utils as wu


class UnprotectedLeft(BaseScenario):
    NAME = "unprotected_left"
    NEEDS = ["junction"]

    def setup(self, ctx):
        self.turner = None
        self.junction, _entry, _d = wu.find_junction_ahead(ctx.map, ctx.ego)
        if self.junction is None:
            self.finished = True
            return
        self.trigger_point = self.junction.bounding_box.location
        wu.set_lights_near(ctx.world, ctx.ego.get_location(), 60.0,
                           carla.TrafficLightState.Green)

        ego_fwd = ctx.ego.get_transform().get_forward_vector()
        ego_road = ctx.map.get_waypoint(ctx.ego.get_location()).road_id
        best = None
        for entry, exit_wp in wu.junction_entries(self.junction, ego_road):
            e_fwd = entry.transform.get_forward_vector()
            dot_in = ego_fwd.x * e_fwd.x + ego_fwd.y * e_fwd.y
            x_fwd = exit_wp.transform.get_forward_vector()
            dot_out = ego_fwd.x * x_fwd.x + ego_fwd.y * x_fwd.y
            # oncoming approach (opposes ego) whose exit is NOT oncoming
            if dot_in < -0.5 and dot_out > -0.3:
                best = entry
                break
        if best is None:  # fallback: any non-ego approach
            pairs = wu.junction_entries(self.junction, ego_road)
            best = pairs[0][0] if pairs else None
        if best is None:
            self.finished = True
            return

        prev = best.previous(24.0)
        start_wp = prev[0] if prev else best
        bp = self._pick_bp(ctx, ("vehicle.nissan.micra", "vehicle.audi.tt"))
        self.turner = wu.try_spawn(ctx.world, bp, start_wp.transform)
        if self.turner is None:
            self.finished = True
            return
        self.actors.append(self.turner)
        ctx.threats.append(self.turner)
        route = wu.chain_route(start_wp, step=3.0, length=80.0)
        self.driver = wu.RouteDriver(self.turner, route, target_speed=7.5)

    def on_tick(self, ctx, frame, sim_time):
        if self.turner is None:
            return
        if self.check_trigger(ctx, self.trigger_point, frame,
                              "unprotected_left_launch"):
            self.drivers.append(self.driver)
        super().on_tick(ctx, frame, sim_time)
