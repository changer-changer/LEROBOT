from typing import cast
from lerobot.tactile.configs import TactileSensorConfig

def make_tactile_sensors_from_configs(sensor_configs: dict[str, TactileSensorConfig]):
    from lerobot.tactile.tactile_sensor import TactileSensor
    sensors: dict[str, TactileSensor] = {}

    for key, cfg in sensor_configs.items():
        if cfg.type == "tac3d":
            from lerobot.tactile.direct_connection.tac3d_sensor import Tac3DTactileSensor
            sensors[key] = Tac3DTactileSensor(cfg)
        elif cfg.type == "pointcloud2":
            from lerobot.tactile.ros2_bridge.pointcloud2_sensor import PointCloud2TactileSensor
            sensors[key] = PointCloud2TactileSensor(cfg)
        else:
            raise ValueError(f"Unknown tactile sensor type {cfg.type}")

    return sensors
