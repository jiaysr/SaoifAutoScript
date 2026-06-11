# utils/points.py 逐行代码详解

> 源文件路径：`module/base/utils/points.py`

---

## 1. 文件概述

`points.py` 提供了点（Points）和线（Lines）的几何计算框架，主要用于：
- **Points 类**：点集合的操作（均值、分组、连线）
- **Lines 类**：线集合的操作（极坐标表示、求交、分组、排序）
- **辅助函数**：区域与角点转换、透视变换、点拟合

适用于游戏地图网格识别、屏幕元素定位等场景。

---

## 2. 导入部分解释

```python
import numpy as np                    # 数值计算，数组操作
from scipy import optimize            # 优化算法（用于 fit_points）
from .utils import area_pad           # 从同包导入区域内缩函数
```

---

## 3. Points 类 — 点集合

### 3.1 `__init__(self, points)` — 构造函数

```python
class Points:
    def __init__(self, points):
        if points is None or len(points) == 0:
            self._bool = False
            self.points = None
        else:
            self._bool = True
            self.points = np.array(points)
            if len(self.points.shape) == 1:
                self.points = np.array([self.points])
            self.x, self.y = self.points.T
```

**第 8-17 行**：
- 空输入时 `_bool=False`，后续操作安全跳过
- 1D 数组（单个点）自动包装为 2D
- `self.x, self.y = self.points.T` 解构出 x 和 y 坐标数组

### 3.2 特殊方法

```python
    def __str__(self):        return str(self.points)     # 字符串表示
    __repr__ = __str__
    def __iter__(self):       return iter(self.points)     # 可迭代
    def __getitem__(self, item): return self.points[item]  # 下标访问
    def __len__(self):        return len(self.points) if self else 0  # 长度
    def __bool__(self):       return self._bool            # 布尔值
```

**第 19-37 行**：实现 Python 容器协议。

### 3.3 `link(self, point, is_horizontal=False)` — 连线生成

```python
    def link(self, point, is_horizontal=False):
        if is_horizontal:
            lines = [[y, np.pi / 2] for y in self.y]
            return Lines(lines, is_horizontal=True)
        else:
            x, y = point
            theta = -np.arctan((self.x - x) / (self.y - y))
            rho = self.x * np.cos(theta) + self.y * np.sin(theta)
            lines = np.array([rho, theta]).T
            return Lines(lines, is_horizontal=False)
```

**第 39-48 行**：
- 水平模式：生成水平线集合（theta = π/2）
- 非水平模式：计算每个点到目标点的极坐标线表示 (rho, theta)

### 3.4 `mean(self)` — 计算均值点

```python
    def mean(self):
        if not self:
            return None
        return np.round(np.mean(self.points, axis=0)).astype(int)
```

**第 50-54 行**：返回所有点的平均坐标（四舍五入为整数）。

### 3.5 `group(self, threshold=3)` — 点分组

```python
    def group(self, threshold=3):
        if not self:
            return np.array([])
        groups = []
        points = self.points
        if len(points) == 1:
            return np.array([points[0]])
        while len(points):
            p0, p1 = points[0], points[1:]
            distance = np.sum(np.abs(p1 - p0), axis=1)    # 曼哈顿距离
            new = Points(np.append(p1[distance <= threshold], [p0], axis=0)).mean().tolist()
            groups.append(new)
            points = p1[distance > threshold]
        return np.array(groups)
```

**第 56-71 行**：
- 贪心聚类算法
- 取第一个点，找所有曼哈顿距离 ≤ threshold 的点
- 这些点取均值作为一个组
- 剩余点继续分组

---

## 4. Lines 类 — 线集合（极坐标表示）

### 4.1 极坐标表示

线用 `(rho, theta)` 表示：
- `rho`：原点到线的距离
- `theta`：线的法线角度
- 方程：`x*cos(theta) + y*sin(theta) = rho`

### 4.2 `__init__(self, lines, is_horizontal)` — 构造函数

```python
class Lines:
    MID_Y = 360     # 参考 y 坐标（用于计算 mid）

    def __init__(self, lines, is_horizontal):
        if lines is None or len(lines) == 0:
            self._bool = False
            self.lines = None
        else:
            self._bool = True
            self.lines = np.array(lines)
            if len(self.lines.shape) == 1:
                self.lines = np.array([self.lines])
            self.rho, self.theta = self.lines.T
        self.is_horizontal = is_horizontal
```

**第 74-87 行**：与 Points 类似，解构出 rho 和 theta 数组。

### 4.3 属性

```python
    @property
    def sin(self):    return np.sin(self.theta)       # sin(theta)
    @property
    def cos(self):    return np.cos(self.theta)       # cos(theta)
```

**第 109-115 行**。

### 4.4 `mean` 属性 — 均值线

```python
    @property
    def mean(self):
        if not self:
            return None
        if self.is_horizontal:
            return np.mean(self.lines, axis=0)
        else:
            x = np.mean(self.mid)
            theta = np.mean(self.theta)
            rho = x * np.cos(theta) + self.MID_Y * np.sin(theta)
            return np.array((rho, theta))
```

**第 117-127 行**：
- 水平线：直接取 rho 和 theta 的均值
- 非水平线：先取 x 截距均值，再计算对应的 rho

### 4.5 `mid` 属性 — x 截距

```python
    @property
    def mid(self):
        if not self:
            return np.array([])
        if self.is_horizontal:
            return self.rho
        else:
            return (self.rho - self.MID_Y * self.sin) / self.cos
```

**第 129-136 行**：计算线在 y=MID_Y 处的 x 坐标。水平线的 mid 就是 rho。

### 4.6 坐标查询

```python
    def get_x(self, y):   return (self.rho - y * self.sin) / self.cos
    def get_y(self, x):   return (self.rho - x * self.cos) / self.sin
```

**第 138-142 行**：给定 y 求 x，或给定 x 求 y。

### 4.7 `add(self, other)` — 合并线集合

```python
    def add(self, other):
        if not other: return self
        if not self:  return other
        lines = np.append(self.lines, other.lines, axis=0)
        return Lines(lines, is_horizontal=self.is_horizontal)
```

**第 144-150 行**：合并两个线集合。

### 4.8 `move(self, x, y)` — 平移

```python
    def move(self, x, y):
        if not self: return self
        if self.is_horizontal:
            self.lines[:, 0] += y
        else:
            self.lines[:, 0] += x * self.cos + y * self.sin
        return Lines(self.lines, is_horizontal=self.is_horizontal)
```

**第 152-159 行**：水平线只受 y 影响，非水平线按极坐标公式平移。

### 4.9 `sort(self)` — 排序

```python
    def sort(self):
        if not self: return self
        lines = self.lines[np.argsort(self.mid)]
        return Lines(lines, is_horizontal=self.is_horizontal)
```

**第 161-165 行**：按 x 截距排序。

### 4.10 `group(self, threshold=3)` — 线分组

```python
    def group(self, threshold=3):
        if not self: return self
        lines = self.sort()
        prev = 0
        regrouped = []
        group = []
        for mid, line in zip(lines.mid, lines.lines):
            line = line.tolist()
            if mid - prev > threshold:
                if len(regrouped) == 0:
                    if len(group) != 0:
                        regrouped = [group]
                else:
                    regrouped += [group]
                group = [line]
            else:
                group.append(line)
            prev = mid
        regrouped += [group]
        regrouped = np.vstack([Lines(r, is_horizontal=self.is_horizontal).mean for r in regrouped])
        return Lines(regrouped, is_horizontal=self.is_horizontal)
```

**第 167-188 行**：
- 先排序
- 按 mid 值间距分组（间距 > threshold 则新组）
- 每组取均值线

### 4.11 `distance_to_point(self, point)` — 到点的距离

```python
    def distance_to_point(self, point):
        x, y = point
        return self.rho - x * self.cos - y * self.sin
```

**第 190-192 行**：点到线的有符号距离。

### 4.12 `cross_two_lines` / `cross` — 线求交

```python
    @staticmethod
    def cross_two_lines(lines1, lines2):
        for rho1, sin1, cos1 in zip(lines1.rho, lines1.sin, lines1.cos):
            for rho2, sin2, cos2 in zip(lines2.rho, lines2.sin, lines2.cos):
                a = np.array([[cos1, sin1], [cos2, sin2]])
                b = np.array([rho1, rho2])
                yield np.linalg.solve(a, b)

    def cross(self, other):
        points = np.vstack(self.cross_two_lines(self, other))
        return Points(points)
```

**第 194-205 行**：
- 两条线的方程组成 2x2 线性方程组
- 用 `np.linalg.solve` 求解交点
- `cross` 返回所有交点的 Points 对象

### 4.13 `delete(self, other, threshold=3)` — 删除重合线

```python
    def delete(self, other, threshold=3):
        if not self: return self
        other_mid = other.mid
        lines = []
        for mid, line in zip(self.mid, self.lines):
            if np.any(np.abs(other_mid - mid) < threshold):
                continue
            lines.append(line)
        return Lines(lines, is_horizontal=self.is_horizontal)
```

**第 207-218 行**：删除与 other 中 mid 值接近的线。

---

## 5. 辅助函数

### 5.1 `area2corner` / `corner2area` — 区域与角点互转

```python
def area2corner(area):    # (x1,y1,x2,y2) → [左上, 右上, 左下, 右下]
def corner2area(corner):  # [左上, 右上, 左下, 右下] → (x1,y1,x2,y2)
```

**第 221-241 行**。

### 5.2 `corner2inner` / `corner2outer` — 梯形内接/外接矩形

```python
def corner2inner(corner):  # 梯形内最大矩形
def corner2outer(corner):  # 梯形外最小矩形
```

**第 244-271 行**。

### 5.3 `trapezoid2area(corner, pad)` — 梯形转区域

```python
def trapezoid2area(corner, pad=0):
    if pad > 0:   return area_pad(corner2inner(corner), pad=pad)   # 内缩
    elif pad < 0: return area_pad(corner2outer(corner), pad=pad)   # 外扩
    else:         return area_pad(corner2area(corner), pad=pad)
```

**第 274-292 行**。

### 5.4 `points_to_area_generator(points, shape)` — 点网格生成区域

```python
def points_to_area_generator(points, shape):
    points = points.reshape(*shape[::-1], 2)
    for y in range(shape[1] - 1):
        for x in range(shape[0] - 1):
            area = np.array([points[y,x], points[y,x+1], points[y+1,x], points[y+1,x+1]])
            yield ((x, y), area)
```

**第 295-308 行**：将点网格转换为四边形区域的生成器。

### 5.5 `perspective_transform(points, data)` — 透视变换

```python
def perspective_transform(points, data):
    points = np.pad(np.array(points), ((0, 0), (0, 1)), mode='constant', constant_values=1)
    matrix = data.dot(points.T)
    x, y = matrix[0] / matrix[2], matrix[1] / matrix[2]
    return np.array([x, y]).T
```

**第 348-362 行**：使用 3x3 透视矩阵变换点坐标。

### 5.6 `fit_points(points, mod, encourage=1)` — 点拟合

```python
def fit_points(points, mod, encourage=1):
    encourage = np.square(encourage)
    mod = np.array(mod)
    points = np.array(points) % mod
    points = np.append(points - mod, points, axis=0)

    def cal_distance(point):
        distance = np.linalg.norm(points - point, axis=1)
        return np.sum(1 / (1 + np.exp(encourage / distance) / distance))

    area = np.append(-mod - 10, mod + 10)
    result = optimize.brute(cal_distance, ((area[0], area[2]), (area[1], area[3])))
    return result % mod
```

**第 365-395 行**：
- 找到一组点中最具代表性的点（考虑周期性网格）
- 使用暴力优化（`optimize.brute`）找到局部最优解
- `encourage` 控制拟合紧密度

---

## 6. 核心算法流程图

### 线分组算法

```
输入: 未排序的线集合
 │
 ▼
按 mid 值排序
 │
 ▼
遍历每条线:
  mid - prev > threshold ?
  ├─ 是 → 开始新组
  └─ 否 → 加入当前组
 │
 ▼
每组取均值线
 │
 ▼
返回分组后的线集合
```

### 线求交算法

```
线1: x*cos(θ1) + y*sin(θ1) = ρ1
线2: x*cos(θ2) + y*sin(θ2) = ρ2
 │
 ▼
矩阵形式: [cos(θ1) sin(θ1)] [x]   [ρ1]
          [cos(θ2) sin(θ2)] [y] = [ρ2]
 │
 ▼
np.linalg.solve(A, b) → [x, y]
 │
 ▼
返回交点
```

---

## 7. 使用示例

```python
# 创建点集
pts = Points([[10, 20], [12, 22], [50, 60], [52, 62]])
print(pts.mean())    # [31, 41]
print(pts.group(threshold=5))  # [[11, 21], [51, 61]]  两个聚类

# 创建线集并求交
lines1 = pts.link((100, 100))
lines2 = pts.link((0, 0))
intersections = lines1.cross(lines2)

# 区域转换
corner = area2corner((10, 20, 100, 200))
# [[10,20], [100,20], [10,200], [100,200]]

area = corner2area(corner)
# (10, 20, 100, 200)

# 透视变换
matrix = np.array([[1, 0, 10], [0, 1, 20], [0, 0, 1]])
new_points = perspective_transform([[0, 0], [100, 100]], matrix)
# [[10, 20], [110, 120]]
```

---

## 8. 设计模式总结

| 模式 | 说明 |
|------|------|
| **极坐标表示** | 线用 (rho, theta) 表示，便于求交和距离计算 |
| **空值安全** | 所有操作在 `_bool=False` 时安全返回空值或自身 |
| **链式操作** | `sort()`、`group()`、`move()` 等返回新对象，支持链式调用 |
| **生成器模式** | `points_to_area_generator` 使用 yield 惰性生成 |
| **数值优化** | `fit_points` 使用 scipy 暴力优化找全局最优 |
| **容器协议** | Points 和 Lines 实现 `__iter__`、`__getitem__`、`__len__`、`__bool__` |
