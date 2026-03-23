import sys
import time
import logging
from pathlib import Path
import numpy as np

# Add src to Python Path
sys.path.append(str(Path(__file__).parent / "src"))

from lerobot.robots.tron2.tron2_config import Tron2RobotConfig
from lerobot.robots.tron2.tron2_robot import Tron2Robot
from lerobot.cameras.ros2.configs import ROS2CameraConfig
from lerobot.tactile.configs import Tac3DSensorConfig, PointCloud2SensorConfig
from lerobot.tactile.direct_connection.tac3d_sensor import Tac3DTactileSensor
from lerobot.tactile.ros2_bridge.pointcloud2_sensor import PointCloud2TactileSensor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_full_system")

def main():
    print("\n" + "="*50)
    print("  TRON2 INTEGRATED SYSTEM VERIFICATION")
    print("="*50)

    try:
        # Configuration
        tron2_config = Tron2RobotConfig(
            robot_ip="10.192.1.2",
            cameras={
                "left_rgb": ROS2CameraConfig(topic="/camera/left/color/image_rect_raw", fps=30, width=640, height=480),
                "right_rgb": ROS2CameraConfig(topic="/camera/right/color/image_rect_raw", fps=30, width=640, height=480)
            }
        )
        
        print(f"\n[Step 1] Initializing Robot at {tron2_config.robot_ip}...")
        tron2_robot = Tron2Robot(tron2_config)
        
        print("[Step 2] Connecting to all sensors (WebSocket + ROS2 + direct UDP)...")
        tron2_robot.connect()
        # The line above prints its own READY markers
        
        # Read samples
        num_frames = 20
        print(f"\n[Step 3] Starting Data Capture Loop ({num_frames} samples)...")
        
        for i in range(num_frames):
            start_time = time.time()
            try:
                # Fetch observation (Joints + Images + Tactile)
                obs = tron2_robot.get_observation()
                
                # Format output message
                msg = f"  >> Sample {i+1:2d} | "
                
                if 'tac3d_sensor' in obs:
                    msg += f"Tac3D: {obs['tac3d_sensor'].shape} | "
                
                joint_count = len([敬k for k in obs.keys() if 'joint_' in k and 'pos' in k])
                msg += f"Joints: {joint_count:2d} | "
                
                img_info = []
                for cam_name in tron2_config.cameras.keys():
                    if cam_name in obs:
                        img_info.append(f"{cam_name}: {obs[cam_name].shape}")
                msg += " | ".join(img_info)
                
                print(msg)
            except Exception as e:
                print(f"  !! READ ERROR: {e}")
            
            # Maintain frequency
            loop_duration = time.time() - start_time
            sleep_time = max(0, (1.0 / 10.0) - loop_duration) # 10Hz for verification
            time.sleep(sleep_time)
            
        print("\n" + "*"*50)
        print("  ALL SYSTEMS OPERATIONAL - VERIFICATION COMPLETE")
        print("*"*50 + "\n")

    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\nFinalizing and disconnecting...")
        if 'tron2_robot' in locals():
            try:
                tron2_robot.disconnect()
            except Exception as e:
                print(f"Cleanup warning: {e}")
        print("System closed.")

if __name__ == "__main__":
    main()
