"""Sensor rig: complete automotive sensor stack for AV validation.

Attached to the ego vehicle:
  * RGB chase camera    -> evidence frames (PNG) + optional MP4 stream
  * Depth camera        -> depth maps (PNG, represented as grayscale)
  * Semantic seg camera  -> pixel-level road/user labelling (PNG)
  * LiDAR               -> point cloud (.npy per frame + .ply on demand)
  * Collision sensor    -> safety-outcome events

Everything is saved per-frame with the simulation frame index so it can be
re-associated with telemetry.csv / events.json during post-processing.
"""
from pathlib import Path

import carla

from utils.logger import get_logger

log = get_logger("sensors")

# CARLA sensor -> colour converter pairs we want saved as PNG.
_CAMERA_CONVERTERS = {
    "rgb": None,
    "depth": carla.ColorConverter.Depth,
    "semantic": carla.ColorConverter.CityScapesPalette,
}


class SensorRig:
    def __init__(self, world, ego, camera_cfg, frames_dir, on_collision,
                 capture_video=True):
        self.world = world
        self.ego = ego
        self.sensors = []
        self.frames_dir = Path(frames_dir)
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self._save_every = int(camera_cfg.get("save_every_n_frames", 20))
        self._capture_video = capture_video
        self._video_writer = None
        self._video_size = (int(camera_cfg.get("width", 960)),
                            int(camera_cfg.get("height", 540)))
        self._video_fps = 10

        self._attach_cameras(camera_cfg)
        self._attach_lidar(camera_cfg)
        self._attach_collision(on_collision)
        log.info("Sensor rig attached: RGB + Depth + Semantic + LiDAR + Collision")

    # ------------------------------------------------------------------ #
    def _attach_cameras(self, cfg):
        w, h = self._video_size
        fov = str(cfg.get("fov", 90))
        for kind, converter in _CAMERA_CONVERTERS.items():
            bp = self.world.get_blueprint_library().find(
                "sensor.camera.rgb")
            bp.set_attribute("image_size_x", str(w))
            bp.set_attribute("image_size_y", str(h))
            bp.set_attribute("fov", fov)
            transform = carla.Transform(
                carla.Location(x=cfg.get("x", -7.0), z=cfg.get("z", 3.4)),
                carla.Rotation(pitch=cfg.get("pitch", -14.0)))
            cam = self.world.spawn_actor(bp, transform, attach_to=self.ego)
            sub = self.frames_dir / kind
            sub.mkdir(parents=True, exist_ok=True)
            self._listen_camera(cam, sub, converter, kind)
            self.sensors.append(cam)

    def _listen_camera(self, cam, out_dir, converter, kind):
        every, vw = self._save_every, self._video_writer

        def _on_image(image):
            if converter is not None:
                image.convert(converter)
            if image.frame % every == 0:
                image.save_to_disk(str(out_dir / f"frame_{image.frame:07d}.png"))
            # feed the RGB stream into the MP4 writer
            if kind == "rgb" and self._capture_video:
                import numpy as np
                arr = np.frombuffer(image.raw_data, dtype=np.uint8)
                arr = arr.reshape((image.height, image.width, 4))[:, :, :3]
                arr = arr[:, :, ::-1].copy()  # BGR for cv2
                if self._video_writer is None:
                    import cv2
                    vpath = str(self.frames_dir.parent / "live.mp4")
                    self._video_writer = cv2.VideoWriter(
                        vpath, cv2.VideoWriter_fourcc(*"mp4v"),
                        self._video_fps, (image.width, image.height))
                self._video_writer.write(arr)

        cam.listen(_on_image)

    def _attach_lidar(self, cfg):
        bp = self.world.get_blueprint_library().find("sensor.lidar.ray_cast")
        bp.set_attribute("channels", "32")
        bp.set_attribute("points_per_second", "320000")
        bp.set_attribute("rotation_frequency", "20")
        bp.set_attribute("range", "60")
        bp.set_attribute("upper_fov", "5.0")
        bp.set_attribute("lower_fov", "-25.0")
        transform = carla.Transform(carla.Location(z=2.2))
        lidar = self.world.spawn_actor(bp, transform, attach_to=self.ego)
        out_dir = self.frames_dir / "lidar"
        out_dir.mkdir(parents=True, exist_ok=True)

        def _on_lidar(pc):
            import numpy as np
            pts = np.frombuffer(pc.raw_data, dtype=np.float32)
            pts = pts.reshape((-1, 4))  # x, y, z, intensity
            np.save(out_dir / f"frame_{pc.frame:07d}.npy", pts)

        lidar.listen(_on_lidar)
        self.sensors.append(lidar)

    def _attach_collision(self, on_collision):
        bp = self.world.get_blueprint_library().find("sensor.other.collision")
        sensor = self.world.spawn_actor(bp, carla.Transform(),
                                        attach_to=self.ego)
        sensor.listen(on_collision)
        self.sensors.append(sensor)

    # ------------------------------------------------------------------ #
    def destroy(self):
        if self._video_writer is not None:
            self._video_writer.release()
            self._video_writer = None
        for s in self.sensors:
            try:
                if s.is_alive:
                    s.stop()
                    s.destroy()
            except Exception:  # noqa: BLE001
                pass
        self.sensors.clear()
