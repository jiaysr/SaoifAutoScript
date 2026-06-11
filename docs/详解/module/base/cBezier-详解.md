# cBezier.py 逐行代码详解

> 源文件路径：`module/base/cBezier.py`
> 参考来源：https://github.com/2833844911/gurs
> 作者：cbb

---

## 1. 文件概述

`cBezier.py` 基于贝塞尔曲线实现模拟人手动滑动的轨迹生成器，主要用于：
- 模拟自然的手指/鼠标滑动轨迹
- 生成轨迹数组用于自动化操作
- 支持多种滑动速度模式（匀速、先慢后快、先快后慢等）
- 支持终点来回摆动效果

---

## 2. 导入部分解释

```python
import numpy as np       # 数值计算，数组操作
import math              # 阶乘计算 math.factorial
import random            # 随机数，用于轨迹扰动
```

---

## 3. BezierTrajectory 类逐行解释

### 3.1 `_bztsg(cls, dataTrajectory)` — 贝塞尔曲线方程生成器

```python
@classmethod
def _bztsg(cls, dataTrajectory):
```

**第 16-17 行**：类方法，接收控制点列表，返回贝塞尔曲线的 y 值函数。

```python
    lengthOfdata = len(dataTrajectory)
```

**第 18 行**：获取控制点数量（决定贝塞尔曲线的阶数）。

```python
    def staer(x):
        t = ((x - dataTrajectory[0][0]) / (dataTrajectory[-1][0] - dataTrajectory[0][0]))
```

**第 20-21 行**：内部函数 `staer(x)` 计算给定 x 对应的 y 值。
- `t` 是参数化值，将 x 映射到 `[0, 1]` 区间

```python
        y = np.array([0, 0], dtype=np.float64)
        for s in range(len(dataTrajectory)):
            y += dataTrajectory[s] * (
                (math.factorial(lengthOfdata - 1) /
                 (math.factorial(s) * math.factorial(lengthOfdata - 1 - s))) *
                math.pow(t, s) *
                math.pow((1 - t), lengthOfdata - 1 - s)
            )
        return y[1]
```

**第 22-27 行**：贝塞尔曲线公式：
$$B(t) = \sum_{i=0}^{n} \binom{n}{i} (1-t)^{n-i} t^i P_i$$

- `math.factorial(n-1) / (factorial(s) * factorial(n-1-s))` = 组合数 $\binom{n-1}{s}$
- `math.pow(t, s)` = $t^s$
- `math.pow((1-t), n-1-s)` = $(1-t)^{n-1-s}$
- 最终返回 y 坐标（`y[1]`）

```python
    return staer
```

**第 29 行**：返回闭包函数。

---

### 3.2 `_type(cls, type, x, numberList)` — 速度分布生成

```python
@classmethod
def _type(cls, type, x, numberList):
```

**第 31-32 行**：根据速度类型生成 x 轴的分布点。

```python
    numberListre = []
    pin = (x[1] - x[0]) / numberList
```

**第 33-34 行**：`pin` 是每个点的步长。

```python
    if type == 0:                    # 匀速
        for i in range(numberList):
            numberListre.append(i * pin)
        if pin >= 0:
            numberListre = numberListre[::-1]
```

**第 35-39 行**：类型 0 = 均匀分布（匀速滑动）。如果步长为正则反转（从终点到起点）。

```python
    elif type == 1:                  # 先慢后快（加速）
        for i in range(numberList):
            numberListre.append(1 * ((i * pin) ** 2))
        numberListre = numberListre[::-1]
```

**第 40-43 行**：类型 1 = 二次函数分布，开始时变化慢，结束时变化快。

```python
    elif type == 2:                  # 先快后慢（减速）
        for i in range(numberList):
            numberListre.append(1 * ((i * pin - x[1]) ** 2))
```

**第 44-46 行**：类型 2 = 反向二次函数，开始快结束慢。

```python
    elif type == 3:                  # 先慢中间快后慢（S形）
        dataTrajectory = [
            np.array([0,0]),
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

**第 48-55 行**：类型 3 = 使用贝塞尔曲线本身作为速度分布，实现 S 形加速-减速。

```python
    numberListre = np.abs(np.array(numberListre) - max(numberListre))
    biaoNumberList = ((numberListre - numberListre[numberListre.argmin()]) /
                      (numberListre[numberListre.argmax()] - numberListre[numberListre.argmin()])) * (x[1] - x[0]) + x[0]
    biaoNumberList[0] = x[0]
    biaoNumberList[-1] = x[1]
    return biaoNumberList
```

**第 56-61 行**：归一化处理——将分布映射到 `[x[0], x[1]]` 范围，确保首尾精确。

---

### 3.3 `getFun(cls, s)` — 获取贝塞尔方程

```python
@classmethod
def getFun(cls, s):
    dataTrajectory = []
    for i in s:
        dataTrajectory.append(np.array(i))
    return cls._bztsg(dataTrajectory)
```

**第 63-73 行**：将坐标列表转为 numpy 数组，返回贝塞尔曲线方程。

---

### 3.4 `simulation(cls, start, end, le, deviation, bias)` — 模拟轨迹

```python
@classmethod
def simulation(cls, start, end, le=1, deviation=0, bias=0.5):
```

**第 75-76 行**：生成模拟人类滑动的贝塞尔曲线。

```python
    start = np.array(start)
    end = np.array(end)
    cbb = []
    if le != 1:
        e = (1 - bias) / (le - 1)
        cbb = [[bias + e * i, bias + e * (i + 1)] for i in range(le - 1)]
```

**第 86-91 行**：
- `le`：贝塞尔曲线阶数
- `bias`：控制点分布位置
- `cbb`：每个控制点在起止点之间的比例范围

```python
    dataTrajectoryList = [start]
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

**第 93-104 行**：
- 起始点加入列表
- `t` 随机选择 -1 或 1（控制扰动方向）
- 为每个控制点生成随机位置，在直线轨迹基础上添加上下扰动
- 每 2 个控制点切换一次扰动方向

```python
    dataTrajectoryList.append(end)
    return {"equation": cls._bztsg(dataTrajectoryList), "P": np.array(dataTrajectoryList)}
```

**第 106-107 行**：添加终点，返回曲线方程和控制点。

---

### 3.5 `trackArray(cls, ...)` — 生成轨迹数组

```python
@classmethod
def trackArray(cls, start, end, numberList, le=1, deviation=0, bias=0.5,
               type=0, cbb=0, yhh=10):
```

**第 109-110 行**：核心方法，生成完整的轨迹点数组。

```python
    s = []
    fun = cls.simulation(start, end, le, deviation, bias)
    w = fun['P']
    fun = fun["equation"]
```

**第 124-127 行**：获取模拟曲线的方程和控制点。

```python
    if cbb != 0:   # 需要终点摆动
        numberListOfcbb = round(numberList * 0.2 / (cbb + 1))
        numberList -= (numberListOfcbb * (cbb + 1))
```

**第 128-130 行**：如果有终点摆动，将 20% 的点数分配给摆动。

```python
        xTrackArray = cls._type(type, [start[0], end[0]], numberList)
        for i in xTrackArray:
            s.append([i, fun(i)])
```

**第 132-134 行**：生成主轨迹段。

```python
        dq = yhh / cbb
        kg = 0
        ends = np.copy(end)
        for i in range(cbb):
            if kg == 0:
                d = np.array([end[0] + (yhh - dq * i), ...])
                kg = 1
            else:
                d = np.array([end[0] - (yhh - dq * i), ...])
                kg = 0
            y = cls.trackArray(ends, d, numberListOfcbb, le=2, ...)
            s += list(y['trackArray'])
            ends = d
```

**第 135-148 行**：生成终点来回摆动轨迹，递归调用自身。

```python
    else:   # 无摆动
        xTrackArray = cls._type(type, [start[0], end[0]], numberList)
        for i in xTrackArray:
            s.append([i, fun(i)])
```

**第 152-155 行**：无摆动时直接生成轨迹。

```python
    return [[int(s[0]), int(s[1])] for s in s]
```

**第 157 行**：返回整数坐标列表 `[[x, y], [x, y], ...]`。

---

## 4. 核心算法流程图

### 贝塞尔曲线计算

```
控制点: P0, P1, P2, ..., Pn
 │
 ▼
对于参数 t ∈ [0, 1]:
  B(t) = Σ C(n,i) * t^i * (1-t)^(n-i) * Pi
         i=0..n
 │
 ▼
其中 C(n,i) = n! / (i! * (n-i)!)
 │
 ▼
得到曲线上的点 (x, y)
```

### trackArray 生成流程

```
输入: start, end, numberList, type, cbb
 │
 ▼
simulation() 生成贝塞尔曲线方程
 │
 ▼
cbb != 0 ?
 ├─ 否 → _type(type) 生成 x 分布 → 计算 y → 返回轨迹
 └─ 是 → 分配 80% 点数给主轨迹
         │
         ▼
         生成主轨迹段
         │
         ▼
         循环 cbb 次:
           计算摆动目标点
           递归调用 trackArray 生成摆动段
         │
         ▼
         生成回到终点的轨迹
         │
         ▼
         合并所有轨迹点
```

### 速度类型对比

```
type=0 匀速:     ●●●●●●●●●●
type=1 先慢后快: ●●●●●●●●●●  (点从密到疏)
type=2 先快后慢: ●●●●●●●●●●  (点从疏到密)
type=3 S形:      ●●●●●●●●●●  (两端密中间疏)
```

---

## 5. 使用示例

```python
# 基本滑动轨迹
track = BezierTrajectory.trackArray(
    start=[100, 500],
    end=[100, 100],
    numberList=50,
    le=2,         # 二阶贝塞尔
    deviation=10, # 上下波动10像素
    type=0        # 匀速
)
# 返回: [[100, 500], [100, 492], ..., [100, 100]]

# 先慢后快的滑动
track = BezierTrajectory.trackArray(
    start=[0, 0],
    end=[100, 100],
    numberList=100,
    type=1
)

# 带终点摆动的滑动（模拟人类微调）
track = BezierTrajectory.trackArray(
    start=[200, 400],
    end=[200, 200],
    numberList=80,
    le=3,
    deviation=5,
    type=3,       # S形速度
    cbb=2,        # 摆动2次
    yhh=15        # 摆动范围15像素
)
```

---

## 6. 设计模式总结

| 模式 | 说明 |
|------|------|
| **闭包模式** | `_bztsg` 返回内部函数 `staer`，封装曲线方程 |
| **递归** | `trackArray` 递归调用自身生成摆动段 |
| **工厂方法** | `simulation` 和 `trackArray` 作为类方法，无需实例化 |
| **参数化设计** | 通过 `type`、`le`、`deviation`、`bias` 等参数组合实现多种轨迹风格 |
| **数学建模** | 使用贝塞尔曲线数学公式模拟自然滑动轨迹 |
