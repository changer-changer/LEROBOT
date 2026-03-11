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

            if title == "response_get_joint_state" and data.get("result") == "success":
                # Arm joints (usually 14)
                q_vals = data.get("q", [])
                dq_vals = data.get("dq", [])
                tau_vals = data.get("tau", [])
                with self._lock:
                    for i in range(min(len(q_vals), 14)):
                        self._q[i] = q_vals[i]
                        self._dq[i] = dq_vals[i]
                        self._tau[i] = tau_vals[i]
                    self._last_state_time = time.time()

            elif title == "response_get_limx_2fclaw_state" and data.get("result") == "success":
                # Gripper states
                left_opening = data.get("left_opening", 0)
                right_opening = data.get("right_opening", 0)
                with self._lock:
                    # Map to joints 14 and 15
                    self._q[14] = float(left_opening)
                    self._q[15] = float(right_opening)
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
            raise RuntimeError(f"Could not connect to Tron2 at {url}")
        
        self.is_running = True
        threading.Thread(target=self._poll_loop, daemon=True).start()
        
        for name, cam in self.cameras.items():
            cam.connect()
        
        self.logger.info(f"Tron2 Robot Connected (ACCID: {self.accid})")

    def disconnect(self):
        self.is_running = False
        if self.ws:
            self.ws.close()
        for cam in self.cameras.values():
            cam.disconnect()

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

        for name, cam in self.cameras.items():
            obs[name] = cam.async_read()
        return obs

    def send_action(self, action: dict[str, Any]) -> dict[str, Any]:
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
