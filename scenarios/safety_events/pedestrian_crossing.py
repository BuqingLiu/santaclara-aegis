"""#1 Sudden pedestrian crossing: a pedestrian waits at the curb ~45 m ahead
and dashes across the ego lane once the ego closes within trigger distance."""
from scenarios.base_scenario import BaseScenario


class PedestrianCrossing(BaseScenario):
    NAME = "pedestrian_crossing"
    NEEDS = []

    def setup(self, ctx):
        self.walker, self.ctrl, self.wp = self.spawn_walker_offset(
            ctx, distance_ahead=45.0, right_offset=3.6)

    def on_tick(self, ctx, frame, sim_time):
        super().on_tick(ctx, frame, sim_time)
        if self.walker is None:
            self.finished = True
            return
        if self.check_trigger(ctx, self.walker, frame, "pedestrian_dash"):
            self.send_walker_kinematic(self.walker, self.wp,
                                       right_offset=-5.5, speed=2.8)
