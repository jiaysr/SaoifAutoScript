# module/team_flow/host.py 代码详解

## 1. 文件概述

`host.py` 是团队流程的主控端模块，实现了多人协作任务的协调管理功能。通过 MQTT 协议实现多玩家之间的通信，管理团队任务的调度、策略发布和状态同步。

**文件路径**: `module/team_flow/host.py`
**代码行数**: 171 行
**主要功能**:
- 多人任务协调管理
- MQTT 消息订阅和发布
- 玩家上下线处理
- 策略同步和更新
- 配置与任务数据的双向转换

---

## 2. 导入部分解释

```python
import json
from time import sleep
from datetime import datetime, time
from cached_property import cached_property
from tasks.GlobalGame.config import TeamFlow, Transport
from module.team_flow.mqtt import Mqtt
from module.config.config import Config
from module.team_flow.player import Player
from module.team_flow.task import Task
from module.logger import logger
```

| 导入项 | 来源模块 | 说明 |
|--------|----------|------|
| `json` | Python标准库 | JSON 数据序列化 |
| `sleep` | time | 线程休眠 |
| `datetime`, `time` | datetime | 日期时间处理 |
| `cached_property` | cached_property | 缓存属性装饰器 |
| `TeamFlow`, `Transport` | tasks.GlobalGame.config | 团队流程配置类 |
| `Mqtt` | module.team_flow.mqtt | MQTT 通信基类 |
| `Config` | module.config.config | 项目配置类 |
| `Player` | module.team_flow.player | 玩家基类 |
| `Task` | module.team_flow.task | 任务类 |
| `logger` | module.logger | 日志记录器 |

---

## 3. 类定义解释

### 模块级函数 on_message

```python
def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload)
    except json.JSONDecodeError:
        logger.error(f'Get [{msg.topic}]: {msg.payload}')
        return
    logger.info(f'Get {msg.topic}: {data}')
    for username, data in data.items():
        if username == userdata.username:
            continue
        userdata.match_topic[msg.topic](username, data)
```

**功能**: MQTT 消息接收回调函数

| 行号 | 代码 | 说明 |
|------|------|------|
| 18-20 | `json.loads(msg.payload)` | 解析 JSON 消息 |
| 21-22 | 异常处理 | JSON 解析失败记录错误日志 |
| 23 | `logger.info(...)` | 记录接收到的消息 |
| 24-28 | 遍历消息分发 | 跳过自己，调用对应主题的处理函数 |

### Host 类

```python
class Host(Mqtt, Player):
    def __init__(self, config: Config):
        Player.__init__(self, config.global_game.team_flow.username)
        Mqtt.__init__(self, config.global_game.team_flow)
        self.config = config
        self.players: list[Player] = []
        self.set_on_message(on_message)
```

**继承关系**: `Host` → `Mqtt`, `Player`（多重继承）

**核心属性**:
- `config`: 项目配置对象
- `players`: 在线玩家列表
- `match_topic`: 主题到处理函数的映射字典

---

## 4. 每个方法的逐行解释

### `__init__` 方法

```python
def __init__(self, config: Config):
    Player.__init__(self, config.global_game.team_flow.username)
    Mqtt.__init__(self, config.global_game.team_flow)
    self.config = config
    self.players: list[Player] = []
    self.set_on_message(on_message)
```

| 行号 | 代码 | 说明 |
|------|------|------|
| 33 | `Player.__init__(...)` | 初始化 Player 基类，设置用户名 |
| 34 | `Mqtt.__init__(...)` | 初始化 Mqtt 基类，建立 MQTT 连接 |
| 35 | `self.config = config` | 存储配置对象 |
| 36 | `self.players = []` | 初始化在线玩家列表 |
| 37 | `self.set_on_message(on_message)` | 设置消息回调函数 |

### `match_topic` 属性

```python
@cached_property
def match_topic(self):
    return {
        'FirstNotice': self.on_first_notice,
        'LastWill': self.on_last_will,
        'TaskStart': self.on_task_start,
        'Strategy': self.on_strategy
    }
```

**功能**: 创建主题到处理函数的映射表，使用 `@cached_property` 缓存结果。

| 主题 | 处理函数 | 说明 |
|------|----------|------|
| `FirstNotice` | `on_first_notice` | 玩家上线通知 |
| `LastWill` | `on_last_will` | 玩家下线通知 |
| `TaskStart` | `on_task_start` | 任务开始通知 |
| `Strategy` | `on_strategy` | 策略更新通知 |

### `on_first_notice` 方法

```python
def on_first_notice(self, player: str, data: dict):
    if 'type' in data:
        logger.info(f'Player {player} is online')
        self.q_publish.put(['Strategy', self.publish_data()])
    else:
        pass
```

**功能**: 处理玩家上线通知

| 行号 | 代码 | 说明 |
|------|------|------|
| 50 | `if 'type' in data:` | 检查是否为上线类型消息 |
| 51 | `logger.info(...)` | 记录玩家上线日志 |
| 52 | `self.q_publish.put(...)` | 将自己的策略发布出去，让新玩家获取 |
| 54-55 | `else: pass` | 其他类型消息暂不处理 |

### `on_last_will` 方法

```python
def on_last_will(self, player: str, data: dict):
    if player not in self.players:
        logger.warning(f'Player {player} is not in players')
        return
    self.players.remove(player)
    logger.info(f'Player {player} is offline')
    self._config_to_player()
    self._update_strategy()
    self._player_to_config()
    self.q_publish.put(['Strategy', self.publish_data()])
```

**功能**: 处理玩家下线通知

| 行号 | 代码 | 说明 |
|------|------|------|
| 58-60 | 检查玩家是否存在 | 不存在则警告并返回 |
| 61 | `self.players.remove(player)` | 从在线列表移除 |
| 62 | `logger.info(...)` | 记录玩家下线日志 |
| 63 | `self._config_to_player()` | 从配置更新任务缓存 |
| 64 | `self._update_strategy()` | 更新策略 |
| 65 | `self._player_to_config()` | 将任务缓存写回配置 |
| 66 | `self.q_publish.put(...)` | 广播更新后的策略 |

### `on_task_start` 和 `on_strategy` 方法

```python
def on_task_start(self, player: str, data: dict):
    pass

def on_strategy(self, player: str, data: dict):
    pass
```

**功能**: 预留的处理函数，当前未实现。

### `_config_to_player` 方法

```python
def _config_to_player(self):
    tasks = {'orochi': self.config.model.orochi,
             'fallen_sun': self.config.model.fallen_sun,
             'eternity_sea': self.config.model.eternity_sea,
             'evo_zone': self.config.model.evo_zone,
             'exploration': self.config.model.exploration
             }
    for key, value in tasks.items():
        task_name: str = key
        limit_time: time = None
        limit_count: int = None
        role: str = None
        if key == 'orochi':
            limit_time = value.orochi_config.limit_time
            limit_count = value.orochi_config.limit_count
            role = str(value.orochi_config.user_status)
        # ... 其他任务类似
        if not value.scheduler.enable:
            continue
        if task_name not in self.multi_tasks:
            self.multi_tasks[task_name] = Task(
                next_run=value.scheduler.next_run,
                target_run=value.scheduler.next_run,
                limit_time=limit_time,
                team_task=True,
                role=role,
                limit_count=limit_count,
            )
        else:
            self.multi_tasks[task_name].update_info(
                next_run=value.scheduler.next_run,
                limit_time=limit_time,
                role=role,
                limit_count=limit_count
            )
```

**功能**: 将配置数据转换为任务缓存

| 行号 | 代码 | 说明 |
|------|------|------|
| 80-85 | `tasks = {...}` | 定义任务配置映射 |
| 86-114 | 遍历任务配置 | 提取每个任务的时间、次数、角色等配置 |
| 115-116 | 检查任务是否启用 | 未启用则跳过 |
| 117-127 | 新任务创建 | 首次出现的任务创建 Task 对象 |
| 128-134 | 任务更新 | 已存在的任务更新配置信息 |

### `_player_to_config` 方法

```python
def _player_to_config(self):
    for key, value in self.multi_tasks.items():
        if key == 'orochi':
            self.config.task_delay(task='Orochi', target=value.next_run)
        elif key == 'fallen_sun':
            self.config.task_delay(task='FallenSun', target=value.next_run)
        # ... 其他任务类似
```

**功能**: 将任务缓存写回配置

| 行号 | 代码 | 说明 |
|------|------|------|
| 137 | 遍历任务缓存 | 获取每个任务的配置 |
| 138-150 | 任务映射 | 将内部任务名映射为配置任务名 |
| 139 | `self.config.task_delay(...)` | 更新配置中的任务延迟时间 |

### `_update_strategy` 方法

```python
def _update_strategy(self):
    pass
```

**功能**: 预留的策略更新方法，当前未实现。

---

## 5. 核心算法流程图

### Host 初始化流程

```
┌─────────────────────────────────────┐
│          Host.__init__              │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   Player.__init__(username)         │
│   初始化玩家基类                      │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   Mqtt.__init__(team_flow)          │
│   建立 MQTT 连接                     │
│   订阅主题                           │
│   启动消息循环线程                    │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   set_on_message(on_message)        │
│   设置消息回调函数                    │
└─────────────────────────────────────┘
```

### 消息处理流程

```
┌─────────────────────────────────────┐
│      MQTT 消息到达                   │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│      on_message 回调                 │
│      json.loads(msg.payload)        │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   遍历消息中的玩家数据               │
│   for username, data in data.items()│
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   跳过自己 (username == self)       │
│   调用 match_topic[msg.topic]       │
└─────────────────┬───────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
┌───────────────┐   ┌───────────────┐
│ FirstNotice   │   │ LastWill      │
│ 玩家上线      │   │ 玩家下线      │
│ → 广播策略    │   │ → 更新策略    │
└───────────────┘   └───────────────┘
```

### 玩家下线处理流程

```
┌─────────────────────────────────────┐
│      on_last_will                   │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   检查玩家是否在列表中               │
│   not in players → return           │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   players.remove(player)            │
│   移除下线玩家                       │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   _config_to_player()               │
│   配置 → 任务缓存                    │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   _update_strategy()                │
│   更新策略                           │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   _player_to_config()               │
│   任务缓存 → 配置                    │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   q_publish.put(['Strategy', ...])  │
│   广播更新后的策略                    │
└─────────────────────────────────────┘
```

### 配置与任务缓存同步流程

```
┌─────────────────────────────────────────────────────┐
│              配置与任务缓存双向同步                   │
└───────────────────────────┬─────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        ▼                                       ▼
┌───────────────────┐                   ┌───────────────────┐
│ _config_to_player │                   │ _player_to_config │
│ 配置 → 缓存       │                   │ 缓存 → 配置       │
└─────────┬─────────┘                   └─────────┬─────────┘
          │                                       │
          ▼                                       ▼
┌───────────────────┐                   ┌───────────────────┐
│ 遍历任务配置      │                   │ 遍历任务缓存      │
│ 提取时间/次数/角色 │                   │ 映射任务名称      │
└─────────┬─────────┘                   └─────────┬─────────┘
          │                                       │
          ▼                                       ▼
┌───────────────────┐                   ┌───────────────────┐
│ 新任务: 创建 Task │                   │ task_delay()      │
│ 旧任务: 更新信息  │                   │ 更新配置延迟时间  │
└───────────────────┘                   └───────────────────┘
```

---

## 6. 使用示例

### 基本使用

```python
from module.config.config import Config
from module.team_flow.host import Host

# 创建配置
config = Config('oas1')

# 创建 Host 实例
host = Host(config)

# 等待其他玩家上线
from time import sleep
sleep(30)

# 更新配置到任务缓存
host._config_to_player()

# 发布策略
host.q_publish.put(['Strategy', host.publish_data()])
```

### 多人协作场景

```python
# 玩家 A 作为 Host
host_a = Host(config_a)

# 玩家 B 作为普通玩家（通过 Mqtt 连接）
# 当 B 上线时，会发送 FirstNotice
# Host A 收到后会广播自己的策略
# B 收到策略后可以优化自己的任务安排
```

### 配置与任务同步

```python
# 从配置更新到任务缓存
host._config_to_player()

# 更新策略
host._update_strategy()

# 从任务缓存写回配置
host._player_to_config()

# 发布更新后的策略
host.q_publish.put(['Strategy', host.publish_data()])
```

### 主题消息处理

```python
# 主题处理函数映射
match_topic = {
    'FirstNotice': host.on_first_notice,  # 玩家上线
    'LastWill': host.on_last_will,        # 玩家下线
    'TaskStart': host.on_task_start,      # 任务开始
    'Strategy': host.on_strategy          # 策略更新
}
```

---

## 7. 设计模式总结

| 设计模式 | 应用说明 |
|----------|----------|
| **观察者模式** | 通过 MQTT 实现发布-订阅机制 |
| **中介者模式** | Host 作为玩家之间的协调中介 |
| **多重继承** | 同时继承 Mqtt 和 Player，组合两者能力 |
| **缓存模式** | 使用 `@cached_property` 缓存主题映射 |
| **队列模式** | 使用 `q_publish` 队列异步处理消息发布 |

**设计优点**:
- 通过 MQTT 实现松耦合的多人协作
- 主题映射机制便于扩展新的消息类型
- 配置与任务缓存双向同步，保持数据一致性
- 异步消息队列避免阻塞主线程

**MQTT 主题设计**:

| 主题 | QoS | 说明 |
|------|-----|------|
| `FirstNotice` | 2 | 玩家上线通知（确保送达） |
| `LastWill` | 2 | 玩家下线通知（遗嘱消息） |
| `TaskStart` | 0 | 任务开始通知（可丢失） |
| `Strategy` | 0 | 策略更新通知（可丢失） |

**待完成功能**:
- `on_task_start` 任务开始处理
- `on_strategy` 策略更新处理
- `_update_strategy` 策略更新逻辑
- 探索任务的完整支持

**适用场景**:
- 多人协作自动化任务
- 团队任务调度和协调
- 分布式任务执行
