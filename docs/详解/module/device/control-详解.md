# module.device.control 模块详解

## 1. 文件概述

`control.py` 定义了 `Control` 类，负责设备的**输入控制**，包括：
- 点击（click）、长按（long_click）
- 滑动（swipe）、向量滑动（swipe_vector）
- 拖拽（drag）
- 多次点击（multi_click）

支持多种控制方法：ADB、uiautomator2、minitouch、window_message、scrcpy。

**文件路径**: `module/device/control.py`
**代码行数**: 250 行

## 2. 导入部分解释

```python
from module.base.decorator import cached_property  # 缓存属性
from module.base.timer import Timer                # 定时器
from module.base.utils import *                    # 工具函数（ensure_int, point2str 等）
from module.device.env import IS_WINDOWS           # 平台检测
from module.device.method.minitouch import Minitouch  # minitouch 控制方法
from module.device.method.adb import Adb           # ADB 控制方法
from module.device.method.scrcpy import Scrcpy     # scrcpy 控制方法
from module.device.method.windows import Window    # Windows 窗口消息控制方法
from module.logger import logger
```

## 3. 类定义解释

```python
class Control(Minitouch, Adb, Scrcpy, Window):
```

通过多重继承组合所有控制方法。方法解析顺序（MRO）决定了属性查找优先级。

## 4. 方法逐行解释

### 4.1 `handle_control_check(self, button)` — 控制检查钩子（第 16-18 行）

```python
def handle_control_check(self, button):
    # Will be overridden in Device
    pass
```

占位方法，在 `Device` 类中被重写，用于记录点击和检测卡死。

### 4.2 `click_methods` — 点击方法映射（第 20-29 行）

```python
@cached_property
def click_methods(self):
    return {
        'ADB': self.click_adb,                       # adb shell input tap
        'uiautomator2': self.click_uiautomator2,     # u2.click()
        'minitouch': self.click_minitouch,            # minitouch 协议
        'window_message': self.click_window_message if IS_WINDOWS else None,  # Win32 消息
    }
```

### 4.3 `long_click_methods` — 长按方法映射（第 31-41 行）

```python
@cached_property
def long_click_methods(self):
    return {
        'ADB': self.long_click_adb,
        'uiautomator2': self.long_click_uiautomator2,
        'minitouch': self.long_click_minitouch,
        'window_message': self.long_click_window_message if IS_WINDOWS else None,
        'scrcpy': self.long_click_scrcpy
    }
```

### 4.4 `click(self, x, y, control_check, control_name)` — 点击（第 63-82 行）

```python
def click(self, x: int, y: int, control_check=True, control_name='Click') -> None:
    if control_check:
        self.handle_control_check(control_name)  # 记录点击，检测卡死
    x, y = ensure_int(x, y)  # 确保整数坐标
    logger.info('Click %s @ %s' % (point2str(x, y), control_name))
    method = self.click_methods.get(
        self.config.script.device.control_method,
        self.click_adb  # 默认 ADB
    )
    method(x, y)  # 执行点击
```

### 4.5 `multi_click(self, button, n, interval)` — 多次点击（第 85-101 行）

```python
def multi_click(self, button, n, interval=(0.1, 0.2)):
    self.handle_control_check(button)
    click_timer = Timer(0.1)
    for _ in range(n):
        remain = ensure_time(interval) - click_timer.current()  # 计算剩余等待时间
        if remain > 0:
            self.sleep(remain)  # 等待间隔
        click_timer.reset()
        self.click(button, control_check=False)  # 不重复检查
```

### 4.6 `long_click(self, x, y, duration, control_name)` — 长按（第 131-151 行）

```python
def long_click(self, x: int, y: int, duration=(0.5, 2), control_name='LongClick') -> None:
    self.handle_control_check(control_name)
    x, y = ensure_int(x, y)
    if duration is None:
        duration = 0.8
    duration = ensure_time(duration)  # 如果是范围则随机取值
    logger.info('Click %s @ %s %s' % (point2str(x, y), control_name, duration))
    method = self.long_click_methods.get(
        self.config.script.device.control_method,
        self.long_click_adb
    )
    method(x, y, duration)
```

### 4.7 `swipe(self, p1, p2, duration, control_name, distance_check)` — 滑动（第 153-198 行）

```python
def swipe(self, p1, p2, duration=(0.1, 0.2), control_name='SWIPE', distance_check=True):
    self.handle_control_check(control_name)
    p1, p2 = ensure_int(p1, p2)
    duration = ensure_time(duration)

    # 根据方法记录不同格式的日志
    method = self.config.script.device.control_method
    if method == 'minitouch':
        logger.info('Swipe %s -> %s' % (point2str(*p1), point2str(*p2)))
    elif method == 'uiautomator2':
        logger.info('Swipe %s -> %s, %s' % (point2str(*p1), point2str(*p2), duration))
    else:
        duration *= 2.5  # ADB 需要更慢的滑动
        logger.info('Swipe %s -> %s, %s' % (point2str(*p1), point2str(*p2), duration))

    # 距离检查
    if distance_check:
        if p1[0] == p2[0]:
            p1[0] += 1  # 避免 x 距离为 0
        if p1[1] == p2[1]:
            p1[1] += 1  # 避免 y 距离为 0
        if np.linalg.norm(np.subtract(p1, p2)) < 10:
            logger.info('Swipe distance < 10px, dropped')  # 距离太短，跳过
            return

    # 执行滑动
    if method == 'minitouch':
        self.swipe_minitouch(p1, p2)
    elif method == 'window_message':
        self.swipe_window_message(p1, p2)
    elif method == 'uiautomator2':
        self.swipe_uiautomator2(p1, p2, duration=duration)
    elif method == 'scrcpy':
        self.swipe_scrcpy(p1, p2)
    else:
        self.swipe_adb(p1, p2, duration=duration)
```

### 4.8 `swipe_vector(self, vector, box, ...)` — 向量滑动（第 200-226 行）

```python
def swipe_vector(self, vector, box=(123, 159, 1175, 628), random_range=(0, 0, 0, 0),
                 padding=15, duration=(0.1, 0.2), whitelist_area=None,
                 blacklist_area=None, name='SWIPE', distance_check=True):
    # 根据向量和边界框生成随机起止点
    p1, p2 = random_rectangle_vector_opted(
        vector,
        box=box,
        random_range=random_range,
        padding=padding,
        whitelist_area=whitelist_area,
        blacklist_area=blacklist_area
    )
    self.swipe(p1, p2, duration=duration, name=name, distance_check=distance_check)
```

**参数说明**:
- `vector`: 滑动方向向量 `(x, y)`
- `box`: 滑动区域边界框 `(x1, y1, x2, y2)`
- `random_range`: 随机偏移范围
- `whitelist_area`: 安全落点区域列表
- `blacklist_area`: 禁止落点区域列表

### 4.9 `drag(self, p1, p2, ...)` — 拖拽（第 228-250 行）

```python
def drag(self, p1, p2, segments=1, shake=(0, 15), point_random=(-10, -10, 10, 10),
         shake_random=(-5, -5, 5, 5), swipe_duration=0.25, shake_duration=0.1, name='DRAG'):
    self.handle_control_check(name)
    p1, p2 = ensure_int(p1, p2)
    logger.info('Drag %s -> %s' % (point2str(*p1), point2str(*p2)))

    method = self.config.script.emulator.control_method
    if method == 'minitouch':
        self.drag_minitouch(p1, p2, point_random=point_random)
    elif method == 'uiautomator2':
        self.drag_uiautomator2(
            p1, p2, segments=segments, shake=shake,
            point_random=point_random, shake_random=shake_random,
            swipe_duration=swipe_duration, shake_duration=shake_duration)
    elif method == 'scrcpy':
        self.drag_scrcpy(p1, p2, point_random=point_random)
    else:
        logger.warning(f'Control method {method} does not support drag well')
        self.swipe_adb(p1, p2, duration=ensure_time(swipe_duration * 2))
```

## 5. 核心算法流程图

```
click(x, y) 流程:
  │
  ├── 1. handle_control_check()  ← 记录 + 卡死检测
  │
  ├── 2. ensure_int(x, y)  ← 坐标整数化
  │
  ├── 3. 选择控制方法
  │     ├── 'ADB'            → adb shell input tap x y
  │     ├── 'uiautomator2'   → u2.click(x, y)
  │     ├── 'minitouch'      → minitouch 协议触摸
  │     └── 'window_message' → Win32 SendMessage
  │
  └── 4. method(x, y)  ← 执行点击

swipe(p1, p2) 流程:
  │
  ├── 1. handle_control_check()
  │
  ├── 2. 距离检查
  │     ├── x/y 距离为 0 → 偏移 1px
  │     └── 总距离 < 10px → 跳过
  │
  ├── 3. 选择控制方法
  │     ├── 'minitouch'      → swipe_minitouch()
  │     ├── 'window_message' → swipe_window_message()
  │     ├── 'uiautomator2'   → swipe_uiautomator2(duration)
  │     ├── 'scrcpy'         → swipe_scrcpy()
  │     └── 'ADB'            → swipe_adb(duration * 2.5)
  │
  └── 4. 执行滑动

拖拽与普通滑动的区别:
  ├── drag 支持 segments（分段数）
  ├── drag 支持 shake（到达后抖动）
  ├── drag 支持 point_random（点随机偏移）
  └── drag 支持 shake_random（抖动随机偏移）
```

## 6. 使用示例

```python
control = Control(config="oas1")

# 点击屏幕坐标 (640, 360)
control.click(640, 360, control_name='CENTER')

# 长按 1 秒
control.long_click(640, 360, duration=1.0, control_name='HOLD')

# 从 (100, 300) 滑动到 (500, 300)
control.swipe((100, 300), (500, 300), duration=0.3)

# 向右滑动（向量方式）
control.swipe_vector(vector=(300, 0), box=(100, 200, 1100, 500))

# 连续点击 5 次
control.multi_click(button, n=5, interval=0.15)

# 拖拽
control.drag((200, 300), (800, 300), swipe_duration=0.5)
```

## 7. 设计模式总结

- **策略模式**: 通过 `click_methods`/`long_click_methods` 字典实现运行时方法选择
- **模板方法**: `click()`/`swipe()` 定义固定流程（检查→选择方法→执行），具体实现在各 method 类中
- **钩子方法**: `handle_control_check()` 在基类中为空，由 `Device` 子类重写注入卡死检测逻辑
- **距离保护**: 滑动距离 < 10px 时自动跳过，避免被误识别为点击
- **ADB 降级**: ADB 滑动时自动将 duration 乘以 2.5，补偿其较慢的执行速度
