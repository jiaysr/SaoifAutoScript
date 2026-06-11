# module/team_flow/player.py 代码详解

## 1. 文件概述

`player.py` 是团队流程中的玩家模块，定义了玩家的基本属性和数据发布功能。作为 `Host` 类的基类之一，提供玩家身份标识和多人任务数据管理能力。

**文件路径**: `module/team_flow/player.py`
**代码行数**: 33 行
**主要功能**:
- 玩家身份标识（用户名）
- 多人任务缓存管理
- 发布数据提取

---

## 2. 导入部分解释

```python
from time import sleep
from datetime import datetime, time
from random import randint
from module.config.config import Config
from module.team_flow.task import Task
```

| 导入项 | 来源模块 | 说明 |
|--------|----------|------|
| `sleep` | time | 线程休眠（当前未使用） |
| `datetime`, `time` | datetime | 日期时间类型（当前未使用） |
| `randint` | random | 随机数生成（当前未使用） |
| `Config` | module.config.config | 配置类（当前未使用） |
| `Task` | module.team_flow.task | 任务类，用于类型注解 |

**注意**: 部分导入在当前版本中未实际使用，可能是为后续扩展预留。

---

## 3. 类定义解释

### Player 类

```python
class Player:
    def __init__(self, username: str):
        self.username = username
        self.multi_tasks: dict[str: Task] = {}
```

**核心属性**:
- `username`: 玩家用户名，用于在 MQTT 消息中标识自己
- `multi_tasks`: 多人任务字典，键为任务名，值为 Task 对象

**设计意图**: 作为 `Host` 类的基类，提供玩家基础数据结构和发布功能。

---

## 4. 每个方法的逐行解释

### `__init__` 方法

```python
def __init__(self, username: str):
    self.username = username
    self.multi_tasks: dict[str: Task] = {}
```

| 行号 | 代码 | 说明 |
|------|------|------|
| 13 | `def __init__(self, username: str):` | 构造函数，接收用户名参数 |
| 14 | `self.username = username` | 存储玩家用户名 |
| 15 | `self.multi_tasks: dict[str: Task] = {}` | 初始化空的任务字典，类型注解为 `dict[str, Task]` |

**参数说明**:
- `username` (str): 玩家的唯一标识名称

### `publish_data` 方法

```python
def publish_data(self) -> dict:
    result = {}
    for name, task in self.multi_tasks.items():
        item = {}
        if not task.team_task:
            continue
        item['next_run'] = str(task.next_run)
        item['role'] = str(task.role)
        item['limit_time'] = str(task.limit_time)
        item['limit_count'] = int(task.limit_count)
        result[name] = item
    return result
```

**功能**: 提取要发布到 MQTT 的任务数据

| 行号 | 代码 | 说明 |
|------|------|------|
| 23 | `result = {}` | 初始化结果字典 |
| 24 | `for name, task in self.multi_tasks.items():` | 遍历所有多人任务 |
| 25 | `item = {}` | 初始化单个任务的数据字典 |
| 26-27 | `if not task.team_task: continue` | 跳过非团队任务 |
| 28 | `item['next_run'] = str(task.next_run)` | 提取下次运行时间，转为字符串 |
| 29 | `item['role'] = str(task.role)` | 提取角色（leader/member） |
| 30 | `item['limit_time'] = str(task.limit_time)` | 提取时间限制 |
| 31 | `item['limit_count'] = int(task.limit_count)` | 提取次数限制，转为整数 |
| 32 | `result[name] = item` | 添加到结果字典 |
| 33 | `return result` | 返回发布数据 |

**返回数据格式**:
```json
{
    "orochi": {
        "next_run": "2023-09-13 18:46:23",
        "role": "leader",
        "limit_time": "00:30:00",
        "limit_count": 50
    },
    "fallen_sun": {
        "next_run": "2023-09-13 19:00:00",
        "role": "member",
        "limit_time": "00:30:00",
        "limit_count": 30
    }
}
```

---

## 5. 核心算法流程图

### Player 初始化流程

```
┌─────────────────────────────────────┐
│        Player.__init__              │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   接收 username 参数                │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   self.username = username          │
│   存储玩家用户名                     │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   self.multi_tasks = {}             │
│   初始化空任务字典                    │
└─────────────────────────────────────┘
```

### publish_data 发布流程

```
┌─────────────────────────────────────┐
│        publish_data()               │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   result = {}                       │
│   初始化结果字典                     │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   for name, task in multi_tasks:    │
│   遍历所有多人任务                    │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   检查 task.team_task               │
│   非团队任务 → skip                  │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   提取任务信息:                       │
│   ├─ next_run (下次运行时间)         │
│   ├─ role (角色)                     │
│   ├─ limit_time (时间限制)           │
│   └─ limit_count (次数限制)          │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   result[name] = item               │
│   添加到结果字典                     │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   return result                     │
│   返回发布数据字典                    │
└─────────────────────────────────────┘
```

---

## 6. 使用示例

### 基本使用

```python
from module.team_flow.player import Player

# 创建玩家实例
player = Player(username="player1")

# 访问玩家信息
print(f"用户名: {player.username}")
print(f"任务数量: {len(player.multi_tasks)}")
```

### 添加任务

```python
from module.team_flow.task import Task
from datetime import datetime, time

# 创建任务
task = Task(
    next_run=datetime.now(),
    limit_time=time(minute=30),
    team_task=True,
    role='leader',
    limit_count=50
)

# 添加到玩家任务列表
player.multi_tasks['orochi'] = task
```

### 发布数据

```python
# 获取发布数据
data = player.publish_data()
print(data)
# 输出:
# {
#     'orochi': {
#         'next_run': '2023-09-13 18:46:23',
#         'role': 'leader',
#         'limit_time': '00:30:00',
#         'limit_count': 50
#     }
# }
```

### 与 Host 结合使用

```python
from module.team_flow.host import Host
from module.config.config import Config

# Host 继承了 Player
config = Config('oas1')
host = Host(config)

# Host 作为 Player 使用
print(f"Host 用户名: {host.username}")

# 发布 Host 的任务数据
host_data = host.publish_data()
print(f"Host 任务: {host_data}")
```

### 筛选团队任务

```python
# publish_data 自动筛选 team_task=True 的任务
player.multi_tasks['solo_task'] = Task(
    next_run=datetime.now(),
    limit_time=time(minute=30),
    team_task=False,  # 非团队任务
    role='leader'
)

player.multi_tasks['team_task'] = Task(
    next_run=datetime.now(),
    limit_time=time(minute=30),
    team_task=True,   # 团队任务
    role='member'
)

data = player.publish_data()
print(data)
# 只包含 'team_task'，不包含 'solo_task'
```

---

## 7. 设计模式总结

| 设计模式 | 应用说明 |
|----------|----------|
| **数据传输对象** | `publish_data` 将内部数据转换为可传输的字典格式 |
| **继承复用** | 作为 `Host` 的基类，提供玩家基础能力 |
| **过滤模式** | 自动过滤非团队任务，只发布相关数据 |
| **类型注解** | 使用 `dict[str, Task]` 提供类型提示 |

**设计优点**:
- 简洁明了，职责单一
- 作为基类可被 Host 继承复用
- 类型注解提高代码可读性
- 自动过滤非团队任务

**数据结构**:

```
Player
├── username: str
└── multi_tasks: dict[str, Task]
    ├── "orochi": Task
    ├── "fallen_sun": Task
    ├── "eternity_sea": Task
    └── ...
```

**与其他模块的关系**:

```
┌─────────────────────────────────────┐
│              Host                   │
│   (多重继承 Mqtt + Player)          │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│             Player                  │
│   - username                        │
│   - multi_tasks                     │
│   - publish_data()                  │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│              Task                   │
│   - next_run                        │
│   - role                            │
│   - limit_time                      │
│   - limit_count                     │
└─────────────────────────────────────┘
```

**注意事项**:
- `multi_tasks` 的键是任务名称字符串
- 只有 `team_task=True` 的任务才会被发布
- 所有值在发布时被转换为字符串或整数
- 该类设计为被继承使用，不建议直接实例化
