# timer.py 逐行代码详解

> 源文件路径：`module/base/timer.py`

---

## 1. 文件概述

`timer.py` 提供了时间相关的工具函数和一个计时器类，主要用于：
- **函数计时装饰器**：测量函数执行耗时
- **时间计算工具**：解析时间字符串，计算未来/过去时间、时间范围
- **Timer 类**：带确认计数的通用计时器，广泛用于自动化脚本中的超时判断和状态确认

---

## 2. 导入部分解释

```python
import time                                    # 提供 time.time() 获取当前时间戳（秒）
from datetime import datetime, timedelta       # datetime 用于日期时间操作，timedelta 用于时间偏移
from functools import wraps                    # wraps 用于装饰器中保留被装饰函数的元数据
```

---

## 3. 函数定义解释

### 3.1 `timer(function)` — 函数计时装饰器

```python
def timer(function):
```

**第 8 行**：定义装饰器函数 `timer`，接收一个函数作为参数。

```python
    @wraps(function)
    def function_timer(*args, **kwargs):
```

**第 12 行**：`@wraps(function)` 确保装饰后的函数保留原函数的 `__name__`、`__doc__` 等属性。
**第 13 行**：定义内部包装函数，`*args` 和 `**kwargs` 接收任意参数以兼容任何函数签名。

```python
        t0 = time.time()
        result = function(*args, **kwargs)
        t1 = time.time()
```

**第 14 行**：记录函数执行前的时间戳。
**第 16 行**：调用原始函数并保存返回值。
**第 17 行**：记录函数执行后的时间戳。

```python
        print('%s: %s s' % (function.__name__, str(round(t1 - t0, 10))))
        return result
```

**第 18 行**：打印函数名和执行耗时，保留 10 位小数。
**第 19 行**：返回原始函数的执行结果。

```python
    return function_timer
```

**第 21 行**：返回包装后的函数，完成装饰器逻辑。

---

### 3.2 `future_time(string)` — 获取未来时间

```python
def future_time(string):
```

**第 24 行**：定义函数，接收格式为 `"HH:MM"` 的时间字符串。

```python
    hour, minute = [int(x) for x in string.split(':')]
```

**第 32 行**：以 `:` 分割字符串，将小时和分钟转为整数。

```python
    future = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
```

**第 33 行**：获取当前时间，并将时、分替换为指定值，秒和微秒归零。

```python
    future = future + timedelta(days=1) if future < datetime.now() else future
```

**第 34 行**：如果计算出的时间已经过去（小于当前时间），则加 1 天，确保返回的是未来时间。

```python
    return future
```

**第 35 行**：返回 datetime 对象。

---

### 3.3 `past_time(string)` — 获取过去时间

```python
def past_time(string):
```

**第 38 行**：与 `future_time` 对称，获取过去的时间点。

```python
    hour, minute = [int(x) for x in string.split(':')]
    past = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    past = past - timedelta(days=1) if past > datetime.now() else past
```

**第 46-48 行**：逻辑与 `future_time` 相反——如果计算出的时间在未来，则减去 1 天。

```python
    return past
```

**第 49 行**：返回 datetime 对象。

---

### 3.4 `future_time_range(string)` — 获取未来时间范围

```python
def future_time_range(string):
```

**第 52 行**：接收格式为 `"HH:MM-HH:MM"` 的时间范围字符串。

```python
    start, end = [future_time(s) for s in string.split('-')]
```

**第 60 行**：以 `-` 分割，分别对起止时间调用 `future_time`。

```python
    if start > end:
        start = start - timedelta(days=1)
```

**第 61-62 行**：如果开始时间晚于结束时间（如 `23:30-06:30`，跨午夜），将开始时间减 1 天。

```python
    return start, end
```

**第 63 行**：返回 `(start, end)` 元组。

---

### 3.5 `time_range_active(time_range)` — 判断当前是否在时间范围内

```python
def time_range_active(time_range):
```

**第 66 行**：接收 `(start, end)` 时间范围元组。

```python
    return time_range[0] < datetime.now() < time_range[1]
```

**第 74 行**：判断当前时间是否在 start 和 end 之间，返回布尔值。

---

## 4. Timer 类逐行解释

### 4.1 `__init__(self, limit, count=0)` — 构造函数

```python
class Timer:
    def __init__(self, limit, count=0):
```

**第 77-78 行**：定义 Timer 类。`limit` 为超时时间（秒），`count` 为确认次数。

```python
        self.limit = limit
        self.count = count
        self._current = 0
        self._reach_count = count
```

**第 95 行**：保存超时限制。
**第 96 行**：保存确认次数阈值。
**第 97 行**：`_current` 记录计时器启动的时间戳，0 表示未启动。
**第 98 行**：`_reach_count` 初始化为 `count`，表示默认已达到确认次数（未启动状态）。

### 4.2 `start(self)` — 启动计时器

```python
    def start(self):
        if not self.started():
            self._current = time.time()
            self._reach_count = 0
        return self
```

**第 100-105 行**：如果计时器未启动，则记录当前时间并将确认计数归零。返回 `self` 支持链式调用。

### 4.3 `started(self)` — 判断是否已启动

```python
    def started(self):
        return bool(self._current)
```

**第 107-108 行**：`_current` 为 0 时返回 `False`，否则返回 `True`。

### 4.4 `current(self)` — 获取已流逝时间

```python
    def current(self):
        if self.started():
            return time.time() - self._current
        else:
            return 0.
```

**第 110-118 行**：已启动则返回从启动到现在的秒数，否则返回 0.0。

### 4.5 `reached(self)` — 判断是否超时

```python
    def reached(self):
        self._reach_count += 1
        return time.time() - self._current > self.limit and self._reach_count > self.count
```

**第 120-126 行**：
- 每次调用 `_reach_count` 自增 1
- 返回 `True` 需同时满足两个条件：超时 **且** 调用次数超过 `count`
- `count` 机制用于防止因单次截图耗时过长而误判超时

### 4.6 `reset(self)` — 重置计时器

```python
    def reset(self):
        self._current = time.time()
        self._reach_count = 0
        return self
```

**第 128-131 行**：重新记录启动时间，确认计数归零。

### 4.7 `clear(self)` — 清除计时器

```python
    def clear(self):
        self._current = 0
        self._reach_count = self.count
        return self
```

**第 133-136 行**：将 `_current` 置 0（未启动状态），`_reach_count` 设为 `count` 使下次 `reached()` 立即返回 `True`。

### 4.8 `reached_and_reset(self)` — 超时则重置

```python
    def reached_and_reset(self):
        if self.reached():
            self.reset()
            return True
        else:
            return False
```

**第 138-147 行**：组合操作——如果超时则重置并返回 `True`，否则返回 `False`。

### 4.9 `wait(self)` — 阻塞等待至超时

```python
    def wait(self):
        diff = self._current + self.limit - time.time()
        if diff > 0:
            time.sleep(diff)
        return self
```

**第 149-156 行**：计算剩余时间，如果大于 0 则 `sleep` 等待。

### 4.10 `show(self)` — 打印计时器状态

```python
    def show(self):
        from module.logger import logger
        logger.info(str(self))
```

**第 158-160 行**：延迟导入 logger 并打印当前状态。

### 4.11 `remain(self)` — 获取剩余时间

```python
    def remain(self):
        return self._current + self.limit - time.time()
```

**第 162-167 行**：返回距离超时还剩多少秒。

### 4.12 `__str__` / `__repr__` — 字符串表示

```python
    def __str__(self):
        return f'Timer(limit={round(self.current(), 3)}/{self.limit}, count={self._reach_count}/{self.count})'

    __repr__ = __str__
```

**第 169-172 行**：格式化输出当前已用时间/限制时间、当前确认次数/确认阈值。

---

## 5. 核心算法流程图

### Timer.reached() 判断流程

```
开始
 │
 ▼
_reach_count += 1
 │
 ▼
当前时间 - 启动时间 > limit ? ──否──▶ 返回 False
 │
 是
 │
 ▼
_reach_count > count ? ──否──▶ 返回 False
 │
 是
 │
 ▼
返回 True
```

### future_time 处理流程

```
输入: "14:59"
 │
 ▼
解析 hour=14, minute=59
 │
 ▼
替换当前时间为 14:59:00.000
 │
 ▼
14:59 < 当前时间 ? ──是──▶ +1天
 │
 否
 │
 ▼
返回 datetime
```

---

## 6. 使用示例

```python
# 函数计时装饰器
@timer
def slow_function():
    time.sleep(1.5)
# 输出: slow_function: 1.500234 s

# 未来时间
t = future_time("23:59")  # 返回今天的 23:59 或明天的 23:59

# 时间范围（跨午夜）
start, end = future_time_range("23:30-06:30")

# Timer 类基本用法
timer_obj = Timer(limit=5, count=2)
timer_obj.start()
# ... 执行某些操作 ...
if timer_obj.reached():  # 需要调用超过2次且超过5秒才返回True
    print("超时确认")

# Timer 常见模式
confirm_timer = Timer(limit=3, count=3).start()
if self.appear(MAIN_CHECK):
    if confirm_timer.reached():
        # 确认到达主页
        pass
else:
    confirm_timer.reset()
```

---

## 7. 设计模式总结

| 模式 | 说明 |
|------|------|
| **装饰器模式** | `timer()` 作为装饰器，在不修改原函数的情况下添加计时功能 |
| **确认计数模式** | `Timer` 的 `count` 参数实现"连续 N 次超时才确认"，防止误判 |
| **Builder 模式** | `start()`、`reset()`、`clear()` 均返回 `self`，支持链式调用 |
| **延迟导入** | `show()` 方法中延迟导入 `logger`，避免循环依赖 |
| **惰性初始化** | `_current=0` 表示未启动，`start()` 时才记录时间 |
