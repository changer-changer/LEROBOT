import sys
import logging
import time
from pathlib import Path

# Add lerobot straight to path just in case
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from lerobot.robots.utils import make_robot_from_config
from lerobot.robots.tron2.tron2_config import Tron2RobotConfig

logging.basicConfig(level=logging.INFO)

def main():
    print("Testing Tron2 JSON API Integration...")
    # Using real IP as default for testing on robot
    robot_ip = "10.192.1.2"
    if len(sys.argv) > 1:
        robot_ip = sys.argv[1]

    try:
        config = Tron2RobotConfig(robot_ip=robot_ip)
        print(f"Config: {config}")

        print("Instantiating robot...")
        robot = make_robot_from_config(config)
        
        print("Connecting to robot (5s timeout)...")
        robot.connect()
        
        print("Connected! Fetching observations for 3 seconds...")
        for _ in range(15):
            obs = robot.get_observation()
            # Just print a slice of joints to keep it readable
            q = [f"{obs[f'joint_{i}_pos']:.3f}" for i in range(16)]
            print(f"Joints State: {q}")
            time.sleep(0.2)
            
        print("Disconnecting...")
        robot.disconnect()
        print("Test Complete.")
        
    except Exception as e:
        print(f"Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
