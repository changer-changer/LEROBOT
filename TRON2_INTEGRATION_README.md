# Tron2 (逐动力) 机器人 LeRobot 整合说明文档

你好！本篇文档是为了方便人类开发者（您和您的团队）快速理解和接手这个项目中关于 **Tron2 机器人** 的集成工作。这份集成是基于最新版官方的 `lerobot-main` 代码库而完成的。

---

## 🚀 核心改动概览

为了让 LeRobot 框架能够无缝识别和调用 Tron2（逐动力）机器人的底层 SDK，我主要进行了以下模块的开发与修改：

### 1. 新增 Tron2 机器人专属驱动层

该部分的灵感参考了 `realman` 的集成方式，但严格遵守了新版 LeRobot `src/lerobot/robots/` 的代码结构规则。

- **参数模型配置**：创建了 [`src/lerobot/robots/tron2/tron2_config.py`](src/lerobot/robots/tron2/tron2_config.py)
  - 这里定义了 `Tron2RobotConfig`，继承自基础的 `RobotConfig`。
  - 主要字段包含了机器人的 IP（默认 `10.192.1.2`），并且使用 `draccus` 绑定了标识符 `"tron2"`。
  - 默认映射了 16 个关节的数据状态。

- **逻辑控制及数采实现**：创建了 [`src/lerobot/robots/tron2/tron2_robot.py`](src/lerobot/robots/tron2/tron2_robot.py)
  - 封装了底层 `limxsdk` 并继承自 `Robot` 基类。
  - 接驳了观测数据 `get_observation` 接口（16个关节的位置/速度/力矩以及任意摄像头同步读取）。
  - 接驳了动作下发 `send_action` 接口（实现了异步下发以及相对位置安全保护——若配置了最大移动限幅 `max_relative_target` 则自动触发截断）。

### 2. 在 LeRobot 核心工厂方法中注册 Tron2

为了让命令行工具（CLI）直接通过 `--robot.type=tron2` 调用，我们修改并暴露了两个文件：

- 增加了引入：修改 `src/lerobot/robots/__init__.py` 将 `Tron2Robot` 添加到导出中。
- 添加了分支实例化：修改 `src/lerobot/robots/utils.py`，让 `make_robot_from_config()` 方法在识别到 `config.type == "tron2"` 时，正确返回我们编写的实例。

### 3. 一键安装 SDK 辅助脚本

在 `scripts/install_limxsdk.sh` 中为您编写了自动化安装 SDK 的脚本。如果换了新的环境，运行这个 bash 脚本就能快速自动拉取、安装对应的 Python SDK 工具包。

### 4. 单发测试脚本

根目下的 `test_tron2.py` 是用来离线跑通整个工作流测试用的。

---

## 🛠️ 如何使用和连接？

由于现在你直接位于已经集成好 Tron2 的代码仓库 (`lerobot(tron2)`) 下，用法已经和原本官方的任何机器人一致：

### 第一步：开启数据录制

连接到机器人的 WiFi 后（确保电脑可访问 10.192.1.2 ），执行：

```bash
python3 -m lerobot.scripts.lerobot_record \
    --robot.type=tron2 \
    --robot.robot_ip=10.192.1.2 \
    --fps=30 \
    --repo_id=local/tron2_dataset
```

### 第二步：真实遥操作测试

验证命令映射能否走通：

```bash
python3 -m lerobot.scripts.lerobot_teleoperate \
    --robot.type=tron2 \
    --robot.robot_ip=10.192.1.2
```

---

## ⚠️ 注意事项与局限

由于我们在代码内写入了 `limxsdk` 官方文档中要求的默认控制刚度（Kp, Kd）：

```python
Kp: [21.0, 21.0, 15.0, 15.0, 10.0, ... ]
Kd: [0.6, 0.6, 0.75, 0.75, 0.5, ... ]
```

若您后续在真机上运动时发现刚度过硬或过软，您可以随时前往 `src/lerobot/robots/tron2/tron2_robot.py` 这个文件的 `send_action` 函数下方的 Kp 和 Kd 参数进行微调！

祝您研发顺利！🚀
