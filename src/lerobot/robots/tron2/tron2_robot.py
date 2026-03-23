import logging
import time
import json
import uuid
import threading
import numpy as np
import websocket
from typing import Any, Dict, List

from lerobot.robots.robot import Robot
from .tron2_config import Tron2RobotConfig
from lerobot.cameras.utils import make_cameras_from_configs
from lerobot.tactile.utils import make_tactile_sensors_from_configs

class Tron2Robot(Robot):
    config_class = Tron2RobotConfig
    name = "tron2"

    def __init__(self, config: Tron2RobotConfig):
        super().__init__(config)
        self.config = config
        self.logger = logging.getLogger(self.name)

        self.ws = None
        self.accid = None
        self.is_running = False
        
        # Latest state buffer
        # 14 arm joints + 2 grippers = 16
        self._q = np.zeros(16, dtype=np.float32)
        self._dq = np.zeros(16, dtype=np.float32)
        self._tau = np.zeros(16, dtype=np.float32)
        
        self._last_state_time = 0
        self._lock = threading.Lock()

        # Initialize cameras
        self.cameras = make_cameras_from_configs(config.cameras)

        # Initialize tactile sensors
        self.tactile_sensors = make_tactile_sensors_from_configs(getattr(config, "tactile_sensors", {}))

    @property
    def observation_features(self) -> dict:
        features: Dict[str, Any] = {}
        # 14 arms + 2 grippers (joint_14: left, joint_15: right)
        for i in range(16):
            features[f"joint_{i}_pos"] = float
            features[f"joint_{i}_vel"] = float
            features[f"joint_{i}_tau"] = float
        for cam_name, cam_cfg in self.config.cameras.items():
            features[cam_name] = (cam_cfg.height, cam_cfg.width, 3)
        for tac_name, tac_cfg in getattr(self.config, "tactile_sensors", {}).items():
            features[tac_name] = tac_cfg.expected_shape
        return features

    @property
    def action_features(self) -> dict:
        features = {}
        for i in range(16):
            features[f"action.joint_{i}_pos"] = float
        return features

    @property
    def is_connected(self) -> bool:
        return self.ws is not None and self.ws.sock and self.ws.sock.connected

    def _send_request(self, title: str, data: dict = None):
        if not self.is_connected:
            return
        
        message = {
            "accid": self.accid,
            "title": title,
            "timestamp": int(time.time() * 1000),
            "guid": str(uuid.uuid4()),
            "data": data or {}
        }
        try:
            self.ws.send(json.dumps(message))
        except Exception as e:
            self.logger.error(f"WS Send Error: {e}")

    def on_message(self, ws, message):
        try:
            msg = json.loads(message)
            title = msg.get("title", "")
            data = msg.get("data", {})
            
            if self.accid is None and "accid" in msg:
                self.accid = msg["accid"]
            
            if title == "notify_robot_info":
                # Regular update from robot, useful for accid and health check
                pass

            if title == "response_get_joint_state" and data.get("result") == "success":
                # Arm joints (14 for DACH_TRON2A)
                q_vals = data.get("q", [])
                dq_vals = data.get("dq", [])
                tau_vals = data.get("tau", [])
                with self._lock:
                    num = min(len(q_vals), 14)
                    self._q[:num] = q_vals[:num]
                    self._dq[:num] = dq_vals[:num]
                    self._tau[:num] = tau_vals[:num]
                    self._last_state_time = time.time()

            elif title == "response_get_limx_2fclaw_state" and data.get("result") == "success":
                # Gripper states (开口度 0-100)
                # Map to joints 14 (left) and 15 (right)
                with self._lock:
                    if "left_opening" in data:
                        self._q[14] = float(data["left_opening"])
                    if "right_opening" in data:
                        self._q[15] = float(data["right_opening"])
                    self._last_state_time = time.time()
        except Exception as e:
            self.logger.error(f"WS Parsing Error: {e}")

    def _poll_loop(self):
        """Background loop to fetch status at 50Hz"""
        while self.is_running:
            if self.is_connected:
                self._send_request("request_get_joint_state")
                self._send_request("request_get_limx_2fclaw_state")
            time.sleep(0.02) # 50Hz

    def connect(self):
        # Use robot_ip from config
        url = f"ws://{self.config.robot_ip}:5000"
        self.logger.info(f"Connecting to {url}...")
        
        def _on_message(ws, msg):
            self.on_message(ws, msg)
            
        def _on_error(ws, e):
            self.logger.error(f"WS Error: {e}")
            
        def _on_close(ws, close_status_code, close_msg):
            self.logger.info(f"WS Closed: {close_status_code} - {close_msg}")

        self.ws = websocket.WebSocketApp(
            url,
            on_message=_on_message,
            on_error=_on_error,
            on_close=_on_close
        )
        
        # Buffer sizes to handle high freq data
        self.ws.sock_opt = [
            ("socket", "SO_SNDBUF", 2 * 1024 * 1024),
            ("socket", "SO_RCVBUF", 2 * 1024 * 1024)
        ]

        # Start WS thread
        threading.Thread(target=self.ws.run_forever, daemon=True).start()
        
        # Wait for connection and accid (serial number)
        timeout = 5.0
        start_t = time.time()
        while (not self.is_connected or self.accid is None) and (time.time() - start_t < timeout):
            time.sleep(0.1)
        
        if not self.is_connected:
            print(f"FAILED to connect to Tron2 at {url}")
            raise RuntimeError(f"Could not connect to Tron2 at {url}")
        
        print(f"Tron2 WebSocket Link established! ACCID: {self.accid}")
        self.is_running = True
        threading.Thread(target=self._poll_loop, daemon=True).start()
        
        for name, cam in self.cameras.items():
            cam_src = getattr(cam.config, "topic", getattr(cam.config, "index_or_path", "unknown"))
            print(f"Starting Camera: {name} ({cam_src})...")
            cam.connect()
            print(f"Camera {name} is READY.")
        
        for name, tac in self.tactile_sensors.items():
            print(f"Synchronizing Tac3D Sensor: {name} (Port {tac.config.udp_port})...")
            tac.connect()
            print(f"Tac3D Sensor {name} is READY.")
        
        print("\n" + "="*40)
        print("  SUCCESS: TRON2 ROBOT & ALL SENSORS CONNECTED")
        print("="*40 + "\n")

    def disconnect(self):
        print("Safely disconnecting and releasing robot resources...")
        self.is_running = False
        if self.ws:
            self.ws.close()
        for cam in self.cameras.values():
            if getattr(cam, "is_connected", False):
                cam.disconnect()
        for tac in self.tactile_sensors.values():
            if getattr(tac, "is_connected", False):
                tac.disconnect()
        print("All robot resources released.")

    def calibrate(self):
        pass

    def configure(self):
        pass

    @property
    def is_calibrated(self) -> bool:
        return True

    def get_observation(self) -> dict:
        obs: Dict[str, Any] = {}
        with self._lock:
            q = self._q.copy()
            dq = self._dq.copy()
            tau = self._tau.copy()

        for i in range(16):
            obs[f"joint_{i}_pos"] = float(q[i])
            obs[f"joint_{i}_vel"] = float(dq[i])
            obs[f"joint_{i}_tau"] = float(tau[i])

        # Always ensure all camera and tactile keys exist to avoid downstream crashes
        for name, cam in self.cameras.items():
            try:
                # Use async_read with a reasonable timeout to prevent blocking the main loop indefinitely
                cam_data = cam.async_read(timeout_ms=1000)
            except Exception as e:
                self.logger.error(f"Failed to read image from camera '{name}': {e}")
                raise
            
            if cam_data is None:
                raise RuntimeError(f"Camera '{name}' returned None image in get_observation().")
                
            obs[name] = cam_data

        for name, tac in self.tactile_sensors.items():
            try:
                # Use blocking read, exactly like Realman/Tac3D integration
                tac_data = tac.read()
            except Exception as e:
                self.logger.error(f"Failed to read data from tactile sensor '{name}': {e}")
                raise
                
            if tac_data is None:
                raise RuntimeError(f"Tactile sensor '{name}' returned None data in get_observation().")
                
            obs[name] = tac_data
            
        return obs

    def get_observation_latest(self) -> dict:
        """Non-blocking observation fetch for high-speed manual recording loops."""
        obs: Dict[str, Any] = {}
        with self._lock:
            q = self._q.copy()
            dq = self._dq.copy()
            tau = self._tau.copy()

        for i in range(16):
            obs[f"joint_{i}_pos"] = float(q[i])
            obs[f"joint_{i}_vel"] = float(dq[i])
            obs[f"joint_{i}_tau"] = float(tau[i])

        # Always ensure all camera and tactile keys exist to avoid downstream crashes
        for name, cam in self.cameras.items():
            try:
                # Use async_read with a reasonable timeout to prevent blocking the main loop indefinitely
                cam_data = cam.async_read(timeout_ms=1000)
            except Exception as e:
                self.logger.error(f"Failed to read image from camera '{name}': {e}")
                raise

            if cam_data is None:
                raise RuntimeError(f"Camera '{name}' returned None image in get_observation_latest().")
                
            obs[name] = cam_data

        for name, tac in self.tactile_sensors.items():
            try:
                # Use blocking read, exactly like Realman/Tac3D integration
                tac_data = tac.read()
            except Exception as e:
                self.logger.error(f"Failed to read data from tactile sensor '{name}': {e}")
                raise
                
            if tac_data is None:
                raise RuntimeError(f"Tactile sensor '{name}' returned None data in get_observation_latest().")
                
            obs[name] = tac_data
            
        return obs

    def send_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """Send action using ServoJ (real-time servo control) - Legacy method"""
        targets = np.zeros(16, dtype=np.float32)
        has_action = False
        
        with self._lock:
            current_q = self._q.copy()

        for i in range(16):
            key_long = f"action.joint_{i}_pos"
            key_short = f"joint_{i}_pos"
            if key_short in action:
                targets[i] = action[key_short]
                has_action = True
            elif key_long in action:
                targets[i] = action[key_long]
                has_action = True
            else:
                targets[i] = current_q[i]

        if not has_action:
            return action

        # 1. Send Arm Action (request_servoj for joints 0-13)
        arm_q = targets[0:14].tolist()
        servoj_data = {
            "q": arm_q,
            "v": [0.0]*14,
            "kp": [150.0]*14,
            "kd": [10.0]*14,
            "tau": [0.0]*14,
            "mode": [0]*14,
            "na": 0
        }
        self._send_request("request_servoj", servoj_data)

        # 2. Send Gripper Action (joint 14 -> left, 15 -> right)
        # Note: input represents opening (0-100)
        gripper_data = {
            "left_opening": int(np.clip(targets[14], 0, 100)),
            "left_speed": 50,
            "left_force": 50,
            "right_opening": int(np.clip(targets[15], 0, 100)),
            "right_speed": 50,
            "right_force": 50
        }
        self._send_request("request_set_limx_2fclaw_cmd", gripper_data)
        
        return action

    def send_action_movej(self, action: dict[str, Any], move_time: float = 0.1) -> dict[str, Any]:
        """
        Send action using MoveJ (joint space interpolation) - Safer method
        
        MoveJ 是关节空间插值运动，机器人会自动规划平滑轨迹，
        不会出现 ServoJ 的振荡问题。
        
        Args:
            action: 动作字典，包含 16 个关节目标位置
            move_time: 运动时间（秒），默认 0.1s
                      建议根据动作幅度调整：
                      - 小幅动作：0.05-0.1s
                      - 中幅动作：0.1-0.3s  
                      - 大幅动作：0.3-0.5s
        """
        targets = np.zeros(16, dtype=np.float32)
        has_action = False
        
        with self._lock:
            current_q = self._q.copy()

        for i in range(16):
            key_long = f"action.joint_{i}_pos"
            key_short = f"joint_{i}_pos"
            if key_short in action:
                targets[i] = action[key_short]
                has_action = True
            elif key_long in action:
                targets[i] = action[key_long]
                has_action = True
            else:
                targets[i] = current_q[i]

        if not has_action:
            return action

        # 1. Send Arm Action using MoveJ (joints 0-13)
        # SDK 文档: time 单位是秒（示例: {"time": 5} 表示 5 秒）
        arm_q = targets[0:14].tolist()
        movej_data = {
            "time": float(move_time),  # 秒
            "joint": arm_q
        }
        self._send_request("request_movej", movej_data)

        # 2. Send Gripper Action (joint 14 -> left, 15 -> right)
        gripper_data = {
            "left_opening": int(np.clip(targets[14], 0, 100)),
            "left_speed": 50,
            "left_force": 50,
            "right_opening": int(np.clip(targets[15], 0, 100)),
            "right_speed": 50,
            "right_force": 50
        }
        self._send_request("request_set_limx_2fclaw_cmd", gripper_data)
        
        return action
