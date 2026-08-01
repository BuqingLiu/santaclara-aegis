"""#10 Hard rain + lead vehicle brake: reduced-friction emergency braking
scenario proving safe following distance policy in adverse weather."""
import carla

from scenarios.base_scenario import BaseScenario
from simulation import world_utils as wu


class AdverseWeather(BaseScenario):
    NAME = "adverse_weather"
    NEEDS = []
    BRAKE_TICKS = 70   # 3.5 s of full braking

    def setup(self, ctx):
        self.lead, _ = self.spawn_vehicle_ahead(
            ctx, distance=22.0, lane="same",
            patterns=("vehicle.toyota.prius", "vehicle.audi.a2"),
            autopilot=True)
        if self.lead is not None:
            ctx.tm.vehicle_percentage_speed_difference(self.lead, 10)
        self._brake_left = 0

    def on_tick(self, ctx, frame, sim_time):
        super().on_tick(ctx, frame, sim_time)
        if self.lead is None or not self.lead.is_alive:
            self.finished = True
            return
        if self.check_trigger(ctx, self.lead, frame, "lead_brake_in_rain"):
            self.lead.set_autopilot(False, ctx.tm_port)
            self._brake_left = self.BRAKE_TICKS
        if self._brake_left > 0:
            self.lead.apply_control(carla.VehicleControl(brake=1.0))
            self._brake_left -= 1
            if self._brake_left == 0:
                self.lead.set_autopilot(True, ctx.tm_port)
                ctx.collector.mark_event("lead_resumes", frame)
