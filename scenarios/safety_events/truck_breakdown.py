"""#21 Disabled truck blocking lane: a broken-down heavy vehicle partially
occupies the ego lane (Caltrans "move over" / FMS incident scenario).
"""
import carla

from scenarios.base_scenario import BaseScenario
from simulation import world_utils as wu


class TruckBreakdown(BaseScenario):
    NAME = "truck_breakdown"
    NEEDS = []

    def setup(self, ctx):
        self.truck, _ = self.spawn_vehicle_ahead(
            ctx, distance=20.0, lane="same",
            patterns=("vehicle.carlamotors.carlacola",
                      "vehicle.mercedes.sprinter"),
            autopilot=False)
        if self.truck is not None:
            self.truck.apply_control(
                carla.VehicleControl(brake=1.0, hand_brake=True))

    def on_tick(self, ctx, frame, sim_time):
        super().on_tick(ctx, frame, sim_time)
        if self.truck is None or not self.truck.is_alive:
            self.finished = True
            return
        self.check_trigger(ctx, self.truck, frame, "disabled_truck")
