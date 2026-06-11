# module/server/script_process.py 详解

## 1. 文件概述

`script_process.py` 是脚本进程管理模块，负责：
- 管理脚本子进程的生命周期
- 处理进程间通信（日志和状态）
- 提供进程启动、停止和状态广播功能
- 支持多进程并发执行脚本

## 2. 导入部分解释

```python
import sys, os                              # 系统和操作系统模块
import signal                               # 信号处理
import multiprocessing                      # 多进程支持
from asyncio import QueueEmpty, CancelledError, sleep  # 异步编程
from enum import Enum                        # 枚举类
from module.logger import logger             # 日志模块
from module.server.config_manager import ConfigManager  # 配置管理器
from module.server.script_websocket import ScriptWSManager  # WebSocket 管理器
```

## 3. 类定义解释

### ScriptState 枚举类（第16-20行）
```python
class ScriptState(int, Enum):
    INACTIVE = 0    # 未激活
    RUNNING = 1     # 运行中
    WARNING = 2     # 警告
    UPDATING = 3    # 更新中
```

### ScriptProcess 类（第23-120行）
继承自 `ScriptWSManager`，管理单个脚本进程。

## 4. 每个方法的逐行解释

### ScriptProcess.__init__ 方法（第25-33行）
```python
def __init__(self, config_name: str) -> None:
    super().__init__()  # 调用父类构造函数
    if config_name not in ConfigManager.all_script_files():  # 检查配置文件是否存在
        raise FileNotFoundError(f'{config_name}.json not found')
    self.config_name = config_name  # 配置名称
    self.log_pipe_out, self.log_pipe_in = multiprocessing.Pipe(False)  # 日志管道
    self.state_queue = multiprocessing.Queue()  # 状态队列
    self.state: ScriptState = ScriptState.INACTIVE  # 初始状态
    self._process = None  # 子进程引用
```

### ScriptProcess.start 方法（第35-48行）
```python
async def start(self):
    self.state = ScriptState.RUNNING  # 设置状态为运行中
    await self.broadcast_state({"state": self.state})  # 广播状态
    if self._process:  # 如果进程已存在
        logger.warning(f'Script {self.config_name} is initialized')
    if self._process and self._process.is_alive():  # 如果进程正在运行
        logger.warning(f'Script {self.config_name} is already running and first stop it')
        self.stop()  # 先停止
    self._process = multiprocessing.Process(target=func,  # 创建子进程
                                            args=(self.config_name, self.state_queue, self.log_pipe_in,),
                                            name=self.config_name,
                                            daemon=True  # 守护进程
                                            )
    self._process.start()  # 启动子进程
```

### ScriptProcess.stop 方法（第50-64行）
```python
async def stop(self):
    self.state = ScriptState.INACTIVE  # 设置状态为未激活
    await self.broadcast_state({"state": self.state})  # 广播状态
    if self._process is None:  # 如果进程不存在
        logger.warning(f'Script {self.config_name} process is removed')
        return
    if not self._process.is_alive():  # 如果进程已停止
        logger.warning(f'Script {self.config_name} is not running')
        return
    self._process.terminate()  # 终止进程
    self._process.join(timeout=0.7)  # 等待进程结束
    if self._process.is_alive():  # 如果进程仍在运行
        logger.error(f'Script {self.config_name} subprocess terminate failed')
        self._process.kill()  # 强制杀死进程
    self._process = None  # 清除进程引用
```

### ScriptProcess.coroutine_broadcast_state 方法（第66-93行）
```python
async def coroutine_broadcast_state(self):
    try:
        while 1:  # 无限循环
            if self.state == ScriptState.INACTIVE:  # 如果未激活
                await sleep(1)  # 等待1秒
                continue
            await sleep(0.1)  # 等待0.1秒
            try:
                if self.state_queue.empty():  # 如果队列为空
                    await sleep(1)  # 等待1秒
                    continue
                data = self.state_queue.get_nowait()  # 非阻塞获取数据
                if not data:  # 如果数据为空
                    await sleep(0.5)
                    continue
                if 'state' in data and data['state'] == ScriptState.WARNING:  # 如果是警告状态
                    self.state = ScriptState.WARNING  # 更新状态
                await self.broadcast_state(data)  # 广播状态
            except QueueEmpty as e:
                logger.warning(f'QueueEmpty: {e}')
                await sleep(0.5)
                continue
            except Exception as e:
                logger.error(f'Error: {e}')
                continue
    except CancelledError as e:
        logger.warning(f'{self.config_name} state coroutine is cancelled')
        return
```

### ScriptProcess.coroutine_broadcast_log 方法（第95-120行）
```python
async def coroutine_broadcast_log(self):
    try:
        while 1:  # 无限循环
            if self.state == ScriptState.INACTIVE:  # 如果未激活
                await sleep(1)  # 等待1秒
                continue
            await sleep(0.05)  # 等待0.05秒
            try:
                if not self.log_pipe_out.poll():  # 如果管道没有数据
                    await sleep(0.3)  # 等待0.3秒
                    continue
                log = self.log_pipe_out.recv()  # 接收日志数据
                if not log:  # 如果日志为空
                    await sleep(0.5)
                    continue
                await self.broadcast_log(log)  # 广播日志
            except EOFError as e:
                await sleep(0.5)
                logger.warning(f'EOFError: {e}')
                continue
            except Exception as e:
                logger.error(f'Log Error: {e}')
                continue
    except CancelledError as e:
        logger.warning(f'{self.config_name} log coroutine is cancelled')
        return
```

### func 函数（第123-162行）
```python
def func(config: str, state_queue: multiprocessing.Queue, log_pipe_in) -> None:
    def signal_handler(signum, frame):
        logger.info(f'Script {config} received signal {signum}, exiting gracefully')
        log_pipe_in.close()  # 关闭日志管道
        state_queue.close()  # 关闭状态队列
        sys.exit(0)  # 退出

    signal.signal(signal.SIGTERM, signal_handler)  # 注册 SIGTERM 信号处理
    signal.signal(signal.SIGINT, signal_handler)   # 注册 SIGINT 信号处理

    def start_log() -> None:
        try:
            from module.logger import set_file_logger, set_func_logger
            set_file_logger(name=config)  # 设置文件日志
            set_func_logger(log_pipe_in.send)  # 设置函数日志
        except Exception as e:
            logger.exception(f'Start log error')
            logger.error(f'Error: {e}')
            raise
    start_log()  # 初始化日志
    import time
    try:
        from script import Script  # 导入 Script 类
        script = Script(config_name=config)  # 创建 Script 实例
        script.state_queue = state_queue  # 设置状态队列
        script.loop()  # 运行脚本循环
    except SystemExit as e:
        logger.info(f'Script {config} process exit')
        logger.error(f'Error: {e}')
        state_queue.put({"state": ScriptState.WARNING})  # 发送警告状态
        time.sleep(0.1)
        exit(-1)  # 退出
    except Exception as e:
        logger.exception(f'Run script {config} error')
        logger.error(f'Error: {e}')
        raise
```

### __main__ 测试代码（第165-171行）
```python
if __name__ == '__main__':
    p = ScriptProcess('oas1')  # 创建进程
    p.start()  # 启动进程
    from time import sleep
    sleep(10)  # 等待10秒
    logger.info(p._process.exitcode)  # 打印退出码
```

## 5. 核心算法流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    脚本进程管理流程                           │
├─────────────────────────────────────────────────────────────┤
│  进程启动                                                    │
│  ├─ 设置状态为 RUNNING                                       │
│  ├─ 广播状态                                                 │
│  ├─ 创建子进程                                               │
│  └─ 启动子进程                                               │
│                                                             │
│  进程停止                                                    │
│  ├─ 设置状态为 INACTIVE                                      │
│  ├─ 广播状态                                                 │
│  ├─ 终止子进程                                               │
│  └─ 清理进程引用                                             │
│                                                             │
│  状态广播协程                                                │
│  ├─ 检查状态                                                 │
│  ├─ 从队列获取状态数据                                       │
│  └─ 广播状态                                                 │
│                                                             │
│  日志广播协程                                                │
│  ├─ 检查状态                                                 │
│  ├─ 从管道获取日志数据                                       │
│  └─ 广播日志                                                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    子进程执行流程                             │
├─────────────────────────────────────────────────────────────┤
│  1. 注册信号处理函数                                         │
│     ↓                                                        │
│  2. 初始化日志系统                                           │
│     ↓                                                        │
│  3. 创建 Script 实例                                         │
│     ↓                                                        │
│  4. 运行脚本循环                                             │
│     ↓                                                        │
│  5. 处理异常和退出                                           │
└─────────────────────────────────────────────────────────────┘
```

## 6. 使用示例

### 创建和启动脚本进程
```python
from module.server.script_process import ScriptProcess

# 创建进程
process = ScriptProcess('oas1')

# 启动进程
await process.start()

# 停止进程
await process.stop()
```

### 广播状态和日志
```python
# 广播状态
await process.broadcast_state({"state": "running"})

# 广播日志
await process.broadcast_log("Script started")
```

### 使用信号处理
```python
import signal

def signal_handler(signum, frame):
    print(f"Received signal {signum}")
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
```

## 7. 设计模式总结

1. **多进程模式**: 使用 `multiprocessing.Process` 创建子进程
2. **进程间通信模式**: 使用 `Queue` 和 `Pipe` 进行进程间通信
3. **协程模式**: 使用异步协程处理状态和日志广播
4. **信号处理模式**: 注册信号处理函数实现优雅退出
5. **状态管理模式**: 使用枚举管理进程状态
6. **守护进程模式**: 子进程设置为守护进程，主进程退出时自动终止