"""#23 Roadway debris / abandoned object: a fallen object occupies the ego
lane, forcing an emergency swerve or stop (Caltrans FMS "object on roadway"
incidents — common on Bay Area arterials). Modeled as a stationary bicycle.
"""
import carla

from scenarios.base_scenario import BaseScenario
from simulation import world_utils as wu


class RoadDebris(BaseScenario):
    NAME = "road_debris"
    NEEDS = []

    def setup(self, ctx):
        self.debris, _ = self.spawn_vehicle_ahead(
            ctx, distance=22.0, lane="same",
            patterns=("vehicle.bh.crossbike",
                      "vehicle.diamondback.century"),
            autopilot=False)
        if self.debris is not None:
            self.debris.apply_control(
                carla.VehicleControl(brake=1.0, hand_brake=True))

    def on_tick(self, ctx, frame, sim_time):
        super().on_tick(ctx, frame, sim_time)
        if self.debris is None or not self.debris.is_alive:
            self.finished = True
            return
        self.check_trigger(ctx, self.debris, frame, "road_debris_ahead")
