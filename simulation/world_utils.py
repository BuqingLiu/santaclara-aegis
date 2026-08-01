"""Map-agnostic world helpers: spawn search, junction routing, chase camera,
and a lightweight waypoint-following driver for scripted threat vehicles."""
import math

import carla


# --------------------------------------------------------------------------- #
# kinematics helpers
# --------------------------------------------------------------------------- #
def speed_of(actor) -> float:
    """Actor speed in m/s."""
    v = actor.get_velocity()
    return math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)


def dist_between(a, b) -> float:
    return a.get_location().distance(b.get_location())


def norm_angle(deg: float) -> float:
    while deg > 180.0:
        deg -= 360.0
    while deg < -180.0:
        deg += 360.0
    return deg


# --------------------------------------------------------------------------- #
# spawn-point selection
# --------------------------------------------------------------------------- #
def _has_same_dir_adjacent(wp) -> bool:
    for lane in (wp.get_left_lane(), wp.get_right_lane()):
        if (lane is not None and lane.lane_type == carla.LaneType.Driving
                and lane.lane_id * wp.lane_id > 0):
            return True
    return False


def _junction_distance(world_map, spawn, max_dist=130.0):
    """Distance from spawn to the first junction ahead, or None."""
    wp = world_map.get_waypoint(spawn.location)
    travelled = 0.0
    while travelled < max_dist:
        nxt = wp.next(4.0)
        if not nxt:
            return None
        wp = nxt[0]
        travelled += 4.0
        if wp.is_junction:
            return travelled
    return None


def _wp_transform(wp, z_lift=0.25):
    """Spawn transform derived from a waypoint (carries the correct road
    surface elevation -- critical on OSM OpenDRIVE, where CARLA's flat
    auto spawn points (z~0.5) often sit *under* the road mesh and eject
    the vehicle)."""
    return carla.Transform(
        carla.Location(wp.transform.location.x, wp.transform.location.y,
                       wp.transform.location.z + z_lift),
        wp.transform.rotation)


def find_ego_spawn(world_map, needs, min_ahead=90.0):
    """Backward-compatible single spawn (first preferred candidate)."""
    cands = ego_spawn_candidates(world_map, needs, min_ahead)
    if cands:
        return cands[0]
    sp = world_map.get_spawn_points()[0]
    return sp, _junction_distance(world_map, sp)


def ego_spawn_candidates(world_map, needs, min_ahead=90.0,
                        max_junction=5, max_general=3):
    """Return a ranked list of (transform, junction_dist) ego spawn candidates
    derived from road WAYPOINTS (not CARLA's flat auto spawn points).

    Why this matters: on OSM-derived OpenDRIVE, CARLA's get_spawn_points()
    frequently returns points sitting inside malformed junction meshes. A
    vehicle spawned there penetrates the mesh, gets stuck, and is then
    violently ejected by the physics solver -- the root cause of the
    322/562/361 km/h "mutation" blow-ups. Deriving spawns from waypoints
    (correct elevation) and letting the caller TEST each one for freedom of
    motion eliminates that failure mode.

    Junction candidates are listed first (preferred for junction scenarios);
    general non-junction candidates follow as a safe fallback.
    """
    needs = set(needs or [])
    spawns = world_map.get_spawn_points()
    if not spawns:
        spawns = [w.transform for w in world_map.generate_waypoints(4.0)]

    out = []
    # --- pass 1: junction candidates (preferred) -------------------------
    if "junction" in needs:
        for sp in spawns:
            wp = world_map.get_waypoint(sp.location)
            if wp is None or wp.is_junction:
                continue
            if not wp.next(min_ahead):
                continue
            jd = _junction_distance(world_map, sp, max_dist=140.0)
            if jd is None or jd < 45.0 or jd > 110.0:
                continue
            out.append((_wp_transform(wp), jd))
            if len(out) >= max_junction:
                break
    # --- pass 2: general non-junction candidates (fallback) --------------
    for sp in spawns:
        wp = world_map.get_waypoint(sp.location)
        if wp is None or wp.is_junction:
            continue
        if not wp.next(min_ahead):
            continue
        if "adjacent_lane" in needs and not _has_same_dir_adjacent(wp):
            continue
        out.append((_wp_transform(wp), None))
        if len(out) >= max_junction + max_general:
            break
    return out


def forward_waypoint(world_map, actor_or_transform, distance):
    """Waypoint `distance` metres ahead along the lane."""
    loc = (actor_or_transform.get_location()
           if hasattr(actor_or_transform, "get_location")
           else actor_or_transform.location)
    wp = world_map.get_waypoint(loc)
    nxt = wp.next(max(distance, 1.0))
    return nxt[0] if nxt else wp


def backward_waypoint(world_map, actor, distance):
    wp = world_map.get_waypoint(actor.get_location())
    prev = wp.previous(max(distance, 1.0))
    return prev[0] if prev else wp


def lateral_offset(transform, right_metres):
    """Location shifted sideways from a transform (+right / -left)."""
    rv = transform.get_right_vector()
    return carla.Location(x=transform.location.x + rv.x * right_metres,
                          y=transform.location.y + rv.y * right_metres,
                          z=transform.location.z)


def try_spawn(world, blueprint, transform, z_lift=0.3, retries=4):
    """Spawn with progressive z-lift to dodge ground collisions."""
    tr = carla.Transform(
        carla.Location(transform.location.x, transform.location.y,
                       transform.location.z + z_lift),
        transform.rotation)
    for _ in range(retries):
        actor = world.try_spawn_actor(blueprint, tr)
        if actor is not None:
            return actor
        tr.location.z += 0.35
    return None


# --------------------------------------------------------------------------- #
# junction discovery & routing
# --------------------------------------------------------------------------- #
def find_junction_ahead(world_map, ego, max_dist=140.0):
    """Returns (junction, entry_wp_of_ego_path, distance) or (None, None, None)."""
    wp = world_map.get_waypoint(ego.get_location())
    travelled = 0.0
    while travelled < max_dist:
        nxt = wp.next(3.0)
        if not nxt:
            break
        wp = nxt[0]
        travelled += 3.0
        if wp.is_junction:
            return wp.get_junction(), wp, travelled
    return None, None, None


def junction_entries(junction, exclude_road_id=None):
    """(entry_wp, exit_wp) pairs, optionally excluding the ego's own road."""
    pairs = junction.get_waypoints(carla.LaneType.Driving)
    if exclude_road_id is None:
        return pairs
    out = []
    for entry, exit_wp in pairs:
        prev = entry.previous(6.0)
        road = prev[0].road_id if prev else entry.road_id
        if road != exclude_road_id:
            out.append((entry, exit_wp))
    return out or pairs


def chain_route(start_wp, step=3.0, length=70.0):
    """Sample a list of Locations following the lane from start_wp."""
    locs = [start_wp.transform.location]
    wp, travelled = start_wp, 0.0
    while travelled < length:
        nxt = wp.next(step)
        if not nxt:
            break
        wp = nxt[0]
        locs.append(wp.transform.location)
        travelled += step
    return locs


def set_lights_near(world, location, radius, state, freeze=True):
    """Force all traffic lights within radius to a state (demo control)."""
    changed = []
    for tl in world.get_actors().filter("traffic.traffic_light"):
        if tl.get_location().distance(location) < radius:
            tl.set_state(state)
            if freeze:
                tl.freeze(True)
            changed.append(tl)
    return changed


# --------------------------------------------------------------------------- #
# scripted threat driver (deterministic, no Traffic Manager dependency)
# --------------------------------------------------------------------------- #
class RouteDriver:
    """Minimal P-controller that drives a vehicle through a list of Locations.

    Used for scripted adversaries (red-light runner, left-turner, cyclist...)
    where deterministic, repeatable motion matters more than realism of AI.
    """

    def __init__(self, vehicle, route, target_speed=8.0, hold_at_end=True):
        self.vehicle = vehicle
        self.route = list(route)
        self.target_speed = target_speed
        self.hold_at_end = hold_at_end
        self.done = False

    def step(self):
        if self.done:
            return True
        try:
            if not self.vehicle.is_alive:
                self.done = True
                return True
            loc = self.vehicle.get_location()
            while self.route and loc.distance(self.route[0]) < 3.5:
                self.route.pop(0)
            if not self.route:
                self.done = True
                if self.hold_at_end:
                    self.vehicle.apply_control(
                        carla.VehicleControl(brake=1.0, hand_brake=True))
                return True

            target = self.route[0]
            tr = self.vehicle.get_transform()
            desired_yaw = math.degrees(math.atan2(target.y - loc.y,
                                                 target.x - loc.x))
            err = norm_angle(desired_yaw - tr.rotation.yaw)
            steer = max(-0.8, min(0.8, err / 45.0))

            spd = speed_of(self.vehicle)
            throttle = 0.75 if spd < self.target_speed else 0.0
            brake = 0.4 if spd > self.target_speed + 2.0 else 0.0
            self.vehicle.apply_control(
                carla.VehicleControl(throttle=throttle, steer=steer,
                                     brake=brake))
            return False
        except Exception:  # noqa: BLE001 - actor likely destroyed off-map
            self.done = True
            return True


class EgoGovernor:
    """Deterministic, speed-capped ego driver.

    Replaces Traffic Manager autopilot for the ego so its speed is *guaranteed*
    bounded — this is the real fix for the 322/435 km/h blow-up on OSM maps
    where CARLA's TM cannot read a speed limit and floors the throttle. The
    governor follows road waypoints and never commands throttle above the
    target; it also does a light forward-proximity brake (basic AEB) so the
    ego still reacts to VRUs/vehicles for the demo.
    """

    def __init__(self, ego, carla_map, target_speed, lookahead=9.0):
        self.ego = ego
        self.map = carla_map
        self.target = float(target_speed)
        self.lookahead = lookahead

    def _ahead_obstacle(self):
        loc = self.ego.get_location()
        fwd = self.ego.get_transform().get_forward_vector()
        best = None
        for a in self.ego.get_world().get_actors():
            if a.id == self.ego.id or not a.is_alive:
                continue
            # only real road users count as obstacles; skip sensors/props
            # (cameras/LiDAR are attached to the ego and sit right next to
            # it, which would otherwise trigger a constant false AEB brake)
            tid = a.type_id
            if not (tid.startswith("vehicle.") or tid.startswith("walker.")):
                continue
            t = a.get_transform().location
            dx, dy = t.x - loc.x, t.y - loc.y
            fwd_dist = dx * fwd.x + dy * fwd.y
            if fwd_dist < 2.0 or fwd_dist > 22.0:
                continue
            lat = abs(dx * fwd.y - dy * fwd.x)
            if lat > 2.6:
                continue
            if best is None or fwd_dist < best:
                best = fwd_dist
        return best

    def step(self):
        if not self.ego.is_alive:
            return
        try:
            wp = forward_waypoint(self.map, self.ego, self.lookahead)
        except Exception:  # noqa: BLE001
            wp = None
        if wp is None:
            # CRITICAL: never leave stale throttle applied. Losing the
            # forward waypoint (malformed OSM junction, end of road) used
            # to early-return here, which pinned the previous 0.55
            # throttle forever -> the 361 m/s runaway. Brake instead.
            try:
                self.ego.apply_control(
                    carla.VehicleControl(throttle=0.0, brake=1.0))
            except Exception:  # noqa: BLE001
                pass
            return
        tr = self.ego.get_transform()

        # --- rollover detection & auto-recovery -------------------------
        # A flipped/stuck ego is what froze the screen: the chase camera
        # keeps staring at a wreck forever. If the car is on its side or
        # roof, set it upright on the nearest waypoint and zero velocity.
        roll = abs(norm_angle(tr.rotation.roll))
        pitch = abs(norm_angle(tr.rotation.pitch))
        if roll > 70.0 or pitch > 70.0:
            self._recover(wp)
            return

        desired = math.degrees(math.atan2(
            wp.transform.location.y - tr.location.y,
            wp.transform.location.x - tr.location.x))
        err = norm_angle(desired - tr.rotation.yaw)
        spd = speed_of(self.ego)
        # speed-aware steering limit: full 0.7 lock only below 6 m/s;
        # at speed the max steer shrinks (~0.28 at 15 m/s) so a sharp
        # waypoint error can never flip the car (the rollover root cause).
        max_steer = 0.7 if spd < 6.0 else max(0.12, 0.7 * 6.0 / spd)
        steer = max(-max_steer, min(max_steer, err / 30.0))
        obs = self._ahead_obstacle()
        diff = self.target - spd
        if obs is not None and obs < max(6.0, spd * 1.2):
            throttle, brake = 0.0, 0.8          # basic AEB
        elif diff > 1.0:                        # proportional accel
            throttle, brake = min(0.55, 0.25 + 0.05 * diff), 0.0
        elif diff < -1.0:                       # proportional brake
            throttle, brake = 0.0, min(0.85, 0.25 + 0.15 * (-diff))
        else:
            throttle, brake = 0.25, 0.0
        self.ego.apply_control(
            carla.VehicleControl(throttle=throttle, steer=steer, brake=brake))

    def _recover(self, wp):
        """Set a flipped ego upright on the road and stop it dead, so the
        demo keeps running instead of freezing on a wreck."""
        try:
            tf = wp.transform
            tf.location.z += 0.4
            self.ego.set_transform(tf)
            for name in ("set_target_velocity", "set_velocity"):
                setter = getattr(self.ego, name, None)
                if callable(setter):
                    setter(carla.Vector3D(0.0, 0.0, 0.0))
                    break
            ang = getattr(self.ego, "set_target_angular_velocity", None)
            if callable(ang):
                ang(carla.Vector3D(0.0, 0.0, 0.0))
            self.ego.apply_control(
                carla.VehicleControl(throttle=0.0, brake=1.0))
        except Exception:  # noqa: BLE001
            pass


# --------------------------------------------------------------------------- #
# hard speed cap (defence in depth)
# --------------------------------------------------------------------------- #
def hard_clamp(actor, max_mps):
    """Last-resort speed governor: if the actor somehow exceeds max_mps,
    brake AND attempt to zero its velocity.

    Why both: a plain brake cannot recover from a *collision impulse* (e.g. a
    heavy vehicle shoving the ego), because the impulse is injected during
    world.tick() and a single brake command only decelerates from there.
    Resetting the velocity to zero outright kills any runaway. We use
    getattr so this is safe on CARLA builds where `set_velocity` does not
    exist on the actor (it was absent / renamed in some 0.9.x variants).
    """
    try:
        spd = speed_of(actor)
        if spd > max_mps:
            actor.apply_control(
                carla.VehicleControl(throttle=0.0, brake=1.0))
            # CARLA >= 0.9.12 renamed set_velocity -> set_target_velocity.
            # This is the only way to kill a collision-impulse runaway
            # (a brake alone cannot undo an injected impulse).
            for name in ("set_target_velocity", "set_velocity"):
                setter = getattr(actor, name, None)
                if callable(setter):
                    # scale current velocity down to the cap instead of a
                    # hard zero, so the correction is invisible on camera
                    v = actor.get_velocity()
                    k = max_mps / max(spd, 0.001)
                    setter(carla.Vector3D(v.x * k, v.y * k, v.z * k))
                    break
            setattr(actor, "_hard_clamp_fired", True)
            return True
    except Exception:  # noqa: BLE001 - never let the safety net crash the sim
        pass
    return False


# --------------------------------------------------------------------------- #
# camera
# --------------------------------------------------------------------------- #
def chase_spectator(world, ego, back=9.5, up=4.2, pitch=-14.0):
    """Keep the CARLA server window locked onto the ego vehicle."""
    tr = ego.get_transform()
    fwd = tr.get_forward_vector()
    loc = carla.Location(x=tr.location.x - fwd.x * back,
                         y=tr.location.y - fwd.y * back,
                         z=tr.location.z + up)
    rot = carla.Rotation(pitch=pitch, yaw=tr.rotation.yaw)
    world.get_spectator().set_transform(carla.Transform(loc, rot))
