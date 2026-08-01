"""#7 Head-on wrong-way driver: a vehicle drives against traffic in the ego
lane; the driver corrects late, producing a measured near-miss."""
import carla

from scenarios.base_scenario import BaseScenario
from simulation import world_utils as wu


class WrongWayDriver(BaseScenario):
    NAME = "wrong_way_driver"
    NEEDS = []

    def setup(self, ctx):
        wp = wu.forward_waypoint(ctx.map, ctx.ego, 85.0)
        tr = carla.Transform(wp.transform.location, wp.transform.rotation)
        tr.rotation.yaw += 180.0   # facing the ego
        bp = self._pick_bp(ctx, ("vehicle.jeep.wrangler*",
                                 "vehicle.audi.a2"))
        self.ww = wu.try_spawn(ctx.world, bp, tr)
        if self.ww is None:
            self.finished = True
            return
        self.actors.append(self.ww)
        ctx.threats.append(self.ww)
        self.correcting = False
        self.evasive = False

    def on_tick(self, ctx, frame, sim_time):
        super().on_tick(ctx, frame, sim_time)
        if self.ww is None or not self.ww.is_alive:
            self.finished = True
            return
        gap = wu.dist_between(ctx.ego, self.ww)

        if self.check_trigger(ctx, self.ww, frame, "wrong_way_approach"):
            pass  # flag only; motion handled below

        if self.triggered and not self.correcting:
            self.ww.apply_control(carla.VehicleControl(throttle=0.45))
            if gap < 26.0 and not self.evasive:
                # ego defensive action: brake via TM slowdown
                ctx.tm.vehicle_percentage_speed_difference(ctx.ego, 60)
                ctx.collector.mark_event("ego_defensive_brake", frame,
                                         {"gap_m": round(gap, 2)})
                self.evasive = True
            if gap < 18.0:
                # human driver corrects: swerves back to their own side
                self.correcting = True
                ctx.collector.mark_event("wrong_way_corrects", frame,
                                         {"gap_m": round(gap, 2)})
        elif self.correcting:
            self.ww.apply_control(
                carla.VehicleControl(throttle=0.4, steer=-0.45))
            if gap > 10.0 and self.evasive:
                ctx.tm.vehicle_percentage_speed_difference(
                    ctx.ego, ctx.config["ego_speed_boost_pct"])
