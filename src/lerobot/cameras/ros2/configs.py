import logging
from dataclasses import dataclass, field
from lerobot.cameras.configs import CameraConfig

logger = logging.getLogger(__name__)

@CameraConfig.register_subclass("ros2")
@dataclass(kw_only=True)
class ROS2CameraConfig(CameraConfig):
    """Configuration for a ROS2 camera that subscribes to an Image topic."""
    type: str = field(default="ros2")
    topic: str
    
    # Resizing options: Default to None to keep original resolution
    # Set to specific values (e.g., 640, 480) if you need to resize
    width: int | None = None
    height: int | None = None
    
    # Optional conversion flag if it's already RGB/BGR
    is_bgr: bool = True 
