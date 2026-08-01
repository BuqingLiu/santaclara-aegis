"""Robust CARLA connection + synchronous-mode lifecycle management."""
import carla

from utils.logger import get_logger

log = get_logger("client")


class CarlaSession:
    """Owns the client/world/traffic-manager and guarantees clean restore."""

    def __init__(self, config):
        self.cfg = config
        self.client = None
        self.world = None
        self.tm = None
        self._original_settings = None

    # ------------------------------------------------------------------ #
    def connect(self):
        self.client = carla.Client(self.cfg["host"], self.cfg["port"])
        self.client.set_timeout(self.cfg["timeout"])
        version = self.client.get_server_version()
        log.info("Connected to CARLA server %s @ %s:%s",
                 version, self.cfg["host"], self.cfg["port"])
        return version

    def load_map(self, map_name=None, region=None):
        map_name = map_name or self.cfg["map"]

        # Real-road path: download OSM -> convert -> load OpenDRIVE world.
        if map_name in ("custom", "real", "osm"):
            from simulation.map_loader import load_real_map
            region = region or self.cfg.get("region", "santa_clara")
            log.info("Real-road mode requested (region=%s).", region)
            self.world = load_real_map(self, region=region)
            self._apply_map_layers()
            return self.world

        self.world = self.client.get_world()
        current = self.world.get_map().name  # e.g. "Carla/Maps/Town10HD_Opt"
        if map_name.split("/")[-1] not in current:
            log.info("Loading map %s (current: %s)...", map_name, current)
            self.world = self.client.load_world(map_name)
        else:
            log.info("Map %s already loaded - reusing (fast path).", current)

        if self.cfg.get("unload_heavy_layers") and "_Opt" in current + map_name:
            for layer in (carla.MapLayer.ParkedVehicles, carla.MapLayer.Props,
                          carla.MapLayer.Decals, carla.MapLayer.Foliage):
                try:
                    self.world.unload_map_layer(layer)
                except Exception:  # noqa: BLE001 - cosmetic only
                    pass
        return self.world

    def _apply_map_layers(self):
        """For real OSM maps: keep buildings/props (they add realism) but
        optionally strip only the heaviest decorative layers on low-end GPUs."""
        if not self.cfg.get("unload_heavy_layers"):
            return
        try:
            for layer in (carla.MapLayer.Decals, carla.MapLayer.Foliage):
                try:
                    self.world.unload_map_layer(layer)
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001
            pass

    def enable_sync(self):
        self._original_settings = self.world.get_settings()
        settings = self.world.get_settings()
        settings.synchronous_mode = self.cfg["sync_mode"]
        settings.fixed_delta_seconds = self.cfg["fixed_delta_seconds"]
        self.world.apply_settings(settings)

        self.tm = self.client.get_trafficmanager(self.cfg["tm_port"])
        self.tm.set_synchronous_mode(self.cfg["sync_mode"])
        self.tm.set_random_device_seed(self.cfg["tm_seed"])
        self.tm.set_global_distance_to_leading_vehicle(3.0)
        # Cap speed so the ego/background never run away on OSM-derived maps
        # where CARLA infers an unbounded speed limit.
        try:
            self.tm.set_global_speed_limit(float(self.cfg.get("max_speed_mps",
                                                              16.0)))
        except Exception:  # noqa: BLE001 - method may differ across versions
            pass
        log.info("Synchronous mode ON (dt=%.2fs, TM seed=%s, vmax=%.1f m/s)",
                 self.cfg["fixed_delta_seconds"], self.cfg["tm_seed"],
                 float(self.cfg.get("max_speed_mps", 16.0)))

    def restore(self):
        """Always return the server to a safe async state."""
        try:
            if self.tm is not None:
                self.tm.set_synchronous_mode(False)
            if self.world is not None and self._original_settings is not None:
                self._original_settings.synchronous_mode = False
                self._original_settings.fixed_delta_seconds = None
                self.world.apply_settings(self._original_settings)
            log.info("World settings restored (async mode).")
        except Exception as exc:  # noqa: BLE001
            log.warning("Restore skipped: %s", exc)
