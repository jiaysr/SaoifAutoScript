# cBezier.py 代码详解

## 1. 文件概述

`module/atom/cBezier.py` 是一个基于**贝塞尔曲线**的轨迹模拟库，用于生成模拟人手动滑动的轨迹数据。其核心应用场景包括：

- **Selenium 自动化测试**中模拟真实的鼠标/触摸滑动轨迹
- **生成轨迹数组**用于 JS 加密，绕过网站服务器后端的风控检测

该库由 `cbb` 编写，通过控制贝塞尔曲线的阶数、波动幅度、速度分布类型等参数，生成高度拟人化的滑动轨迹。

---

## 2. 导入部分解释

```python
import numpy as np    # 用于高效的数值计算，处理数组和矩阵运算
import math           # 提供数学函数，主要用到 math.factorial（阶乘）和 math.pow（幂运算）
import random         # 提供随机数生成，用于轨迹的随机波动模拟
```

**依赖关系说明**：
- `numpy`：贝塞尔曲线的控制点使用 `np.array` 表示，支持向量加法和标量乘法
- `math`：计算贝塞尔曲线公式中的二项式系数（阶乘形式）
- `random`：在控制点生成时引入随机偏移，使轨迹更自然

---

## 3. 类定义解释

```python
class BezierTrajectory:
```

`BezierTrajectory` 是一个纯工具类，所有方法均为 `@classmethod`（类方法），无需实例化即可使用。类内部结构如下：

| 方法名 | 访问级别 | 功能 |
|--------|---------|------|
| `_bztsg` | 私有 | 核心贝塞尔曲线方程生成器 |
| `_type` | 私有 | 速度曲线分布生成（匀速/加速/减速等） |
| `getFun` | 公开 | 根据控制点返回贝塞尔曲线方程 |
| `simulation` | 公开 | 生成贝塞尔曲线的控制点和方程 |
| `trackArray` | 公开 | 生成完整的轨迹坐标数组（主入口） |

---

## 4. 每个方法的逐行解释

### 4.1 `_bztsg` 方法 — 贝塞尔曲线方程生成器

```python
@classmethod
def _bztsg(cls, dataTrajectory):
```

**功能**：接收一组控制点坐标，返回一个可调用的贝塞尔曲线函数 `staer(x)`。

**逐行解析**：

```python
lengthOfdata = len(dataTrajectory)
```
- 获取控制点的数量 `n`，用于后续计算贝塞尔曲线的阶数（阶数 = `n - 1`）

```python
def staer(x):
```
- 定义内部闭包函数，`x` 为 x 轴坐标值，返回对应的 y 值

```python
t = ((x - dataTrajectory[0][0]) / (dataTrajectory[-1][0] - dataTrajectory[0][0]))
```
- 将输入的 `x` 归一化为参数 `t`，范围 `[0, 1]`
- `dataTrajectory[0][0]` 是起点的 x 坐标，`dataTrajectory[-1][0]` 是终点的 x 坐标
- 公式：`t = (x - x_start) / (x_end - x_start)`

```python
y = np.array([0, 0], dtype=np.float64)
```
- 初始化结果向量为 `[0, 0]`，用于累加各控制点的贡献

```python
for s in range(len(dataTrajectory)):
    y += dataTrajectory[s] * (
        (math.factorial(lengthOfdata - 1) /
         (math.factorial(s) * math.factorial(lengthOfdata - 1 - s)))
        * math.pow(t, s)
        * math.pow((1 - t), lengthOfdata - 1 - s)
    )
```
- 这是**贝塞尔曲线的标准公式**（Bernstein 基函数形式）：

$$B(t) = \sum_{i=0}^{n} \binom{n}{i} (1-t)^{n-i} t^i \cdot P_i$$

- `math.factorial(n-1) / (math.factorial(s) * math.factorial(n-1-s))` = 组合数 $C_{n-1}^{s}$
- `math.pow(t, s)` = $t^s$
- `math.pow(1-t, n-1-s)` = $(1-t)^{n-1-s}$
- `dataTrajectory[s]` = 第 `s` 个控制点的坐标 $P_s$
- 每次循环累加一个控制点对最终位置的加权贡献

```python
return y[1]
```
- 返回结果向量的 y 分量（即曲线上的纵坐标值）

---

### 4.2 `_type` 方法 — 速度分布曲线生成器

```python
@classmethod
def _type(cls, type, x, numberList):
```

**功能**：根据指定的速度类型，生成 x 轴上的采样点序列，控制滑动速度的变化模式。

**参数说明**：
- `type`：速度类型（0=匀速，1=先慢后快，2=先快后慢，3=先慢中间快后慢）
- `x`：x 轴范围 `[x_start, x_end]`
- `numberList`：采样点数量

**逐行解析**：

```python
numberListre = []
pin = (x[1] - x[0]) / numberList
```
- 计算每个采样间隔的步长 `pin`

#### type=0：匀速

```python
if type == 0:
    for i in range(numberList):
        numberListre.append(i * pin)
    if pin >= 0:
        numberListre = numberListre[::-1]
```
- 均匀生成 `numberList` 个等间距的 x 值
- 若步长为正（从左到右），则反转数组（使轨迹从起点递增）

#### type=1：先慢后快（加速）

```python
elif type == 1:
    for i in range(numberList):
        numberListre.append(1 * ((i * pin) ** 2))
    numberListre = numberListre[::-1]
```
- 使用平方函数 `y = x²` 生成非线性分布，前期点密集（慢），后期点稀疏（快）
- 反转数组使起点对应起始位置

#### type=2：先快后慢（减速）

```python
elif type == 2:
    for i in range(numberList):
        numberListre.append(1 * ((i * pin - x[1]) ** 2))
```
- 使用平移后的平方函数，前期点稀疏（快），后期点密集（慢）

#### type=3：先慢中间快后慢（S 形）

```python
elif type == 3:
    dataTrajectory = [
        np.array([0, 0]),
        np.array([(x[1]-x[0])*0.8, (x[1]-x[0])*0.6]),
        np.array([x[1]-x[0], 0])
    ]
    fun = cls._bztsg(dataTrajectory)
    numberListre = [0]
    for i in range(1, numberList):
        numberListre.append(fun(i * pin) + numberListre[-1])
    if pin >= 0:
        numberListre = numberListre[::-1]
```
- 构造一个二阶贝塞尔曲线作为速度分布函数
- 控制点：起点 `(0,0)`、中间偏上 `(0.8L, 0.6L)`、终点 `(L, 0)`
- 累加曲线值形成位置序列，实现 S 形速度变化

#### 归一化处理（通用）

```python
numberListre = np.abs(np.array(numberListre) - max(numberListre))
```
- 取绝对值并偏移，确保所有值非负

```python
biaoNumberList = (
    (numberListre - numberListre[numberListre.argmin()]) /
    (numberListre[numberListre.argmax()] - numberListre[numberListre.argmin()])
) * (x[1] - x[0]) + x[0]
```
- **Min-Max 归一化**：将值映射到 `[x[0], x[1]]` 的范围内

```python
biaoNumberList[0] = x[0]
biaoNumberList[-1] = x[1]
```
- 强制首尾点精确等于起止 x 坐标，消除浮点误差

```python
return biaoNumberList
```

---

### 4.3 `getFun` 方法 — 公开接口：获取贝塞尔方程

```python
@classmethod
def getFun(cls, s):
    dataTrajectory = []
    for i in s:
        dataTrajectory.append(np.array(i))
    return cls._bztsg(dataTrajectory)
```

- 接收一个二维坐标列表 `s`（如 `[[0,0], [50,80], [100,100]]`）
- 将每个坐标转换为 `np.array`
- 调用 `_bztsg` 返回可调用的贝塞尔曲线函数

---

### 4.4 `simulation` 方法 — 贝塞尔曲线控制点生成

```python
@classmethod
def simulation(cls, start, end, le=1, deviation=0, bias=0.5):
```

**功能**：根据起点、终点和参数，自动生成贝塞尔曲线的中间控制点，并返回曲线方程。

**逐行解析**：

```python
start = np.array(start)
end = np.array(end)
```
- 将列表转为 numpy 数组，支持向量运算

```python
cbb = []
if le != 1:
    e = (1 - bias) / (le - 1)
    cbb = [[bias + e * i, bias + e * (i + 1)] for i in range(le - 1)]
```
- 当阶数 > 1 时，计算中间控制点的分布区间
- `bias` 控制波动区域的起始位置（0.5 表示从中间开始）
- `e` 是每个控制点区间的宽度
- `cbb` 列表存储每个中间控制点的 x 比例范围

```python
dataTrajectoryList = [start]
```
- 初始化控制点列表，起点为第一个控制点

```python
t = random.choice([-1, 1])
w = 0
for i in cbb:
    px1 = start[0] + (end[0] - start[0]) * (random.random() * (i[1] - i[0]) + i[0])
    p = np.array([px1, cls._bztsg([start, end])(px1) + t * deviation])
    dataTrajectoryList.append(p)
    w += 1
    if w >= 2:
        w = 0
        t = -1 * t
```
- `t` 随机选择 `[-1, 1]`，决定波动方向（上或下）
- `px1`：在指定比例范围内随机生成 x 坐标
- `cls._bztsg([start, end])(px1)`：计算起点到终点直线上对应 x 的 y 值
- `+ t * deviation`：在直线 y 值基础上叠加波动偏移
- 每生成 2 个控制点后翻转波动方向，形成自然的波浪轨迹

```python
dataTrajectoryList.append(end)
return {"equation": cls._bztsg(dataTrajectoryList), "P": np.array(dataTrajectoryList)}
```
- 添加终点为最后一个控制点
- 返回包含曲线方程和所有控制点的字典

---

### 4.5 `trackArray` 方法 — 主入口：生成轨迹数组

```python
@classmethod
def trackArray(cls, start, end, numberList, le=1, deviation=0, bias=0.5, type=0, cbb=0, yhh=10):
```

**功能**：生成完整的轨迹坐标数组，是整个库的主要对外接口。

**参数说明**：
- `start` / `end`：起止坐标 `[x, y]`
- `numberList`：返回轨迹点的数量
- `le`：贝塞尔曲线阶数
- `deviation`：轨迹上下波动范围
- `bias`：波动分布位置
- `type`：速度类型（0/1/2/3）
- `cbb`：终点来回摆动次数
- `yhh`：终点来回摆动的范围

**逐行解析**：

```python
s = []
fun = cls.simulation(start, end, le, deviation, bias)
w = fun['P']
fun = fun["equation"]
```
- 调用 `simulation` 获取贝塞尔曲线方程和控制点

#### 无摆动模式（cbb=0）

```python
if cbb != 0:
    # ... 摆动逻辑（见下文）
else:
    xTrackArray = cls._type(type, [start[0], end[0]], numberList)
    for i in xTrackArray:
        s.append([i, fun(i)])
```
- 使用 `_type` 生成 x 轴采样点序列
- 对每个 x 值，通过贝塞尔方程计算对应的 y 值
- 组合成 `[x, y]` 坐标点加入轨迹数组

#### 摆动模式（cbb≠0）

```python
numberListOfcbb = round(numberList * 0.2 / (cbb + 1))
numberList -= (numberListOfcbb * (cbb + 1))
```
- 将 20% 的轨迹点分配给摆动段
- 每段摆动（含回归终点）平均分配点数

```python
xTrackArray = cls._type(type, [start[0], end[0]], numberList)
for i in xTrackArray:
    s.append([i, fun(i)])
```
- 先生成主轨迹段（占 80% 点数）

```python
dq = yhh / cbb
kg = 0
ends = np.copy(end)
for i in range(cbb):
    if kg == 0:
        d = np.array([end[0] + (yhh - dq*i), ...])
        kg = 1
    else:
        d = np.array([end[0] - (yhh - dq*i), ...])
        kg = 0
    y = cls.trackArray(ends, d, numberListOfcbb, le=2, deviation=0, bias=0.5, type=0, cbb=0, yhh=10)
    s += list(y['trackArray'])
    ends = d
```
- 生成终点附近的来回摆动轨迹
- `dq`：每次摆动的递减幅度
- `kg` 标志位交替控制摆动方向（左/右）
- **递归调用** `trackArray` 生成每段摆动的平滑轨迹
- `d` 的 y 坐标通过直线方程 `y = kx + b` 计算，保持在起止点连线上

```python
y = cls.trackArray(ends, end, numberListOfcbb, le=2, deviation=0, bias=0.5, type=0, cbb=0, yhh=10)
s += list(y['trackArray'])
```
- 最后从最后一次摆动位置回归到终点

```python
return [[int(s[0]), int(s[1])] for s in s]
```
- 将所有浮点坐标转为整数列表返回

---

## 5. 核心算法流程图

```
trackArray(start, end, numberList, ...) 入口
│
├── simulation(start, end, le, deviation, bias)
│   │
│   ├── 计算中间控制点分布区间 cbb
│   │   └── cbb = [[bias, bias+e], [bias+e, bias+2e], ...]
│   │
│   ├── 生成中间控制点
│   │   ├── 随机确定波动方向 t = ±1
│   │   ├── 在每个区间内随机生成 x 坐标 px1
│   │   ├── 计算直线上对应 y 值 + t * deviation
│   │   └── 每 2 个控制点翻转波动方向
│   │
│   ├── 控制点列表 = [start, P1, P2, ..., end]
│   │
│   └── _bztsg(控制点列表) → 返回贝塞尔方程 fun(x)
│       │
│       └── staer(x):
│           ├── t = (x - x_start) / (x_end - x_start)
│           ├── B(t) = Σ C(n,i) * t^i * (1-t)^(n-i) * Pi
│           └── return y 分量
│
├── cbb == 0? ──→ 否 ──→ 摆动模式
│   │                     ├── 分配 20% 点数给摆动段
│   │                     ├── 生成主轨迹（80% 点数）
│   │                     ├── 循环 cbb 次摆动
│   │                     │   ├── 计算摆动目标点 d
│   │                     │   ├── 递归调用 trackArray
│   │                     │   └── 交替摆动方向
│   │                     └── 回归终点
│   │
└── 是 ──→ 简单模式
            ├── _type(type, [x_start, x_end], numberList)
            │   ├── type=0: 匀速（等间距）
            │   ├── type=1: 先慢后快（x²）
            │   ├── type=2: 先快后慢（平移x²）
            │   └── type=3: S形（贝塞尔速度曲线）
            │
            ├── 对每个 x 采样点: fun(x) → y
            └── 返回 [[x1,y1], [x2,y2], ...]（整数）
```

---

## 6. 使用示例

### 6.1 基本用法：生成匀速直线轨迹

```python
from module.atom.cBezier import BezierTrajectory

# 从 (0,0) 滑动到 (500,800)，生成 100 个点，匀速
trajectory = BezierTrajectory.trackArray(
    start=[0, 0],
    end=[500, 800],
    numberList=100
)
print(trajectory)
# 输出: [[0, 0], [5, 8], [10, 16], ..., [500, 800]]
```

### 6.2 带波动的拟人轨迹

```python
# 二阶贝塞尔曲线，波动范围 15 像素，先慢后快
trajectory = BezierTrajectory.trackArray(
    start=[0, 0],
    end=[500, 800],
    numberList=150,
    le=2,          # 二阶贝塞尔
    deviation=15,  # 上下波动 15px
    bias=0.5,      # 波动集中在中间
    type=1         # 先慢后快
)
```

### 6.3 带终点摆动的轨迹（模拟手指抬起前的微调）

```python
# 四阶贝塞尔，到达终点后来回摆动 3 次，摆动范围 20px
trajectory = BezierTrajectory.trackArray(
    start=[100, 200],
    end=[600, 900],
    numberList=200,
    le=4,
    deviation=10,
    type=3,        # S形速度
    cbb=3,         # 摆动 3 次
    yhh=20         # 摆动范围 20px
)
```

### 6.4 获取贝塞尔方程（用于自定义计算）

```python
# 手动指定控制点，获取方程
control_points = [[0, 0], [30, 100], [70, 50], [100, 100]]
func = BezierTrajectory.getFun(control_points)

# 计算 x=50 时的 y 值
y_value = func(50)
print(f"x=50 时, y={y_value}")
```

### 6.5 与 Selenium 集成

```python
from selenium.webdriver.common.action_chains import ActionChains

# 生成轨迹
trajectory = BezierTrajectory.trackArray(
    start=[0, 0],
    end=[300, 500],
    numberList=80,
    le=3,
    deviation=5,
    type=1
)

# 模拟鼠标移动
element = driver.find_element("id", "target")
actions = ActionChains(driver)
actions.move_to_element(element)
for x, y in trajectory:
    actions.move_by_offset(x - prev_x, y - prev_y)
    prev_x, prev_y = x, y
actions.perform()
```

---

## 7. 设计模式总结

### 7.1 设计模式

| 模式 | 体现 |
|------|------|
| **工厂方法模式** | `_bztsg` 作为工厂，根据控制点生成不同的曲线函数 |
| **策略模式** | `_type` 方法通过 `type` 参数切换不同的速度分布策略（匀速/加速/减速/S形） |
| **递归组合模式** | `trackArray` 在摆动模式下递归调用自身，将复杂轨迹分解为多段简单轨迹 |
| **闭包模式** | `_bztsg` 返回的 `staer` 函数捕获了 `dataTrajectory` 和 `lengthOfdata`，形成闭包 |
| **门面模式** | `trackArray` 作为统一入口，封装了内部的 `_bztsg`、`_type`、`simulation` 等复杂逻辑 |

### 7.2 代码特点

- **纯函数式设计**：所有方法无副作用（除 `random`），输入相同参数得到相似结果
- **类方法作为命名空间**：不需要实例化，避免状态管理
- **数学驱动**：核心算法完全基于贝塞尔曲线的数学定义
- **参数可调性强**：通过 8 个参数组合可生成千变万化的轨迹

### 7.3 潜在改进点

| 问题 | 建议 |
|------|------|
| `type` 参数使用魔法数字 | 可改用枚举类型 `SpeedType.UNIFORM` 等 |
| `simulation` 返回值格式不一致 | `trackArray` 最终返回列表而非字典，与 `simulation` 不统一 |
| `print(d)` 调试语句残留 | 第 144 行的 `print(d)` 应移除 |
| 摆动模式的直线斜率计算 | 当 `end[0] == start[0]` 时会除零，缺少防护 |
| 变量命名 | `cbb`、`yhh`、`pin`、`kg` 等命名不够语义化 |
