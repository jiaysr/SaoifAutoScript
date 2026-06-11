# module/server/main_manager.py 详解

## 1. 文件概述

`main_manager.py` 是主进程管理模块，负责：
- 管理所有脚本进程的生命周期
- 处理进程间通信和状态广播
- 提供配置缓存和脚本文件管理
- 支持服务器关闭和进程重启

## 2. 导入部分解释

```python
import asyncio                              # 异步编程
import sys                                  # 系统模块
import os                                   # 操作系统模块
import signal                               # 信号处理
from asyncio.tasks import Task              # 异步任务
from threading import Thread                # 线程
from module.logger import logger            # 日志模块
from module.config.config import Config     # 配置类
from module.server.script_process import ScriptProcess, ScriptState  # 脚本进程
from module.server.config_manager import ConfigManager  # 配置管理器
```

## 3. 类定义解释

### MainManager 类（第18-113行）
继承自 `ConfigManager`，主进程管理器。

## 4. 每个方法的逐行解释

### MainManager.__init__ 方法（第24-31行）
```python
def __init__(self) -> None:
    super().__init__()  # 调用父类构造函数
    self.script_process: dict[str: ScriptProcess] = {}  # 脚本进程字典
    self._all_script_files = self.all_script_files()  # 获取所有脚本文件
    for script_name in self._all_script_files:
        self.script_process[script_name] = ScriptProcess(script_name)  # 为每个脚本创建进程
    self.push_data_thread = Thread(target=self.start_push_data_thread, daemon=True)  # 创建数据推送线程
    self.push_data_thread.start()  # 启动线程
```

### MainManager.config_cache 静态方法（第45-47行）
```python
@staticmethod
def config_cache(name: str) -> Config:
    return Config(name)  # 返回配置实例
```

### MainManager.add_script_file 方法（第49-55行）
```python
def add_script_file(self, file_name: str):
    # 当你添加了新的脚本文件后，需要添加缓存的列表
    if file_name in self._all_script_files:  # 如果已存在
        logger.warning(f'[{file_name}] script file already exists')
        return
    self._all_script_files = self.all_script_files()  # 刷新列表
    self.script_process[file_name] = ScriptProcess(file_name)  # 创建新进程
```

### MainManager.start_push_data_thread 方法（第57-71行）
```python
def start_push_data_thread(self):
    try:
        asyncio.run(self.push_data_handle())  # 运行异步处理
    except SystemExit as e:
        logger.info('Kill the main process')
        try:
            os.kill(os.getpid(), signal.SIGILL)  # 杀死进程
            print("Process killed successfully.")
        except OSError:
            print("Failed to kill the process.")

    except Exception as e:
        logger.exception(e)
        sys.exit(0)  # 退出
```

### MainManager.push_data_handle 方法（第73-100行）
```python
async def push_data_handle(self):
    tasks: dict[str, Task] = {}
    from asyncio import sleep
    while 1:
        await sleep(3)  # 每3秒检查一次
        if MainManager.signal_kill_server:  # 如果收到关闭信号
            logger.info('Kill all server')
            for script_p in self.script_process.values():
                await script_p.stop()  # 停止所有脚本
            logger.info('Kill push data thread')
            sys.exit(0)  # 退出
        for name, script_p in self.script_process.items():
            # 遍历所有脚本进程
            if script_p.state == ScriptState.INACTIVE:  # 如果未激活
                continue
            coroutine_state_name = f'coroutine_state_{name}'
            if coroutine_state_name not in tasks:  # 如果状态协程不存在
                tasks[coroutine_state_name] = asyncio.create_task(script_p.coroutine_broadcast_state(),
                                                                  name=coroutine_state_name)  # 创建状态广播协程
            coroutine_log_name = f'coroutine_log_{name}'
            if coroutine_log_name not in tasks:  # 如果日志协程不存在
                tasks[coroutine_log_name] = asyncio.create_task(script_p.coroutine_broadcast_log(),
                                                                name=coroutine_log_name)  # 创建日志广播协程
```

### MainManager.restart_processes 方法（第102-111行）
```python
async def restart_processes(self, script_instances: list[str]):
    for instance in script_instances:
        logger.info(f'Restart script {instance}')
        if instance not in self.script_process:  # 如果进程不存在
            try:
                self.script_process[instance] = ScriptProcess(instance)  # 创建新进程
            except FileNotFoundError:
                logger.error(f'{instance} file not found')
                continue
        await self.script_process[instance].start()  # 启动进程
```

### mm 实例（第114行）
```python
mm = MainManager()  # 创建全局主管理器实例
```

## 5. 核心算法流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    主管理器初始化流程                         │
├─────────────────────────────────────────────────────────────┤
│  1. 调用父类构造函数                                         │
│     ↓                                                        │
│  2. 初始化脚本进程字典                                       │
│     ↓                                                        │
│  3. 获取所有脚本文件                                         │
│     ↓                                                        │
│  4. 为每个脚本创建进程                                       │
│     ↓                                                        │
│  5. 创建并启动数据推送线程                                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    数据推送线程流程                           │
├─────────────────────────────────────────────────────────────┤
│  1. 进入无限循环                                             │
│     ↓                                                        │
│  2. 等待3秒                                                  │
│     ↓                                                        │
│  3. 检查关闭信号                                             │
│     ├─ 如果收到信号                                          │
│     │   ├─ 停止所有脚本                                     │
│     │   └─ 退出                                             │
│     └─ 如果没有信号                                          │
│         ↓                                                    │
│  4. 遍历所有脚本进程                                         │
│     ├─ 跳过未激活的进程                                      │
│     ├─ 创建状态广播协程（如果不存在）                        │
│     └─ 创建日志广播协程（如果不存在）                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    进程重启流程                               │
├─────────────────────────────────────────────────────────────┤
│  1. 遍历指定的脚本实例                                       │
│     ↓                                                        │
│  2. 检查进程是否存在                                         │
│     ├─ 如果不存在                                            │
│     │   ├─ 创建新进程                                       │
│     │   └─ 处理文件未找到异常                               │
│     └─ 如果存在                                              │
│         ↓                                                    │
│  3. 启动进程                                                 │
└─────────────────────────────────────────────────────────────┘
```

## 6. 使用示例

### 获取主管理器实例
```python
from module.server.main_manager import mm

# 获取所有脚本文件
scripts = mm.all_script_files()
print(scripts)  # ['oas1', 'oas2', ...]

# 获取配置缓存
config = mm.config_cache('oas1')
```

### 管理脚本进程
```python
from module.server.main_manager import mm

# 启动脚本
await mm.script_process['oas1'].start()

# 停止脚本
await mm.script_process['oas1'].stop()

# 获取脚本状态
state = mm.script_process['oas1'].state
```

### 添加新脚本文件
```python
from module.server.main_manager import mm

# 添加新脚本
mm.add_script_file('oas3')

# 重启指定脚本
await mm.restart_processes(['oas1', 'oas2'])
```

### 关闭服务器
```python
from module.server.main_manager import MainManager

# 设置关闭信号
MainManager.signal_kill_server = True
```

## 7. 设计模式总结

1. **单例模式**: 使用全局变量 `mm` 作为主管理器实例
2. **进程管理模式**: 管理多个脚本子进程的生命周期
3. **异步任务模式**: 使用异步协程处理状态和日志广播
4. **守护线程模式**: 使用守护线程处理数据推送
5. **信号处理模式**: 使用信号机制实现优雅关闭
6. **配置管理模式**: 提供配置缓存和文件管理功能