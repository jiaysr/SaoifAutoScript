# module/team_flow/mqtt.py 逐行代码详解

## 1. 文件概述

本文件实现了基于 MQTT 协议的消息通信模块，用于团队协作中多个玩家之间的广播通信。MQTT 是一种轻量级的发布/订阅消息传输协议，适用于物联网和分布式系统中的低带宽、高延迟网络环境。

**核心功能**：
- 连接 MQTT 代理服务器（支持 SSL/TLS 加密）
- 发布/订阅消息机制
- 多线程消息循环处理
- 策略消息的去重与批量发送优化

**设计意图**：
- 使用 MQTT 做广播通信，避免手动实现复杂的网络广播逻辑
- 所有玩家在更新策略后必须广播给其他玩家
- 新玩家加入时，所有现有玩家需重新广播策略
- 玩家退出时，通过遗嘱消息通知其他玩家

---

## 2. 导入部分解释

```python
from time import sleep
```
- 从标准库 `time` 模块导入 `sleep` 函数
- 用于在程序中暂停执行指定秒数
- 虽然导入但在主代码中未直接使用（主要用于 `__main__` 测试块）

```python
import json
```
- 导入 JSON 序列化/反序列化模块
- 用于将字典数据转换为 JSON 字符串发送，以及解析接收到的 JSON 消息

```python
from random import randint
```
- 从 `random` 模块导入 `randint` 函数
- 用于生成随机整数，此处用于创建唯一的客户端 ID

```python
from paho.mqtt import client as mqtt_client
```
- 从 `paho.mqtt` 库导入 MQTT 客户端模块
- `paho-mqtt` 是 Python 中最流行的 MQTT 客户端库
- 提供连接、发布、订阅等 MQTT 核心功能

```python
from threading import Thread
```
- 从 `threading` 模块导入 `Thread` 类
- 用于创建独立线程运行 MQTT 消息循环
- 避免阻塞主程序执行

```python
from queue import Queue
```
- 从 `queue` 模块导入 `Queue` 类
- 线程安全的 FIFO（先进先出）队列
- 用于缓存待发布的消息

```python
from tasks.GlobalGame.config import TeamFlow, Transport
```
- 从项目配置模块导入 `TeamFlow` 和 `Transport`
- `TeamFlow`：团队通信配置数据类，包含 broker 地址、端口、认证信息等
- `Transport`：传输协议枚举，区分普通 TCP 和 SSL/TLS 连接

```python
from module.logger import logger
```
- 从项目日志模块导入 `logger` 实例
- 用于记录运行时信息、错误和警告

```python
from module.base.timer import Timer
```
- 从项目基础模块导入 `Timer` 类
- 用于实现定时逻辑，此处用于控制策略消息的发送频率

---

## 3. 模块级函数：on_message

```python
def on_message(client, userdata, msg):
    if msg.topic == 'FirstNotice':
        return
    logger.info(f"Received `{msg.payload}` from `{userdata}` ")
```

**功能**：默认的消息接收回调函数

**逐行解析**：
- **第 18 行**：定义函数 `on_message`，接收三个参数
  - `client`：MQTT 客户端实例
  - `userdata`：用户数据（此处为 `Mqtt` 实例）
  - `msg`：接收到的消息对象，包含 `topic`（主题）和 `payload`（内容）
- **第 19-20 行**：忽略 `FirstNotice` 主题的消息
  - 因为这是新玩家加入的通知，现有玩家不需要处理，只需响应该通知
- **第 21 行**：记录接收到的消息日志
  - `msg.payload` 是字节类型，记录消息内容和来源

---

## 4. 类定义：Mqtt

### 4.1 类注释与设计说明

```python
# 使用MQTT是为了做广播，自己手撸的话太麻烦了
# 0. 所有玩家更新自己的策略后必须广播出去, 可以延迟一下
# 1. 当一个玩家启动接入网络后，会向服务器发送FirstNotice，这个时候所有的玩家都要发送一次自己的策略来给新加入的玩家来优化自己的策略
# 2. 当一个玩家退出网络后，会向服务器发送LastNotice，这个时候所有的玩家都要更新自己的策略
```

这段注释说明了 MQTT 通信的三个核心场景：
1. **策略更新广播**：玩家更新策略后广播给所有人
2. **新玩家加入**：新玩家发送 `FirstNotice`，所有现有玩家响应广播策略
3. **玩家退出**：通过遗嘱消息（`LastWill`）通知其他玩家

### 4.2 类属性

```python
class Mqtt:
    q_publish: Queue = None
```
- **第 28 行**：定义 `Mqtt` 类
- **第 30 行**：定义类属性 `q_publish`，类型注解为 `Queue`，默认值为 `None`
  - 实际在 `__init__` 中初始化为 `Queue()` 实例
  - 用于缓存待发布的消息

---

### 4.3 构造函数 `__init__`

```python
def __init__(self, team_flow: TeamFlow):
```
- **第 32 行**：构造函数接收一个 `TeamFlow` 配置对象

#### 4.3.1 内部函数 on_connect

```python
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT Broker!")
    elif rc == 1:
        logger.error(f"Connection refused - incorrect protocol version. return code: {rc}")
    elif rc == 2:
        logger.error(f"Connection refused - invalid client identifier. return code: {rc}")
    elif rc == 3:
        logger.error(f"Connection refused - server unavailable. return code: {rc}")
    elif rc == 4:
        logger.error(f"Connection refused - bad username or password. return code: {rc}")
    elif rc == 5:
        logger.error(f"Connection refused - not authorised. return code: {rc}")
    else:
        logger.info("Failed to connect, return code %d\n", rc)
```

**功能**：连接结果回调函数，定义在构造函数内部

**逐行解析**：
- **第 33 行**：定义连接回调，`rc` 是返回码（return code）
- **第 34-35 行**：`rc == 0` 表示连接成功
- **第 36-37 行**：`rc == 1` 协议版本错误
- **第 38-39 行**：`rc == 2` 客户端标识符无效
- **第 40-41 行**：`rc == 3` 服务器不可用
- **第 42-43 行**：`rc == 4` 用户名或密码错误
- **第 44-45 行**：`rc == 5` 未授权
- **第 46-47 行**：其他未知错误码

#### 4.3.2 初始化实例属性

```python
self.q_publish = Queue()
```
- **第 53 行**：初始化消息发布队列

```python
self.broker = team_flow.broker
```
- **第 54 行**：从配置中读取 MQTT 代理服务器地址

```python
self.port = team_flow.port
```
- **第 55 行**：从配置中读取端口号

```python
self.protocol = team_flow.transport
```
- **第 56 行**：从配置中读取传输协议类型

```python
self.ca = team_flow.ca
```
- **第 57 行**：从配置中读取 CA 证书路径（用于 SSL/TLS）

```python
self.username = team_flow.username
```
- **第 58 行**：从配置中读取用户名

```python
self.password = team_flow.password
```
- **第 59 行**：从配置中读取密码

```python
self.client_id = f'{self.username}-{randint(0, 1000)}'
```
- **第 60 行**：生成唯一客户端 ID
  - 格式：`用户名-随机数`
  - 随机数范围 0-1000，避免多实例时 ID 冲突

#### 4.3.3 创建并配置 MQTT 客户端

```python
self.client = mqtt_client.Client(self.client_id, clean_session=True, userdata=self)
```
- **第 62 行**：创建 MQTT 客户端实例
  - `self.client_id`：唯一标识符
  - `clean_session=True`：每次连接清理会话，不保留之前的订阅和消息
  - `userdata=self`：将当前 `Mqtt` 实例作为用户数据传递给回调函数

```python
if self.protocol == Transport.SSL_TLS:
    self.client.tls_set(ca_certs=self.ca)
```
- **第 63-64 行**：如果使用 SSL/TLS 协议，设置 CA 证书
  - `tls_set()` 方法配置 TLS 加密连接
  - `ca_certs` 参数指定 CA 证书文件路径

```python
self.client.username_pw_set(self.username, self.password)
```
- **第 65 行**：设置认证的用户名和密码

```python
self.client.on_connect = on_connect
```
- **第 66 行**：绑定连接回调函数

```python
self.client.on_message = on_message
```
- **第 67 行**：绑定默认消息接收回调函数

#### 4.3.4 设置遗嘱消息

```python
self.client.will_set(topic='LastWill', payload=json.dumps({self.username: ""}), qos=2)
```
- **第 68 行**：设置遗嘱消息（Last Will and Testament）
  - **作用**：当客户端异常断开时，代理服务器会自动发布此消息
  - `topic='LastWill'`：遗嘱消息主题
  - `payload=json.dumps({self.username: ""})`：消息内容，包含用户名的 JSON
  - `qos=2`：服务质量等级 2，确保消息恰好到达一次

#### 4.3.5 连接服务器并订阅主题

```python
self.client.connect(self.broker, self.port)
```
- **第 69 行**：连接到 MQTT 代理服务器

```python
self.client.subscribe(topic='FirstNotice', qos=2)
self.client.subscribe(topic='LastWill', qos=2)
self.client.subscribe(topic='TaskStart', qos=0)
self.client.subscribe(topic='Strategy', qos=0)
```
- **第 71-74 行**：订阅四个主题
  - `FirstNotice`（qos=2）：新玩家加入通知
  - `LastWill`（qos=2）：玩家退出通知
  - `TaskStart`（qos=0）：任务启动通知
  - `Strategy`（qos=0）：策略更新通知
- QoS 等级说明：
  - 0：最多一次，可能丢失
  - 1：至少一次，可能重复
  - 2：恰好一次，最可靠但最慢

#### 4.3.6 发布加入通知并启动消息循环线程

```python
self.publish("FirstNotice", {"type": "join"})
```
- **第 76 行**：发布 `FirstNotice` 消息，通知所有现有玩家有新成员加入

```python
self.mqtt_timer = Timer(30)
self.mqtt_timer.start()
```
- **第 78-79 行**：创建并启动 30 秒定时器
  - 用于控制消息循环中策略消息的发送频率

```python
self.mqtt_thread = Thread(target=self.mqtt_loop, name='mqtt_loop', daemon=True)
self.mqtt_thread.start()
```
- **第 80-81 行**：创建并启动守护线程
  - `target=self.mqtt_loop`：线程执行的函数
  - `name='mqtt_loop'`：线程名称
  - `daemon=True`：守护线程，主程序退出时自动终止

---

### 4.4 方法：set_on_message

```python
def set_on_message(self, on_msg):
    self.client.on_message = on_msg
```

**功能**：替换消息接收回调函数

**逐行解析**：
- **第 85 行**：定义方法，接收新的回调函数 `on_msg`
- **第 86 行**：替换客户端的消息回调
- **用途**：允许在运行时动态更改消息处理逻辑

---

### 4.5 方法：publish

```python
def publish(self, topic: str, msg: dict) -> bool:
    if not isinstance(msg, dict):
        logger.warning(f"Msg must be a dict, but got {type(msg)}")
        return False
    msg = {self.username: msg}
    result = self.client.publish(topic, json.dumps(msg))
    status = result[0]
    if status == 0:
        logger.info(f"Send `msg` to topic `{topic}`")
        return True
    else:
        logger.info(f"Failed to send message to topic {topic} {status}")
        return False
```

**功能**：发布消息到指定主题

**逐行解析**：
- **第 88 行**：定义发布方法，参数为主题和消息字典，返回布尔值
- **第 95-97 行**：类型检查，确保消息是字典类型
- **第 98 行**：将消息包装为 `{用户名: 消息}` 格式
  - 这样接收方可以识别消息来源
- **第 99 行**：调用客户端的 `publish` 方法发送消息
  - `json.dumps(msg)` 将字典序列化为 JSON 字符串
- **第 100-101 行**：获取发送结果状态码
  - `result` 是一个元组 `[status, mid]`
  - `status == 0` 表示发送成功
- **第 102-107 行**：根据状态码记录日志并返回结果

---

### 4.6 方法：TaskStart 和 Strategy

```python
def TaskStart(self, msg):
    self.publish('TaskStart', msg)

def Strategy(self, msg):
    self.publish('Strategy', msg)
```

**功能**：便捷方法，分别发布任务启动和策略更新消息

**逐行解析**：
- **第 109-110 行**：`TaskStart` 方法，发布到 `TaskStart` 主题
- **第 112-113 行**：`Strategy` 方法，发布到 `Strategy` 主题
- 这两个方法是 `publish` 的语法糖，简化特定主题的消息发布

---

### 4.7 方法：mqtt_loop（核心消息循环）

```python
def mqtt_loop(self):
    while True:
        try:
            self.client.loop(timeout=5)
        except Exception as e:
            logger.error(e)

        if not self.mqtt_timer.reached():
            continue
        self.mqtt_timer.reset()
        publish_strategy_msg = None
        while not self.q_publish.empty():
            try:
                topic, msg = self.q_publish.get(block=False)
            except Exception as e:
                continue
            if topic == 'Strategy':
                publish_strategy_msg = msg
                continue
            self.publish(topic, msg)
        if publish_strategy_msg:
            self.publish('Strategy', publish_strategy_msg)
```

**功能**：主消息循环，在独立线程中运行

**逐行解析**：
- **第 115 行**：定义消息循环方法
- **第 116 行**：无限循环，持续运行直到程序退出

**网络消息处理**：
- **第 119-122 行**：调用客户端的 `loop` 方法处理网络消息
  - `timeout=5`：最多等待 5 秒
  - 使用 `try-except` 捕获并记录异常，避免线程崩溃

**定时器检查**：
- **第 124-125 行**：检查 30 秒定时器是否到达
  - 如果未到达，跳过队列处理，继续下一次循环
  - 这限制了策略消息最多每 30 秒发送一次
- **第 126 行**：重置定时器

**队列消息处理**：
- **第 127 行**：初始化策略消息变量为 `None`
- **第 128 行**：循环处理队列中的所有消息
- **第 129-132 行**：非阻塞方式从队列获取消息
  - `block=False`：队列为空时立即抛出异常
- **第 133-135 行**：如果主题是 `Strategy`，保存最新消息但不立即发送
  - 这样做是为了去重，只发送最新的策略
- **第 136 行**：非策略消息立即发送

**策略消息发送**：
- **第 137-139 行**：如果存在策略消息，发送最新的一个
  - 这是去重优化：队列中可能有多个策略更新，只发送最新的

---

## 5. 核心算法流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                     Mqtt 类初始化流程                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  读取配置信息     │
                    │  (broker/port/  │
                    │   认证信息等)    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  生成客户端ID    │
                    │  username-rand  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  创建MQTT客户端  │
                    └────────┬────────┘
                             │
                             ▼
                   ┌─────────────────────┐
                   │  是否使用SSL/TLS？   │
                   └──────┬──────┬───────┘
                          │      │
                    Yes   │      │   No
                          ▼      ▼
               ┌──────────────┐  │
               │  设置CA证书   │  │
               └──────┬───────┘  │
                      │          │
                      ▼          ▼
                    ┌─────────────────┐
                    │  设置用户名密码  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  设置遗嘱消息    │
                    │  (LastWill)     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  连接服务器      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  订阅4个主题     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  发布加入通知    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  启动消息循环线程│
                    └─────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                     mqtt_loop 消息循环流程                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  处理网络消息    │◄──────────┐
                    │  (loop 5秒)     │           │
                    └────────┬────────┘           │
                             │                    │
                             ▼                    │
                    ┌─────────────────┐           │
                    │  检查30秒定时器  │           │
                    └──────┬──────┬───┘           │
                           │      │               │
                 未到达    │      │   到达         │
                           ▼      ▼               │
                    ┌────────┐  ┌─────────────┐   │
                    │continue│  │ 重置定时器   │   │
                    └────────┘  └──────┬──────┘   │
                                       │          │
                                       ▼          │
                              ┌─────────────────┐ │
                              │  遍历消息队列    │ │
                              └──────┬──────┬───┘ │
                                     │      │     │
                           策略消息  │      │ 其他消息
                                     ▼      ▼     │
                            ┌──────────┐ ┌──────┐ │
                            │ 保存最新 │ │立即  │ │
                            │ 策略消息 │ │发送  │ │
                            └────┬─────┘ └──────┘ │
                                 │                │
                                 ▼                │
                          ┌─────────────┐         │
                          │ 发送最新策略 │         │
                          └──────┬──────┘         │
                                 │                │
                                 └────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                     消息发布流程                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  接收topic和msg  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  msg是字典？     │
                    └──────┬──────┬───┘
                           │      │
                     No    │      │   Yes
                           ▼      ▼
                    ┌────────┐  ┌─────────────────┐
                    │ return │  │ 包装为           │
                    │ False  │  │ {username: msg}  │
                    └────────┘  └────────┬────────┘
                                         │
                                         ▼
                                ┌─────────────────┐
                                │  序列化为JSON    │
                                │  并发布          │
                                └────────┬────────┘
                                         │
                                         ▼
                                ┌─────────────────┐
                                │  检查发送状态    │
                                └──────┬──────┬───┘
                                       │      │
                                成功   │      │  失败
                                       ▼      ▼
                                ┌────────┐ ┌────────┐
                                │ return │ │ return │
                                │ True   │ │ False  │
                                └────────┘ └────────┘
```

---

## 6. 使用示例

### 6.1 基本使用

```python
from tasks.GlobalGame.config import TeamFlow, Transport
from module.team_flow.mqtt import Mqtt

# 创建配置
team_flow = TeamFlow()
team_flow.broker = 'mqtt.example.com'
team_flow.port = 8883
team_flow.transport = Transport.SSL_TLS
team_flow.ca = './config/ca.crt'
team_flow.username = 'player1'
team_flow.password = 'password123'

# 创建 MQTT 客户端
mqtt = Mqtt(team_flow)

# 发布策略更新
mqtt.Strategy({
    "action": "attack",
    "target": "boss",
    "priority": 1
})

# 发布任务启动
mqtt.TaskStart({
    "task_id": "dungeon_001",
    "difficulty": "hard"
})
```

### 6.2 自定义消息处理

```python
def custom_on_message(client, userdata, msg):
    """自定义消息处理函数"""
    import json
    payload = json.loads(msg.payload)
    
    if msg.topic == 'Strategy':
        # 处理策略更新
        for username, strategy in payload.items():
            print(f"玩家 {username} 更新策略: {strategy}")
    
    elif msg.topic == 'TaskStart':
        # 处理任务启动
        for username, task_info in payload.items():
            print(f"玩家 {username} 启动任务: {task_info}")
    
    elif msg.topic == 'LastWill':
        # 处理玩家退出
        for username in payload:
            print(f"玩家 {username} 已退出")

# 替换默认消息处理
mqtt.set_on_message(custom_on_message)
```

### 6.3 多玩家协作场景

```python
from time import sleep
from module.team_flow.mqtt import Mqtt
from tasks.GlobalGame.config import TeamFlow, Transport

def create_player(username, password):
    """创建一个玩家客户端"""
    config = TeamFlow()
    config.broker = 'mqtt.example.com'
    config.port = 8883
    config.transport = Transport.SSL_TLS
    config.ca = './config/ca.crt'
    config.username = username
    config.password = password
    return Mqtt(config)

# 创建三个玩家
leader = create_player('leader', 'pass1')
member1 = create_player('member1', 'pass2')
member2 = create_player('member2', 'pass3')

# 队长发布任务
leader.TaskStart({
    "task": "raid_boss",
    "members": ["leader", "member1", "member2"]
})

sleep(2)

# 成员发布策略
member1.Strategy({
    "role": "tank",
    "position": "front"
})

member2.Strategy({
    "role": "healer",
    "position": "back"
})
```

---

## 7. 设计模式总结

### 7.1 发布-订阅模式（Pub/Sub）

本模块是发布-订阅模式的典型实现：

- **发布者（Publisher）**：`Mqtt` 实例通过 `publish()` 方法发送消息
- **订阅者（Subscriber）**：`Mqtt` 实例通过 `subscribe()` 订阅主题
- **代理（Broker）**：MQTT 服务器负责消息路由
- **主题（Topic）**：`FirstNotice`、`LastWill`、`TaskStart`、`Strategy`

**优势**：
- 发布者和订阅者解耦
- 支持一对多广播
- 动态添加/移除参与者

### 7.2 生产者-消费者模式

消息队列 `q_publish` 实现了生产者-消费者模式：

- **生产者**：外部调用 `publish()` 方法将消息放入队列
- **消费者**：`mqtt_loop` 线程从队列取出消息并发送
- **缓冲**：队列起到缓冲作用，平衡生产消费速度

### 7.3 观察者模式

通过回调函数实现观察者模式：

- `on_connect`：连接状态变化时通知
- `on_message`：接收到消息时通知
- `set_on_message()`：允许动态添加观察者

### 7.4 守护线程模式

```python
self.mqtt_thread = Thread(target=self.mqtt_loop, daemon=True)
```

- 使用守护线程运行后台任务
- 主程序退出时自动清理
- 避免程序无法正常退出

### 7.5 遗嘱消息模式（Last Will）

```python
self.client.will_set(topic='LastWill', payload=..., qos=2)
```

- 客户端异常断开时自动通知其他参与者
- 实现优雅的故障检测
- QoS=2 确保消息可靠传递

### 7.6 消息去重优化

```python
if topic == 'Strategy':
    publish_strategy_msg = msg
    continue
# ...
if publish_strategy_msg:
    self.publish('Strategy', publish_strategy_msg)
```

- 策略消息只保留最新的一条
- 避免短时间内发送大量重复策略
- 30 秒定时器进一步限制发送频率

### 7.7 线程安全设计

- 使用 `Queue` 实现线程安全的消息传递
- 消息发布在独立线程中执行
- 回调函数在 MQTT 客户端线程中执行
- 通过队列解耦不同线程的访问

---

## 附录：MQTT QoS 等级说明

| QoS 等级 | 名称 | 说明 | 使用场景 |
|---------|------|------|---------|
| 0 | 最多一次 | 消息可能丢失，不重试 | TaskStart、Strategy（实时性要求高） |
| 1 | 至少一次 | 消息可能重复 | 不常用 |
| 2 | 恰好一次 | 保证消息到达且不重复 | FirstNotice、LastWill（关键通知） |
