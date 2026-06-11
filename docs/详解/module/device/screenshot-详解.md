# module.device.screenshot 模块详解

## 1. 文件概述

`screenshot.py` 定义了 `Screenshot` 类，负责设备屏幕截图的核心逻辑，包括：
- 多种截图方法的统一调度（ADB、uiautomator2、DroidCast、scrcpy、nemu_ipc 等）
- 截图间隔控制和限速
- 屏幕尺寸校验（必须为 1280x720）
- 黑屏检测和处理
- 截图保存和历史记录管理
- 屏幕方向修正

**文件路径**: `module/device/screenshot.py`
**代码行数**: 277 行

## 2. 导入部分解释

```python
import os              # 文件路径操作
import time            # 时间戳
from collections import deque  # 双端队列，用于截图历史
from datetime import datetime  # 时间戳记录
from pathlib import Path       # 路径操作

import cv2             # OpenCV，图像处理（旋转等）
import numpy as np     # NumPy 数组，图像数据格式
from PIL import Image  # Pillow，图像显示

from module.base.decorator import cached_property   # 缓存属性
from module.base.timer import Timer                 # 定时器
from module.base.utils import get_color, image_size, limit_in, save_image  # 工具函数
from module.device.env import IS_WINDOWS            # 平台检测
from module.device.method.adb import Adb            # ADB 截图方法
from module.device.method.windows import Window     # Windows 窗口截图方法
from module.device.method.droidcast import DroidCast # DroidCast 截图方法
from module.device.method.scrcpy import Scrcpy      # scrcpy 截图方法
from module.device.method.nemu_ipc import NemuIpc   # MuMu IPC 截图方法
from module.exception import RequestHumanTakeover, ScriptError
from module.logger import logger
```

## 3. 类定义解释

```python
class Screenshot(Adb, DroidCast, Scrcpy, Window, NemuIpc):
```

通过多重继承组合了所有截图方法实现。MRO（方法解析顺序）决定了方法查找优先级。

### 3.1 类变量

```python
_screen_size_checked = False    # 屏幕尺寸是否已校验通过
_screen_black_checked = False   # 黑屏是否已校验通过
_minicap_uninstalled = False    # minicap 是否已卸载
_screenshot_interval = Timer(0.1)  # 截图间隔定时器，默认 0.1 秒
_last_save_time = {}            # 各类型截图的最后保存时间
image: np.ndarray               # 当前截图数据（类型注解）
```

## 4. 方法逐行解释

### 4.1 `__init__(self, *args, **kwargs)` — 构造函数（第 32-34 行）

```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)              # 正常的 MRO 初始化链
    super(Window, self).__init__(*args, **kwargs)  # 跳过 Window 的 __init__
```

**关键点**: `Window` 类的 `__init__` 被跳过，因为它可能有与 ADB 初始化冲突的逻辑。

### 4.2 `screenshot_methods` — 截图方法映射表（第 36-49 行）

```python
@cached_property
def screenshot_methods(self):
    return {
        'ADB': self.screenshot_adb,               # 通过 adb exec-out screencap
        'ADB_nc': self.screenshot_adb_nc,         # ADB + netcat 传输
        'uiautomator2': self.screenshot_uiautomator2,  # 通过 u2 截图
        'DroidCast': self.screenshot_droidcast,   # DroidCast HTTP 截图
        'DroidCast_raw': self.screenshot_droidcast_raw,  # DroidCast 原始格式
        'scrcpy': self.screenshot_scrcpy,         # scrcpy 视频流
        'window_background': self.screenshot_window_background if IS_WINDOWS else None,
        'nemu_ipc': self.screenshot_nemu_ipc      # MuMu IPC 直连
    }
```

### 4.3 `screenshot(self)` — 主截图方法（第 51-80 行）

```python
def screenshot(self):
    self._screenshot_interval.wait()   # 等待间隔时间
    self._screenshot_interval.reset()  # 重置定时器

    for _ in range(2):  # 最多重试 2 次
        method = self.screenshot_methods.get(
            self.config.script.device.screenshot_method,
            self.screenshot_adb  # 默认使用 ADB
        )
        self.image = method()  # 执行截图

        if self.config.script.error.save_error:
            self.screenshot_deque.append({
                'time': datetime.now(),
                'image': self.image
            })  # 保存截图历史（用于错误调试）

        if self.check_screen_size() and self.check_screen_black():
            break  # 校验通过，退出循环
        else:
            continue  # 校验失败，重试

    return self.image
```

**流程**:
1. 等待截图间隔 → 限速保护
2. 根据配置选择截图方法 → 策略模式
3. 保存截图历史 → 错误调试支持
4. 校验屏幕尺寸和黑屏 → 质量保证
5. 最多重试 2 次 → 容错机制

### 4.4 `_handle_orientated_image(self, image)` — 旋转修正（第 82-106 行）

```python
def _handle_orientated_image(self, image):
    width, height = image_size(self.image)
    if width == 1280 and height == 720:
        return image  # 标准分辨率，无需旋转

    if self.orientation == 0:
        pass                                    # 正常
    elif self.orientation == 1:
        image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)  # HOME 键在右
    elif self.orientation == 2:
        image = cv2.rotate(image, cv2.ROTATE_180)                  # HOME 键在上
    elif self.orientation == 3:
        image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)         # HOME 键在左
    else:
        raise ScriptError(f'Invalid device orientation: {self.orientation}')
    return image
```

### 4.5 `screenshot_deque` — 截图历史队列（第 108-111 行）

```python
@cached_property
def screenshot_deque(self):
    return deque(maxlen=int(self.config.script.error.screenshot_length))
```

双端队列，最大长度由配置决定，自动丢弃最旧的截图。

### 4.6 `save_screenshot(self, genre, interval, to_base_folder)` — 保存截图（第 113-146 行）

```python
def save_screenshot(self, genre='items', interval=None, to_base_folder=False):
    now = time.time()
    if interval is None:
        interval = 1  # 默认 1 秒间隔

    if now - self._last_save_time.get(genre, 0) > interval:
        fmt = 'png'
        file = '%s.%s' % (int(now * 1000), fmt)  # 毫秒时间戳作为文件名
        folder = Path('./log/screenshots')
        folder.mkdir(parents=True, exist_ok=True)
        file = folder / file
        file = file.resolve()
        self.image_save(file)
        self._last_save_time[genre] = now
        return True
    else:
        self._last_save_time[genre] = now
        return False  # 间隔太短，跳过保存
```

### 4.7 `screenshot_interval_set(self, interval)` — 设置截图间隔（第 151-187 行）

```python
def screenshot_interval_set(self, interval=None):
    if interval is None:
        origin = self.config.script.optimization.screenshot_interval
        interval = limit_in(origin, 0.1, 0.3)  # 限制在 0.1-0.3 秒
        if self.config.Emulator_ScreenshotMethod == 'nemu_ipc':
            interval = limit_in(origin, 0.1, 0.2)  # nemu_ipc 允许更低
    elif interval == 'combat':
        origin = self.config.script.optimization.combat_screenshot_interval
        interval = limit_in(origin, 0.3, 1.0)  # 战斗模式 0.3-1.0 秒
    elif isinstance(interval, (int, float)):
        pass  # 手动设置无限制

    if self.config.script.device.screenshot_method == 'scrcpy':
        interval = 0.1  # scrcpy 视频流持续接收，间隔无意义

    self._screenshot_interval.limit = interval
```

### 4.8 `check_screen_size(self)` — 屏幕尺寸校验（第 197-233 行）

```python
def check_screen_size(self):
    if self._screen_size_checked:
        return True  # 已校验通过

    for _ in range(2):
        width, height = image_size(self.image)
        if width == 1280 and height == 720:
            self._screen_size_checked = True
            return True  # 标准分辨率
        elif not orientated and (width == 720 and height == 1280):
            # 竖屏截图，尝试旋转修正
            self.get_orientation()
            self.image = self._handle_orientated_image(self.image)
            orientated = True
        elif hasattr(self, 'app_is_running') and not self.app_is_running():
            return True  # 游戏未运行，跳过
        else:
            logger.critical(f'Resolution not supported: {width}x{height}')
            raise RequestHumanTakeover
```

### 4.9 `check_screen_black(self)` — 黑屏检测（第 235-270 行）

```python
def check_screen_black(self):
    if self._screen_black_checked:
        return True

    color = get_color(self.image, area=(0, 0, 1280, 720))  # 全屏平均颜色
    if sum(color) < 1:  # 纯黑
        if self.config.script.device.screenshot_method == 'uiautomator2':
            logger.warning('Received pure black screenshots, uninstall minicap')
            self.uninstall_minicap()  # minicap 可能导致黑屏
            self._screen_black_checked = False
            return False  # 重试
        else:
            logger.warning(f'Screenshot method may not work on this emulator')
            if self.is_mumu_family:
                if self.config.script.device.screenshot_method == 'DroidCast':
                    self.droidcast_stop()  # 重启 DroidCast
            self._screen_black_checked = False
            return False
    else:
        self._screen_black_checked = True
        return True
```

## 5. 核心算法流程图

```
screenshot() 主流程:
  │
  ├── 1. _screenshot_interval.wait()  ← 限速等待
  │
  ├── 2. 选择截图方法
  │     ├── 'ADB'           → adb exec-out screencap
  │     ├── 'ADB_nc'        → adb shell screencap | nc
  │     ├── 'uiautomator2'  → u2.screenshot()
  │     ├── 'DroidCast'     → HTTP GET 截图
  │     ├── 'DroidCast_raw' → HTTP GET 原始格式
  │     ├── 'scrcpy'        → 视频流解码
  │     ├── 'window_background' → Win32 窗口截图
  │     └── 'nemu_ipc'      → MuMu IPC 直连
  │
  ├── 3. 保存到截图历史队列
  │
  ├── 4. check_screen_size()
  │     ├── 1280x720     → 通过
  │     ├── 720x1280     → 旋转修正
  │     └── 其他分辨率   → 报错退出
  │
  ├── 5. check_screen_black()
  │     ├── 正常颜色     → 通过
  │     └── 纯黑         → 卸载 minicap / 重启 DroidCast → 重试
  │
  └── 6. return self.image

截图间隔控制:
  │
  ├── 普通模式: 0.1 ~ 0.3 秒
  ├── 战斗模式: 0.3 ~ 1.0 秒
  ├── nemu_ipc: 0.1 ~ 0.2 秒
  └── scrcpy:   固定 0.1 秒（视频流）
```

## 6. 使用示例

```python
# 基本截图
screenshot = Screenshot(config="oas1")
image = screenshot.screenshot()  # 返回 np.ndarray (720, 1280, 3)

# 显示截图
screenshot.image_show()

# 保存截图
screenshot.save_screenshot(genre='debug', interval=5)

# 调整截图间隔
screenshot.screenshot_interval_set(0.2)        # 手动设置 0.2 秒
screenshot.screenshot_interval_set('combat')   # 切换到战斗模式间隔
```

## 7. 设计模式总结

- **策略模式**: `screenshot_methods` 字典将方法名映射到具体实现，运行时根据配置动态选择
- **模板方法**: `screenshot()` 定义了截图的固定流程（等待→截图→校验），子方法只负责具体截图逻辑
- **装饰器条件分发**: 通过 `@Config.when()` 实现 HTTP/非 HTTP 的方法版本切换
- **限速器模式**: `Timer` 对象控制截图频率，防止过度占用资源
- **重试机制**: 截图失败时自动重试（最多 2 次），配合黑屏检测和尺寸校验
- **队列缓冲**: `deque` 保存最近 N 张截图，用于错误发生时的回溯分析
