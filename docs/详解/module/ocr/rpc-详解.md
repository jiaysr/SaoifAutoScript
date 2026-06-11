# module/ocr/rpc.py 代码详解

## 1. 文件概述

`rpc.py` 实现了 OCR 服务的 RPC（远程过程调用）架构，支持将 OCR 推理任务分离到独立进程中执行。主要包含：

1. **OcrServer**：OCR 服务端，运行在独立进程中，提供 OCR 识别服务
2. **ModelProxy**：OCR 客户端代理，透明地将请求转发到远程服务
3. **服务管理函数**：启动、停止、检测 OCR 服务状态

**设计目的**：
- 解耦 OCR 推理与主程序
- 支持多进程并发调用
- 支持分布式部署（OCR 服务可在不同机器上）

---

## 2. 导入部分解释

```python
import atexit                    # 程序退出时的清理钩子
import multiprocessing           # 多进程支持
import pickle                    # 对象序列化（用于传输图像）
import socket                    # 网络套接字（用于端口检测）
import time                      # 时间操作（用于等待服务启动）
from typing import Any, Dict, List, Optional  # 类型注解

import numpy as np               # NumPy 数组操作
import zerorpc                   # ZeroRPC 框架（基于 ZeroMQ 的 RPC）

from module.exception import ScriptError  # 自定义异常
from module.logger import logger          # 日志记录器
from module.ocr.ppocr import TextSystem   # OCR 文本识别系统
```

**关键依赖**：
- `zerorpc`：基于 ZeroMQ 和 MessagePack 的 RPC 框架，高性能、易用
- `pickle`：Python 对象序列化，用于将图像数组转换为字节流传输

---

## 3. 类定义解释

### 3.1 模块级变量

```python
_OCR_SERVER_PROCESS: Optional[multiprocessing.Process] = None
```
保存 OCR 服务进程的引用，用于后续管理（停止、状态检查）。

---

## 4. 每个方法的逐行解释

### 4.1 `_normalize_address` 函数

```python
def _normalize_address(address: str) -> str:
    """规范化地址格式，确保包含 tcp:// 前缀"""
    if address.startswith("tcp://"):
        return address
    return f"tcp://{address}"
```

### 4.2 `_split_host_port` 函数

```python
def _split_host_port(address: str) -> tuple[str, int]:
    """
    从地址中提取主机和端口
    输入: "127.0.0.1:22268" 或 "tcp://127.0.0.1:22268"
    输出: ("127.0.0.1", 22268)
    """
    addr = address.replace("tcp://", "")  # 移除协议前缀
    if ":" not in addr:
        return addr, 22268  # 无端口时使用默认端口
    host, port = addr.rsplit(":", 1)  # 从右边分割，处理 IPv6 地址
    return host, int(port)
```

### 4.3 `_is_port_in_use` 函数

```python
def _is_port_in_use(host: str, port: int) -> bool:
    """
    检测端口是否被占用
    通过尝试建立 TCP 连接来判断
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(0.5)           # 设置超时 0.5 秒
        s.connect((host, port))     # 尝试连接
        s.shutdown(2)               # 关闭连接
        return True                 # 连接成功，端口被占用
    except Exception:
        return False                # 连接失败，端口未被占用
    finally:
        s.close()                   # 确保关闭套接字
```

### 4.4 `ensure_ocr_server_started` 函数

```python
def ensure_ocr_server_started() -> bool:
    """
    确保 OCR 服务已启动
    返回: True=服务可用, False=服务不可用
    """
    from module.server.setting import State  # 延迟导入，避免循环依赖

    deploy_config = State.deploy_config
    
    # 检查配置是否启用 OCR 服务
    if not deploy_config.StartOcrServer:
        return False

    # 获取端口配置
    if deploy_config.OcrServerPort:
        port = int(deploy_config.OcrServerPort)
    else:
        _, port = _split_host_port(str(deploy_config.OcrClientAddress))
    host = "0.0.0.0"  # 监听所有网络接口

    # 检查端口是否已被占用（服务可能已在运行）
    if _is_port_in_use("127.0.0.1", port):
        logger.info(f"OCR server already running on port {port}")
        return True

    # 检查进程是否已启动
    global _OCR_SERVER_PROCESS
    if _OCR_SERVER_PROCESS is not None and _OCR_SERVER_PROCESS.is_alive():
        logger.info("OCR server process already started")
        return True

    # 启动新的服务进程
    _OCR_SERVER_PROCESS = multiprocessing.Process(
        target=run_ocr_server,       # 目标函数
        args=(host, port),           # 参数
        name="ocr_server",           # 进程名
        daemon=True,                 # 守护进程（主进程退出时自动终止）
    )
    _OCR_SERVER_PROCESS.start()
    logger.info(f"Start OCR server on {host}:{port}")

    # 等待服务就绪（最多 5 秒）
    for _ in range(50):
        if _is_port_in_use("127.0.0.1", port):
            return True
        time.sleep(0.1)
    
    logger.error(f"OCR server is not ready on port {port}")
    return False
```

**设计说明**：
1. 首先检查配置是否启用服务
2. 然后检查端口是否已被占用（避免重复启动）
3. 最后启动进程并等待就绪

### 4.5 `shutdown_ocr_server` 函数

```python
def shutdown_ocr_server(timeout: float = 2.0) -> bool:
    """
    停止 OCR 服务
    参数: timeout - 等待进程退出的超时时间（秒）
    返回: True=成功停止, False=无需停止或失败
    """
    global _OCR_SERVER_PROCESS

    process = _OCR_SERVER_PROCESS
    if process is None:
        return False  # 无进程引用

    if not process.is_alive():
        _OCR_SERVER_PROCESS = None
        return False  # 进程已退出

    logger.info("Stopping OCR server process")
    try:
        process.terminate()              # 发送终止信号
        process.join(timeout=timeout)    # 等待进程退出
        if process.is_alive():
            # 超时未退出，强制杀死
            logger.warning("OCR server process did not exit in time, force killing")
            process.kill()
            process.join(timeout=1.0)
        logger.info("OCR server process stopped")
        return True
    except Exception as e:
        logger.exception(e)
        return False
    finally:
        _OCR_SERVER_PROCESS = None  # 清除引用
```

### 4.6 `run_ocr_server` 函数

```python
def run_ocr_server(host: str, port: int) -> None:
    """OCR 服务入口函数，运行在独立进程中"""
    server = zerorpc.Server(OcrServer())  # 创建 ZeroRPC 服务器
    server.bind(f"tcp://{host}:{port}")   # 绑定地址
    server.run()                          # 启动事件循环
```

### 4.7 `OcrServer` 类

```python
class OcrServer:
    """OCR 服务端实现"""

    def __init__(self) -> None:
        self.model = TextSystem()  # 初始化 OCR 模型

    def ping(self) -> bool:
        """心跳检测，用于验证连接"""
        return True

    @staticmethod
    def _rotate_vertical(image: np.ndarray) -> np.ndarray:
        """旋转竖向文本图像为横向"""
        height, width = image.shape[0:2]
        if height * 1.0 / width >= 1.5:  # 高宽比 >= 1.5 视为竖向
            return np.rot90(image)  # 逆时针旋转 90 度
        return image

    def ocr_single_line(self, image_bytes: bytes):
        """
        单行 OCR 识别
        参数: image_bytes - 序列化的图像字节
        返回: (识别文本, 置信度)
        """
        image = pickle.loads(image_bytes)  # 反序列化图像
        result, score = self.model.ocr_single_line(image)
        return result, float(score)

    def detect_and_ocr(
        self,
        image_bytes: bytes,
        drop_score: float = 0.5,
        unclip_ratio: Optional[float] = None,
        box_thresh: Optional[float] = None,
        vertical: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        检测并识别所有文本
        参数:
            image_bytes - 序列化的图像字节
            drop_score - 丢弃阈值
            unclip_ratio - 文本框扩展比例
            box_thresh - 文本框置信度阈值
            vertical - 是否为竖向文本
        返回: 结果字典列表
        """
        image = pickle.loads(image_bytes)
        
        if not vertical:
            # 横向文本：直接识别
            results = self.model.detect_and_ocr(
                image, drop_score=drop_score,
                unclip_ratio=unclip_ratio,
                box_thresh=box_thresh
            )
            return [
                {"box": r.box.tolist(), "ocr_text": r.ocr_text, "score": float(r.score)}
                for r in results
            ]

        # 竖向文本：临时替换识别器，添加旋转逻辑
        text_recognizer = self.model.text_recognizer

        def vertical_text_recognizer(img_crop_list):
            img_crop_list = [self._rotate_vertical(i) for i in img_crop_list]
            return text_recognizer(img_crop_list)

        self.model.text_recognizer = vertical_text_recognizer
        try:
            results = self.model.detect_and_ocr(
                image, drop_score=drop_score,
                unclip_ratio=unclip_ratio,
                box_thresh=box_thresh
            )
        finally:
            self.model.text_recognizer = text_recognizer  # 恢复原始识别器

        return [
            {"box": r.box.tolist(), "ocr_text": r.ocr_text, "score": float(r.score)}
            for r in results
        ]
```

**设计说明**：`detect_and_ocr` 方法支持竖向文本识别，通过临时替换 `text_recognizer` 实现，使用 `try/finally` 确保恢复原始状态。

### 4.8 `ModelProxy` 类

```python
class ModelProxy:
    """OCR 客户端代理，透明地转发请求到远程服务"""
    
    is_proxy = True  # 标识位，用于判断是否为代理

    def __init__(self, address: str) -> None:
        self.address = _normalize_address(address)  # 规范化地址
        self.client = zerorpc.Client()               # 创建 ZeroRPC 客户端
        try:
            self.client.connect(self.address)  # 连接服务端
            self.client.ping()                 # 验证连接
        except Exception as e:
            raise ScriptError(f"OCR server connection failed: {self.address}") from e

    def ocr_single_line(self, image: np.ndarray):
        """单行识别：序列化图像 -> 发送 -> 接收结果"""
        payload = pickle.dumps(image, protocol=4)  # 序列化（protocol=4 兼容性好）
        return self.client.ocr_single_line(payload)

    def detect_and_ocr(
        self,
        image: np.ndarray,
        drop_score: float = 0.5,
        unclip_ratio: Optional[float] = None,
        box_thresh: Optional[float] = None,
        vertical: bool = False,
    ):
        """检测并识别：序列化 -> 发送 -> 接收 -> 反序列化结果"""
        payload = pickle.dumps(image, protocol=4)
        results = self.client.detect_and_ocr(
            payload, drop_score, unclip_ratio, box_thresh, vertical
        )
        # 将字典转换为 BoxedResult 对象
        from ppocronnx.predict_system import BoxedResult
        return [
            BoxedResult(np.array(item["box"]), None, item["ocr_text"], item["score"])
            for item in results
        ]
```

**接口兼容性**：`ModelProxy` 的接口与 `TextSystem` 完全一致，可以无缝替换。

### 4.9 程序退出钩子

```python
atexit.register(shutdown_ocr_server)
```
注册程序退出时的清理函数，确保 OCR 服务进程被正确终止。

---

## 5. 核心算法流程图

### 5.1 RPC 调用流程

```
客户端 (ModelProxy)                    服务端 (OcrServer)
     │                                      │
     │  1. pickle.dumps(image)              │
     │     序列化图像                        │
     │                                      │
     │  2. client.ocr_single_line(payload)  │
     │ ─────────────────────────────────────>│
     │     ZeroRPC 传输                     │
     │                                      │  3. pickle.loads(payload)
     │                                      │     反序列化图像
     │                                      │
     │                                      │  4. model.ocr_single_line(image)
     │                                      │     执行 OCR 识别
     │                                      │
     │  5. return (result, score)           │
     │ <─────────────────────────────────────│
     │     ZeroRPC 传输                     │
     │                                      │
     │  6. 返回结果                          │
     ▼                                      ▼
```

### 5.2 服务启动流程

```
ensure_ocr_server_started()
    │
    ▼
┌─────────────────┐
│ 检查配置是否     │
│ 启用 OCR 服务   │──否──▶ 返回 False
└────────┬────────┘
         │是
         ▼
┌─────────────────┐
│ 检查端口是否     │
│ 已被占用         │──是──▶ 返回 True（服务已在运行）
└────────┬────────┘
         │否
         ▼
┌─────────────────┐
│ 检查进程是否     │
│ 已启动           │──是──▶ 返回 True
└────────┬────────┘
         │否
         ▼
┌─────────────────┐
│ 启动新进程       │
│ Process(daemon)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 等待服务就绪     │
│ (最多 5 秒)      │
└────────┬────────┘
         │
         ▼
    返回 True/False
```

### 5.3 竖向文本识别流程

```
输入: vertical=True
    │
    ▼
┌─────────────────┐
│ 保存原始         │
│ text_recognizer  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ 创建包装函数                         │
│ vertical_text_recognizer:           │
│   对每个裁剪区域旋转 90 度           │
│   然后调用原始识别器                 │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ 替换模型的       │
│ text_recognizer  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 执行 detect_and_ocr │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 恢复原始         │
│ text_recognizer  │  ← finally 块确保执行
└────────┬────────┘
         │
         ▼
    返回结果
```

---

## 6. 使用示例

### 6.1 自动启动服务

```python
from module.ocr.rpc import ensure_ocr_server_started
from module.ocr.models import get_ocr_model

# 确保服务已启动（如果配置启用）
if ensure_ocr_server_started():
    print("OCR 服务已就绪")

# 获取模型（自动判断使用本地模型或远程代理）
model = get_ocr_model("ch")

# 使用模型（透明调用，无需关心是本地还是远程）
text, score = model.ocr_single_line(image)
```

### 6.2 手动管理服务

```python
from module.ocr.rpc import run_ocr_server, shutdown_ocr_server

# 在独立进程中手动启动服务
import multiprocessing
process = multiprocessing.Process(
    target=run_ocr_server,
    args=("0.0.0.0", 22268)
)
process.start()

# 客户端连接
from module.ocr.rpc import ModelProxy
proxy = ModelProxy("127.0.0.1:22268")
result = proxy.ocr_single_line(image)

# 停止服务
shutdown_ocr_server()
```

### 6.3 竖向文本识别

```python
from module.ocr.models import get_ocr_model

model = get_ocr_model("ch")

# 识别竖向文本
results = model.detect_and_ocr(
    vertical_image,
    vertical=True  # 启用竖向文本处理
)

for r in results:
    print(f"文本: {r.ocr_text}")
```

---

## 7. 设计模式总结

| 设计模式 | 应用位置 | 说明 |
|---------|---------|------|
| **代理模式** | `ModelProxy` | 客户端代理，透明转发请求到远程服务 |
| **进程池** | `multiprocessing.Process` | 使用独立进程运行 OCR 服务 |
| **单例模式** | `_OCR_SERVER_PROCESS` | 全局只维护一个服务进程 |
| **装饰器模式** | `vertical_text_recognizer` | 包装原始识别器，添加旋转逻辑 |
| **资源管理** | `atexit.register` | 程序退出时自动清理资源 |

### 核心设计思想

1. **透明代理**：`ModelProxy` 与 `TextSystem` 接口一致，上层代码无需修改
2. **自动管理**：服务的启动、停止、健康检查自动化
3. **容错设计**：超时处理、强制杀死、异常捕获
4. **性能优化**：使用 `pickle` 序列化图像，`zerorpc` 高性能传输
5. **灵活性**：支持本地和远程两种部署模式
