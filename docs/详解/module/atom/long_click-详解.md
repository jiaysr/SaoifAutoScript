# `long_click.py` 逐行代码详解

> 文件路径：`module/atom/long_click.py`
> 作者：runhey
> GitHub：https://github.com/runhey

---

## 1. 文件概述

`long_click.py` 定义了 `RuleLongClick` 类，用于描述屏幕上的**长按操作规则**。它继承自 `RuleClick`（普通点击规则），在普通点击的基础上增加了 `duration`（长按时长）属性。

该类是整个自动脚本框架中原子操作层的核心组件之一，主要用于：

- 定义屏幕上可长按区域的坐标范围（ROI）
- 生成长按位置的随机坐标（防止被检测）
- 携带长按持续时间参数，供上层调用时使用

在整个项目中，`RuleLongClick` 被广泛应用于 100+ 个资源文件中，例如探索副本旋转操作、喂食操作、御魂整理等场景。

---

## 2. 导入部分解释

```python
# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
```

- **第 1 行**：文件编码声明，指定使用 UTF-8 编码，确保中文等非 ASCII 字符能正确处理。
- **第 2-3 行**：作者信息和 GitHub 地址的注释，属于文档性注释。

```python
import numpy as np
```

- **第 4 行**：导入 NumPy 库并重命名为 `np`。虽然本文件未直接使用 `np`，但父类 `RuleClick` 中的 `coord()` 和 `coord_more()` 方法使用了 `np.random.randint()` 来生成随机坐标。此导入可能是为了保持与父类文件的一致性，或者为后续扩展预留。

```python
from module.base.decorator import cached_property
```

- **第 6 行**：从 `module.base.decorator` 模块导入 `cached_property` 装饰器。`cached_property` 是一个描述符，它将方法的返回值缓存到实例的 `__dict__` 中，后续访问同一属性时直接返回缓存值，避免重复计算。虽然本文件未直接使用，但父类或子类可能会用到。

```python
from module.logger import logger
```

- **第 7 行**：导入项目统一的日志记录器 `logger`，用于输出调试、信息、警告等日志。本文件中未直接使用，但在项目的其他模块中广泛使用。

```python
from module.atom.click import RuleClick
```

- **第 8 行**：从 `module.atom.click` 模块导入 `RuleClick` 类。这是 `RuleLongClick` 的父类，提供了基础的点击规则功能，包括：
  - `roi_front` / `roi_back`：前景/背景感兴趣区域
  - `coord()`：从 `roi_front` 生成随机坐标
  - `coord_more()`：从 `roi_back` 生成随机坐标
  - `center`：返回 `roi_front` 的中心坐标
  - `move()`：移动 `roi_front` 的位置

---

## 3. 类定义解释

```python
class RuleLongClick(RuleClick):
```

- **第 11 行**：定义 `RuleLongClick` 类，继承自 `RuleClick`。

### 继承关系

```
RuleClick (module/atom/click.py)
    │
    │  提供：roi_front, roi_back, coord(), coord_more(), center, move()
    │
    └── RuleLongClick (module/atom/long_click.py)
            │
            │  新增：duration 属性
            │
            └── 用于定义长按操作的规则
```

`RuleLongClick` 继承了 `RuleClick` 的所有功能，并扩展了 `duration` 属性来表示长按的持续时间。

---

## 4. 每个方法的逐行解释

### 4.1 `__init__` 方法

```python
def __init__(self, roi_front: tuple, roi_back: tuple, duration: int = 1000, name: str=None) -> None:
```

- **第 13 行**：构造方法定义。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `roi_front` | `tuple` | 必填 | 前景感兴趣区域，格式为 `(x, y, w, h)`，表示点击的主要目标区域 |
| `roi_back` | `tuple` | 必填 | 背景感兴趣区域，格式为 `(x, y, w, h)`，表示备选的点击区域 |
| `duration` | `int` | `1000` | 长按持续时间，单位为**毫秒（ms）**，默认 1000ms = 1 秒 |
| `name` | `str` | `None` | 规则名称，用于标识和日志输出 |

返回值类型为 `None`。

```python
    """
    初始化
    :param roi_front:
    :param roi_back:
    :param duration:
    """
```

- **第 14-19 行**：文档字符串（docstring），说明这是一个初始化方法，并列出参数。`:param roi_front:` 等标记是 Python 的文档字符串约定，用于生成 API 文档。

```python
    if not name:
        name = 'long_click'
```

- **第 20-21 行**：如果未提供 `name` 参数，则使用默认名称 `'long_click'`。`if not name` 在 `name` 为 `None`、空字符串 `''`、`0`、`False` 等假值时都会为 `True`。

```python
    super().__init__(roi_front, roi_back, name=name)
```

- **第 22 行**：调用父类 `RuleClick` 的构造方法，传入 `roi_front`、`roi_back` 和 `name`。这会完成：
  - `self.roi_front = roi_front`：设置前景区域
  - `self.roi_back = roi_back`：设置背景区域
  - `self.name = name`：设置规则名称

```python
    self.duration = duration
```

- **第 23 行**：将 `duration` 参数保存为实例属性。这是 `RuleLongClick` 相对于 `RuleClick` 唯一新增的属性。

---

## 5. 核心算法流程图

### 5.1 对象创建流程

```
┌─────────────────────────────────────────────────────────────┐
│                    创建 RuleLongClick 对象                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  接收参数: roi_front, roi_back, duration, name               │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  检查 name 参数                                              │
│  if not name:                                                │
│      name = 'long_click'                                     │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  调用父类 RuleClick.__init__()                               │
│  ├── self.roi_front = roi_front                              │
│  ├── self.roi_back = roi_back                                │
│  └── self.name = name                                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  self.duration = duration  (新增属性)                         │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  对象创建完成                                                 │
│  属性: roi_front, roi_back, name, duration                   │
│  方法: coord(), coord_more(), center, move()                 │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 使用时的坐标生成流程（继承自 RuleClick）

```
┌─────────────────────────────────────────────────────────────┐
│                    调用 rule.coord()                          │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  解包 roi_front: x, y, w, h = self.roi_front                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  生成随机坐标:                                                │
│  x = np.random.randint(x, x + w)   # 在宽度范围内随机        │
│  y = np.random.randint(y, y + h)   # 在高度范围内随机        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  返回随机坐标 (x, y)                                         │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 上层调用长按流程（base_task.py 中的 appear_then_click）

```
┌─────────────────────────────────────────────────────────────┐
│                appear_then_click(target, action)             │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  检测目标图片是否出现 (appear)                                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
              ┌───────────┴───────────┐
              │ 出现                    │ 未出现
              ▼                        ▼
┌──────────────────────────┐  ┌──────────────────┐
│ 检查 action 类型          │  │ 返回 False        │
└────────────┬─────────────┘  └──────────────────┘
             │
    ┌────────┴────────┐
    │                  │
    ▼                  ▼
┌─────────────┐ ┌─────────────┐
│ RuleLongClick│ │ RuleClick   │
└──────┬──────┘ └──────┬──────┘
       │               │
       ▼               ▼
┌──────────────┐ ┌──────────────┐
│ 获取随机坐标  │ │ 获取随机坐标  │
│ x,y=coord()  │ │ x,y=coord()  │
└──────┬───────┘ └──────┬───────┘
       │               │
       ▼               ▼
┌──────────────┐ ┌──────────────┐
│ device.      │ │ device.      │
│ long_click(  │ │ click(x, y)  │
│  x, y,       │ │              │
│  duration/   │ │              │
│  1000)       │ │              │
└──────────────┘ └──────────────┘
```

---

## 6. 使用示例

### 6.1 基本创建

```python
from module.atom.long_click import RuleLongClick

# 创建一个长按规则：在区域 (100, 200, 50, 50) 内长按 1500ms
long_click_rule = RuleLongClick(
    roi_front=(100, 200, 50, 50),   # 主点击区域：x=100, y=200, 宽=50, 高=50
    roi_back=(100, 200, 50, 50),    # 备选区域（通常与 roi_front 相同）
    duration=1500,                   # 长按 1500 毫秒
    name="my_long_click"            # 规则名称
)

# 使用默认名称和默认时长（1000ms）
simple_rule = RuleLongClick(
    roi_front=(50, 100, 30, 30),
    roi_back=(50, 100, 30, 30)
)
# simple.rule.name = 'long_click'
# simple.rule.duration = 1000
```

### 6.2 项目中的实际使用

在 `tasks/SoulsTidy/assets.py` 中的御魂整理长按操作：

```python
from module.atom.long_click import RuleLongClick

class SoulsTidyAssets:
    # 长按第一个御魂位置，持续 1500ms
    L_ONE = RuleLongClick(
        roi_front=(88, 272, 100, 78),
        roi_back=(88, 272, 100, 78),
        duration=1500,
        name="one"
    )
```

在 `tasks/Exploration/assets.py` 中的探索副本旋转操作：

```python
class ExplorationAssets:
    # 四个旋转按钮的长按操作
    L_ROTATE_1 = RuleLongClick(roi_front=(516,582,22,21), roi_back=(516,582,22,21), duration=1500, name="rotate_1")
    L_ROTATE_2 = RuleLongClick(roi_front=(650,587,21,21), roi_back=(650,587,21,21), duration=1500, name="rotate_2")
    L_ROTATE_3 = RuleLongClick(roi_front=(785,587,21,21), roi_back=(785,587,21,21), duration=1500, name="rotate_3")
    L_ROTATE_4 = RuleLongClick(roi_front=(921,590,21,21), roi_back=(921,590,21,21), duration=1500, name="rotate_4")
```

### 6.3 在任务中调用长按

```python
from tasks.base_task import BaseTask

class MyTask(BaseTask):
    def run(self):
        # 方法1：使用 appear_then_click 自动检测并长按
        if self.appear_then_click(target=SOME_IMAGE, action=SOME_LONG_CLICK_RULE):
            pass  # 目标出现并执行了长按

        # 方法2：手动指定 duration 覆盖默认值
        self.appear_then_click(
            target=SOME_IMAGE,
            action=SOME_LONG_CLICK_RULE,
            duration=2000  # 覆盖为 2000ms
        )

        # 方法3：直接获取坐标并长按
        x, y = SOME_LONG_CLICK_RULE.coord()
        self.device.long_click(x, y, duration=SOME_LONG_CLICK_RULE.duration / 1000)
```

### 6.4 使用继承的方法

```python
rule = RuleLongClick(roi_front=(100, 200, 50, 60), roi_back=(80, 180, 90, 100), duration=1500)

# 获取随机坐标（来自 roi_front）
x, y = rule.coord()          # 例如: (123, 234)

# 获取备选随机坐标（来自 roi_back）
x2, y2 = rule.coord_more()   # 例如: (95, 210)

# 获取中心坐标
cx, cy = rule.center          # (125, 230) = (100+50//2, 200+60//2)

# 访问属性
print(rule.duration)          # 1500
print(rule.roi_front)         # (100, 200, 50, 60)
print(rule.name)              # 'long_click'
```

---

## 7. 设计模式总结

### 7.1 继承与扩展模式（Inheritance）

`RuleLongClick` 采用了经典的**单继承**模式来扩展 `RuleClick` 的功能：

- **父类 `RuleClick`**：封装了通用的点击区域定义和坐标生成逻辑
- **子类 `RuleLongClick`**：仅新增 `duration` 属性，复用父类所有方法

这种设计遵循了**开闭原则（Open/Closed Principle）**：对扩展开放（可以新增属性），对修改关闭（不修改父类代码）。

### 7.2 数据类模式（Data Class）

`RuleLongClick` 本质上是一个**数据类**，用于封装长按操作的配置数据：

| 属性 | 说明 |
|------|------|
| `roi_front` | 前景区域 (x, y, w, h) |
| `roi_back` | 背景区域 (x, y, w, h) |
| `name` | 规则标识名 |
| `duration` | 长按时长（ms） |

### 7.3 随机化策略

坐标生成采用**随机化策略**，在 ROI 范围内随机选取坐标点，而不是固定点击中心。这是一种**反检测机制**，模拟人类点击的不确定性，避免被游戏反作弊系统识别为自动化操作。

### 7.4 多态设计

在 `base_task.py` 的 `appear_then_click` 方法中，通过 `isinstance()` 检查 action 的类型来决定执行普通点击还是长按点击，体现了**运行时多态**：

```python
if isinstance(action, RuleLongClick):
    self.device.long_click(x, y, duration=action.duration / 1000)
elif isinstance(action, RuleClick):
    self.device.click(x, y)
```

### 7.5 模块化架构

```
module/atom/              ← 原子操作层（最底层）
    ├── click.py          ← RuleClick：普通点击规则
    ├── long_click.py     ← RuleLongClick：长按点击规则
    ├── image.py          ← RuleImage：图片匹配规则
    └── ocr.py            ← RuleOcr：文字识别规则

tasks/base_task.py        ← 基础任务层（中间层）
    └── appear_then_click()  ← 统一的"出现则点击"逻辑

tasks/*/assets.py         ← 资源定义层（最上层）
    └── 定义具体的 RuleLongClick 实例
```

这种三层架构将**规则定义**、**业务逻辑**和**资源配置**分离，使得代码易于维护和扩展。
