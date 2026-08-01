"""#5 Emergency vehicle yield: a lights-on emergency vehicle approaches fast
from behind; the ego must move over (CA CVC 21806) and resume afterwards."""
import carla

from scenarios.base_scenario import BaseScenario
from simulation import world_utils as wu


class EmergencyVehicle(BaseScenario):
    NAME = "emergency_vehicle"
    NEEDS = ["adjacent_lane"]

    def setup(self, ctx):
        wp = wu.backward_waypoint(ctx.map, ctx.ego, 32.0)
        bp = self._pick_bp(ctx, ("vehicle.ford.ambulance",
                                 "vehicle.dodge.charger_police*",
                                 "vehicle.carlamotors.firetruck"))
        self.ev = wu.try_spawn(ctx.world, bp, wp.transform)
        if self.ev is None:
            self.finished = True
            return
        self.actors.append(self.ev)
        ctx.threats.append(self.ev)
        self.ev.set_autopilot(True, ctx.tm_port)
        ctx.tm.vehicle_percentage_speed_difference(self.ev, -55)  # much faster
        ctx.tm.ignore_lights_percentage(self.ev, 100)
        ctx.tm.distance_to_leading_vehicle(self.ev, 1.0)
        try:  # siren / strobes
            self.ev.set_light_state(carla.VehicleLightState(
                carla.VehicleLightState.Special1
                | carla.VehicleLightState.Special2
                | carla.VehicleLightState.LowBeam))
        except Exception:  # noqa: BLE001 - cosmetic
            pass
        self.yielded = False
        self.resumed = False

    def on_tick(self, ctx, frame, sim_time):
        super().on_tick(ctx, frame, sim_time)
        if self.ev is None or not self.ev.is_alive:
            self.finished = True
            return
        gap = wu.dist_between(ctx.ego, self.ev)
        if not self.yielded and self.check_trigger(ctx, self.ev, frame,
                                                   "emergency_approach"):
            # pull toward the right lane & slow down = statutory yield
            ctx.tm.force_lane_change(ctx.ego, False)
            ctx.tm.vehicle_percentage_speed_difference(ctx.ego, 45)
            self.yielded = True
            ctx.collector.mark_event("ego_yield_right", frame,
                                     {"gap_m": round(gap, 2)})
        elif self.yielded and not self.resumed:
            # emergency vehicle has passed -> resume normal speed
            ego_fwd = ctx.ego.get_transform().get_forward_vector()
            rel = self.ev.get_location() - ctx.ego.get_location()
            ahead = ego_fwd.x * rel.x + ego_fwd.y * rel.y
            if ahead > 12.0:
                ctx.tm.vehicle_percentage_speed_difference(
                    ctx.ego, ctx.config["ego_speed_boost_pct"])
                self.resumed = True
                ctx.collector.mark_event("ego_resume", frame,
                                         {"gap_m": round(gap, 2)})
