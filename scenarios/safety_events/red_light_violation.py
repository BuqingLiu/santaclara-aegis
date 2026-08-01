"""#3 Cross-traffic red-light runner: at the junction ahead of the ego, a
scripted vehicle enters from another approach against the signal exactly as
the ego arrives. Ego's own signal is forced green so the conflict is real."""
import carla

from scenarios.base_scenario import BaseScenario
from simulation import world_utils as wu


class RedLightViolation(BaseScenario):
    NAME = "red_light_violation"
    NEEDS = ["junction"]

    def setup(self, ctx):
        self.violator = None
        self.junction, ego_entry, dist = wu.find_junction_ahead(
            ctx.map, ctx.ego)
        if self.junction is None:
            self.finished = True
            return
        self.trigger_point = self.junction.bounding_box.location

        # give ego a green so it proceeds into the conflict zone
        wu.set_lights_near(ctx.world, ctx.ego.get_location(), 60.0,
                           carla.TrafficLightState.Green)

        ego_road = ctx.map.get_waypoint(ctx.ego.get_location()).road_id
        for entry, _exit in wu.junction_entries(self.junction, ego_road):
            prev = entry.previous(28.0)
            if not prev:
                continue
            start_wp = prev[0]
            bp = self._pick_bp(ctx, ("vehicle.dodge.charger*",
                                     "vehicle.audi.a2"))
            self.violator = wu.try_spawn(ctx.world, bp, start_wp.transform)
            if self.violator is not None:
                self.actors.append(self.violator)
                ctx.threats.append(self.violator)
                route = wu.chain_route(start_wp, step=3.0, length=85.0)
                # Slower so ego has time to clear the junction
                self.driver = wu.RouteDriver(self.violator, route,
                                             target_speed=6.5)
                break
        if self.violator is None:
            self.finished = True

    def on_tick(self, ctx, frame, sim_time):
        if self.violator is None:
            return
        if self.check_trigger(ctx, self.trigger_point, frame,
                              "red_light_runner_launch"):
            self.drivers.append(self.driver)   # starts moving only now
        super().on_tick(ctx, frame, sim_time)
