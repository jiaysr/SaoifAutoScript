# scheduler.py 代码详解

## 1. 文件概述

`scheduler.py` 定义了 `TaskScheduler` 类，实现了任务调度的核心算法。它支持三种调度策略：过滤器模式（FILTER）、先进先出（FIFO）和优先级模式（PRIORITY）。

**主要职责：**
- 实现任务调度算法
- 支持多种调度策略
- 管理任务执行顺序

## 2. 导入部分解释

```python
import datetime                              # 日期时间处理
import operator                              # 操作符模块

from cached_property import cached_property  # 缓存属性

from module.base.filter import Filter       # 过滤器基类

from module.config.config_manual import ConfigManual  # 手动配置
from module.logger import logger             # 日志记录器

from tasks.Script.config_optimization import ScheduleRule  # 调度规则枚举
```

**导入说明：**
- `operator.attrgetter`: 用于获取对象属性，便于排序
- `Filter`: 过滤器类，用于解析优先级规则
- `ConfigManual`: 提供 SCHEDULER_PRIORITY 优先级字符串
- `ScheduleRule`: 调度规则枚举（FILTER、FIFO、PRIORITY）

## 3. 类定义解释

### 3.1 TaskScheduler 类

```python
class TaskScheduler:
    # 类级别的过滤器，解析优先级规则
    filter = Filter(regex=r"(.*)", attr=["command"])
    filter.load(ConfigManual.SCHEDULER_PRIORITY)
```

**类属性说明：**
- `filter`: 预加载的过滤器实例，用于 FILTER 调度模式

## 4. 每个方法的逐行解释

### 4.1 schedule 静态方法

```python
@staticmethod
def schedule(rule: ScheduleRule, pending: list["Function"]) -> list["Function"]:
    """
    执行 任务的调度
    :param rule: 调度规则
    :param pending: 待调度任务列表
    :return: 调度后的任务列表
    """
    # 验证调度规则
    if rule != ScheduleRule.FILTER and rule != ScheduleRule.FIFO and rule != ScheduleRule.PRIORITY:
        logger.error(f"Invalid rule: {rule}")
        return pending
    
    # 验证任务列表
    if isinstance(pending, list) is False:
        logger.error(f"Invalid pending: {pending}")
        return pending

    # 根据调度规则选择算法
    if rule == ScheduleRule.FILTER:
        pending_task = TaskScheduler.filter.apply(pending)
        return pending_task

    if rule == ScheduleRule.FIFO:
        pending_task = TaskScheduler.fifo(pending)
        return pending_task

    if rule == ScheduleRule.PRIORITY:
        pending_task = TaskScheduler.priority(pending)
        return pending_task
```

**功能：** 根据指定的调度规则对任务列表进行排序。

**参数说明：**
- `rule`: 调度规则枚举值
- `pending`: 待调度的 Function 对象列表

**返回值：** 排序后的任务列表

### 4.2 fifo 静态方法

```python
@staticmethod
def fifo(pending: list["Function"]) -> list["Function"]:
    """
    先来后到，（按照任务的先后顺序进行调度）
    :param pending: 待调度任务列表
    :return: 排序后的任务列表
    """
    # 按 next_run 时间排序
    tasks_pending = sorted(pending, key=operator.attrgetter("next_run"))
    
    # 确保 Restart 任务始终在第一位
    for task in tasks_pending:
        if task.command == 'Restart':
            tasks_pending.remove(task)
            tasks_pending.insert(0, task)
            break
    
    return tasks_pending
```

**功能：** 按照任务的下次运行时间排序，先到先执行。

**排序逻辑：**
1. 按 `next_run` 时间升序排序
2. 将 `Restart` 任务移到第一位

**示例：**
```
输入: [Orochi(12:00), Restart(12:05), AreaBoss(11:50)]
输出: [Restart(12:05), AreaBoss(11:50), Orochi(12:00)]
      ↑ Restart 始终第一    ↑ 按时间排序
```

### 4.3 priority 静态方法

```python
@staticmethod
def priority(pending: list["Function"]) -> list["Function"]:
    """
    基于优先级，同一个优先级的任务按照先来后到的顺序进行调度，
    优先级高的任务先调度
    :param pending: 待调度任务列表
    :return: 排序后的任务列表
    """
    # 1. 按照优先级进行分组
    sorted(pending, key=operator.attrgetter("priority"))
    groups = {}
    for task in pending:
        if groups.get(task.priority) is None:
            groups[task.priority] = []
        groups[task.priority].append(task)
    
    # 2. 对每一组进行先来后到的排序
    for priority, tasks in groups.items():
        groups[priority] = TaskScheduler.fifo(tasks)

    # 3. 按照顺序合并所有的任务
    tasks_pending = []
    for priority in sorted(groups.keys()):
        tasks_pending.extend(groups[priority])

    return tasks_pending
```

**功能：** 按优先级分组，组内按 FIFO 排序。

**排序逻辑：**
1. 按 `priority` 字段分组
2. 每个组内使用 FIFO 排序
3. 按优先级从高到低合并

**示例：**
```
输入: 
  - Orochi(priority=2, next_run=12:00)
  - Restart(priority=1, next_run=12:05)
  - AreaBoss(priority=2, next_run=11:50)
  - GoldYoukai(priority=1, next_run=11:55)

分组:
  priority=1: [Restart(12:05), GoldYoukai(11:55)]
  priority=2: [AreaBoss(11:50), Orochi(12:00)]

组内排序:
  priority=1: [GoldYoukai(11:55), Restart(12:05)]
  priority=2: [AreaBoss(11:50), Orochi(12:00)]

输出: [GoldYoukai(11:55), Restart(12:05), AreaBoss(11:50), Orochi(12:00)]
       ↑ 优先级1（高）                              ↑ 优先级2（低）
```

## 5. 核心算法流程图

### 5.1 调度算法选择流程

```
┌─────────────────────────────────────────────────────────────┐
│                   schedule() 算法选择                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  输入: rule, pending                                         │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────┐                                            │
│  │ 验证参数    │                                            │
│  └─────────────┘                                            │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                选择调度规则                           │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                        │
│     ├─ FILTER ──→ filter.apply(pending)                     │
│     │                                                        │
│     ├─ FIFO ───→ fifo(pending)                              │
│     │                                                        │
│     └─ PRIORITY ─→ priority(pending)                        │
│                                                              │
│     ▼                                                        │
│  返回排序后的任务列表                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 FIFO 排序流程

```
┌─────────────────────────────────────────────────────────────┐
│                    fifo() 排序流程                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  输入: [Task1, Task2, Task3, ...]                           │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 按 next_run 时间升序排序                              │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 查找 Restart 任务                                    │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                        │
│     ├─ 找到 ──→ 移动到列表第一位                            │
│     │                                                        │
│     └─ 未找到 ──→ 保持原顺序                                │
│                                                              │
│     ▼                                                        │
│  返回排序后的任务列表                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 优先级排序流程

```
┌─────────────────────────────────────────────────────────────┐
│                  priority() 排序流程                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  输入: [Task1, Task2, Task3, ...]                           │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 按 priority 字段分组                                  │   │
│  │ groups = {                                            │   │
│  │   1: [Task1, Task3],                                  │   │
│  │   2: [Task2, Task4],                                  │   │
│  │   ...                                                 │   │
│  │ }                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 对每个组执行 FIFO 排序                                │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 按优先级从低到高合并（priority=1 最高）               │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                        │
│     ▼                                                        │
│  返回排序后的任务列表                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 6. 使用示例

```python
from module.config.scheduler import TaskScheduler
from tasks.Script.config_optimization import ScheduleRule

# 假设有以下待调度任务
pending_tasks = [
    Function({'scheduler': {'enable': True, 'next_run': '2024-01-01 12:00:00', 'priority': 2}}),
    Function({'scheduler': {'enable': True, 'next_run': '2024-01-01 11:50:00', 'priority': 1}}),
    Function({'scheduler': {'enable': True, 'next_run': '2024-01-01 12:05:00', 'priority': 1}}),
]

# 使用 FIFO 调度
fifo_result = TaskScheduler.schedule(ScheduleRule.FIFO, pending_tasks)
print("FIFO 排序结果:")
for task in fifo_result:
    print(f"  {task.command}: {task.next_run}")

# 使用 FILTER 调度（基于 ConfigManual.SCHEDULER_PRIORITY）
filter_result = TaskScheduler.schedule(ScheduleRule.FILTER, pending_tasks)
print("FILTER 排序结果:")
for task in filter_result:
    print(f"  {task.command}: {task.priority}")

# 使用 PRIORITY 调度
priority_result = TaskScheduler.schedule(ScheduleRule.PRIORITY, pending_tasks)
print("PRIORITY 排序结果:")
for task in priority_result:
    print(f"  {task.command}: priority={task.priority}, {task.next_run}")

# 在 Config 类中的使用方式
class Config:
    def update_scheduler(self):
        if self.pending_task:
            # 使用配置的调度规则
            self.pending_task = TaskScheduler.schedule(
                rule=self.model.script.optimization.schedule_rule,
                pending=self.pending_task
            )
```

## 7. 设计模式总结

### 7.1 策略模式（Strategy）
通过 `ScheduleRule` 枚举选择不同的调度算法，实现了可插拔的调度策略。

### 7.2 静态工厂方法模式
`schedule()` 作为静态工厂方法，根据参数创建不同的排序结果。

### 7.3 模板方法模式
`priority()` 方法中调用 `fifo()` 实现了模板方法模式。

### 7.4 类级别初始化
过滤器在类级别初始化并加载优先级规则，所有实例共享。

**设计优点：**
- 灵活性：支持三种不同的调度策略
- 可扩展：易于添加新的调度算法
- 性能：使用 `operator.attrgetter` 优化排序
- 特殊处理：确保 Restart 任务始终优先执行

**调度策略对比：**

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| FILTER | 基于优先级字符串过滤 | 需要严格优先级控制 |
| FIFO | 按时间排序，先到先执行 | 公平调度 |
| PRIORITY | 优先级分组，组内 FIFO | 平衡优先级和公平性 |

**注意事项：**
- `priority()` 方法中第一行 `sorted()` 没有赋值，可能是笔误
- Restart 任务在 FIFO 模式下有特殊处理
- 过滤器规则定义在 `ConfigManual.SCHEDULER_PRIORITY`
