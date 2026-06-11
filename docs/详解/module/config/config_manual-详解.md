# config_manual.py 代码详解

## 1. 文件概述

`config_manual.py` 定义了 `ConfigManual` 类，包含手动配置的常量和静态参数。这些参数通常是固定的，不需要用户频繁修改，但在系统初始化时需要读取。

**主要职责：**
- 定义任务调度优先级规则
- 配置设备连接参数
- 存储文件路径常量

## 2. 导入部分解释

```python
# 本文件没有导入任何外部模块
# 所有配置都是静态常量，不依赖外部库
```

## 3. 类定义解释

### 3.1 ConfigManual 类

```python
class ConfigManual:
    """
    module.device
    """
```

这个类包含了所有手动配置的常量，主要用于设备连接和任务调度。

## 4. 每个方法的逐行解释

### 4.1 SCHEDULER_PRIORITY 常量

```python
SCHEDULER_PRIORITY = """
    Restart > SoulsTidy
    > KekkaiUtilize > KekkaiActivation > DemonEncounter
    > AreaBoss > GoldYoukai > ExperienceYoukai > Nian > Tako > AutoCheckinBigGod > RealmRaid > RyouToppa > DailyTrifles > Exploration
    > Dokan > AbyssShadows > Hunt > GuildBanquet > DemonRetreat > GuildActivityMonitor
    > Orochi > OrochiMoans > OrochiJudgement > Sougenbi > FallenSun > EternitySea > SixRealms
    > ActivityShikigami > WantedQuests
    > BondlingFairyland > EvoZone > GoryouRealm > HeroTest
    > CollectiveMissionsr
    > Pets > TalismanPass > Delegation > Hyakkiyakou
    > Secret > WeeklyTrifles > MysteryShop > Duel 
    > TrueOrochi > RichMan
    > MetaDemon > FrogBoss > FloatParade > Quiz > KittyShop > DyeTrials > MemoryScrolls
    """
```

**优先级说明：**
- 使用 `>` 符号分隔优先级层级
- 越靠前的任务优先级越高
- `Restart` 具有最高优先级，确保系统重启任务优先执行
- `SoulsTidy` 次之，用于清理御魂
- 日常任务（AreaBoss、GoldYoukai 等）具有中等优先级
- 活动任务（MetaDemon、FrogBoss 等）优先级较低

**优先级层级：**
```
Level 1: Restart
Level 2: SoulsTidy
Level 3: KekkaiUtilize, KekkaiActivation, DemonEncounter
Level 4: AreaBoss, GoldYoukai, ExperienceYoukai, Nian, Tako, AutoCheckinBigGod, RealmRaid, RyouToppa, DailyTrifles, Exploration
Level 5: Dokan, AbyssShadows, Hunt, GuildBanquet, DemonRetreat, GuildActivityMonitor
Level 6: Orochi, OrochiMoans, OrochiJudgement, Sougenbi, FallenSun, EternitySea, SixRealms
Level 7: ActivityShikigami, WantedQuests
Level 8: BondlingFairyland, EvoZone, GoryouRealm, HeroTest
Level 9: CollectiveMissions
Level 10: Pets, TalismanPass, Delegation, Hyakkiyakou
Level 11: Secret, WeeklyTrifles, MysteryShop, Duel
Level 12: TrueOrochi, RichMan
Level 13: MetaDemon, FrogBoss, FloatParade, Quiz, KittyShop, DyeTrials, MemoryScrolls
```

### 4.2 设备连接配置

```python
DEVICE_OVER_HTTP = False           # 是否通过 HTTP 连接设备
FORWARD_PORT_RANGE = (20000, 21000)  # 端口转发范围
REVERSE_SERVER_PORT = 7903         # 反向服务器端口
```

**配置说明：**
- `DEVICE_OVER_HTTP`: 设为 True 时使用 HTTP 连接，适用于远程设备
- `FORWARD_PORT_RANGE`: ADB 端口转发的端口范围
- `REVERSE_SERVER_PORT`: 反向代理服务器的端口号

### 4.3 DroidCast 配置

```python
DROIDCAST_VERSION = 'DroidCast'  # DroidCast 版本
DROIDCAST_FILEPATH_LOCAL = './bin/droidcast/DroidCast_raw-release-1.0.apk'  # 本地 APK 路径
DROIDCAST_FILEPATH_REMOTE = '/data/local/tmp/DroidCast_raw.apk'  # 设备端路径
```

**DroidCast 说明：**
- 用于 Android 设备屏幕截图
- `DroidCast` 和 `DroidCast_raw` 是两种不同的版本
- 本地路径指向 APK 安装包
- 远程路径是设备上的安装位置

### 4.4 其他设备配置

```python
MINITOUCH_FILEPATH_REMOTE = '/data/local/tmp/minitouch'  # minitouch 设备端路径
HERMIT_FILEPATH_LOCAL = './bin/hermit/hermit.apk'        # Hermit 本地 APK 路径
```

**minitouch：** 用于模拟触摸操作的工具
**Hermit：** 另一种设备控制工具

## 5. 核心算法流程图

### 5.1 优先级调度流程

```
┌─────────────────────────────────────────────────────────────┐
│                   优先级调度流程                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 解析 SCHEDULER_PRIORITY 字符串                           │
│     │                                                        │
│     ▼                                                        │
│  2. 构建优先级映射表                                          │
│     {                                                        │
│       "Restart": 1,                                          │
│       "SoulsTidy": 2,                                        │
│       "KekkaiUtilize": 3,                                    │
│       ...                                                    │
│     }                                                        │
│     │                                                        │
│     ▼                                                        │
│  3. 对 pending_task 按优先级排序                              │
│     │                                                        │
│     ▼                                                        │
│  4. 返回排序后的任务列表                                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘

示例：
输入: [AreaBoss, Restart, Orochi]
输出: [Restart, AreaBoss, Orochi]
      (Restart 优先级最高)
```

### 5.2 设备连接流程

```
┌─────────────────────────────────────────────────────────────┐
│                   设备连接流程                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 检查 DEVICE_OVER_HTTP 配置                               │
│     ├─ True ──→ HTTP 连接模式                                │
│     └─ False ──→ ADB 连接模式                                │
│                                                              │
│  2. ADB 连接模式                                             │
│     ├─ 使用 FORWARD_PORT_RANGE 进行端口转发                   │
│     └─ 使用 REVERSE_SERVER_PORT 建立反向连接                  │
│                                                              │
│  3. 安装必要的工具                                            │
│     ├─ DroidCast: 屏幕截图                                   │
│     ├─ minitouch: 触摸模拟                                   │
│     └─ Hermit: 设备控制                                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 6. 使用示例

```python
from module.config.config_manual import ConfigManual

# 访问调度优先级
priority_str = ConfigManual.SCHEDULER_PRIORITY
print(f"调度优先级:\n{priority_str}")

# 获取设备配置
http_mode = ConfigManual.DEVICE_OVER_HTTP
port_range = ConfigManager.FORWARD_PORT_RANGE
reverse_port = ConfigManual.REVERSE_SERVER_PORT

print(f"HTTP 模式: {http_mode}")
print(f"端口范围: {port_range}")
print(f"反向端口: {reverse_port}")

# 获取 DroidCast 配置
droidcast_version = ConfigManual.DROIDCAST_VERSION
local_path = ConfigManual.DROIDCAST_FILEPATH_LOCAL
remote_path = ConfigManual.DROIDCAST_FILEPATH_REMOTE

print(f"DroidCast 版本: {droidcast_version}")
print(f"本地路径: {local_path}")
print(f"远程路径: {remote_path}")

# 在 TaskScheduler 中的使用方式
from module.config.scheduler import TaskScheduler

# 解析优先级字符串
filter = Filter(regex=r"(.*)", attr=["command"])
filter.load(ConfigManual.SCHEDULER_PRIORITY)

# 对任务列表应用优先级过滤
pending_tasks = [task1, task2, task3]
sorted_tasks = filter.apply(pending_tasks)
```

## 7. 设计模式总结

### 7.1 常量类模式
将所有静态配置集中在单一类中，便于管理和维护。

### 7.2 配置分离模式
将手动配置（ConfigManual）与动态配置（ConfigModel）分离，职责清晰。

### 7.3 字符串解析模式
使用特定格式的字符串定义优先级规则，通过 Filter 类解析执行。

### 7.4 路径配置模式
使用相对路径配置文件位置，便于跨平台部署。

**设计优点：**
- 集中管理：所有静态配置在一个地方
- 易于修改：只需修改常量值即可调整行为
- 清晰命名：常量名清晰表达其用途
- 文档化：优先级字符串本身就是一种文档

**注意事项：**
- `CollectiveMissionsr` 可能是拼写错误，应为 `CollectiveMissions`
- 优先级字符串中的空格和换行不影响解析
- 路径配置使用相对路径，依赖于工作目录
