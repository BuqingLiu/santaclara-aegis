"""#19 Impaired (DUI) driver weaving: a lead vehicle swerves across lanes with
unbalanced/erratic control — a major real-world crash precursor (NHTSA:
impairment is a factor in ~30% of fatal CA traffic crashes).
"""
import math

import carla

from scenarios.base_scenario import BaseScenario
from simulation import world_utils as wu


class DuiErraticWeave(BaseScenario):
    NAME = "dui_erratic_weave"
    NEEDS = []

    def setup(self, ctx):
        self.lead, _ = self.spawn_vehicle_ahead(
            ctx, distance=14.0, lane="same",
            patterns=("vehicle.chevrolet.impala", "vehicle.audi.tt"),
            autopilot=True)
        self._t = 0.0

    def on_tick(self, ctx, frame, sim_time):
        super().on_tick(ctx, frame, sim_time)
        if self.lead is None or not self.lead.is_alive:
            self.finished = True
            return
        if self.check_trigger(ctx, self.lead, frame, "dui_weave_start"):
            self.lead.set_autopilot(False, ctx.tm_port)
        if self.triggered:
            dt = ctx.config.get("fixed_delta_seconds", 0.05)
            self._t += dt
            steer = 0.7 * math.sin(self._t * 3.0)        # swerve
            surge = 0.6 + 0.4 * math.sin(self._t * 1.7)  # speed surges
            self.lead.apply_control(
                carla.VehicleControl(throttle=surge, steer=steer, brake=0.0))
