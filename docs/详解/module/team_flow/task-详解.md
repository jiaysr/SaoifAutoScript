# module/team_flow/task.py 逐行代码详解

## 1. 文件概述

本文件定义了团队任务系统的核心数据模型 `Task` 类，用于表示游戏中可调度执行的任务。该类封装了任务的时间管理、角色分配和效用计算功能，是团队协作调度的基础组件。

**核心功能**：
- 任务时间管理（下次运行时间、限制时间、目标运行时间）
- 角色管理（队长/成员）
- 效用函数计算（收益-成本模型）
- 任务间时间差计算

**设计意图**：
- 为团队任务调度提供统一的数据结构
- 支持基于效用函数的任务优先级决策
- 灵活处理多种时间格式输入

---

## 2. 导入部分解释

```python
from time import sleep
```
- 从标准库 `time` 模块导入 `sleep` 函数
- 用于在程序中暂停执行指定秒数
- 在本文件中导入但未直接使用（可能用于调试或测试）

```python
from datetime import datetime, time, timedelta
```
- 从 `datetime` 模块导入三个核心时间类：
  - `datetime`：表示日期和时间的组合，如 `2023-09-13 18:46:23`
  - `time`：表示一天中的时间（不含日期），如 `00:30:00`
  - `timedelta`：表示两个日期/时间之间的差值

```python
from random import randint
```
- 从 `random` 模块导入 `randint` 函数
- 用于生成随机整数
- 在本文件中导入但未直接使用（可能预留用于随机化功能）

```python
from module.config.config import Config
```
- 从项目配置模块导入 `Config` 类
- 提供全局配置访问能力
- 在本文件中导入但未直接使用（可能预留用于配置读取）

```python
from tasks.Component.config_base import TimeDelta
```
- 从项目组件配置模块导入 `TimeDelta` 类
- 可能是自定义的时间间隔配置类
- 在本文件中导入但未直接使用（可能用于扩展功能）

---

## 3. 类定义：Task

### 3.1 构造函数 `__init__`

```python
class Task:
    def __init__(self,
                 next_run: datetime,
                 limit_time: time,
                 target_run: datetime = None,
                 team_task: bool = False,
                 role: str = 'leader',
                 limit_count: int = 0,
                 ):
```

**功能**：初始化任务实例

**参数说明**：
- `next_run: datetime`：下次运行时间
- `limit_time: time`：任务限制时间（最大允许执行时长）
- `target_run: datetime = None`：目标运行时间（可选）
- `team_task: bool = False`：是否为团队任务
- `role: str = 'leader'`：角色，默认为队长
- `limit_count: int = 0`：限制次数，0 表示无限制

**逐行解析**：
- **第 13 行**：定义 `Task` 类
- **第 14-21 行**：定义构造函数，包含 6 个参数，其中 3 个有默认值

```python
self.next_run = next_run
```
- **第 22 行**：保存下次运行时间到实例属性

```python
self.target_run = target_run
```
- **第 23 行**：保存目标运行时间

```python
self.limit_time = limit_time
```
- **第 24 行**：保存限制时间

```python
self.team_task = team_task
```
- **第 25 行**：保存是否为团队任务的标志

```python
self.role = role
```
- **第 26 行**：保存角色信息

```python
self.limit_count = limit_count
```
- **第 27 行**：保存限制次数

---

### 3.2 方法：update_info

```python
def update_info(self,
                next_run: datetime,
                limit_time: time,
                limit_count: int,
                role: str):
```

**功能**：更新任务信息，支持多种输入格式

**参数说明**：
- `next_run`：下次运行时间，支持 `datetime` 对象或 ISO 格式字符串
- `limit_time`：限制时间，支持 `time` 对象或 ISO 格式字符串
- `limit_count`：限制次数，支持 `int` 或字符串
- `role`：角色，必须为字符串

#### 3.2.1 更新 next_run

```python
if isinstance(next_run, datetime):
    self.next_run = next_run
elif isinstance(next_run, str):
    self.next_run = datetime.fromisoformat(next_run)
else:
    raise TypeError(f'next_run must be datetime or str, not {type(next_run)}')
```

**逐行解析**：
- **第 35 行**：检查是否为 `datetime` 类型
- **第 36 行**：如果是，直接赋值
- **第 37 行**：检查是否为字符串类型
- **第 38 行**：如果是，使用 `fromisoformat()` 解析 ISO 格式字符串
  - 支持格式如：`2023-09-13T18:46:23` 或 `2023-09-13 18:46:23`
- **第 39-40 行**：如果都不是，抛出类型错误异常

#### 3.2.2 更新 limit_count

```python
if isinstance(limit_count, int):
    self.limit_count = limit_count
elif isinstance(limit_count, str):
    self.limit_count = int(limit_count)
else:
    raise TypeError(f'limit_count must be int or str, not {type(limit_count)}')
```

**逐行解析**：
- **第 42 行**：检查是否为整数类型
- **第 43 行**：如果是，直接赋值
- **第 44 行**：检查是否为字符串类型
- **第 45 行**：如果是，转换为整数
- **第 46-47 行**：如果都不是，抛出类型错误异常

#### 3.2.3 更新 limit_time

```python
if isinstance(limit_time, time):
    self.limit_time = limit_time
elif isinstance(limit_time, str):
    self.limit_time = time.fromisoformat(limit_time)
else:
    raise TypeError(f'limit_time must be time or str, not {type(limit_time)}')
```

**逐行解析**：
- **第 49 行**：检查是否为 `time` 类型
- **第 50 行**：如果是，直接赋值
- **第 51 行**：检查是否为字符串类型
- **第 52 行**：如果是，使用 `fromisoformat()` 解析
  - 支持格式如：`00:30:00` 或 `PT30M`（ISO 8601 持续时间格式）
- **第 53-54 行**：如果都不是，抛出类型错误异常

#### 3.2.4 更新 role

```python
if isinstance(role, str):
    self.role = role
else:
    raise TypeError(f'role must be str, not {type(role)}')
```

**逐行解析**：
- **第 56 行**：检查是否为字符串类型
- **第 57 行**：如果是，直接赋值
- **第 58-59 行**：如果不是，抛出类型错误异常

---

### 3.3 方法：u（效用函数）

```python
def u(self) -> float:
    if self.role == 'leader':
        return self.r_leader() - self.r_leader()
    elif self.role == 'member':
        return self.r_member() - self.c_member()
```

**功能**：计算任务的效用值（Utility）

**设计原理**：
- 效用 = 收益（Revenue）- 成本（Cost）
- 根据角色不同，使用不同的收益和成本计算方法

**逐行解析**：
- **第 63 行**：定义效用函数，返回浮点数
- **第 68 行**：检查是否为队长角色
- **第 69 行**：计算队长效用
  - **注意**：这里有一个代码错误，应该是 `self.r_leader() - self.c_leader()`
  - 当前写法 `self.r_leader() - self.r_leader()` 结果永远为 0
- **第 70-71 行**：检查是否为成员角色
- **第 71 行**：计算成员效用 = 成员收益 - 成员成本

---

### 3.4 方法：r_leader（队长收益函数）

```python
def r_leader(self, tasks: list['Task']) -> float:
    result = 0
    for task in tasks:
        if task.role == 'leader':
            pass
    return result
```

**功能**：计算队长角色的收益

**参数说明**：
- `tasks: list['Task']`：同组内启用的同一任务列表

**逐行解析**：
- **第 73 行**：定义队长收益函数
- **第 79 行**：初始化收益为 0
- **第 80 行**：遍历任务列表
- **第 81-82 行**：检查是否为队长角色的任务
  - `pass` 表示当前未实现具体逻辑
- **第 84 行**：返回计算结果

**设计意图**：
- 收益计算可能基于：
  - 团队成员数量
  - 任务完成难度
  - 协作效率等因素
- 当前为框架代码，需要具体实现

---

### 3.5 方法：c_leader（队长成本函数）

```python
def c_leader(self) -> float:
    """
    成本函数
    :return:
    """
```

**功能**：计算队长角色的成本

**当前状态**：函数体为空，未实现

**可能的成本因素**：
- 时间成本
- 资源消耗
- 机会成本

---

### 3.6 方法：r_member（成员收益函数）

```python
def r_member(self) -> float:
    """
    收益函数
    :return:
    """
```

**功能**：计算成员角色的收益

**当前状态**：函数体为空，未实现

---

### 3.7 方法：c_member（成员成本函数）

```python
def c_member(self) -> float:
    """
    成本函数
    :return:
    """
```

**功能**：计算成员角色的成本

**当前状态**：函数体为空，未实现

---

## 4. 模块级函数：t_diff

```python
def t_diff(before: Task, after: Task) -> timedelta:
    return (after.next_run - before.next_run).total_seconds()
```

**功能**：计算两个任务之间的时间差

**参数说明**：
- `before: Task`：第一个任务
- `after: Task`：第二个任务

**逐行解析**：
- **第 105 行**：定义函数，返回 `timedelta` 类型（但实际返回的是秒数）
- **第 112 行**：计算时间差
  - `after.next_run - before.next_run`：两个任务的下次运行时间之差
  - `.total_seconds()`：将时间差转换为总秒数
  - 返回值是浮点数，单位为秒

**注意**：函数签名标注返回 `timedelta`，但实际返回 `float`，存在类型标注不一致

---

## 5. 核心算法流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                     Task 类初始化流程                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  接收参数        │
                    │  next_run       │
                    │  limit_time     │
                    │  target_run     │
                    │  team_task      │
                    │  role           │
                    │  limit_count    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  保存到实例属性  │
                    └─────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                     update_info 流程                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  接收参数        │
                    └────────┬────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │  处理 next_run               │
              └──────┬──────────────┬────────┘
                     │              │
              datetime             str
                     │              │
                     ▼              ▼
              ┌──────────┐  ┌──────────────┐
              │ 直接赋值 │  │ fromisoformat│
              └──────────┘  └──────┬───────┘
                                   │
                                   ▼
                            ┌─────────────┐
                            │   赋值      │
                            └─────────────┘


              ┌──────────────────────────────┐
              │  处理 limit_count            │
              └──────┬──────────────┬────────┘
                     │              │
                     int            str
                     │              │
                     ▼              ▼
              ┌──────────┐  ┌──────────────┐
              │ 直接赋值 │  │ int() 转换   │
              └──────────┘  └──────┬───────┘
                                   │
                                   ▼
                            ┌─────────────┐
                            │   赋值      │
                            └─────────────┘


              ┌──────────────────────────────┐
              │  处理 limit_time             │
              └──────┬──────────────┬────────┘
                     │              │
                     time           str
                     │              │
                     ▼              ▼
              ┌──────────┐  ┌──────────────┐
              │ 直接赋值 │  │ fromisoformat│
              └──────────┘  └──────┬───────┘
                                   │
                                   ▼
                            ┌─────────────┐
                            │   赋值      │
                            └─────────────┘


              ┌──────────────────────────────┐
              │  处理 role                   │
              └──────┬──────────────┬────────┘
                     │              │
                     str           其他
                     │              │
                     ▼              ▼
              ┌──────────┐  ┌──────────────┐
              │ 直接赋值 │  │ 抛出TypeError│
              └──────────┘  └──────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                     效用函数 u() 流程                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  检查角色        │
                    └──────┬──────┬───┘
                           │      │
                    leader │      │ member
                           ▼      ▼
                ┌────────────┐ ┌────────────┐
                │ r_leader() │ │ r_member() │
                │ -          │ │ -          │
                │ r_leader() │ │ c_member() │
                └─────┬──────┘ └─────┬──────┘
                      │              │
                      ▼              ▼
               ┌──────────┐   ┌──────────┐
               │ 返回 0   │   │ 返回差值 │
               │ (bug)    │   │          │
               └──────────┘   └──────────┘


┌─────────────────────────────────────────────────────────────────┐
│                     t_diff 流程                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  接收两个Task    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  after.next_run │
                    │  -              │
                    │  before.next_run│
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  .total_seconds()│
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  返回秒数 (float)│
                    └─────────────────┘
```

---

## 6. 使用示例

### 6.1 创建任务实例

```python
from datetime import datetime, time
from module.team_flow.task import Task

# 创建队长任务
leader_task = Task(
    next_run=datetime(2023, 9, 13, 18, 46, 23),
    limit_time=time(0, 30, 0),  # 30分钟限制
    target_run=datetime(2023, 9, 13, 19, 0, 0),
    team_task=True,
    role='leader',
    limit_count=5
)

# 创建成员任务
member_task = Task(
    next_run=datetime(2023, 9, 13, 18, 50, 0),
    limit_time=time(0, 20, 0),  # 20分钟限制
    team_task=True,
    role='member'
)

print(f"队长任务下次运行: {leader_task.next_run}")
print(f"成员任务下次运行: {member_task.next_run}")
```

### 6.2 更新任务信息

```python
# 使用字符串更新
leader_task.update_info(
    next_run='2023-09-13T19:00:00',
    limit_time='00:45:00',
    limit_count='10',
    role='leader'
)

# 使用对象更新
from datetime import datetime, time

leader_task.update_info(
    next_run=datetime(2023, 9, 13, 20, 0, 0),
    limit_time=time(1, 0, 0),
    limit_count=15,
    role='leader'
)

print(f"更新后限制时间: {leader_task.limit_time}")
print(f"更新后限制次数: {leader_task.limit_count}")
```

### 6.3 计算时间差

```python
from module.team_flow.task import Task, t_diff
from datetime import datetime, time

# 创建两个任务
task1 = Task(
    next_run=datetime(2023, 9, 13, 18, 0, 0),
    limit_time=time(0, 30, 0)
)

task2 = Task(
    next_run=datetime(2023, 9, 13, 18, 30, 0),
    limit_time=time(0, 30, 0)
)

# 计算时间差
diff_seconds = t_diff(task1, task2)
print(f"任务时间差: {diff_seconds} 秒")  # 输出: 1800.0 秒
print(f"任务时间差: {diff_seconds / 60} 分钟")  # 输出: 30.0 分钟
```

### 6.4 团队任务管理

```python
from datetime import datetime, time
from module.team_flow.task import Task

class TeamTaskManager:
    def __init__(self):
        self.tasks = []
    
    def add_task(self, task: Task):
        self.tasks.append(task)
    
    def get_sorted_tasks(self):
        """按下次运行时间排序"""
        return sorted(self.tasks, key=lambda t: t.next_run)
    
    def get_leader_tasks(self):
        """获取所有队长任务"""
        return [t for t in self.tasks if t.role == 'leader']
    
    def get_member_tasks(self):
        """获取所有成员任务"""
        return [t for t in self.tasks if t.role == 'member']

# 使用示例
manager = TeamTaskManager()

# 添加任务
manager.add_task(Task(
    next_run=datetime(2023, 9, 13, 18, 0, 0),
    limit_time=time(0, 30, 0),
    role='leader'
))

manager.add_task(Task(
    next_run=datetime(2023, 9, 13, 18, 15, 0),
    limit_time=time(0, 20, 0),
    role='member'
))

manager.add_task(Task(
    next_run=datetime(2023, 9, 13, 18, 10, 0),
    limit_time=time(0, 25, 0),
    role='member'
))

# 获取排序后的任务
sorted_tasks = manager.get_sorted_tasks()
for task in sorted_tasks:
    print(f"{task.role}: {task.next_run}")
```

### 6.5 效用计算（模拟实现）

```python
from datetime import datetime, time
from module.team_flow.task import Task

class TaskWithUtility(Task):
    """扩展 Task 类，实现效用计算"""
    
    def r_leader(self, tasks: list) -> float:
        """队长收益：基于团队规模"""
        team_size = len(tasks)
        return team_size * 10.0  # 每个成员贡献10点收益
    
    def c_leader(self) -> float:
        """队长成本：固定管理成本"""
        return 5.0
    
    def r_member(self) -> float:
        """成员收益：基于任务时间"""
        # 假设限制时间越长，收益越高
        hours = self.limit_time.hour + self.limit_time.minute / 60
        return hours * 20.0
    
    def c_member(self) -> float:
        """成员成本：基于限制时间"""
        hours = self.limit_time.hour + self.limit_time.minute / 60
        return hours * 5.0
    
    def u(self) -> float:
        """计算效用"""
        if self.role == 'leader':
            # 需要传入团队任务列表
            return 0  # 简化示例
        elif self.role == 'member':
            return self.r_member() - self.c_member()
        return 0

# 使用示例
member_task = TaskWithUtility(
    next_run=datetime(2023, 9, 13, 18, 0, 0),
    limit_time=time(0, 30, 0),
    role='member'
)

utility = member_task.u()
print(f"成员任务效用: {utility}")  # 输出: 10.0 - 2.5 = 7.5
```

---

## 7. 设计模式总结

### 7.1 数据传输对象模式（DTO）

`Task` 类是一个典型的数据传输对象：

```python
class Task:
    def __init__(self, next_run, limit_time, target_run, team_task, role, limit_count):
        self.next_run = next_run
        self.limit_time = limit_time
        # ...
```

**特点**：
- 主要用于封装数据
- 包含简单的数据验证逻辑
- 便于在不同层之间传输任务信息

### 7.2 策略模式（Strategy Pattern）

效用函数的实现采用了策略模式的思想：

```python
def u(self) -> float:
    if self.role == 'leader':
        return self.r_leader() - self.c_leader()
    elif self.role == 'member':
        return self.r_member() - self.c_member()
```

**特点**：
- 根据角色选择不同的计算策略
- 收益和成本函数可以独立扩展
- 便于添加新的角色类型

### 7.3 模板方法模式（Template Method）

效用计算框架是模板方法模式的应用：

```python
def u(self) -> float:
    return self.r() - self.c()  # 模板：收益 - 成本

def r(self):  # 需要子类实现
    pass

def c(self):  # 需要子类实现
    pass
```

**特点**：
- 定义算法骨架（效用 = 收益 - 成本）
- 具体步骤延迟到子类实现
- 便于扩展不同的计算方法

### 7.4 类型安全设计

`update_info` 方法展示了防御性编程：

```python
if isinstance(next_run, datetime):
    self.next_run = next_run
elif isinstance(next_run, str):
    self.next_run = datetime.fromisoformat(next_run)
else:
    raise TypeError(...)
```

**特点**：
- 运行时类型检查
- 自动类型转换
- 清晰的错误信息
- 提高代码健壮性

### 7.5 工厂方法模式（潜在）

`update_info` 方法可以看作是一种简化的工厂方法：

```python
# 根据输入类型创建不同的对象
if isinstance(next_run, str):
    next_run = datetime.fromisoformat(next_run)  # 字符串 -> datetime
```

**特点**：
- 隐藏对象创建细节
- 统一的接口处理多种输入
- 简化调用方代码

### 7.6 值对象模式（Value Object）

时间相关属性体现了值对象的特点：

```python
self.next_run = datetime(...)  # 不可变的时间点
self.limit_time = time(...)    # 不可变的时间段
```

**特点**：
- 表示领域中的值
- 通常不可变
- 通过相等性比较而非标识比较

---

## 附录：代码问题与改进建议

### 问题 1：效用函数 bug

```python
def u(self) -> float:
    if self.role == 'leader':
        return self.r_leader() - self.r_leader()  # 错误：应该是 c_leader()
```

**修复**：
```python
return self.r_leader() - self.c_leader()
```

### 问题 2：类型标注不一致

```python
def t_diff(before: Task, after: Task) -> timedelta:
    return (after.next_run - before.next_run).total_seconds()  # 返回 float
```

**修复**：
```python
def t_diff(before: Task, after: Task) -> float:
    return (after.next_run - before.next_run).total_seconds()
```

### 问题 3：未使用的导入

```python
from time import sleep
from random import randint
from module.config.config import Config
from tasks.Component.config_base import TimeDelta
```

**建议**：移除未使用的导入，或添加使用场景

### 问题 4：收益/成本函数未实现

```python
def r_leader(self, tasks: list['Task']) -> float:
    result = 0
    for task in tasks:
        if task.role == 'leader':
            pass  # 未实现
    return result
```

**建议**：实现具体的收益计算逻辑，或标记为抽象方法

### 改进建议

1. **使用抽象基类**：
```python
from abc import ABC, abstractmethod

class BaseTask(ABC):
    @abstractmethod
    def r(self) -> float:
        pass
    
    @abstractmethod
    def c(self) -> float:
        pass
```

2. **添加数据验证**：
```python
def __post_init__(self):
    if self.limit_count < 0:
        raise ValueError("limit_count must be non-negative")
```

3. **使用 dataclass**：
```python
from dataclasses import dataclass
from datetime import datetime, time

@dataclass
class Task:
    next_run: datetime
    limit_time: time
    target_run: datetime = None
    team_task: bool = False
    role: str = 'leader'
    limit_count: int = 0
```

4. **添加序列化支持**：
```python
def to_dict(self) -> dict:
    return {
        'next_run': self.next_run.isoformat(),
        'limit_time': self.limit_time.isoformat(),
        'role': self.role,
        # ...
    }

@classmethod
def from_dict(cls, data: dict) -> 'Task':
    return cls(
        next_run=datetime.fromisoformat(data['next_run']),
        limit_time=time.fromisoformat(data['limit_time']),
        role=data['role'],
        # ...
    )
```
