"""#13 Lead vehicle panic brake: classic rear-end avoidance (NHTSA LVD)."""
import carla

from scenarios.base_scenario import BaseScenario


class SuddenBrake(BaseScenario):
    NAME = "sudden_brake"
    NEEDS = []
    BRAKE_TICKS = 60   # 3 s full brake

    def setup(self, ctx):
        self.lead, _ = self.spawn_vehicle_ahead(
            ctx, distance=18.0, lane="same",
            patterns=("vehicle.chevrolet.impala", "vehicle.audi.tt"),
            autopilot=True)
        if self.lead is not None:
            ctx.tm.vehicle_percentage_speed_difference(self.lead, 5)
        self._brake_left = 0

    def on_tick(self, ctx, frame, sim_time):
        super().on_tick(ctx, frame, sim_time)
        if self.lead is None or not self.lead.is_alive:
            self.finished = True
            return
        if self.check_trigger(ctx, self.lead, frame, "lead_panic_brake"):
            self.lead.set_autopilot(False, ctx.tm_port)
            self._brake_left = self.BRAKE_TICKS
        if self._brake_left > 0:
            self.lead.apply_control(
                carla.VehicleControl(brake=1.0, hand_brake=self._brake_left < 20))
            self._brake_left -= 1
            if self._brake_left == 0:
                self.lead.set_autopilot(True, ctx.tm_port)
                ctx.collector.mark_event("lead_resumes", frame)
