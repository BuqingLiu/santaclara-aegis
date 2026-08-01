"""#12 Multi-pedestrian jaywalking group: three pedestrians cross mid-block
at staggered speeds, forcing multi-object tracking and gap negotiation."""
from scenarios.base_scenario import BaseScenario


class _IdleTrigger:
    """A 'driver' that fires a one-shot callback after `delay_s` and then sits."""

    def __init__(self, delay_s, fn):
        self.ticks = max(1, int(round(delay_s / 0.05)))
        self.fn = fn
        self.done = False

    def step(self):
        if self.done:
            return
        self.ticks -= 1
        if self.ticks <= 0:
            try:
                self.fn()
            finally:
                self.done = True


class JaywalkingGroup(BaseScenario):
    NAME = "jaywalking_group"
    NEEDS = []
    LAYOUT = [(35.0, 3.4, 1.6), (40.0, 3.8, 2.2), (45.0, 3.2, 2.8)]
    # (distance ahead, curb offset, crossing speed m/s)

    def __init__(self, meta):
        super().__init__(meta)
        self.group = []

    def setup(self, ctx):
        for dist, offset, speed in self.LAYOUT:
            walker, ctrl, wp = self.spawn_walker_offset(
                ctx, distance_ahead=dist, right_offset=offset)
            if walker is not None:
                self.group.append((walker, ctrl, wp, dist, speed))
        if not self.group:
            self.finished = True
            return
        # staggered starts: lead walker crosses first
        self.group.sort(key=lambda g: g[3])
        for i, (_walker, ctrl, wp, _dist, speed) in enumerate(self.group):
            delay = i * 0.8
            self.drivers.append(_IdleTrigger(delay, self._start_crossing))
        self.triggered = True

    def _start_crossing(self):
        for walker, ctrl, wp, _dist, speed in self.group:
            self.send_walker_kinematic(walker, wp, right_offset=-5.5,
                                       speed=speed)

    def on_tick(self, ctx, frame, sim_time):
        super().on_tick(ctx, frame, sim_time)
        if not self.group:
            return
        ctx.collector.mark_event("group_jaywalk_active", frame,
                                 {"n_walkers": len(self.group)})
