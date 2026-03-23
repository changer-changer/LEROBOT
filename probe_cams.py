import cv2

print("Probing all /dev/video* nodes for color frames")
for i in [0, 2, 8, 16, 20]:
    device_path = f'/dev/video{i}'
    cap = cv2.VideoCapture(device_path, cv2.CAP_V4L2)
    
    if not cap.isOpened():
        continue
        
    print(f"\n--- Testing {device_path} ---")
    
    # Try 848x480
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 848)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    print(f"Requested 848x480, got {w}x{h}")
    
    ret, frame = cap.read()
    if ret:
        print(f"Success reading 848x480! Shape: {frame.shape}")
    else:
        print("Failed to read frame at 848x480")
        
    # Test with UYVY fourcc
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'UYVY'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 848)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    print(f"Requested 848x480 with UYVY, got {w}x{h}")
    ret, frame = cap.read()
    if ret:
        print(f"Success reading UYVY! Shape: {frame.shape}")
        
    cap.release()
