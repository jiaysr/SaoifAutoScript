# module/map/map_grids.py 代码详解

## 1. 文件概述

`map_grids.py` 是地图网格操作模块，提供了对游戏地图网格(Grid)的集合操作能力。包含两个核心类：`SelectedGrids` 用于网格集合的选择和操作，`RoadGrids` 用于道路网格的路径分析。

**文件路径**: `module/map/map_grids.py`
**代码行数**: 377 行
**主要功能**:
- 网格集合的选择、过滤、排序
- 网格属性的批量操作
- 集合运算（并集、交集、差集）
- 道路阻塞分析
- 按距离和角度排序

---

## 2. 导入部分解释

```python
import operator
import typing as t
```

| 导入项 | 来源模块 | 说明 |
|--------|----------|------|
| `operator` | Python标准库 | 操作符模块，用于 `attrgetter` 属性获取 |
| `typing` | Python标准库 | 类型注解支持 |

---

## 3. 类定义解释

### SelectedGrids 类

```python
class SelectedGrids:
    def __init__(self, grids):
        self.grids = grids
        self.indexes: t.Dict[tuple, SelectedGrids] = {}
```

**核心属性**:
- `grids`: 网格对象列表
- `indexes`: 索引字典，用于快速查询

**设计意图**: 模拟 SQL 查询的链式操作，提供类似 ORM 的网格操作体验。

### RoadGrids 类

```python
class RoadGrids:
    def __init__(self, grids):
        self.grids = []
        for grid in grids:
            if isinstance(grid, list):
                self.grids.append(SelectedGrids(grids=grid))
            else:
                self.grids.append(SelectedGrids(grids=[grid]))
```

**设计意图**: 表示一条路径上的多个网格组，用于分析道路阻塞情况。

---

## 4. 每个方法的逐行解释

### SelectedGrids 类方法

#### `__init__` 方法

```python
def __init__(self, grids):
    self.grids = grids
    self.indexes: t.Dict[tuple, SelectedGrids] = {}
```

| 行号 | 代码 | 说明 |
|------|------|------|
| 6 | `self.grids = grids` | 存储网格列表 |
| 7 | `self.indexes = {}` | 初始化空索引字典 |

#### `__iter__` 方法

```python
def __iter__(self):
    return iter(self.grids)
```

使 `SelectedGrids` 可迭代，支持 `for grid in selected_grids` 语法。

#### `__getitem__` 方法

```python
def __getitem__(self, item):
    if isinstance(item, int):
        return self.grids[item]
    else:
        return SelectedGrids(self.grids[item])
```

| 行号 | 代码 | 说明 |
|------|------|------|
| 14 | `if isinstance(item, int):` | 判断索引类型 |
| 15 | `return self.grids[item]` | 整数索引返回单个网格 |
| 17 | `return SelectedGrids(self.grids[item])` | 切片索引返回新的 SelectedGrids |

#### `__contains__` 方法

```python
def __contains__(self, item):
    return item in self.grids
```

支持 `in` 运算符，判断网格是否在集合中。

#### `__str__` 方法

```python
def __str__(self):
    return '[' + ', '.join([str(grid) for grid in self]) + ']'
```

返回格式化的字符串表示，如 `[Grid(1,1), Grid(2,2)]`。

#### `__len__` 方法

```python
def __len__(self):
    return len(self.grids)
```

返回网格数量，支持 `len()` 函数。

#### `__bool__` 方法

```python
def __bool__(self):
    return self.count > 0
```

支持布尔判断，空集合返回 `False`。

#### `location` 属性

```python
@property
def location(self):
    return [grid.location for grid in self.grids]
```

返回所有网格的位置坐标列表。

#### `cost` 属性

```python
@property
def cost(self):
    return [grid.cost for grid in self.grids]
```

返回所有网格的消耗值列表。

#### `weight` 属性

```python
@property
def weight(self):
    return [grid.weight for grid in self.grids]
```

返回所有网格的权重列表。

#### `count` 属性

```python
@property
def count(self):
    return len(self.grids)
```

返回网格数量。

#### `select` 方法

```python
def select(self, **kwargs):
    def matched(obj):
        flag = True
        for k, v in kwargs.items():
            obj_v = obj.__getattribute__(k)
            if type(obj_v) != type(v) or obj_v != v:
                flag = False
        return flag
    return SelectedGrids([grid for grid in self.grids if matched(grid)])
```

**功能**: 根据属性条件筛选网格

| 行号 | 代码 | 说明 |
|------|------|------|
| 75 | `def matched(obj):` | 内部匹配函数 |
| 77 | `for k, v in kwargs.items():` | 遍历筛选条件 |
| 78 | `obj_v = obj.__getattribute__(k)` | 获取网格属性值 |
| 79 | `if type(obj_v) != type(v) or obj_v != v:` | 类型和值都要匹配 |
| 83 | `return SelectedGrids([...])` | 返回新的筛选结果 |

**使用示例**: `grids.select(is_enemy=True, is_cleared=False)`

#### `create_index` 方法

```python
def create_index(self, *attrs):
    indexes = {}
    for grid in self.grids:
        k = tuple(grid.__getattribute__(attr) for attr in attrs)
        try:
            indexes[k].append(grid)
        except KeyError:
            indexes[k] = [grid]
    indexes = {k: SelectedGrids(v) for k, v in indexes.items()}
    self.indexes = indexes
    return indexes
```

**功能**: 创建索引以加速查询

| 行号 | 代码 | 说明 |
|------|------|------|
| 86 | `indexes = {}` | 初始化索引字典 |
| 88-89 | 循环构建索引键 | 使用多个属性值组合作为键 |
| 90-93 | 添加到索引 | 键存在则追加，否则新建列表 |
| 95 | 转换为 SelectedGrids | 将列表转换为 SelectedGrids 对象 |

#### `indexed_select` 方法

```python
def indexed_select(self, *values):
    return self.indexes.get(values, SelectedGrids([]))
```

使用索引快速查询，避免遍历所有网格。

#### `left_join` 方法

```python
def left_join(self, right, on_attr, set_attr, default=None):
    right.create_index(*on_attr)
    for grid in self:
        attr_value = tuple([grid.__getattribute__(attr) for attr in on_attr])
        right_grid = right.indexed_select(*attr_value).first_or_none()
        if right_grid is not None:
            for attr in set_attr:
                grid.__setattr__(attr, right_grid.__getattribute__(attr))
        else:
            for attr in set_attr:
                grid.__setattr__(attr, default)
    return self
```

**功能**: 类似 SQL 的左连接操作

| 参数 | 说明 |
|------|------|
| `right` | 右表（SelectedGrids） |
| `on_attr` | 连接属性（元组） |
| `set_attr` | 要设置的属性（元组） |
| `default` | 无匹配时的默认值 |

#### `filter` 方法

```python
def filter(self, func):
    return SelectedGrids([grid for grid in self if func(grid)])
```

使用自定义函数过滤网格。

#### `set` 方法

```python
def set(self, **kwargs):
    for grid in self:
        for key, value in kwargs.items():
            grid.__setattr__(key, value)
```

批量设置网格属性。

#### `get` 方法

```python
def get(self, attr):
    return [grid.__getattribute__(attr) for grid in self.grids]
```

获取所有网格的指定属性值列表。

#### `call` 方法

```python
def call(self, func, **kwargs):
    return [grid.__getattribute__(func)(**kwargs) for grid in self]
```

批量调用网格方法。

#### `first_or_none` 方法

```python
def first_or_none(self):
    try:
        return self.grids[0]
    except IndexError:
        return None
```

返回第一个网格或 None。

#### `add` 方法

```python
def add(self, grids):
    return SelectedGrids(list(set(self.grids + grids.grids)))
```

集合并集（基于 hash 去重）。

#### `add_by_eq` 方法

```python
def add_by_eq(self, grids):
    new = []
    for grid in self.grids + grids.grids:
        if grid not in new:
            new.append(grid)
    return SelectedGrids(new)
```

集合并集（基于 `__eq__` 去重）。

#### `intersect` 方法

```python
def intersect(self, grids):
    return SelectedGrids(list(set(self.grids).intersection(set(grids.grids))))
```

集合交集（基于 hash）。

#### `intersect_by_eq` 方法

```python
def intersect_by_eq(self, grids):
    new = []
    for grid in self.grids:
        if grid in grids.grids:
            new.append(grid)
    return SelectedGrids(new)
```

集合交集（基于 `__eq__`）。

#### `delete` 方法

```python
def delete(self, grids):
    g = [grid for grid in self.grids if grid not in grids]
    return SelectedGrids(g)
```

集合差集。

#### `sort` 方法

```python
def sort(self, *args):
    if not self:
        return self
    if len(args):
        grids = sorted(self.grids, key=operator.attrgetter(*args))
        return SelectedGrids(grids)
    else:
        return self
```

按属性排序网格。

#### `sort_by_camera_distance` 方法

```python
def sort_by_camera_distance(self, camera):
    import numpy as np
    if not self:
        return self
    location = np.array(self.location)
    diff = np.sum(np.abs(location - camera), axis=1)
    grids = tuple(np.array(self.grids)[np.argsort(diff)])
    return SelectedGrids(grids)
```

按曼哈顿距离排序（距离相机由近到远）。

#### `sort_by_clock_degree` 方法

```python
def sort_by_clock_degree(self, center=(0, 0), start=(0, 1), clockwise=True):
    import numpy as np
    if not self:
        return self
    vector = np.subtract(self.location, center)
    theta = np.arctan2(vector[:, 1], vector[:, 0]) / np.pi * 180
    vector = np.subtract(start, center)
    theta = theta - np.arctan2(vector[1], vector[0]) / np.pi * 180
    if not clockwise:
        theta = -theta
    theta[theta < 0] += 360
    grids = tuple(np.array(self.grids)[np.argsort(theta)])
    return SelectedGrids(grids)
```

按顺时针/逆时针角度排序。

---

### RoadGrids 类方法

#### `__init__` 方法

```python
def __init__(self, grids):
    self.grids = []
    for grid in grids:
        if isinstance(grid, list):
            self.grids.append(SelectedGrids(grids=grid))
        else:
            self.grids.append(SelectedGrids(grids=[grid]))
```

将输入的网格列表转换为 `SelectedGrids` 列表。

#### `roadblocks` 方法

```python
def roadblocks(self):
    grids = []
    for block in self.grids:
        if block.count == block.select(is_enemy=True).count:
            grids += block.grids
    return SelectedGrids(grids)
```

返回完全被敌人阻塞的网格。

#### `potential_roadblocks` 方法

```python
def potential_roadblocks(self):
    grids = []
    for block in self.grids:
        if any([grid.is_fleet for grid in block]):
            continue
        if any([grid.is_cleared for grid in block]):
            continue
        if block.count - block.select(is_enemy=True).count == 1:
            grids += block.select(is_enemy=True).grids
    return SelectedGrids(grids)
```

返回潜在的阻塞网格（仅剩一个非敌人网格）。

#### `first_roadblocks` 方法

```python
def first_roadblocks(self):
    grids = []
    for block in self.grids:
        if any([grid.is_fleet for grid in block]):
            continue
        if any([grid.is_cleared for grid in block]):
            continue
        if block.select(is_enemy=True).count >= 1:
            grids += block.select(is_enemy=True).grids
    return SelectedGrids(grids)
```

返回第一个遇到的敌人网格。

#### `combine` 方法

```python
def combine(self, road):
    out = RoadGrids([])
    for select_1 in self.grids:
        for select_2 in road.grids:
            select = select_1.add(select_2)
            out.grids.append(select)
    return out
```

组合两条道路的所有可能路径。

---

## 5. 核心算法流程图

### SelectedGrids 操作流程

```
┌─────────────────────────────────────────────────────┐
│                 SelectedGrids 操作                   │
└───────────────────────────┬─────────────────────────┘
                            │
    ┌───────────────────────┼───────────────────────┐
    │                       │                       │
    ▼                       ▼                       ▼
┌─────────┐           ┌─────────┐           ┌─────────┐
│  选择    │           │  排序    │           │  集合    │
│ select  │           │  sort   │           │ 运算     │
└────┬────┘           └────┬────┘           └────┬────┘
     │                     │                     │
     ▼                     ▼                     ▼
┌─────────┐           ┌─────────┐           ┌─────────┐
│ filter  │           │ 按属性   │           │ add     │
│ 按条件   │           │ 按距离   │           │ intersect│
│ 过滤    │           │ 按角度   │           │ delete  │
└─────────┘           └─────────┘           └─────────┘
```

### 道路阻塞分析流程

```
┌─────────────────────────────────────┐
│         RoadGrids 分析              │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   遍历每个 block (网格组)            │
└─────────────────┬───────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
┌───────────────┐   ┌───────────────┐
│ roadblocks    │   │ potential_    │
│ 全是敌人?     │   │ roadblocks    │
│ → 完全阻塞    │   │ 仅剩1个非敌人?│
└───────────────┘   │ → 潜在阻塞    │
                    └───────────────┘
```

### 排序算法流程

```
┌─────────────────────────────────────┐
│     sort_by_camera_distance         │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   location = np.array(locations)    │
│   diff = Σ|location - camera|       │
│   (曼哈顿距离)                       │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   np.argsort(diff)                  │
│   按距离升序排列                      │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│     sort_by_clock_degree            │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   vector = location - center        │
│   θ = arctan2(y, x) (弧度→角度)     │
│   θ = θ - start角度                 │
│   顺时针: θ < 0 → θ += 360          │
│   逆时针: θ = -θ                    │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   np.argsort(theta)                 │
│   按角度升序排列                      │
└─────────────────────────────────────┘
```

---

## 6. 使用示例

### 基本选择和过滤

```python
from module.map.map_grids import SelectedGrids

# 假设有网格列表
grids = SelectedGrids([grid1, grid2, grid3, grid4])

# 选择敌人网格
enemy_grids = grids.select(is_enemy=True)
print(f"敌人网格数量: {enemy_grids.count}")

# 过滤已清除的网格
cleared = grids.filter(lambda g: g.is_cleared)
```

### 集合运算

```python
# 并集
all_grids = grids_a.add(grids_b)

# 交集
common_grids = grids_a.intersect(grids_b)

# 差集
remaining = grids_a.delete(grids_b)
```

### 排序操作

```python
# 按消耗排序
sorted_by_cost = grids.sort('cost')

# 按相机距离排序
camera_pos = (100, 200)
nearest = grids.sort_by_camera_distance(camera_pos)

# 按顺时针角度排序
center = (50, 50)
clockwise = grids.sort_by_clock_degree(center=center, clockwise=True)
```

### 批量操作

```python
# 批量设置属性
grids.set(is_visited=True, step_count=3)

# 批量获取属性
costs = grids.get('cost')

# 批量调用方法
results = grids.call('calculate_distance', target=(10, 20))
```

### 索引查询

```python
# 创建索引
grids.create_index('x', 'y')

# 使用索引查询
result = grids.indexed_select(5, 10)  # 查询 x=5, y=10 的网格
```

### 左连接操作

```python
# 类似 SQL 的 LEFT JOIN
grids.left_join(
    right=other_grids,
    on_attr=('x', 'y'),
    set_attr=('enemy_type', 'danger_level'),
    default=0
)
```

### 道路分析

```python
from module.map.map_grids import RoadGrids

road = RoadGrids([[grid1, grid2], [grid3], [grid4, grid5]])

# 获取完全阻塞的网格
blocks = road.roadblocks()

# 获取潜在阻塞
potential = road.potential_roadblocks()

# 组合两条道路
combined = road1.combine(road2)
```

---

## 7. 设计模式总结

| 设计模式 | 应用说明 |
|----------|----------|
| **集合模式** | `SelectedGrids` 封装了集合操作（并、交、差） |
| **链式调用** | 方法返回新的 `SelectedGrids`，支持链式操作 |
| **迭代器模式** | 实现 `__iter__` 支持 for 循环遍历 |
| **索引模式** | `create_index` 创建索引加速查询 |
| **策略模式** | 不同的排序策略（按属性、距离、角度） |
| **SQL 类比** | `select`、`filter`、`left_join` 模拟 SQL 操作 |

**设计优点**:
- 接口设计简洁，类似 SQL 查询语法
- 支持链式操作，代码可读性强
- 索引机制提升查询性能
- 集合运算完整（并、交、差）
- 多种排序方式满足不同需求

**性能优化**:
- 使用 NumPy 进行距离和角度计算
- 索引机制避免重复遍历
- 惰性计算（仅在需要时导入 NumPy）

**适用场景**:
- 游戏地图路径规划
- 网格选择和过滤
- 道路阻塞分析
- 敌人位置分析
