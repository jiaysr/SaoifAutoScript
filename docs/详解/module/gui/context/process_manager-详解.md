# context/process_manager.py 代码详解

## 1. 文件概述

`context/process_manager.py` 是进程管理核心模块，负责管理多个脚本进程的生命周期，包括创建、启动、停止、重启等操作。该模块还管理进程间的通信（zerorpc）、日志收集和任务状态更新。

**核心职责：**
- 管理多个 ScriptProcess 进程实例
- 通过 zerorpc 实现进程间通信
- 收集和转发日志到 GUI
- 更新任务状态到 GUI
- 提供 GUI 配置参数的读写接口

---

## 2. 导入部分解释

```python
import socket                                    # 网络套接字，用于端口检测
import random                                    # 随机数生成，用于端口分配
import zerorpc                                   # ZeroRPC 框架，用于进程间 RPC 通信
import asyncio                                   # 异步 IO（当前未使用）
import cv2                                       # OpenCV，用于图像处理
import msgpack                                   # MessagePack 序列化（zerorpc 依赖）
import numpy as np                               # NumPy 数组库，用于图像数据处理
import io                                        # IO 流，用于内存缓冲区
import json                                      # JSON 序列化

from typing import Union, Any, Dict              # 类型注解
from cached_property import cached_property      # 缓存属性装饰器
from PySide6.QtCore import QObject, Slot, Signal, Property  # Qt 核心类
from PySide6.QtGui import QImage                 # Qt 图像类
from queue import Queue, Empty                   # 队列和空异常
from rich.console import Console                 # Rich 终端美化（当前未使用）
from multiprocessing.managers import SyncManager # 同步管理器，用于进程间共享队列
from threading import Thread                     # 线程类

from module.base.log_highlighter import highlight_text  # 日志高亮处理
from module.gui.process.script_process import ScriptProcess  # 脚本进程类
from module.config.config_menu import ConfigMenu        # 配置菜单
from module.config.config_modify import ConfigModify    # 配置修改器
from module.gui.context.add import Add                  # 脚本添加器
from module.logger import logger                        # 日志记录器
```

---

## 3. 函数定义解释

### 3.1 `is_port_in_use(ip, port)` 辅助函数

```python
def is_port_in_use(ip, port) -> bool:
    """
    检查端口是否被占用
    :param ip: IP 地址
    :param port: 端口号
    :return: True 表示端口被占用，False 表示可用
    """
    # 创建 TCP 套接字
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # 尝试连接指定端口
        s.connect((ip, port))
        # 关闭连接（2 = SHUT_RDWR，停止收发）
        s.shutdown(2)
        logger.info(f'Port {port} is in use')
        return True  # 连接成功说明端口被占用
    except:
        logger.info(f'Port {port} is not in use')
        return False  # 连接失败说明端口可用
```

---

## 4. 类定义解释

```python
class ProcessManager(QObject):
    """
    进程管理类
    管理多个脚本进程的生命周期和通信
    """
    # 信号定义
    log_signal = Signal(str, str)           # 日志信号：(config_name, log_content)
    sig_update_task = Signal(str, str)      # 更新任务信号：(config_name, task_json)
    sig_update_pending = Signal(str, str)   # 更新待处理任务信号
    sig_update_waiting = Signal(str, str)   # 更新等待任务信号
```

---

## 5. 每个方法的逐行解释

### 5.1 `__init__(self)` 构造函数

```python
def __init__(self) -> None:
    super().__init__()

    # 进程字典：{config_name: ScriptProcess}
    self.processes: Dict[str, ScriptProcess] = {}

    # 配置字典：{config_name: ConfigModify}
    self.configs: Dict[str, ConfigModify] = {}

    # 端口字典：{config_name: port_number}
    self.ports: Dict[str, int] = {}

    # zerorpc 客户端字典：{config_name: zerorpc.Client}
    self.clients = {}

    # 同步管理器（用于跨进程共享队列）
    self.manager = SyncManager()
    self.manager.start()  # 启动管理器进程

    # 日志队列字典：{config_name: Queue}
    self.log_queue: Dict[str, Queue] = {}

    # 日志线程字典：{config_name: Thread}
    self.log_thread: Dict[str, Thread] = {}

    # 任务更新队列和线程
    self.update_queue: Queue = None
    self.update_thread: Thread = None
    self.start_update_tasks()  # 启动更新线程
```

### 5.2 `create_all(self)` 方法

```python
@Slot()
def create_all(self) -> None:
    """创建所有的配置实例"""
    # 获取所有脚本配置文件
    configs = Add().all_script_files()

    # 为每个配置创建进程
    for config in configs:
        self.add(config)
```

### 5.3 `add(self, config)` 方法

```python
@Slot(str)
def add(self, config: str) -> None:
    """
    添加并启动一个脚本进程
    :param config: 配置名称，如 'oas1'
    """
    if config not in self.processes:
        # 1. 分配随机端口（40000-40200）
        port = 40000 + random.randint(0, 200)
        while is_port_in_use('127.0.0.1', port):
            port = 40000 + random.randint(0, 200)
        self.ports[config] = port

        # 2. 启动日志队列
        q = self.start_log(config)

        # 3. 创建进程实例
        self.processes[config] = ScriptProcess(config, port, q, update_queue=self.update_queue)

        # 4. 启动日志线程
        self.log_thread[config].start()

        # 5. 创建 zerorpc 客户端并连接
        logger.info(f'Create script {config} on port {port}')
        try:
            self.clients[config] = zerorpc.Client()
            self.clients[config].connect(f'tcp://127.0.0.1:{self.ports[config]}')
        except:
            logger.exception(f'Connect to script {config} error')
            raise

        # 6. 启动进程
        self.processes[config].start()
        logger.info(f'Add script {config}')
    else:
        logger.info(f'Script {config} is already running')
```

### 5.4 `remove(self, config)` 方法

```python
def remove(self, config: str) -> None:
    """移除一个脚本进程"""
    if config in self.processes:
        self.processes[config].stop()   # 停止进程
        del self.processes[config]      # 删除进程引用
        del self.ports[config]          # 删除端口记录
        del self.clients[config]        # 删除客户端引用
        logger.info(f'Remove script {config}')
    else:
        logger.info(f'Script {config} is not running')
```

### 5.5 `restart(self, config)` 方法

```python
@Slot(str)
def restart(self, config: str) -> None:
    """重启某个进程"""
    if config in self.processes:
        # 检查进程是否已死亡
        if not self.processes[config].is_alive():
            logger.info(f'{config} process is dead, restart it')

        # 强制终止进程
        self.processes[config].terminate()

        # 检查并修复资源
        if self.ports[config] is None:
            logger.error(f'{config} port is None')
        if self.clients[config] is None:
            logger.error(f'{config} client is None')
        if self.log_queue[config] is None:
            logger.info(f'{config} log_queue is None')
            self.log_queue[config] = self.manager.Queue()
        if self.log_thread[config] is None or not self.log_thread[config].is_alive():
            logger.info(f'{config} log_thread is None')

        # 重新创建进程
        self.processes[config] = ScriptProcess(
            config=config,
            port=self.ports[config],
            log_queue=self.log_queue[config],
            update_queue=self.update_queue
        )
        self.processes[config].start()
        logger.info(f'Restart script {config}')
    else:
        logger.info(f'Script {config} is not running')
```

### 5.6 `gui_mirror_image(self, config)` 方法

```python
@Slot(str, result="QImage")
def gui_mirror_image(self, config: str) -> QImage:
    """获取脚本的镜像截图"""
    if config in self.clients:
        logger.info(f'Gui get mirror image of {config}')

        # 1. 通过 zerorpc 获取图像流
        stream = self.clients[config].gui_mirror_image()

        # 2. 创建 BytesIO 缓冲区存储图像数据
        buffer = io.BytesIO()
        for data in stream:
            buffer.write(data)

        # 3. 将缓冲区数据解码为 OpenCV 图像
        buffer.seek(0)
        image_data = np.frombuffer(buffer.getvalue(), dtype=np.uint8)
        image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)

        # 4. 转换为 QImage 格式
        height, width, _ = image.shape
        image_qt = QImage(image.data, width, height, QImage.Format_RGB888).rgbSwapped()

        return image_qt
    else:
        logger.info(f'Script {config} is not running')
        return None
```

### 5.7 `check_script(self, config)` 方法

```python
def check_script(self, config: str):
    """
    检查脚本状态并返回可用的配置接口
    如果进程活着，返回 zerorpc 客户端
    如果进程死了，返回 ConfigModify 本地接口
    """
    if config in self.processes and self.processes[config].is_alive():
        # 进程活着，删除可能存在的本地配置
        if config in self.configs:
            del self.configs[config]
        return self.clients[config]  # 返回 RPC 客户端
    else:
        # 进程死了，使用本地配置修改器
        if config not in self.configs:
            self.configs[config] = ConfigModify(config)
        return self.configs[config]
```

### 5.8 `start_log(self, config_name)` 方法

```python
def start_log(self, config_name: str) -> Queue:
    """
    启动某个脚本实例的日志系统
    :param config_name: 配置名称
    :return: 日志队列
    """
    # 创建日志队列（如果不存在）
    if config_name not in self.log_queue:
        self.log_queue[config_name] = self.manager.Queue()

    # 创建日志线程（如果不存在）
    if config_name not in self.log_thread:
        self.log_thread[config_name] = Thread(
            target=self.log_thread_func,
            args=(config_name,),
            daemon=True
        )

    return self.log_queue[config_name]
```

### 5.9 `log_thread_func(self, config_name)` 方法

```python
def log_thread_func(self, config_name: str) -> None:
    """日志线程函数，从队列读取日志并发送信号"""
    q = self.log_queue.get(config_name)
    if q is None:
        logger.error(f'Process manager has no config {config_name}')
        return

    # 持续监听日志队列
    while self.log_thread[config_name].is_alive():
        try:
            log = q.get(timeout=1)  # 阻塞等待，超时1秒
            if log is None:
                continue

            # 高亮处理日志文本
            log = highlight_text(str(log))

            # 发送日志信号到 GUI
            self.log_signal.emit(config_name, log)

        except Empty:
            continue  # 超时，继续循环
        except Exception as e:
            logger.error(f'Log thread of {config_name} error: {e}')
            break
```

### 5.10 `start_update_tasks(self)` 方法

```python
def start_update_tasks(self) -> None:
    """启动任务更新线程"""
    if self.update_queue is not None and self.update_thread is not None:
        logger.error(f'Update thread has already started')

    # 创建更新队列和线程
    self.update_queue = self.manager.Queue()
    self.update_thread = Thread(target=self.update_thread_func, daemon=True)
    self.update_thread.start()
```

### 5.11 `update_thread_func(self)` 方法

```python
def update_thread_func(self) -> None:
    """任务更新线程函数"""
    logger.info(f'Update thread start')

    while self.update_thread.is_alive():
        try:
            update = self.update_queue.get(timeout=1)
            if update is None or not isinstance(update, dict):
                continue

            logger.info(f'Update thread get')

            # 解析并发送任务状态到 GUI
            for key, value in update.items():
                if "task" and "pending" and "waiting" in value:
                    self.sig_update_task.emit(key, json.dumps(value["task"]))
                    self.sig_update_pending.emit(key, json.dumps(value["pending"]))
                    self.sig_update_waiting.emit(key, json.dumps(value["waiting"]))

        except Empty:
            continue
        except Exception as e:
            logger.error(f'Update thread error: {e}')
            break
```

### 5.12 `start_script(self, config)` 方法

```python
@Slot(str)
def start_script(self, config: str) -> None:
    """启动脚本的主循环"""
    if not self.processes[config].is_alive():
        logger.info(f'Start script {config}')
        return self.restart(config)

    logger.info(f'Script {config} is already running')
    self.clients[config].start_loop()
```

### 5.13 `stop_script(self, config)` 方法

```python
@Slot(str)
def stop_script(self, config: str) -> None:
    """停止脚本的主循环"""
    if config in self.processes:
        logger.info(f'Stop script {config}')
        self.processes[config].stop()
    else:
        logger.info(f'Script {config} is not running')
```

---

## 6. 核心算法流程图

### 6.1 进程添加流程

```
add(config)
    │
    ▼
┌─────────────────────────────────────┐
│  config 是否已存在？                 │
│  ├─ 是 → 记录日志，返回             │
│  └─ 否 ↓                           │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  分配随机端口 (40000-40200)         │
│  while is_port_in_use(port)         │
│      port = 40000 + random(0,200)   │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  创建日志队列和线程                  │
│  start_log(config)                  │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  创建 ScriptProcess 实例            │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  创建 zerorpc 客户端并连接           │
│  client.connect(f'tcp://127.0.0.1:{port}')│
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  启动进程                           │
│  process.start()                    │
└─────────────────────────────────────┘
```

### 6.2 日志收集流程

```
┌─────────────────────────────────────┐
│  ScriptProcess (子进程)             │
│  └─ script 运行产生日志             │
│     └─ log_queue.put(log)           │
└─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│  log_queue (跨进程队列)             │
└─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│  log_thread_func (主进程线程)       │
│  ├─ log = queue.get(timeout=1)      │
│  ├─ log = highlight_text(log)       │
│  └─ log_signal.emit(config, log)    │
└─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│  QML GUI                            │
│  └─ 显示高亮日志                    │
└─────────────────────────────────────┘
```

### 6.3 任务状态更新流程

```
┌─────────────────────────────────────┐
│  ScriptProcess (子进程)             │
│  └─ update_tasks(data)              │
│     └─ update_queue.put(msg)        │
└─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│  update_queue (跨进程队列)          │
└─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│  update_thread_func (主进程线程)    │
│  ├─ update = queue.get(timeout=1)   │
│  ├─ 解析 task/pending/waiting       │
│  └─ 发送三个信号到 GUI              │
│     sig_update_task.emit(...)       │
│     sig_update_pending.emit(...)    │
│     sig_update_waiting.emit(...)    │
└─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│  QML GUI                            │
│  └─ 更新任务列表显示                │
└─────────────────────────────────────┘
```

---

## 7. 使用示例

### 7.1 在 Python 中使用

```python
from module.gui.context.process_manager import ProcessManager

pm = ProcessManager()

# 创建所有配置
pm.create_all()

# 添加单个配置
pm.add('oas1')

# 启动脚本
pm.start_script('oas1')

# 停止脚本
pm.stop_script('oas1')

# 重启脚本
pm.restart('oas1')

# 移除配置
pm.remove('oas1')
```

### 7.2 在 QML 中使用

```qml
import QtQuick 2.15

Button {
    onClicked: {
        // 启动脚本
        processManager.start_script("oas1")
    }
}

// 连接信号
Connections {
    target: processManager
    function onLogSignal(config, log) {
        console.log(config + ": " + log)
    }
    function onSigUpdateTask(config, task) {
        // 更新任务显示
    }
}
```

---

## 8. 设计模式总结

| 设计模式 | 应用位置 | 说明 |
|---------|---------|------|
| **管理者模式** | ProcessManager 类 | 统一管理多个进程的生命周期 |
| **观察者模式** | Signal 信号机制 | 通过信号通知 GUI 状态变化 |
| **代理模式** | check_script() | 根据进程状态选择本地或远程接口 |
| **生产者-消费者模式** | Queue 队列 | 子进程生产日志，主进程消费并显示 |
| **工厂模式** | add() | 创建并配置进程实例 |

**架构特点：**
- 采用多进程架构，每个脚本独立运行
- 使用 zerorpc 实现进程间 RPC 通信
- 通过 Queue 实现跨进程日志收集
- 使用 Signal/Slot 机制与 GUI 通信
- SyncManager 确保跨进程队列的线程安全
