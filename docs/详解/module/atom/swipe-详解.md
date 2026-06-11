# swipe.py 模块详细代码解释

## 1. 文件概述

`swipe.py` 是 SaoifAutoScript 项目中的一个原子操作模块，用于实现滑动操作的轨迹生成。该模块主要提供了 `RuleSwipe` 类，能够根据不同的模式生成平滑的滑动轨迹，支持贝塞尔曲线轨迹和线性轨迹两种模式。

**主要功能：**
- 根据指定的 ROI（感兴趣区域）生成随机起始和结束坐标
- 支持两种滑动模式：`default`（贝塞尔曲线）和 `vector`（线性向量）
- 生成平滑、自然的滑动轨迹点序列

**文件位置：** `D:\project\AuotScript\SaoifAutoScript\module\atom\swipe.py`

---

## 2. 导入部分解释

```python
# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import numpy as np
import random

from math import dist

from module.base.decorator import cached_property
from module.atom.cBezier import BezierTrajectory
from module.logger import logger
```

| 导入模块 | 用途说明 |
|---------|---------|
| `numpy as np` | 用于生成随机整数坐标 (`np.random.randint`) |
| `random` | Python 标准库随机数，用于生成随机参数 |
| `math.dist` | 计算两点之间的欧几里得距离 |
| `cached_property` | 自定义装饰器，实现缓存属性（类似 `functools.cached_property`） |
| `BezierTrajectory` | 贝塞尔曲线轨迹生成器，来自 `module.atom.cBezier` 模块 |
| `logger` | 项目自定义日志记录器（本文件中未使用） |

---

## 3. 类定义解释

### 3.1 `RuleSwipe` 类

```python
class RuleSwipe:
```

`RuleSwipe` 是一个滑动规则类，封装了滑动操作的配置和轨迹生成逻辑。

#### 构造函数 `__init__`

```python
def __init__(self, roi_front: tuple, roi_back: tuple, mode: str, name: str = None) -> None:
```

**参数说明：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `roi_front` | `tuple` | 起始区域，格式为 `(x, y, w, h)`，表示矩形区域的左上角坐标和宽高 |
| `roi_back` | `tuple` | 结束区域，格式为 `(x, y, w, h)`，表示矩形区域的左上角坐标和宽高 |
| `mode` | `str` | 滑动模式，支持 `'default'` 和 `'vector'` |
| `name` | `str` | 可选名称，默认为 `'swipe'` |

**实例属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `self.roi_front` | `tuple` | 起始区域参数 |
| `self.roi_back` | `tuple` | 结束区域参数 |
| `self.mode` | `str` | 当前滑动模式 |
| `self.name` | `str` | 滑动操作名称 |
| `self.interval` | `int` | 每次移动的间隔时间，默认 8 毫秒 |

---

## 4. 每个方法的逐行解释

### 4.1 `is_default_mode` 属性

```python
@cached_property
def is_default_mode(self) -> bool:
    """
    是否是默认模式
    :return:
    """
    return self.mode == 'default'
```

- **装饰器 `@cached_property`**：将方法转换为只读缓存属性，首次访问时计算，后续访问直接返回缓存值
- **功能**：判断当前是否为默认模式（贝塞尔曲线模式）
- **返回值**：布尔值，`True` 表示默认模式

### 4.2 `is_vector_mode` 属性

```python
@cached_property
def is_vector_mode(self) -> bool:
    """
    是否是向量模式
    :return:
    """
    return self.mode == 'vector'
```

- **功能**：判断当前是否为向量模式（线性轨迹模式）
- **返回值**：布尔值，`True` 表示向量模式

### 4.3 `coord` 方法

```python
def coord(self) -> tuple:
    """
    获取坐标, 从roi_front随机获取坐标 和从roi_back随机获取的坐标
    :return: 两个坐标的tuple
    """
    x, y, w, h = self.roi_front
    x = np.random.randint(x, x + w)
    y = np.random.randint(y, y + h)
    x2, y2, w2, h2 = self.roi_back
    x2 = np.random.randint(x2, x2 + w2)
    y2 = np.random.randint(y2, y2 + h2)
    return x, y, x2, y2
```

**逐行解释：**

| 行号 | 代码 | 说明 |
|------|------|------|
| 54 | `x, y, w, h = self.roi_front` | 解包起始区域参数 |
| 55 | `x = np.random.randint(x, x + w)` | 在起始区域宽度范围内随机生成 x 坐标 |
| 56 | `y = np.random.randint(y, y + h)` | 在起始区域高度范围内随机生成 y 坐标 |
| 57 | `x2, y2, w2, h2 = self.roi_back` | 解包结束区域参数 |
| 58 | `x2 = np.random.randint(x2, x2 + w2)` | 在结束区域宽度范围内随机生成 x2 坐标 |
| 59 | `y2 = np.random.randint(y2, y2 + h2)` | 在结束区域高度范围内随机生成 y2 坐标 |
| 60 | `return x, y, x2, y2` | 返回起始坐标 (x, y) 和结束坐标 (x2, y2) |

**返回值格式：** `(start_x, start_y, end_x, end_y)`

### 4.4 `trace` 方法（核心方法）

```python
def trace(self) -> list:
    """
    获取滑动的路径,list的每一项都是tuple
    :return:
    """
```

这是类的核心方法，根据不同的模式生成滑动轨迹。

#### 默认模式（Default Mode）分支

```python
if self.is_default_mode:
    start_pos, end_pos = self.coord()
    # 表示每秒移动1.5个像素点， 总的时间除以每个点10ms就得到总的点的个数
    number_list: int = int(dist(start_pos, end_pos) / (1.5 * self.interval))
    le = random.randint(2, 4)  #
    deviation = random.randint(20, 40)  # 幅度
    b_type = 3
    obbs_type = random.random()  # 0.8的概率是先快中间慢后面快， 0.1概率是先快后慢， 0.1概率先慢后快
    if 0 < obbs_type <= 0.8:
        b_type = 3
    elif obbs_type < 0.9:
        b_type = 2
    else:
        b_type = 1

    return BezierTrajectory.trackArray(start=start_pos, end=end_pos, numberList=number_list, le=le,
             deviation=30, bias=0.5, type=b_type, cbb=0, yhh=20)
```

**逐行解释：**

| 行号 | 代码 | 说明 |
|------|------|------|
| 68 | `start_pos, end_pos = self.coord()` | 调用 `coord()` 方法获取随机起始和结束坐标 |
| 70 | `number_list: int = int(dist(start_pos, end_pos) / (1.5 * self.interval))` | 计算轨迹点数量。公式：距离 / (速度 × 间隔时间) |
| 71 | `le = random.randint(2, 4)` | 随机生成贝塞尔曲线的阶数参数（2-4） |
| 72 | `deviation = random.randint(20, 40)` | 随机生成偏移幅度（20-40 像素） |
| 73 | `b_type = 3` | 默认贝塞尔类型为 3（先快中间慢后面快） |
| 74 | `obbs_type = random.random()` | 生成 0-1 之间的随机数，用于选择运动类型 |
| 75-80 | 条件判断 | 根据随机数选择运动类型：80% 概率类型 3，10% 概率类型 2，10% 概率类型 1 |
| 82-83 | `return BezierTrajectory.trackArray(...)` | 调用贝塞尔轨迹生成器生成轨迹点序列 |

**贝塞尔类型说明：**

| 类型 | 概率 | 运动特征 |
|------|------|---------|
| `b_type = 3` | 80% | 先快 → 中间慢 → 后面快 |
| `b_type = 2` | 10% | 先快 → 后慢 |
| `b_type = 1` | 10% | 先慢 → 后快 |

**`BezierTrajectory.trackArray` 参数说明：**

| 参数 | 值 | 说明 |
|------|-----|------|
| `start` | `start_pos` | 起始坐标 |
| `end` | `end_pos` | 结束坐标 |
| `numberList` | `number_list` | 轨迹点数量 |
| `le` | 2-4 | 曲线阶数 |
| `deviation` | 30 | 偏移量（覆盖了前面的随机值） |
| `bias` | 0.5 | 偏置系数 |
| `type` | 1/2/3 | 运动类型 |
| `cbb` | 0 | 控制参数 |
| `yhh` | 20 | 平滑参数 |

#### 向量模式（Vector Mode）分支

```python
elif self.is_vector_mode:
    # 获取两个点的直线的规矩
    start_pos, end_pos = self.coord()
    # 表示每秒移动1.5个像素点， 总的时间除以每个点10ms就得到总的点的个数
    number_list: int = int(dist(start_pos, end_pos) / (1.5 * self.interval))

    def generate_linear_trajectory(start_pos: tuple, end_pos: tuple, num_points: int) -> list:
        """
        生成线性轨迹
        :param start_pos:
        :param end_pos:
        :param num_points:
        :return:
        """
        trajectory = []
        delta_x = (end_pos[0] - start_pos[0]) / (num_points - 1)
        delta_y = (end_pos[1] - start_pos[1]) / (num_points - 1)
        for i in range(num_points):
            x = start_pos[0] + delta_x * i
            y = start_pos[1] + delta_y * i
            trajectory.append((x, y))
        return trajectory

    return generate_linear_trajectory(start_pos, end_pos, number_list)
```

**逐行解释：**

| 行号 | 代码 | 说明 |
|------|------|------|
| 87 | `start_pos, end_pos = self.coord()` | 获取随机坐标 |
| 89 | `number_list: int = int(...)` | 计算轨迹点数量 |
| 91-106 | `generate_linear_trajectory(...)` | 定义内部函数，生成线性轨迹 |
| 99 | `trajectory = []` | 初始化空轨迹列表 |
| 100 | `delta_x = (end_pos[0] - start_pos[0]) / (num_points - 1)` | 计算 x 方向的步长 |
| 101 | `delta_y = (end_pos[1] - start_pos[1]) / (num_points - 1)` | 计算 y 方向的步长 |
| 102-105 | `for i in range(num_points):` | 循环生成每个轨迹点 |
| 108 | `return generate_linear_trajectory(...)` | 返回线性轨迹 |

#### 错误处理分支

```python
else:
    raise ValueError(f'Invalid mode: {self.mode}')
```

- 当 `mode` 既不是 `'default'` 也不是 `'vector'` 时，抛出 `ValueError` 异常

---

## 5. 核心算法流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                      RuleSwipe.trace()                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │   获取滑动模式     │
                    │   self.mode       │
                    └───────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │   default   │   │   vector    │   │   其他模式   │
    │  (贝塞尔)   │   │  (线性)     │   │   (错误)    │
    └─────────────┘   └─────────────┘   └─────────────┘
              │               │               │
              ▼               ▼               ▼
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │ coord()获取 │   │ coord()获取 │   │  抛出异常   │
    │ 随机坐标    │   │ 随机坐标    │   │ ValueError  │
    └─────────────┘   └─────────────┘   └─────────────┘
              │               │
              ▼               ▼
    ┌─────────────┐   ┌─────────────┐
    │ 计算点数    │   │ 计算点数    │
    │ number_list │   │ number_list │
    └─────────────┘   └─────────────┘
              │               │
              ▼               ▼
    ┌─────────────┐   ┌─────────────┐
    │ 随机选择    │   │ 线性插值    │
    │ 贝塞尔类型  │   │ 生成轨迹    │
    │ (1/2/3)     │   │             │
    └─────────────┘   └─────────────┘
              │               │
              ▼               ▼
    ┌─────────────┐   ┌─────────────┐
    │ BezierTraj  │   │  返回轨迹   │
    │ ectory.     │   │  点列表     │
    │ trackArray  │   │             │
    └─────────────┘   └─────────────┘
              │               │
              └───────┬───────┘
                      ▼
              ┌───────────────┐
              │  返回 list    │
              │  [(x,y), ...] │
              └───────────────┘
```

### 贝塞尔类型选择流程

```
┌─────────────────────────────────┐
│   生成随机数 obbs_type (0-1)    │
└─────────────────────────────────┘
                │
    ┌───────────┼───────────┐
    │           │           │
    ▼           ▼           ▼
┌───────┐  ┌───────┐  ┌───────┐
│ 0-0.8 │  │ 0.8-0.9│ │0.9-1.0│
│  80%  │  │  10%   │ │  10%  │
└───────┘  └───────┘  └───────┘
    │           │           │
    ▼           ▼           ▼
┌───────┐  ┌───────┐  ┌───────┐
│type=3 │  │type=2 │  │type=1 │
│先快中 │  │先快后 │  │先慢后 │
│慢后快 │  │  慢   │  │  快   │
└───────┘  └───────┘  └───────┘
```

---

## 6. 使用示例

### 6.1 基本使用

```python
from module.atom.swipe import RuleSwipe

# 创建默认模式的滑动对象
swipe = RuleSwipe(
    roi_front=(100, 200, 50, 50),  # 起始区域：x=100, y=200, 宽=50, 高=50
    roi_back=(300, 400, 50, 50),   # 结束区域：x=300, y=400, 宽=50, 高=50
    mode='default',                 # 使用默认贝塞尔曲线模式
    name='test_swipe'
)

# 生成轨迹
trajectory = swipe.trace()
print(f"轨迹点数量: {len(trajectory)}")
print(f"起始点: {trajectory[0]}")
print(f"结束点: {trajectory[-1]}")
```

### 6.2 向量模式使用

```python
# 创建向量模式的滑动对象
swipe_vector = RuleSwipe(
    roi_front=(100, 200, 50, 50),
    roi_back=(300, 400, 50, 50),
    mode='vector'  # 使用线性向量模式
)

# 生成线性轨迹
trajectory = swipe_vector.trace()

# 打印轨迹点
for i, (x, y) in enumerate(trajectory):
    print(f"点 {i}: ({x:.2f}, {y:.2f})")
```

### 6.3 坐标获取示例

```python
# 单独获取随机坐标
swipe = RuleSwipe(
    roi_front=(100, 200, 50, 50),
    roi_back=(300, 400, 50, 50),
    mode='default'
)

# 获取随机坐标
start_x, start_y, end_x, end_y = swipe.coord()
print(f"起始坐标: ({start_x}, {start_y})")
print(f"结束坐标: ({end_x}, {end_y})")
```

### 6.4 在自动化脚本中使用

```python
from module.atom.swipe import RuleSwipe

# 模拟向上滑动操作
def swipe_up():
    swipe = RuleSwipe(
        roi_front=(200, 600, 100, 50),  # 屏幕底部
        roi_back=(200, 200, 100, 50),    # 屏幕顶部
        mode='default',
        name='swipe_up'
    )
    
    trajectory = swipe.trace()
    
    # 将轨迹传递给实际的滑动执行器
    for x, y in trajectory:
        # 执行实际的触摸操作
        perform_touch(x, y)
        time.sleep(swipe.interval / 1000)  # 转换为秒

# 模拟向左滑动操作
def swipe_left():
    swipe = RuleSwipe(
        roi_front=(600, 300, 50, 100),  # 屏幕右侧
        roi_back=(100, 300, 50, 100),    # 屏幕左侧
        mode='vector',                    # 使用线性模式
        name='swipe_left'
    )
    
    trajectory = swipe.trace()
    
    for x, y in trajectory:
        perform_touch(x, y)
        time.sleep(swipe.interval / 1000)
```

---

## 7. 设计模式总结

### 7.1 策略模式（Strategy Pattern）

`RuleSwipe` 类实现了策略模式，通过 `mode` 参数选择不同的轨迹生成策略：

- **策略接口**：`trace()` 方法
- **具体策略**：
  - `'default'`：贝塞尔曲线轨迹生成策略
  - `'vector'`：线性轨迹生成策略

```
┌─────────────────┐
│   RuleSwipe     │
├─────────────────┤
│ + mode: str     │
│ + trace(): list │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌────────┐
│Default │ │Vector  │
│Strategy│ │Strategy│
└────────┘ └────────┘
```

### 7.2 单一职责原则（SRP）

- `RuleSwipe` 类只负责滑动轨迹的生成
- 坐标生成 (`coord()`) 和轨迹计算 (`trace()`) 职责分离
- 实际的滑动执行由外部模块负责

### 7.3 封装性

- 将 ROI 参数、模式配置、轨迹生成逻辑封装在一个类中
- 使用 `@cached_property` 优化属性访问性能
- 内部实现细节对外部调用者透明

### 7.4 可扩展性

- 可以通过添加新的 `mode` 值来扩展轨迹生成策略
- 贝塞尔曲线参数可以灵活配置
- 轨迹点数量根据距离自动计算

### 7.5 随机化设计

为了模拟真实的人类滑动行为，模块引入了多处随机化：

| 随机化位置 | 作用 |
|-----------|------|
| `coord()` 中的坐标随机 | 模拟手指触摸位置的不确定性 |
| `le = random.randint(2, 4)` | 曲线阶数随机，增加轨迹多样性 |
| `deviation = random.randint(20, 40)` | 偏移幅度随机，模拟不同的滑动力度 |
| `obbs_type = random.random()` | 运动类型随机，模拟不同的滑动习惯 |

### 7.6 性能优化

- 使用 `@cached_property` 避免重复计算模式判断
- 轨迹点数量基于距离动态计算，避免不必要的点
- 内部函数 `generate_linear_trajectory` 避免类级别的方法膨胀

---

## 附录：相关模块依赖

| 模块 | 用途 |
|------|------|
| `module.base.decorator` | 提供 `cached_property` 装饰器 |
| `module.atom.cBezier` | 提供贝塞尔曲线轨迹生成能力 |
| `module.logger` | 日志记录（当前未使用） |

---

*文档生成时间：2026-06-11*
*源文件：`D:\project\AuotScript\SaoifAutoScript\module\atom\swipe.py`*
