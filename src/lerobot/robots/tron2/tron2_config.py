from dataclasses import dataclass, field
from typing import Dict, List

from lerobot.cameras import CameraConfig
from lerobot.cameras.ros2.configs import ROS2CameraConfig
from lerobot.tactile.configs import TactileSensorConfig, Tac3DSensorConfig
from lerobot.robots.config import RobotConfig

@dataclass
class SimpleCameraConfig(CameraConfig):
    # This inherits CameraConfig parameters (like fps, width, height)
    # We provide a simplified init for local usage.
    type: str = "opencv"


@RobotConfig.register_subclass("tron2")
@dataclass
class Tron2RobotConfig(RobotConfig):
    type: str = "tron2"

    # Robot connection parameters
    robot_ip: str = "10.192.1.2"
    
    # Cameras configuration
    cameras: dict[str, CameraConfig] = field(
        default_factory=lambda: {
            "cam_left": ROS2CameraConfig(
                topic="/camera/right/color/image_rect_raw", fps=30, width=640, height=480
            ),
            "cam_right": ROS2CameraConfig(
                topic="/camera/left/color/image_rect_raw", fps=30, width=640, height=480
            ),
        }
    )

    # Tactile Sensors configuration
    tactile_sensors: dict[str, TactileSensorConfig] = field(
        default_factory=lambda: {
            "tac3d_sensor": Tac3DSensorConfig(udp_port=9988)
        }
    )

    # Initial joint positions if needed to restore state
    # Tron2 has 16 motors
    init_joint_positions: List[float] = field(
        default_factory=lambda: [0.0] * 16
    )

    # Safety: Max relative movement per dt
    max_relative_target: float | None = None


