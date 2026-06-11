# config_state.py 代码详解

## 1. 文件概述

`config_state.py` 定义了 `ConfigState` 类，用于管理配置系统的运行时状态。这是一个简单的状态容器类，存储了任务调度过程中所需的关键状态变量。

**主要职责：**
- 存储配置名称
- 管理待执行任务列表（pending_task）
- 管理等待中任务列表（waiting_task）
- 跟踪当前正在执行的任务

## 2. 导入部分解释

```python
# 本文件没有导入任何外部模块
# 这是一个纯状态定义类，不依赖其他模块
```

## 3. 类定义解释

### 3.1 ConfigState 类

```python
class ConfigState:
    """
    这个类用于 先定义运行过程中所需要的变量
    """
    def __init__(self, config_name: str) -> None:
        self.config_name = config_name                    # 配置文件名称
        self.pending_task: list["Function"] = []          # 待执行任务列表
        self.waiting_task: list["Function"] = []          # 等待中任务列表
        self.task: str = None                             # 当前任务名（大驼峰格式）
```

**属性说明：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `config_name` | str | 配置文件的名称标识符 |
| `pending_task` | list[Function] | 已到执行时间的任务队列 |
| `waiting_task` | list[Function] | 未到执行时间的任务队列 |
| `task` | str | 当前正在执行的任务名称 |

## 4. 每个方法的逐行解释

### 4.1 ConfigState.__init__

```python
def __init__(self, config_name: str) -> None:
    # 设置配置名称，用于标识不同的配置实例
    self.config_name = config_name
    
    # 初始化待执行任务列表
    # Function 对象包含: enable, command, next_run, priority
    self.pending_task: list["Function"] = []
    
    # 初始化等待中任务列表
    # 这些任务已启用但还未到执行时间
    self.waiting_task: list["Function"] = []
    
    # 当前正在执行的任务名称
    # 使用大驼峰格式，如 'Orochi', 'AreaBoss'
    # None 表示没有任务正在执行
    self.task: str = None
```

## 5. 核心算法流程图

### 5.1 状态转换流程

```
┌─────────────────────────────────────────────────────────────┐
│                    ConfigState 状态图                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌──────────┐     update_scheduler()    ┌──────────┐       │
│   │  初始状态  │ ─────────────────────────→ │  等待状态  │       │
│   └──────────┘                           └──────────┘       │
│        │                                      │              │
│        │                                      │              │
│        ▼                                      ▼              │
│   ┌──────────┐     get_next()           ┌──────────┐       │
│   │  空闲状态  │ ─────────────────────────→ │  执行状态  │       │
│   └──────────┘                           └──────────┘       │
│        ▲                                      │              │
│        │                                      │              │
│        │         task_delay()                 │              │
│        └──────────────────────────────────────┘              │
│                                                              │
└─────────────────────────────────────────────────────────────┘

任务列表关系：
┌─────────────────────────────────────────────────────────────┐
│  pending_task (待执行)                                        │
│  ┌─────┐ ┌─────┐ ┌─────┐                                   │
│  │ F1  │ │ F2  │ │ F3  │  ← next_run < 当前时间             │
│  └─────┘ └─────┘ └─────┘                                   │
│       │                                                      │
│       │ get_next() 取第一个                                   │
│       ▼                                                      │
│  ┌─────────┐                                                │
│  │ task=F1 │ ← 当前执行的任务                                │
│  └─────────┘                                                │
│                                                              │
│  waiting_task (等待中)                                        │
│  ┌─────┐ ┌─────┐ ┌─────┐                                   │
│  │ F4  │ │ F5  │ │ F6  │  ← next_run >= 当前时间            │
│  └─────┘ └─────┘ └─────┘                                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 6. 使用示例

```python
# ConfigState 通常不单独使用，而是作为 Config 类的基类
from module.config.config_state import ConfigState

# 创建状态实例
state = ConfigState(config_name='oas1')

# 访问状态属性
print(f"Config name: {state.config_name}")
print(f"Pending tasks: {state.pending_task}")
print(f"Waiting tasks: {state.waiting_task}")
print(f"Current task: {state.task}")

# 在 Config 类中的使用方式
class Config(ConfigState):
    def __init__(self, config_name):
        super().__init__(config_name)
        # 其他初始化...
    
    def get_next(self):
        # 更新 pending_task 和 waiting_task
        self.update_scheduler()
        
        # 从 pending_task 获取下一个任务
        if self.pending_task:
            self.task = self.pending_task[0].command
            return self.pending_task[0]
        
        # 没有待执行任务
        return None
```

## 7. 设计模式总结

### 7.1 状态模式（State Pattern）
`ConfigState` 类封装了调度系统的运行时状态，将状态数据与状态行为分离。

### 7.2 数据传输对象（DTO）
作为简单的数据容器，`ConfigState` 在不同组件之间传递状态信息。

### 7.3 Mixin 模式
`ConfigState` 被设计为 Mixin 类，通过多重继承与其他功能类组合成完整的 `Config` 类。

### 7.4 空对象模式
`task = None` 表示没有任务正在执行，避免了空指针异常。

**设计优点：**
- 职责单一：只负责状态存储，不包含业务逻辑
- 易于测试：简单的数据类，便于单元测试
- 可扩展：可以轻松添加新的状态变量
- 线程安全：状态修改由外部的 Config 类通过 Lock 保护
