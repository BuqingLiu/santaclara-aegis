"""#9 Construction zone forced merge: a cone taper closes the ego lane;
the ego must plan and execute a merge into the adjacent lane (CA MUTCD)."""
import carla

from scenarios.base_scenario import BaseScenario
from simulation import world_utils as wu


class ConstructionZone(BaseScenario):
    NAME = "construction_zone"
    NEEDS = ["adjacent_lane"]

    def setup(self, ctx):
        self.first_cone_loc = None
        cone_bps = ("static.prop.trafficcone01", "static.prop.constructioncone")
        bp = None
        for pat in cone_bps:
            found = ctx.blueprints.filter(pat)
            if found:
                bp = found[0]
                break
        base = 52.0
        for i in range(6):   # taper: edge -> lane centre
            wp = wu.forward_waypoint(ctx.map, ctx.ego, base + i * 4.0)
            offset = max(0.0, 1.8 - i * 0.4)
            loc = wu.lateral_offset(wp.transform, offset)
            loc.z += 0.2
            cone = ctx.world.try_spawn_actor(
                bp, carla.Transform(loc, wp.transform.rotation))
            if cone is not None:
                self.actors.append(cone)
                if self.first_cone_loc is None:
                    self.first_cone_loc = loc

        # merge direction: prefer whichever same-direction lane exists
        ego_wp = ctx.map.get_waypoint(ctx.ego.get_location())
        left = ego_wp.get_left_lane()
        self.merge_left = bool(
            left is not None and left.lane_type == carla.LaneType.Driving
            and left.lane_id * ego_wp.lane_id > 0)

    def on_tick(self, ctx, frame, sim_time):
        super().on_tick(ctx, frame, sim_time)
        if self.first_cone_loc is None:
            self.finished = True
            return
        if self.check_trigger(ctx, self.first_cone_loc, frame,
                              "workzone_merge"):
            ctx.tm.force_lane_change(ctx.ego, self.merge_left)
            ctx.collector.mark_event(
                "ego_lane_change", frame,
                {"direction": "left" if self.merge_left else "right"})
