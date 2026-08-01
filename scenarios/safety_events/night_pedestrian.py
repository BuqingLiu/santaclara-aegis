"""#11 Night-time pedestrian crossing: low-light VRU detection case
(FMVSS 127-aligned PAEB night condition)."""
from scenarios.safety_events.pedestrian_crossing import PedestrianCrossing


class NightPedestrian(PedestrianCrossing):
    """Identical geometry to daytime crossing; weather = Night is applied
    from config/scenarios.json, isolating illumination as the variable."""
    NAME = "night_pedestrian"
    NEEDS = []

    def on_tick(self, ctx, frame, sim_time):
        if self.walker is None:
            self.finished = True
            return
        if self.check_trigger(ctx, self.walker, frame,
                              "night_pedestrian_dash"):
            self.send_walker_kinematic(self.walker, self.wp,
                                       right_offset=-5.5, speed=2.4)
        for d in self.drivers:
            d.step()
