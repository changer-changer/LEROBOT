import logging
import threading
import time
from typing import Any, List, Dict

import numpy as np
import cv2
import gc
from lerobot.cameras.camera import Camera
from lerobot.cameras.ros2.configs import ROS2CameraConfig

try:
    import rclpy
    from rclpy.node import Node
    from rclpy.executors import MultiThreadedExecutor
    from sensor_msgs.msg import Image
    RCLPY_AVAILABLE = True
except ImportError:
    logging.warning("rclpy or sensor_msgs not found. ROS2Camera will not work until ROS2 is sourced.")
    RCLPY_AVAILABLE = False
    Node = object  # Dummy so the class definition below parses
    Image = object

logger = logging.getLogger(__name__)

class ROS2CameraNode(Node):
    def __init__(self, node_name: str, topic: str, target_size: tuple = None):
        super().__init__(node_name)
        self.latest_frame = None
        self.frame_event = threading.Event()
        self.target_size = target_size
        self._callback_count = 0
        self.subscription = self.create_subscription(
            Image,
            topic,
            self.image_callback,
            1  # QoS profile depth (keep only the latest msg)
        )
        logger.info(f"ROS2 Camera Node '{node_name}' subscribed to '{topic}' (Resize: {target_size})")

    def image_callback(self, msg: Image):
        # Extremely fast manual conversion from ROS2 Image to NumPy without cv_bridge dependency
        dtype = np.uint8
        if msg.encoding in ['rgb8', 'bgr8']:
            channels = 3
        elif msg.encoding in ['mono8']:
            channels = 1
        elif msg.encoding in ['16UC1']:
            dtype = np.uint16
            channels = 1
        else:
            logger.warning(f"Unsupported encoding: {msg.encoding}")
            return
            
        frame = np.frombuffer(msg.data, dtype=dtype).reshape((msg.height, msg.width, channels))
        if frame.shape[2] == 1:
            frame = frame.squeeze(axis=2)
            
        if self.target_size is not None:
            try:
                # Use cv2 for high-performance resizing (colleague's approach)
                # INTER_AREA is optimal for downsampling
                frame = cv2.resize(
                    frame, 
                    (self.target_size[0], self.target_size[1]), 
                    interpolation=cv2.INTER_AREA
                )
            except Exception as e:
                logger.warning(f"Resizing failed: {e}. Falling back to slicing.")
                h, w = self.target_size[1], self.target_size[0]
                frame = frame[:h, :w]

        # Explicitly clean up old frame reference to aid GC
        if self.latest_frame is not None:
            del self.latest_frame
            
        self.latest_frame = frame
        self.frame_event.set()
        
        # Periodic local GC to prevent internal heap bloat
        self._callback_count += 1
        if self._callback_count % 100 == 0:
            gc.collect()


class ROS2Camera(Camera):
    """
    Camera Implementation for ROS2 topics.
    Subscribes to `sensor_msgs/msg/Image` and provides standard LeRobot Camera methods.
    """
    def __init__(self, config: ROS2CameraConfig):
        super().__init__(config)
        self.config = config
        self._is_connected = False
        self._node = None
        self._executor = None
        self._thread = None
        
        # Internal rclpy context initialization
        if RCLPY_AVAILABLE:
            try:
                if not rclpy.ok():
                    rclpy.init()
            except Exception as e:
                logger.warning(f"rclpy.init() failed (might already be initialized): {e}")

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @staticmethod
    def find_cameras() -> List[Dict[str, Any]]:
        # Usually requires executing `ros2 topic list` or grabbing node graphs.
        # But ROS2 dynamically publishes, we'll return an empty generic list for now.
        return [{"type": "ros2", "description": "ROS2 Dynamic Topic Interface"}]

    def connect(self, warmup: bool = True) -> None:
        if not RCLPY_AVAILABLE:
            raise RuntimeError("ROS2 environment (rclpy) is not sourced or installed. Cannot connect ROS2Camera.")
        if self._is_connected:
            return

        import uuid
        unique_node_name = f"lerobot_ros2_camera_{uuid.uuid4().hex[:8]}"
        target_size = (self.config.width, self.config.height) if self.config.width and self.config.height else None
        self._node = ROS2CameraNode(node_name=unique_node_name, topic=self.config.topic, target_size=target_size)
        
        self._executor = MultiThreadedExecutor()
        self._executor.add_node(self._node)

        self._thread = threading.Thread(target=self._executor.spin, daemon=True)
        self._thread.start()
        
        self._is_connected = True
        logger.info(f"Connected to ROS2 camera on topic: {self.config.topic}")

        if warmup:
            # Wait until we get the first frame
            self.read()

    def read(self) -> np.ndarray:
        return self.async_read(timeout_ms=5000)

    def async_read(self, timeout_ms: float = 200) -> np.ndarray:
        if not self._is_connected or self._node is None:
            raise RuntimeError("ROS2 Camera is not connected.")

        # Wait for a new frame
        success = self._node.frame_event.wait(timeout=timeout_ms / 1000.0)
        if not success:
            raise TimeoutError(f"No new frame received on '{self.config.topic}' within {timeout_ms}ms")

        # Clear event to wait for the next frame
        self._node.frame_event.clear()
        
        frame = self._node.latest_frame
        
        if self.config.is_bgr and len(frame.shape) == 3 and frame.shape[2] == 3:
            # Depending on config, swap to RGB if LeRobot expects RGB natively (LeRobot usually expects RGB in dataset)
            # if the encoding was 'bgr8'. If already 'rgb8', do nothing.
            # Fast swap BGR to RGB
            frame = frame[..., ::-1]
            
        return frame

    def read_latest(self, max_age_ms: int = 500) -> np.ndarray:
        if not self._is_connected or self._node is None:
            raise RuntimeError("ROS2 Camera is not connected.")
        if self._node.latest_frame is None:
            raise RuntimeError("Camera connected but no frames received yet.")
            
        frame = self._node.latest_frame
        if self.config.is_bgr and len(frame.shape) == 3 and frame.shape[2] == 3:
            frame = frame[..., ::-1]
            
        return frame

    def disconnect(self) -> None:
        if not self._is_connected:
            return

        self._is_connected = False
        logger.info(f"Disconnecting ROS2 camera on topic: {self.config.topic}...")
        
        # Stop the executor first to prevent new callbacks
        try:
            if self._executor:
                self._executor.shutdown()
        except Exception as e:
            logger.warning(f"Error during executor shutdown: {e}")

        # Then destroy the node and its subscriptions
        try:
            if self._node:
                self._node.destroy_node()
        except Exception as e:
            logger.warning(f"Error during node destruction: {e}")

        if self._thread:
            self._thread.join(timeout=1.0)
            
        self._node = None
        self._executor = None
        self._thread = None
        logger.info(f"Disconnected ROS2 camera on topic: {self.config.topic}")
