import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from rclpy.qos import qos_profile_sensor_data, QoSProfile, ReliabilityPolicy, HistoryPolicy
import time
import numpy as np
from collections import deque
import cv2

class CameraDiagnosticsNode(Node):
    def __init__(self):
        super().__init__('camera_diagnostics_node')
        
        # Define the topics we want to monitor
        self.topics = [
            "/camera/right/color/image_resized/compressed",
            "/camera/left/color/image_resized/compressed",
            "/camera/top/color/image_raw/compressed"
        ]
        
        # Use sensor_data QoS profile (Best Effort, matching our robot_camera logic)
        qos = qos_profile_sensor_data
        
        # Metrics storage
        self.stats = {}
        for t in self.topics:
            self.stats[t] = {
                'count': 0,                     # Frames received in current window
                'bytes': 0,                     # Bytes received in current window
                'timestamps': deque(maxlen=60), # Last 60 frame arrival times
                'decode_times': deque(maxlen=10)# Sample decode times
            }
            
            # Create subscriber for each topic
            self.create_subscription(
                CompressedImage, 
                t, 
                lambda msg, topic=t: self.image_callback(msg, topic), 
                qos
            )
            
        self.get_logger().info("Camera Diagnostics Node Started. Waiting for frames...")
        
        # Setup a timer to print stats every 2 seconds
        self.window_size = 2.0
        self.timer = self.create_timer(self.window_size, self.print_stats)
        self.last_print_time = time.time()

    def image_callback(self, msg: CompressedImage, topic: str):
        now = time.time()
        msg_size = len(msg.data)
        
        # Update raw metrics
        self.stats[topic]['count'] += 1
        self.stats[topic]['bytes'] += msg_size
        self.stats[topic]['timestamps'].append(now)
        
        # Sample decode time (1 in 10 frames) to check if CPU is the bottleneck
        if self.stats[topic]['count'] % 10 == 0:
            decode_start = time.perf_counter()
            np_arr = np.frombuffer(msg.data, np.uint8)
            _ = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            decode_time = (time.perf_counter() - decode_start) * 1000 # ms
            self.stats[topic]['decode_times'].append(decode_time)

    def print_stats(self):
        now = time.time()
        elapsed = now - self.last_print_time
        self.last_print_time = now
        
        print("\n" + "="*80)
        print(f"⏱️  DIAGNOSTICS REPORT (Window: {elapsed:.2f}s) - {time.strftime('%H:%M:%S')}")
        print("="*80)
        
        total_bandwidth_mbps = 0
        all_alive = True
        
        for topic in self.topics:
            stat = self.stats[topic]
            count = stat['count']
            bytes_received = stat['bytes']
            
            # Calculate Frequency (Hz)
            hz = count / elapsed if elapsed > 0 else 0
            
            # Calculate Bandwidth (Mbps)
            mbps = (bytes_received * 8) / (1024 * 1024) / elapsed if elapsed > 0 else 0
            total_bandwidth_mbps += mbps
            
            # Calculate Jitter (Interval stability)
            jitter_ms = 0.0
            if len(stat['timestamps']) >= 2:
                intervals = np.diff(list(stat['timestamps']))
                jitter_ms = np.std(intervals) * 1000 # Standard deviation of intervals in ms
            
            # Calculate average decode time
            avg_decode_ms = np.mean(stat['decode_times']) if stat['decode_times'] else 0.0
            
            # Status Indicator
            status = "🟢 OK" if hz >= 28 else ("🟡 WARN" if hz >= 15 else "🔴 BAD")
            if hz == 0:
                all_alive = False
                status = "⚫ DEAD"
            
            # Print Topic Stats
            short_name = topic.split('/')[2].upper() # RIGHT, LEFT, TOP
            print(f"[{status}] {short_name:<5} | Freq: {hz:5.1f} Hz | Bandwidth: {mbps:5.2f} Mbps | Jitter: {jitter_ms:5.1f} ms | Decode: {avg_decode_ms:4.1f} ms")
            
            # Reset counters for next window
            stat['count'] = 0
            stat['bytes'] = 0
            
        print("-" * 80)
        print(f"🌐 Total Network Bandwidth: {total_bandwidth_mbps:.2f} Mbps")
        
        if not all_alive:
            print("⚠️  WARNING: One or more topics are NOT receiving data! Check cables and publishers.")
        elif total_bandwidth_mbps > 800:
            print("⚠️  WARNING: Network bandwidth is very high (>800Mbps), Gigabit Ethernet might be saturated.")
            
        print("="*80)

def main(args=None):
    rclpy.init(args=args)
    node = CameraDiagnosticsNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
