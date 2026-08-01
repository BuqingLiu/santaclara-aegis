"""#8 Occluded pedestrian dash-out: a pedestrian hidden by a parked van
sprints into the lane at very short range - the hardest PAEB-style case."""
import carla

from scenarios.base_scenario import BaseScenario
from simulation import world_utils as wu


class OccludedPedestrian(BaseScenario):
    NAME = "occluded_pedestrian"
    NEEDS = []

    def setup(self, ctx):
        # parked van creating the occlusion
        wp = wu.forward_waypoint(ctx.map, ctx.ego, 38.0)
        park_loc = wu.lateral_offset(wp.transform, 3.2)
        bp = self._pick_bp(ctx, ("vehicle.volkswagen.t2",
                                 "vehicle.carlamotors.carlacola",
                                 "vehicle.mercedes.sprinter"))
        van = wu.try_spawn(ctx.world, bp,
                           carla.Transform(park_loc, wp.transform.rotation))
        if van is not None:
            van.apply_control(carla.VehicleControl(hand_brake=True))
            self.actors.append(van)   # obstacle, not tracked as threat

        # pedestrian hidden just downstream of the van
        self.walker, self.ctrl, self.wp = self.spawn_walker_offset(
            ctx, distance_ahead=44.0, right_offset=3.4)

    def on_tick(self, ctx, frame, sim_time):
        super().on_tick(ctx, frame, sim_time)
        if self.walker is None:
            self.finished = True
            return
        if self.check_trigger(ctx, self.walker, frame, "occluded_dash_out"):
            self.send_walker_kinematic(self.walker, self.wp,
                                       right_offset=-5.0, speed=3.2)
