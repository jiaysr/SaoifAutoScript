# process/script_process.py 代码详解

## 1. 文件概述

`process/script_process.py` 是脚本进程封装模块，定义了继承自 `multiprocessing.Process` 的脚本进程类。该类封装了脚本的启动、停止、日志收集和任务更新功能。

**核心职责：**
- 封装脚本进程的生命周期管理
- 初始化子进程的日志系统
- 启动 zerorpc 服务端
- 将任务状态更新推送到主进程

---

## 2. 导入部分解释

```python
from queue import Queue                    # 队列类，用于进程间通信
from multiprocessing import Process        # 多进程基类

from module.logger import logger           # 日志记录器
```

---

## 3. 类定义解释

```python
class ScriptProcess(Process):
    """
    脚本进程类
    继承 multiprocessing.Process，封装脚本运行逻辑
    """
    def __init__(self, config: str, port: int, log_queue: Queue, update_queue: Queue) -> None:
        """
        初始化脚本进程
        :param config: 配置名称，如 'oas1'
        :param port: zerorpc 服务端口
        :param log_queue: 日志队列，用于向主进程发送日志
        :param update_queue: 任务更新队列，用于向主进程发送任务状态
        """
        super().__init__()          # 调用 Process 构造函数
        self.config = config        # 保存配置名称
        self.port = port            # 保存端口号
        self.name = config          # 设置进程名称（便于调试）
        self.log_queue = log_queue  # 保存日志队列引用
        self.update_queue = update_queue  # 保存更新队列引用
        self.daemon = True          # 设置为守护进程
                                    # 主进程退出时，守护进程自动终止
```

---

## 4. 每个方法的逐行解释

### 4.1 `alive` 属性

```python
@property
def alive(self) -> bool:
    """
    检查进程是否存活
    :return: True 表示进程正在运行
    """
    # 调用 Process 的 is_alive() 方法
    # 这是一个便捷属性封装
    return self.is_alive()
```

### 4.2 `run(self)` 方法

```python
def run(self) -> None:
    """
    进程主函数（子进程入口点）
    当调用 process.start() 时，系统会自动调用此方法
    """
    # 1. 初始化子进程的日志系统
    self.start_log()

    try:
        # 2. 延迟导入 Script 类（避免在主进程中加载）
        from script import Script

        # 3. 创建 Script 实例
        script = Script(config_name=self.config)

        # 4. 设置任务更新回调函数
        # 当脚本内部任务状态变化时，会调用此函数
        script.gui_update_task = self.update_tasks

        # 5. 初始化 zerorpc 服务端
        script.init_server(self.port)

        # 6. 运行 zerorpc 服务端（阻塞）
        script.run_server()

    except:
        logger.exception(f'run script {self.config} error')
        raise
```

### 4.3 `stop(self)` 方法

```python
def stop(self) -> None:
    """
    停止进程
    注意：这是强制终止，不会等待子进程正常结束
    """
    # terminate() 发送 SIGTERM 信号强制终止进程
    self.terminate()

    # join() 等待进程结束，回收资源
    self.join()

    logger.info(f'stop script {self.config}')
```

### 4.4 `start_log(self)` 方法

```python
def start_log(self) -> None:
    """
    初始化子进程的日志系统
    在子进程中调用，配置独立的日志记录器
    """
    try:
        # 延迟导入日志配置函数
        from module.logger import set_file_logger, set_func_logger

        # 设置文件日志记录器（按配置名称命名日志文件）
        set_file_logger(name=self.config)

        # 设置函数日志记录器（将日志发送到队列）
        # log_queue.put 是一个可调用对象，日志系统会调用它
        set_func_logger(self.log_queue.put)

    except:
        logger.exception(f'start log error')
        raise
```

### 4.5 `update_tasks(self, data)` 方法

```python
def update_tasks(self, data) -> None:
    """
    更新任务状态
    此方法作为回调函数绑定到 Script 实例
    :param data: 任务状态数据（字典格式）
    """
    # 构建消息：{config_name: data}
    msg = {self.config: data}

    # 将消息放入更新队列
    # 主进程的 update_thread_func 会从队列读取并处理
    self.update_queue.put(msg)

    logger.info(f'Update tasks {self.config}')
```

---

## 5. 核心算法流程图

### 5.1 进程生命周期

```
┌─────────────────────────────────────┐
│  ScriptProcess.__init__()           │
│  ├─ 保存 config, port, queues       │
│  └─ 设置 daemon = True              │
└─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│  process.start()                    │
│  系统创建子进程，调用 run()          │
└─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│  run() [子进程执行]                  │
│  ├─ start_log() 初始化日志           │
│  ├─ 创建 Script 实例                │
│  ├─ 绑定 update_tasks 回调          │
│  ├─ init_server(port) 启动 RPC      │
│  └─ run_server() 阻塞运行           │
└─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│  运行中...                          │
│  ├─ 处理 RPC 请求                   │
│  ├─ 记录日志到 log_queue            │
│  └─ 推送任务更新到 update_queue     │
└─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│  process.stop() 或 process.terminate()│
│  ├─ terminate() 强制终止            │
│  └─ join() 回收资源                 │
└─────────────────────────────────────┘
```

### 5.2 日志收集流程

```
子进程 (ScriptProcess)
    │
    ├─ start_log()
    │   ├─ set_file_logger(config) → 写入日志文件
    │   └─ set_func_logger(log_queue.put) → 发送到队列
    │
    └─ script 运行
        └─ logger.info("...")
            └─ log_queue.put("...")
                │
                ▼
        log_queue (跨进程队列)
                │
                ▼
主进程 (ProcessManager)
    └─ log_thread_func()
        └─ queue.get() → highlight_text() → log_signal.emit()
```

### 5.3 任务更新流程

```
子进程 (ScriptProcess)
    │
    └─ script 任务状态变化
        └─ gui_update_task(data) 回调
            └─ update_tasks(data)
                └─ update_queue.put({config: data})
                    │
                    ▼
            update_queue (跨进程队列)
                    │
                    ▼
主进程 (ProcessManager)
    └─ update_thread_func()
        └─ queue.get() → 解析 → sig_update_task.emit()
```

---

## 6. 使用示例

### 6.1 在 ProcessManager 中使用

```python
from module.gui.process.script_process import ScriptProcess
from queue import Queue
from multiprocessing.managers import SyncManager

# 创建同步管理器
manager = SyncManager()
manager.start()

# 创建队列
log_queue = manager.Queue()
update_queue = manager.Queue()

# 创建进程
process = ScriptProcess(
    config='oas1',
    port=40000,
    log_queue=log_queue,
    update_queue=update_queue
)

# 启动进程
process.start()

# 检查状态
print(process.alive)  # True

# 停止进程
process.stop()
```

### 6.2 进程配置说明

```python
# daemon = True 的作用：
# 当主进程（GUI）退出时，所有守护子进程会自动终止
# 避免留下僵尸进程

# 端口分配：
# 每个脚本进程占用一个端口用于 zerorpc 通信
# 端口范围：40000-40200
```

---

## 7. 设计模式总结

| 设计模式 | 应用位置 | 说明 |
|---------|---------|------|
| **模板方法模式** | run() | 定义进程启动的标准流程 |
| **回调模式** | update_tasks | 作为回调函数绑定到 Script |
| **生产者模式** | log_queue/update_queue | 生产日志和更新数据供主进程消费 |
| **守护进程模式** | daemon = True | 主进程退出时自动清理子进程 |

**架构特点：**
- 每个脚本运行在独立的子进程中
- 通过 Queue 实现跨进程通信
- 使用 zerorpc 提供 RPC 服务
- 守护进程确保资源自动清理
- 回调机制实现事件通知
