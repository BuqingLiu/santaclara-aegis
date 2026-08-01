"""#2 Aggressive cut-in: adjacent-lane vehicle forces its way into the ego
lane at short gap, verifying ego headway management."""
import carla

from scenarios.base_scenario import BaseScenario


class CutIn(BaseScenario):
    NAME = "cut_in"
    NEEDS = ["adjacent_lane"]

    def setup(self, ctx):
        # try left lane first, fall back to right
        self.threat, wp = self.spawn_vehicle_ahead(
            ctx, distance=22.0, lane="left",   # further out so cut-in has room
            patterns=("vehicle.audi.tt", "vehicle.mini.cooper*"),
            autopilot=True)
        self.from_left = True
        if self.threat is not None:
            threat_wp = ctx.map.get_waypoint(self.threat.get_location())
            ego_wp = ctx.map.get_waypoint(ctx.ego.get_location())
            if threat_wp.lane_id == ego_wp.lane_id:  # left fallback failed
                self.from_left = False
        if self.threat is not None:
            ctx.tm.vehicle_percentage_speed_difference(self.threat, 15)
            ctx.tm.auto_lane_change(self.threat, False)

    def on_tick(self, ctx, frame, sim_time):
        super().on_tick(ctx, frame, sim_time)
        if self.threat is None or not self.threat.is_alive:
            self.finished = True
            return
        if self.check_trigger(ctx, self.threat, frame, "cut_in_executed"):
            # cut toward ego lane: from left lane -> change right (False)
            ctx.tm.force_lane_change(self.threat, not self.from_left)
            ctx.tm.vehicle_percentage_speed_difference(self.threat, 25)
