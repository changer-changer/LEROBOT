### 详细规格

| 相机 | 话题路径 | 图像尺寸 | 编码格式 | 帧率 (FPS) |
| :--- | :--- | :--- | :--- | :--- |
| **左相机** | `/camera/left/color/image_rect_raw` | 848 × 480 | rgb8 | ~7.0 |
| **右相机** | `/camera/right/color/image_rect_raw` | 848 × 480 | rgb8 | ~10.7 |
| **顶部相机** | `/camera/top/color/image_raw` | 640 × 480 | rgb8 | ~9.2 |
| **顶部相机 compressed** | `/camera/top/color/image_raw/compressed` | 640 × 480 | jpeg compressed bgr8 | ~30 |
| **左相机 compressed** | `/camera/left/color/image_rect_raw/compressed` | 848 × 480 | jpeg compressed bgr8 | ~29.9 |
| **左相机 resized** | `/camera/left/color/image_resized/compressed` | 640 × 480 | jpeg compressed bgr8 | ~29.9 |
| **右相机 compressed** | `/camera/right/color/image_rect_raw/compressed` | 848 × 480 | jpeg compressed bgr8 | ~29.9 |
| **右相机 resized** | `/camera/right/color/image_resized/compressed` | 640 × 480 | jpeg compressed bgr8 | ~29.9 |

### 总结

| 相机 | 原始图像 | 压缩图像 | Resized 图像 |
| :--- | :--- | :--- | :--- |
| **左相机** | 848×480 @ ~7 FPS | 848×480 @ ~30 FPS | 640×480 @ ~30 FPS |
| **右相机** | 848×480 @ ~10.7 FPS | 848×480 @ ~30 FPS | 640×480 @ ~30 FPS |
| **顶部相机** | 640×480 @ ~9.2 FPS | 640×480 @ ~30 FPS | - |