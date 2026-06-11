# config_menu.py 代码详解

## 1. 文件概述

`config_menu.py` 定义了 `ConfigMenu` 类，用于构建 GUI 界面的菜单结构。它将所有任务配置按照功能分类组织成层级菜单，便于用户在图形界面中选择和配置任务。

**主要职责：**
- 定义 GUI 菜单的层级结构
- 将任务配置分组到不同的菜单类别
- 提供 JSON 格式的菜单数据供前端使用

## 2. 导入部分解释

```python
import json                                  # JSON 序列化

from cached_property import cached_property  # 缓存属性装饰器
from pydantic import BaseModel, ValidationError, validator, Field  # Pydantic 组件

from module.config.utils import *            # 工具函数
```

**导入说明：**
- `json`: 将菜单字典序列化为 JSON 字符串
- `cached_property`: 缓存计算结果，避免重复计算
- `pydantic`: 虽然导入但本文件未直接使用，可能是预留

## 3. 类定义解释

### 3.1 ConfigMenu 类

```python
class ConfigMenu:
    # 手动的代码配置菜单
    def __init__(self) -> None:
        self.menu = {}
```

**菜单结构：**
- 使用嵌套字典存储菜单结构
- 键为菜单类别名称
- 值为该类别下的任务列表

## 4. 每个方法的逐行解释

### 4.1 __init__ 方法

```python
def __init__(self) -> None:
    self.menu = {}
    
    # 总览（空列表，占位用）
    self.menu["Overview"] = []
    self.menu['TaskList'] = []
    
    # 脚本设置
    self.menu['Script'] = ['Script', 'Restart', 'GlobalGame']
    
    # 刷御魂
    self.menu["Soul Zones"] = ['Orochi', 'Sougenbi', 'FallenSun', 'EternitySea', 'SixRealms']
    
    # 日常任务
    self.menu["Daily Task"] = [
        'DailyTrifles', 'AreaBoss', 'GoldYoukai', 'ExperienceYoukai', 'Nian',
        'TalismanPass', 'DemonEncounter', 'Pets', 'SoulsTidy', 'Delegation', 
        'WantedQuests', 'Tako', 'AutoCheckinBigGod'
    ]
    
    # 肝帝专属
    self.menu["Liver Emperor Exclusive"] = [
        "BondlingFairyland", "EvoZone", "GoryouRealm", "Exploration",
        "Hyakkiyakou", "HeroTest", "FindJade", "MemoryScrolls"
    ]
    
    # 阴阳寮
    self.menu["Guild"] = [
        'KekkaiUtilize', 'KekkaiActivation', 'RealmRaid', 'RyouToppa', 
        'Dokan', 'CollectiveMissions', 'Hunt', 'AbyssShadows', 
        'GuildBanquet', 'DemonRetreat', 'GuildActivityMonitor'
    ]
    
    # 每周任务
    self.menu["Weekly Task"] = [
        'TrueOrochi', 'RichMan', 'Secret', 'WeeklyTrifles', 'MysteryShop', 'Duel'
    ]
    
    # 活动任务
    self.menu["Activity Task"] = [
        'ActivityShikigami', 'MetaDemon', 'FrogBoss', 'FloatParade', 
        'Quiz', 'KittyShop', 'DyeTrials'
    ]
    
    # 开发工具
    self.menu["Tools"] = [
        'Image Rule', 'Ocr Rule', 'Click Rule', 
        'Long Click Rule', 'Swipe Rule', 'List Rule'
    ]
```

**菜单分类说明：**

| 菜单类别 | 说明 | 包含任务数 |
|----------|------|-----------|
| Overview | 总览页面 | 0 |
| TaskList | 任务列表 | 0 |
| Script | 脚本基础设置 | 3 |
| Soul Zones | 御魂副本 | 5 |
| Daily Task | 每日任务 | 13 |
| Liver Emperor Exclusive | 肝帝专属任务 | 8 |
| Guild | 阴阳寮相关任务 | 11 |
| Weekly Task | 每周任务 | 6 |
| Activity Task | 活动任务 | 7 |
| Tools | 开发工具 | 6 |

### 4.2 gui_menu 属性

```python
@cached_property
def gui_menu(self) -> str:
    """
    生成的是json字符串
    :return:
    """
    return json.dumps(self.menu, ensure_ascii=False, sort_keys=False, default=str)
```

**功能：** 返回 JSON 格式的菜单字符串。

**参数说明：**
- `ensure_ascii=False`: 保留中文字符，不转义为 ASCII
- `sort_keys=False`: 不对键排序，保持原始顺序
- `default=str`: 将非序列化对象转为字符串

### 4.3 gui_menu_list 属性

```python
@cached_property
def gui_menu_list(self) -> dict:
    # 删除不需要的菜单项
    del self.menu['TaskList']
    del self.menu['Tools']
    return self.menu
```

**功能：** 返回精简后的菜单字典（删除 TaskList 和 Tools）。

**注意：** 这个方法会修改原始 `self.menu` 对象，且由于使用了 `cached_property`，只会执行一次。

## 5. 核心算法流程图

### 5.1 菜单结构图

```
┌─────────────────────────────────────────────────────────────┐
│                      GUI 菜单结构                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Overview (总览)                                       │   │
│  │   └── (空)                                            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Script (脚本设置)                                     │   │
│  │   ├── Script                                          │   │
│  │   ├── Restart                                         │   │
│  │   └── GlobalGame                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Soul Zones (御魂副本)                                 │   │
│  │   ├── Orochi (八岐大蛇)                               │   │
│  │   ├── Sougenbi (悲悲鸣)                               │   │
│  │   ├── FallenSun (落日)                                │   │
│  │   ├── EternitySea (永生之海)                          │   │
│  │   └── SixRealms (六道)                                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Daily Task (每日任务)                                 │   │
│  │   ├── DailyTrifles (每日琐事)                         │   │
│  │   ├── AreaBoss (地域Boss)                             │   │
│  │   ├── GoldYoukai (金币妖怪)                          │   │
│  │   ├── ExperienceYoukai (经验妖怪)                     │   │
│  │   ├── Nian (年兽)                                     │   │
│  │   ├── TalismanPass (御灵通行证)                       │   │
│  │   ├── DemonEncounter (逢魔之时)                       │   │
│  │   ├── Pets (宠物)                                     │   │
│  │   ├── SoulsTidy (御魂整理)                            │   │
│  │   ├── Delegation (委派)                               │   │
│  │   ├── WantedQuests (悬赏任务)                         │   │
│  │   ├── Tako (章鱼)                                     │   │
│  │   └── AutoCheckinBigGod (大神自动签到)                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Liver Emperor Exclusive (肝帝专属)                    │   │
│  │   ├── BondlingFairyland (契灵之境)                    │   │
│  │   ├── EvoZone (觉醒副本)                              │   │
│  │   ├── GoryouRealm (御灵副本)                          │   │
│  │   ├── Exploration (探索)                              │   │
│  │   ├── Hyakkiyakou (百鬼夜行)                          │   │
│  │   ├── HeroTest (英杰试炼)                             │   │
│  │   ├── FindJade (找玉)                                 │   │
│  │   └── MemoryScrolls (记忆卷轴)                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Guild (阴阳寮)                                        │   │
│  │   ├── KekkaiUtilize (结界利用)                        │   │
│  │   ├── KekkaiActivation (结界激活)                     │   │
│  │   ├── RealmRaid (寮突)                                │   │
│  │   ├── RyouToppa (寮突破)                              │   │
│  │   ├── Dokan (道馆)                                    │   │
│  │   ├── CollectiveMissions (集体任务)                   │   │
│  │   ├── Hunt (狩猎)                                     │   │
│  │   ├── AbyssShadows (深渊暗影)                         │   │
│  │   ├── GuildBanquet (寮宴会)                           │   │
│  │   ├── DemonRetreat (妖魔退治)                         │   │
│  │   └── GuildActivityMonitor (寮活动监控)               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Weekly Task (每周任务)                                │   │
│  │   ├── TrueOrochi (真八岐大蛇)                        │   │
│  │   ├── RichMan (富翁)                                  │   │
│  │   ├── Secret (秘闻)                                   │   │
│  │   ├── WeeklyTrifles (每周琐事)                        │   │
│  │   ├── MysteryShop (神秘商店)                          │   │
│  │   └── Duel (斗技)                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Activity Task (活动任务)                              │   │
│  │   ├── ActivityShikigami (活动式神)                    │   │
│  │   ├── MetaDemon (超鬼王)                              │   │
│  │   ├── FrogBoss (蛙老板)                               │   │
│  │   ├── FloatParade (花车巡游)                          │   │
│  │   ├── Quiz (答题)                                     │   │
│  │   ├── KittyShop (喵商店)                              │   │
│  │   └── DyeTrials (染色试炼)                            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Tools (开发工具)                                      │   │
│  │   ├── Image Rule (图片规则)                           │   │
│  │   ├── Ocr Rule (OCR规则)                              │   │
│  │   ├── Click Rule (点击规则)                           │   │
│  │   ├── Long Click Rule (长按规则)                      │   │
│  │   ├── Swipe Rule (滑动规则)                           │   │
│  │   └── List Rule (列表规则)                            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 6. 使用示例

```python
from module.config.config_menu import ConfigMenu

# 创建菜单实例
menu = ConfigMenu()

# 获取 JSON 格式的菜单（用于前端）
gui_json = menu.gui_menu
print(gui_json)

# 输出示例：
# {
#   "Overview": [],
#   "TaskList": [],
#   "Script": ["Script", "Restart", "GlobalGame"],
#   "Soul Zones": ["Orochi", "Sougenbi", "FallenSun", "EternitySea", "SixRealms"],
#   ...
# }

# 获取精简菜单（删除 TaskList 和 Tools）
menu_list = menu.gui_menu_list
print(menu_list)

# 在前端 JavaScript 中使用
# const menuData = JSON.parse(guiMenuJson);
# for (const [category, tasks] of Object.entries(menuData)) {
#     console.log(`${category}: ${tasks.join(', ')}`);
# }

# 遍历菜单结构
for category, tasks in menu.menu.items():
    print(f"\n{category}:")
    for task in tasks:
        print(f"  - {task}")
```

## 7. 设计模式总结

### 7.1 组合模式（Composite）
菜单使用树形结构组织，每个类别可以包含多个任务项。

### 7.2 数据传输对象（DTO）
`ConfigMenu` 将菜单结构序列化为 JSON，便于前后端传输。

### 7.3 缓存模式
使用 `cached_property` 缓存计算结果，避免重复序列化。

### 7.4 配置驱动模式
菜单结构由代码定义，修改菜单只需调整 `__init__` 中的数据。

**设计优点：**
- 清晰分类：任务按功能清晰分组
- 易于扩展：添加新任务只需在对应类别中添加
- 前端友好：直接输出 JSON 格式
- 性能优化：使用缓存避免重复计算

**使用场景：**
- GUI 界面的侧边栏菜单
- 任务选择下拉框
- 配置页面的分组展示

**注意事项：**
- `gui_menu_list` 会修改原始 `self.menu` 对象
- 由于使用 `cached_property`，修改应在首次访问前完成
- 菜单中的任务名必须与 ConfigModel 中的字段名对应
