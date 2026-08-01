"""#14 Stalled vehicle in lane: hazard-lit dead vehicle blocks the ego lane;
ego must detect, slow, and pass safely (NHTSA Lead Vehicle Stopped)."""
import carla

from scenarios.base_scenario import BaseScenario
from simulation import world_utils as wu


class StationaryHazard(BaseScenario):
    NAME = "stationary_hazard"
    NEEDS = ["adjacent_lane"]

    def setup(self, ctx):
        self.stalled, _wp = self.spawn_vehicle_ahead(
            ctx, distance=58.0, lane="same",
            patterns=("vehicle.nissan.patrol*", "vehicle.audi.a2"),
            autopilot=False)
        if self.stalled is None:
            self.finished = True
            return
        self.stalled.apply_control(carla.VehicleControl(hand_brake=True))
        try:
            self.stalled.set_light_state(carla.VehicleLightState(
                carla.VehicleLightState.RightBlinker
                | carla.VehicleLightState.LeftBlinker
                | carla.VehicleLightState.Position))
        except Exception:  # noqa: BLE001
            pass
        ego_wp = ctx.map.get_waypoint(ctx.ego.get_location())
        left = ego_wp.get_left_lane()
        self.merge_left = bool(
            left is not None and left.lane_type == carla.LaneType.Driving
            and left.lane_id * ego_wp.lane_id > 0)

    def on_tick(self, ctx, frame, sim_time):
        super().on_tick(ctx, frame, sim_time)
        if self.stalled is None:
            return
        if self.check_trigger(ctx, self.stalled, frame, "stalled_vehicle"):
            ctx.tm.force_lane_change(ctx.ego, self.merge_left)
            ctx.collector.mark_event(
                "ego_pass_maneuver", frame,
                {"direction": "left" if self.merge_left else "right"})
