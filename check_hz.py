import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
import time

class HzChecker(Node):
    def __init__(self):
        super().__init__('hz_checker')
        self.topics = [
            "/camera/right/color/image_resized/compressed",
            "/camera/left/color/image_resized/compressed",
            "/camera/top/color/image_raw/compressed"
        ]
        self.counts = {t: 0 for t in self.topics}
        self.start_time = time.time()
        
        self.subs = []
        for t in self.topics:
            sub = self.create_subscription(CompressedImage, t, lambda msg, topic=t: self.callback(topic), 10)
            self.subs.append(sub)
            
        self.timer = self.create_timer(2.0, self.timer_callback)

    def callback(self, topic):
        self.counts[topic] += 1

    def timer_callback(self):
        elapsed = time.time() - self.start_time
        print(f"\n--- Over {elapsed:.2f} seconds ---")
        for t in self.topics:
            hz = self.counts[t] / elapsed
            print(f"Topic {t}: {hz:.2f} Hz")
        
        # Reset
        self.counts = {t: 0 for t in self.topics}
        self.start_time = time.time()

def main():
    rclpy.init()
    node = HzChecker()
    print("Listening for camera topics... (Press Ctrl+C to stop)")
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
