"""#17 Bus-stop pedestrian dart-out: a child/elderly steps from behind a
stopped bus into the ego lane — the classic "vision occlusion" case
(transit-stop VRUs are a top California cyclist/pedestrian fatality source).
"""
import carla

from scenarios.base_scenario import BaseScenario
from simulation import world_utils as wu


class BusStopPedestrian(BaseScenario):
    NAME = "bus_stop_pedestrian"
    NEEDS = []

    def setup(self, ctx):
        # stopped bus in the right lane ahead
        self.bus, _ = self.spawn_vehicle_ahead(
            ctx, distance=16.0, lane="right",
            patterns=("vehicle.mitsubishi.fusorosa",
                      "vehicle.mercedes.sprinter"),
            autopilot=False)
        if self.bus is not None:
            self.bus.apply_control(
                carla.VehicleControl(brake=1.0, hand_brake=True))
        # pedestrian hidden behind the bus (right, slightly behind)
        self.walker, _ctrl, wp = self.spawn_walker_offset(
            ctx, distance_ahead=14.0, right_offset=7.0)
        self._wp = wp

    def on_tick(self, ctx, frame, sim_time):
        super().on_tick(ctx, frame, sim_time)
        if self.walker is None or not self.walker.is_alive:
            return
        if self.check_trigger(ctx, self.walker, frame, "child_dart_from_bus"):
            # dart left across to the ego lane (navmesh-free kinematic move)
            self.send_walker_kinematic(self.walker, self._wp,
                                       right_offset=-6.0, speed=3.2)
