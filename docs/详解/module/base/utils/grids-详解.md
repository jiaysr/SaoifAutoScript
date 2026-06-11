# utils/grids.py 逐行代码详解

> 源文件路径：`module/base/utils/grids.py`

---

## 1. 文件概述

`grids.py` 实现了网格（Grid）集合的管理和操作框架，主要用于：
- **SelectedGrids 类**：网格集合的选择、过滤、排序、集合运算
- **RoadGrids 类**：路径网格管理，用于游戏中的道路/障碍判断

适用于游戏地图中网格单元的批量操作。

---

## 2. 导入部分解释

```python
import operator                    # operator.attrgetter 用于按属性排序
import typing as t                 # 类型注解
```

---

## 3. SelectedGrids 类 — 网格集合

### 3.1 `__init__(self, grids)` — 构造函数

```python
class SelectedGrids:
    def __init__(self, grids):
        self.grids = grids
        self.indexes: t.Dict[tuple, SelectedGrids] = {}
```

**第 5-8 行**：`grids` 是网格对象列表，`indexes` 用于存储索引（加速查询）。

### 3.2 容器协议

```python
    def __iter__(self):     return iter(self.grids)              # 可迭代
    def __getitem__(self, item):                                  # 下标访问
        if isinstance(item, int): return self.grids[item]
        else: return SelectedGrids(self.grids[item])              # 切片返回新集合
    def __contains__(self, item): return item in self.grids       # in 运算符
    def __str__(self):        return '[' + ', '.join([str(grid) for grid in self]) + ']'
    def __len__(self):        return len(self.grids)
    def __bool__(self):       return self.count > 0
```

**第 10-30 行**：实现完整的 Python 容器协议。注意 `__getitem__` 对切片返回新的 `SelectedGrids`。

### 3.3 属性

```python
    @property
    def location(self):   return [grid.location for grid in self.grids]    # 所有位置
    @property
    def cost(self):       return [grid.cost for grid in self.grids]        # 所有代价
    @property
    def weight(self):     return [grid.weight for grid in self.grids]      # 所有权重
    @property
    def count(self):      return len(self.grids)                           # 数量
```

**第 35-65 行**。

### 3.4 `select(self, **kwargs)` — 条件选择

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

**第 67-83 行**：
- 根据属性名和值过滤网格
- 类型和值都要精确匹配
- 返回新的 SelectedGrids

### 3.5 `create_index(*attrs)` / `indexed_select(*values)` — 索引查询

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

    def indexed_select(self, *values):
        return self.indexes.get(values, SelectedGrids([]))
```

**第 85-100 行**：
- `create_index`：按指定属性创建哈希索引，加速后续查询
- `indexed_select`：通过索引直接查找，O(1) 复杂度

### 3.6 `left_join(self, right, on_attr, set_attr, default)` — 左连接

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

**第 102-124 行**：类似 SQL 的左连接操作：
- 在 right 表上创建索引
- 遍历 self 的每个网格，按 on_attr 查找 right 中的匹配项
- 找到则复制 set_attr 属性，否则设为 default

### 3.7 `filter(self, func)` — 函数过滤

```python
    def filter(self, func):
        return SelectedGrids([grid for grid in self if func(grid)])
```

**第 126-136 行**：使用自定义函数过滤网格。

### 3.8 `set(self, **kwargs)` / `get(self, attr)` — 属性操作

```python
    def set(self, **kwargs):
        for grid in self:
            for key, value in kwargs.items():
                grid.__setattr__(key, value)

    def get(self, attr):
        return [grid.__getattribute__(attr) for grid in self.grids]
```

**第 138-159 行**：批量设置或获取属性。

### 3.9 `call(self, func, **kwargs)` — 批量调用

```python
    def call(self, func, **kwargs):
        return [grid.__getattribute__(func)(**kwargs) for grid in self]
```

**第 161-172 行**：对每个网格调用同名方法，返回结果列表。

### 3.10 `first_or_none(self)` — 获取首个或 None

```python
    def first_or_none(self):
        try:
            return self.grids[0]
        except IndexError:
            return None
```

**第 174-182 行**。

### 3.11 集合运算

```python
    def add(self, grids):
        return SelectedGrids(list(set(self.grids + grids.grids)))          # 并集（哈希去重）

    def add_by_eq(self, grids):
        new = []
        for grid in self.grids + grids.grids:
            if grid not in new: new.append(grid)
        return SelectedGrids(new)                                          # 并集（__eq__ 去重）

    def intersect(self, grids):
        return SelectedGrids(list(set(self.grids).intersection(set(grids.grids))))  # 交集

    def intersect_by_eq(self, grids):
        new = []
        for grid in self.grids:
            if grid in grids.grids: new.append(grid)
        return SelectedGrids(new)                                          # 交集（__eq__ 去重）

    def delete(self, grids):
        g = [grid for grid in self.grids if grid not in grids]
        return SelectedGrids(g)                                            # 差集
```

**第 184-247 行**：提供两套去重策略——基于 `__hash__`（快）和基于 `__eq__`（准）。

### 3.12 排序方法

```python
    def sort(self, *args):
        if not self: return self
        if len(args):
            grids = sorted(self.grids, key=operator.attrgetter(*args))
            return SelectedGrids(grids)
        else:
            return self
```

**第 249-263 行**：按属性名排序（如 `sort('cost', 'weight')`）。

```python
    def sort_by_camera_distance(self, camera):
        import numpy as np
        if not self: return self
        location = np.array(self.location)
        diff = np.sum(np.abs(location - camera), axis=1)     # 曼哈顿距离
        grids = tuple(np.array(self.grids)[np.argsort(diff)])
        return SelectedGrids(grids)
```

**第 265-280 行**：按到摄像机的曼哈顿距离排序。

```python
    def sort_by_clock_degree(self, center=(0, 0), start=(0, 1), clockwise=True):
        import numpy as np
        if not self: return self
        vector = np.subtract(self.location, center)
        theta = np.arctan2(vector[:, 1], vector[:, 0]) / np.pi * 180
        vector = np.subtract(start, center)
        theta = theta - np.arctan2(vector[1], vector[0]) / np.pi * 180
        if not clockwise: theta = -theta
        theta[theta < 0] += 360
        grids = tuple(np.array(self.grids)[np.argsort(theta)])
        return SelectedGrids(grids)
```

**第 282-303 行**：按顺时针/逆时针角度排序。

---

## 4. RoadGrids 类 — 路径网格

### 4.1 `__init__(self, grids)` — 构造函数

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

**第 306-317 行**：将输入的网格列表转为 `SelectedGrids` 列表。每个元素是一组可能的路径点。

### 4.2 `__str__` — 字符串表示

```python
    def __str__(self):
        return str(' - '.join([str(grid) for grid in self.grids]))
```

**第 319-320 行**：用 ` - ` 连接各段路径。

### 4.3 `roadblocks(self)` — 路障检测

```python
    def roadblocks(self):
        grids = []
        for block in self.grids:
            if block.count == block.select(is_enemy=True).count:
                grids += block.grids
        return SelectedGrids(grids)
```

**第 322-331 行**：如果一个路径段的所有网格都是敌人，则整段都是路障。

### 4.4 `potential_roadblocks(self)` — 潜在路障

```python
    def potential_roadblocks(self):
        grids = []
        for block in self.grids:
            if any([grid.is_fleet for grid in block]): continue    # 有舰队跳过
            if any([grid.is_cleared for grid in block]): continue  # 已清理跳过
            if block.count - block.select(is_enemy=True).count == 1:
                grids += block.select(is_enemy=True).grids
        return SelectedGrids(grids)
```

**第 333-346 行**：找到只剩一个非敌人网格的路径段，那些敌人就是潜在路障。

### 4.5 `first_roadblocks(self)` — 首个路障

```python
    def first_roadblocks(self):
        grids = []
        for block in self.grids:
            if any([grid.is_fleet for grid in block]): continue
            if any([grid.is_cleared for grid in block]): continue
            if block.select(is_enemy=True).count >= 1:
                grids += block.select(is_enemy=True).grids
        return SelectedGrids(grids)
```

**第 348-361 行**：找到第一个有敌人的路径段。

### 4.6 `combine(self, road)` — 路径组合

```python
    def combine(self, road):
        out = RoadGrids([])
        for select_1 in self.grids:
            for select_2 in road.grids:
                select = select_1.add(select_2)
                out.grids.append(select)
        return out
```

**第 363-376 行**：笛卡尔积组合两条路径的所有可能。

---

## 5. 核心算法流程图

### select() 过滤流程

```
输入: kwargs={is_enemy: True, is_cleared: False}
 │
 ▼
遍历所有 grid:
  │
  ▼
  对每个 kwarg:
    grid.attr == value 且 类型相同 ?
    ├─ 全部匹配 → 加入结果
    └─ 任一不匹配 → 跳过
 │
 ▼
返回新的 SelectedGrids
```

### left_join 流程

```
self (左表)          right (右表)
 │                     │
 │                     ▼
 │                create_index(on_attr)
 │                     │
 ▼                     ▼
遍历 self 的每个 grid:
  │
  ▼
  提取 on_attr 值
  │
  ▼
  indexed_select 查找 right
  ├─ 找到 → 复制 set_attr
  └─ 未找到 → 设为 default
 │
 ▼
返回 self（原地修改）
```

### 路障检测逻辑

```
路径段: [格A, 格B, 格C]
 │
 ▼
block.select(is_enemy=True) → [格A, 格B] (2个敌人)
 │
 ▼
block.count (3) == 敌人数 (2) ?
 ├─ 否 → 不是路障
 └─ 是 → 整段都是路障
```

---

## 6. 使用示例

```python
# 创建网格集合
grids = SelectedGrids([grid1, grid2, grid3, grid4])

# 条件选择
enemies = grids.select(is_enemy=True)
cleared = grids.select(is_cleared=True)

# 集合运算
all_grids = enemies.add(cleared)              # 并集
intersection = enemies.intersect(cleared)     # 交集
remaining = grids.delete(enemies)             # 差集

# 排序
sorted_by_cost = grids.sort('cost')
sorted_by_dist = grids.sort_by_camera_distance(camera=(100, 200))

# 索引加速查询
grids.create_index('type', 'level')
result = grids.indexed_select('enemy', 3)     # O(1) 查找

# 左连接
SelectedGrids(fleet_grids).left_join(
    right=SelectedGrids(status_grids),
    on_attr=['location'],
    set_attr=['hp', 'status'],
    default=0
)

# 路径管理
road = RoadGrids([[grid1, grid2], [grid3], [grid4, grid5]])
blockers = road.roadblocks()
potentials = road.potential_roadblocks()
```

---

## 7. 设计模式总结

| 模式 | 说明 |
|------|------|
| **集合抽象** | `SelectedGrids` 将网格列表抽象为可查询的集合，支持链式操作 |
| **索引优化** | `create_index` / `indexed_select` 实现哈希索引，加速重复查询 |
| **双去重策略** | `add`（哈希）vs `add_by_eq`（相等），适应不同场景 |
| **SQL 风格** | `select`、`filter`、`left_join`、`sort` 模拟 SQL 操作 |
| **不可变操作** | 大多数方法返回新集合而非修改原集合 |
| **延迟导入** | `sort_by_camera_distance` 内部导入 numpy，避免不必要的依赖 |
