# config.py 代码详解

## 1. 文件概述

`config.py` 是整个配置系统的核心入口文件，实现了任务调度器的主要逻辑。它通过多重继承组合了多个功能模块（ConfigState、ConfigManual、ConfigWatcher、ConfigMenu），提供了配置管理、任务调度、延迟执行等核心功能。

**主要职责：**
- 定义 `Function` 类表示可调度的任务函数
- 定义 `Config` 类作为配置系统的主接口
- 实现任务调度算法（获取下一个任务、更新调度队列）
- 管理任务的延迟执行和回调机制

## 2. 导入部分解释

```python
import copy                    # 深拷贝对象，用于复制任务对象避免修改原始数据
import datetime                # 日期时间处理
import operator                # 操作符模块，用于 attrgetter 排序
import threading               # 线程支持
import random                  # 随机数生成，用于添加随机延迟

from datetime import datetime, timedelta  # 从 datetime 导入具体类
from cached_property import cached_property  # 缓存属性装饰器，避免重复计算
from threading import Lock    # 线程锁

from module.base.filter import Filter  # 过滤器基类
from module.config.config_updater import ConfigUpdater  # 配置更新器
from module.config.config_manual import ConfigManual    # 手动配置
from module.config.config_watcher import ConfigWatcher  # 配置文件监视器
from module.config.config_menu import ConfigMenu        # 菜单配置
from module.config.config_model import ConfigModel      # 配置数据模型
from module.config.config_state import ConfigState      # 配置状态管理
from module.config.scheduler import TaskScheduler       # 任务调度器
from module.config.utils import *                       # 工具函数（通配符导入）
from module.notify.notify import Notifier               # 通知器

from module.exception import RequestHumanTakeover, ScriptError  # 自定义异常
from module.logger import logger                        # 日志记录器
```

## 3. 类定义解释

### 3.1 Function 类

`Function` 类表示一个可调度的任务函数，包含任务的启用状态、命令名称、下次运行时间和优先级。

```python
class Function:
    def __init__(self, key: str, data: dict):
```

**属性说明：**
- `enable` (bool): 任务是否启用
- `command` (str): 任务命令名称（大驼峰格式）
- `next_run` (datetime): 下次运行时间
- `priority` (int): 任务优先级

### 3.2 Config 类

```python
class Config(ConfigState, ConfigManual, ConfigWatcher, ConfigMenu):
```

采用多重继承设计，组合了以下功能：
- **ConfigState**: 管理运行时状态（pending_task、waiting_task、task）
- **ConfigManual**: 提供手动配置常量（调度优先级、设备配置）
- **ConfigWatcher**: 监视配置文件变化
- **ConfigMenu**: 提供 GUI 菜单结构

## 4. 每个方法的逐行解释

### 4.1 Function.__init__

```python
def __init__(self, key: str, data: dict):
    # 如果输入不是字典，设置默认值
    if isinstance(data, dict) is False:
        self.enable = False
        self.command = "Unknown"
        self.next_run = DEFAULT_TIME
        return
    
    # 如果没有 scheduler 字段，设置默认值
    if data.get("scheduler") is None:
        self.enable = False
        self.command = "Unknown"
        self.next_run = DEFAULT_TIME
        return

    # 从 scheduler 字段提取配置
    self.enable: bool = data['scheduler']['enable']
    self.command: str = ConfigModel.type(key)  # 获取任务类型名称
    
    # 解析下次运行时间
    next_run = data['scheduler']['next_run']
    if isinstance(next_run, str):
        next_run = datetime.strptime(next_run, "%Y-%m-%d %H:%M:%S")
    self.next_run: datetime = next_run
    
    # 解析优先级
    priority = data['scheduler']['priority']
    if isinstance(priority, str):
        priority = int(priority)
    self.priority: int = priority
```

### 4.2 Function.__str__

```python
def __str__(self):
    enable = "Enable" if self.enable else "Disable"
    return f"{self.command} ({enable}, {self.priority}, {str(self.next_run)})"
```

返回格式：`任务名 (状态, 优先级, 下次运行时间)`

### 4.3 Function.__eq__

```python
def __eq__(self, other):
    if not isinstance(other, Function):
        return False
    # 命令名和下次运行时间相同则认为相等
    if self.command == other.command and self.next_run == other.next_run:
        return True
    else:
        return False
```

### 4.4 name_to_function

```python
def name_to_function(name):
    function = Function({})  # 创建空 Function
    function.command = name  # 设置命令名
    function.enable = True   # 默认启用
    return function
```

### 4.5 Config.__init__

```python
def __init__(self, config_name: str, task=None) -> None:
    super().__init__(config_name)  # 调用 ConfigState 的初始化
    super(ConfigManual, self).__init__()   # 跳过 ConfigManual 的 __init__
    super(ConfigWatcher, self).__init__()  # 跳过 ConfigWatcher 的 __init__
    super(ConfigMenu, self).__init__()     # 跳过 ConfigMenu 的 __init__
    self.model = ConfigModel(config_name=config_name)  # 创建配置模型
    self.scheduler_update_dt = None  # 调度器更新时间戳
```

### 4.6 Config.__getattr__

```python
def __getattr__(self, name):
    try:
        return getattr(self.model, name)  # 委托给 model
    except AttributeError:
        return None  # 属性不存在时返回 None
```

### 4.7 Config.update_scheduler

```python
def update_scheduler(self) -> None:
    pending_task = []   # 待执行任务
    waiting_task = []   # 等待中任务
    error = []          # 错误任务
    self.scheduler_update_dt = datetime.now()
    
    # 遍历所有配置项
    for key, value in self.model.dict().items():
        func = Function(key, value)
        if not func.enable:
            continue  # 跳过未启用的任务
        
        # 分类任务
        if not isinstance(func.next_run, datetime):
            error.append(func)        # 时间格式错误
        elif func.next_run < self.scheduler_update_dt:
            pending_task.append(func)  # 已到执行时间
        else:
            waiting_task.append(func)  # 未到执行时间

    # 对 pending 任务进行调度排序
    if pending_task:
        pending_task = TaskScheduler.schedule(
            rule=self.model.script.optimization.schedule_rule,
            pending=pending_task
        )
        # 保证正在运行的任务不被顶替
        if self.model.running_task and pending_task:
            for i, obj in enumerate(pending_task):
                if obj.command == self.model.running_task:
                    pending_task.insert(0, pending_task.pop(i))
                    break

    # waiting 任务按下次运行时间排序
    if waiting_task:
        waiting_task = sorted(waiting_task, key=operator.attrgetter("next_run"))
    
    # 错误任务放在最前面
    if error:
        pending_task = error + pending_task

    self.pending_task = pending_task
    self.waiting_task = waiting_task
```

### 4.8 Config.get_next

```python
def get_next(self) -> Function:
    self.update_scheduler()  # 先更新调度队列

    # 优先返回待执行任务
    if self.pending_task:
        task = self.pending_task[0]
        self.task = task
        return task

    # 没有待执行任务，返回最近的等待任务
    if self.waiting_task:
        task = copy.deepcopy(self.waiting_task[0])
        return task
    else:
        # 没有任何任务，请求人工干预
        raise RequestHumanTakeover
```

### 4.9 Config.task_delay

```python
def task_delay(self, task: str, start_time: datetime = None,
               success: bool = None, server: bool = True, 
               target: datetime = None) -> None:
    self.reload()  # 重新加载配置
    
    # 任务名预处理
    if not task:
        task = self.task.command
    task = convert_to_underscore(task)
    
    # 获取任务调度器配置
    task_object = getattr(self.model, task, None)
    scheduler = getattr(task_object, 'scheduler', None)
    
    # 计算候选运行时间
    run = []
    if success is not None:
        interval = (scheduler.success_interval if success 
                   else scheduler.failure_interval)
        run.append(start_time + interval)
    
    if target is not None:
        target = [target] if not isinstance(target, list) else target
        target = nearest_future(target)
        run.append(target)
    
    # 选择最早的运行时间
    run = min(run).replace(microsecond=0)
    next_run = run
    
    # 添加服务器更新时间和随机浮动
    if server and hasattr(scheduler, 'server_update'):
        float_seconds = (scheduler.float_time.hour * 3600 +
                        scheduler.float_time.minute * 60 +
                        scheduler.float_time.second)
        random_float = random.randint(0, float_seconds)
        if scheduler.server_update == time(hour=9):
            next_run += timedelta(seconds=random_float)
        else:
            next_run = parse_tomorrow_server(
                scheduler.server_update, scheduler.delay_date, random_float
            )
    
    # 线程安全地保存
    self.lock_config.acquire()
    try:
        scheduler.next_run = next_run
        self.save()
    finally:
        self.lock_config.release()
```

## 5. 核心算法流程图

### 5.1 任务调度流程

```
┌─────────────────────────────────────────────────────────────┐
│                    update_scheduler()                        │
├─────────────────────────────────────────────────────────────┤
│  1. 遍历所有配置项                                           │
│     │                                                        │
│     ├─ 未启用 ──→ 跳过                                       │
│     │                                                        │
│     ├─ next_run 格式错误 ──→ 加入 error 列表                  │
│     │                                                        │
│     ├─ next_run < 当前时间 ──→ 加入 pending_task              │
│     │                                                        │
│     └─ next_run >= 当前时间 ──→ 加入 waiting_task             │
│                                                              │
│  2. 对 pending_task 进行调度排序                               │
│     ├─ FILTER: 使用优先级过滤器                               │
│     ├─ FIFO: 按 next_run 时间排序                             │
│     └─ PRIORITY: 按优先级分组后排序                            │
│                                                              │
│  3. 保证正在运行的任务排在第一位                               │
│                                                              │
│  4. waiting_task 按 next_run 排序                             │
│                                                              │
│  5. error 放在 pending_task 最前面                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      get_next()                              │
├─────────────────────────────────────────────────────────────┤
│  1. 调用 update_scheduler()                                  │
│                                                              │
│  2. 如果 pending_task 不为空                                  │
│     └─ 返回 pending_task[0]                                  │
│                                                              │
│  3. 如果 waiting_task 不为空                                  │
│     └─ 返回 waiting_task[0] 的深拷贝                          │
│                                                              │
│  4. 如果都没有                                                │
│     └─ 抛出 RequestHumanTakeover                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 任务延迟计算流程

```
┌─────────────────────────────────────────────────────────────┐
│                    task_delay()                              │
├─────────────────────────────────────────────────────────────┤
│  1. 重新加载配置                                              │
│  2. 获取任务的 scheduler 配置                                 │
│  3. 计算候选时间列表 run[]                                    │
│     ├─ success_interval 或 failure_interval                  │
│     └─ target 时间                                           │
│  4. 选择 min(run) 作为基础 next_run                          │
│  5. 如果有 server_update                                     │
│     ├─ 计算随机浮动秒数                                       │
│     └─ 使用 parse_tomorrow_server 计算最终时间                │
│  6. 线程安全保存                                              │
└─────────────────────────────────────────────────────────────┘
```

## 6. 使用示例

```python
# 创建配置实例
config = Config(config_name='oas1')

# 获取下一个要执行的任务
task = config.get_next()
print(f"Next task: {task.command}, enabled: {task.enable}")

# 获取配置参数
value = config.get_arg(task='Script', group='Scheduler', argument='Enable')

# 设置配置参数
config.set_arg(task='Script', group='Scheduler', argument='Enable', value=True)

# 任务完成后延迟执行
config.task_delay(
    task='Orochi',
    start_time=datetime.now(),
    success=True,
    server=True
)

# 手动调用任务
config.task_call(task='Orochi', force_call=True)

# 获取调度数据（用于 GUI 显示）
schedule_data = config.get_schedule_data()
print(f"Running: {schedule_data['running']}")
print(f"Pending: {schedule_data['pending']}")
print(f"Waiting: {schedule_data['waiting']}")

# 保存配置
config.save()

# 重新加载配置
config.reload()

# 发送通知
config.notifier.push(title="任务完成", content="Orochi 已完成")
```

## 7. 设计模式总结

### 7.1 多重继承（Mixin 模式）
`Config` 类通过多重继承组合了 4 个 Mixin 类，每个类负责一个特定的功能领域：
- `ConfigState`: 状态管理
- `ConfigManual`: 静态配置
- `ConfigWatcher`: 文件监视
- `ConfigMenu`: GUI 菜单

### 7.2 委托模式（Delegation）
`Config` 通过 `__getattr__` 将属性访问委托给内部的 `ConfigModel` 对象，实现了透明的代理。

### 7.3 策略模式（Strategy）
任务调度使用策略模式，通过 `ScheduleRule` 枚举选择不同的调度算法：
- `FILTER`: 基于优先级过滤
- `FIFO`: 先进先出
- `PRIORITY`: 优先级分组

### 7.4 模板方法模式
`task_delay` 定义了延迟执行的算法骨架，具体的延迟策略由参数决定。

### 7.5 线程安全
使用 `Lock` 保护配置文件的读写操作，防止并发冲突。

### 7.6 缓存属性
使用 `cached_property` 装饰器缓存 `lock_config` 和 `notifier`，避免重复创建。
