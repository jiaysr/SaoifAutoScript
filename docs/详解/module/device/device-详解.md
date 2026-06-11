# module.device.device 模块详解

## 1. 文件概述

`device.py` 定义了 `Device` 类，是整个设备模块的**顶层聚合类**，通过多重继承整合了：
- `Platform`（模拟器平台管理）
- `Screenshot`（截图功能）
- `Control`（输入控制功能）
- `AppControl`（应用控制功能）

同时实现了**游戏卡死检测**和**点击记录**等游戏自动化特有的保护机制。

**文件路径**: `module/device/device.py`
**代码行数**: 252 行

## 2. 导入部分解释

```python
from collections import deque      # 双端队列，用于点击记录
from datetime import datetime      # 时间处理

# 补丁：在导入 adbutils 和 uiautomator2 之前修复 pkg_resources
from module.device.pkg_resources import get_distribution
_ = get_distribution  # 防止被导入优化移除

from module.device.env import IS_WINDOWS
from module.base.timer import Timer
from module.config.utils import get_server_next_update  # 服务器更新时间
from module.device.app_control import AppControl        # 应用控制
from module.device.control import Control               # 输入控制
from module.device.platform2 import Platform            # 平台管理
from module.device.screenshot import Screenshot         # 截图
from module.exception import (
    GameNotRunningError,       # 游戏未运行
    GameStuckError,            # 游戏卡死
    GameTooManyClickError,     # 点击过多
    RequestHumanTakeover,      # 需要人工干预
    EmulatorNotRunningError    # 模拟器未运行
)
from module.logger import logger
```

## 3. 类定义解释

```python
class Device(Platform, Screenshot, Control, AppControl):
```

**MRO（方法解析顺序）**: Device → Platform → Screenshot → Control → AppControl → ...

### 3.1 类变量

```python
_screen_size_checked = False           # 屏幕尺寸是否已校验
detect_record = set()                  # 卡死检测记录（当前等待的按钮集合）
click_record = deque(maxlen=15)        # 点击记录队列（最近 15 次）
stuck_timer = Timer(60, count=60).start()       # 60 秒卡死定时器
stuck_timer_long = Timer(300, count=300).start() # 300 秒长卡死定时器
stuck_long_wait_list = [               # 允许长时间等待的场景
    'BATTLE_STATUS_S', 'PAUSE', 'LOGIN_CHECK', 'PREPARE_BEFORE_BATTLE'
]
```

## 4. 方法逐行解释

### 4.1 `__init__(self, *args, **kwargs)` — 构造函数（第 33-60 行）

```python
def __init__(self, *args, **kwargs):
    for trial in range(4):  # 最多重试 4 次
        try:
            super().__init__(*args, **kwargs)  # 调用 MRO 链上的所有 __init__
            break
        except EmulatorNotRunningError:
            if trial >= 3:
                logger.critical('Failed to start emulator after 3 trial')
                raise RequestHumanTakeover
            # 尝试启动模拟器
            if self.emulator_instance is not None:
                self.emulator_start()
            else:
                logger.critical(f'No emulator with serial "{self.config.Emulator_Serial}" found')
                raise RequestHumanTakeover

    # 自动填充模拟器信息（仅 Windows）
    if IS_WINDOWS and self.config.script.device.emulatorinfo_type == 'auto':
        _ = self.emulator_instance

    self.screenshot_interval_set()  # 设置截图间隔

    # 自动选择最快的截图方法
    if self.config.script.device.screenshot_method == 'auto':
        self.run_simple_screenshot_benchmark()
```

**关键逻辑**: 模拟器未运行时自动尝试启动，最多重试 3 次。

### 4.2 `run_simple_screenshot_benchmark(self)` — 截图性能基准测试（第 62-76 行）

```python
def run_simple_screenshot_benchmark(self):
    logger.info('run_simple_screenshot_benchmark')
    from module.daemon.benchmark import Benchmark  # 延迟导入
    bench = Benchmark(config=self.config, device=self)
    method = bench.run_simple_screenshot_benchmark()  # 测试所有方法，返回最快的
    self.config.script.device.screenshot_method = method
    self.config.save()  # 保存到配置文件
```

### 4.3 `handle_night_commission(self, daily_trigger, threshold)` — 夜间委托处理（第 78-98 行）

```python
def handle_night_commission(self, daily_trigger='21:00', threshold=30):
    update = get_server_next_update(daily_trigger=daily_trigger)  # 下次刷新时间
    now = datetime.now()
    diff = (update.timestamp() - now.timestamp()) % 86400  # 距刷新的秒数
    if threshold < diff < 86400 - threshold:
        return False  # 不在刷新窗口内
    # 在刷新窗口内（前后 30 秒），可处理夜间委托弹窗
    return False  # 当前实现未启用
```

### 4.4 `screenshot(self)` — 截图（第 100-115 行）

```python
def screenshot(self):
    self.stuck_record_check()  # 卡死检测

    try:
        super().screenshot()   # 调用 Screenshot.screenshot()
    except RequestHumanTakeover as e:
        raise RequestHumanTakeover

    if self.handle_night_commission():
        super().screenshot()   # 如果处理了委托弹窗，重新截图

    return self.image
```

### 4.5 `release_during_wait(self)` — 等待时释放资源（第 117-124 行）

```python
def release_during_wait(self):
    if self.config.script.device.screenshot_method == 'scrcpy':
        self._scrcpy_server_stop()  # 停止 scrcpy 视频流
    if self.config.Emulator_ScreenshotMethod == 'nemu_ipc':
        self.nemu_ipc_release()     # 释放 nemu_ipc 连接
```

### 4.6 卡死检测系统（第 126-163 行）

#### `stuck_record_add(self, button)` — 添加卡死记录

```python
def stuck_record_add(self, button):
    self.detect_record.add(str(button))  # 添加到检测集合
    logger.info(f'Add stuck record: {button}')
```

#### `stuck_record_clear(self)` — 清除卡死记录

```python
def stuck_record_clear(self):
    self.detect_record = set()           # 清空集合
    self.stuck_timer.reset()             # 重置 60 秒定时器
    self.stuck_timer_long.reset()        # 重置 300 秒定时器
```

#### `stuck_record_check(self)` — 卡死检测

```python
def stuck_record_check(self):
    reached = self.stuck_timer.reached()        # 60 秒到了？
    reached_long = self.stuck_timer_long.reached()  # 300 秒到了？

    if not reached:
        return False  # 60 秒内，正常

    if not reached_long:
        # 60-300 秒之间
        for button in self.stuck_long_wait_list:
            if button in self.detect_record:
                return False  # 允许长时间等待的场景，继续等

    # 超时！
    logger.warning('Wait too long')
    logger.warning(f'Waiting for {self.detect_record}')
    self.stuck_record_clear()

    if self.app_is_running():
        raise GameStuckError('Wait too long')      # 游戏还在但卡住了
    else:
        raise GameNotRunningError('Game died')     # 游戏已崩溃
```

**两级超时机制**:
- 60 秒: 普通操作超时
- 300 秒: 特殊场景（战斗、暂停等）允许更长等待

### 4.7 点击记录系统（第 165-215 行）

#### `handle_control_check(self, button)` — 控制检查入口

```python
def handle_control_check(self, button):
    self.stuck_record_clear()      # 有操作 → 清除卡死记录
    self.click_record_add(button)  # 记录点击
    self.click_record_check()      # 检查点击过多
```

#### `click_record_add(self, button)` — 记录点击

```python
def click_record_add(self, button):
    self.click_record.append(str(button))  # 添加到队列（自动丢弃最旧的）
```

#### `click_record_remove(self, button)` — 移除点击记录

```python
def click_record_remove(self, button):
    removed = 0
    for _ in range(self.click_record.maxlen):
        try:
            self.click_record.remove(str(button))
            removed += 1
        except ValueError:
            break  # 不在队列中
    return removed
```

#### `click_record_check(self)` — 检查点击过多

```python
def click_record_check(self):
    count = {}
    for key in self.click_record:
        count[key] = count.get(key, 0) + 1  # 统计每个按钮的点击次数
    count = sorted(count.items(), key=lambda item: item[1], reverse=True)

    # 规则 1: 单个按钮点击 ≥ 10 次
    if count[0][1] >= 10:
        self.click_record_clear()
        raise GameTooManyClickError(f'Too many click for a button: {count[0][0]}')

    # 规则 2: 两个按钮各点击 ≥ 6 次（来回点击）
    if len(count) >= 2 and count[0][1] >= 6 and count[1][1] >= 6:
        self.click_record_clear()
        raise GameTooManyClickError(f'Too many click between 2 buttons: {count[0][0]}, {count[1][0]}')
```

### 4.8 `disable_stuck_detection(self)` — 禁用卡死检测（第 217-227 行）

```python
def disable_stuck_detection(self):
    logger.info('Disable stuck detection')
    def empty_function(*arg, **kwargs):
        return False
    self.click_record_check = empty_function   # 替换为空函数
    self.stuck_record_check = empty_function   # 替换为空函数
```

用于半自动模式和调试场景。

### 4.9 `app_start(self)` / `app_stop(self)` — 应用启动/停止（第 229-245 行）

```python
def app_start(self):
    if not self.config.script.error.handle_error:
        logger.critical('No app stop/start, because HandleError disabled')
        raise RequestHumanTakeover  # 错误处理被禁用时不允许自动启停
    super().app_start()
    self.stuck_record_clear()   # 清除所有记录
    self.click_record_clear()

def app_stop(self):
    if not self.config.script.error.handle_error:
        logger.critical('No app stop/start, because HandleError disabled')
        raise RequestHumanTakeover
    super().app_stop()
    self.stuck_record_clear()
    self.click_record_clear()
```

## 5. 核心算法流程图

```
Device 继承体系:
  │
  Device
  ├── Platform      ← 模拟器平台管理（启动/停止/重启）
  ├── Screenshot    ← 截图（多方法支持）
  ├── Control       ← 输入控制（点击/滑动/拖拽）
  └── AppControl    ← 应用控制（启停/层级检测）

Device.__init__() 流程:
  │
  ├── 1. 尝试初始化（最多 4 次）
  │     ├── EmulatorNotRunningError → emulator_start()
  │     └── 成功 → break
  │
  ├── 2. 自动填充模拟器信息
  │
  ├── 3. 设置截图间隔
  │
  └── 4. 自动选择截图方法（benchmark）

截图流程 (screenshot):
  │
  ├── 1. stuck_record_check()  ← 卡死检测
  │     ├── 60 秒内     → 正常
  │     ├── 60-300 秒   → 检查是否允许长等待
  │     └── > 300 秒    → GameStuckError / GameNotRunningError
  │
  ├── 2. super().screenshot()  ← 实际截图
  │
  ├── 3. handle_night_commission()  ← 处理委托弹窗
  │
  └── 4. return self.image

卡死检测机制:
  │
  ├── detect_record (set): 记录当前等待的按钮
  ├── stuck_timer (60s): 普通超时
  ├── stuck_timer_long (300s): 长等待超时
  └── stuck_long_wait_list: 允许长等待的场景

点击过多检测:
  │
  ├── click_record (deque, maxlen=15): 最近 15 次点击
  │
  ├── 规则 1: 单按钮 ≥ 10 次
  │     └── raise GameTooManyClickError
  │
  └── 规则 2: 双按钮各 ≥ 6 次（来回点击死循环）
        └── raise GameTooManyClickError

控制操作 → handle_control_check:
  │
  ├── 1. stuck_record_clear()  ← 有操作，清除卡死记录
  ├── 2. click_record_add()    ← 记录本次点击
  └── 3. click_record_check()  ← 检查是否过多
```

## 6. 使用示例

```python
# 创建 Device 实例（自动初始化所有子系统）
device = Device(config="oas1")

# 截图
image = device.screenshot()  # 返回 np.ndarray (720, 1280, 3)

# 点击
device.click(640, 360, control_name='CENTER')

# 滑动
device.swipe((100, 300), (500, 300))

# 长按
device.long_click(640, 360, duration=1.0)

# 检查应用是否运行
if device.app_is_running():
    print("游戏正在运行")

# 启动/停止应用
device.app_start()
device.app_stop()

# 禁用卡死检测（调试用）
device.disable_stuck_detection()

# 等待时释放资源
device.release_during_wait()
```

## 7. 设计模式总结

- **菱形继承（钻石继承）**: `Device` 通过多重继承聚合 4 个功能类，Python 的 MRO（C3 线性化）确保方法解析的一致性
- **模板方法**: `screenshot()` 在调用父类截图前后插入卡死检测和委托处理
- **两级超时**: 60 秒普通超时 + 300 秒长等待超时，区分不同场景的等待容忍度
- **滑动窗口检测**: `deque(maxlen=15)` 实现固定大小的点击历史窗口
- **猴子补丁**: `disable_stuck_detection()` 通过替换方法引用禁用检测
- **延迟初始化**: 截图方法的 benchmark 在首次使用时执行
- **保护机制**: 所有控制操作都经过 `handle_control_check`，确保卡死和过多点击被及时发现
- **安全门**: `app_start`/`app_stop` 检查 `handle_error` 配置，防止在错误处理禁用时自动启停
