# module.device.env 模块详解

## 1. 文件概述

`env.py` 是设备模块中最简单的文件，仅包含 7 行代码。它的作用是**检测当前运行的操作系统平台**，提供全局常量供其他模块使用，以便在不同平台上执行不同的逻辑分支（例如 Windows 专有的窗口截图方法）。

**文件路径**: `module/device/env.py`

## 2. 导入部分解释

```python
import sys  # Python 标准库，提供对解释器相关变量和函数的访问
```

`sys.platform` 是一个字符串，表示当前操作系统平台：
- `'win32'` — Windows 系统
- `'darwin'` — macOS 系统
- `'linux'` — Linux 系统

## 3. 全局常量定义

```python
IS_WINDOWS = sys.platform == 'win32'     # 是否为 Windows 系统
IS_MACINTOSH = sys.platform == 'darwin'  # 是否为 macOS 系统
IS_LINUX = sys.platform == 'linux'       # 是否为 Linux 系统
```

这三个布尔常量在模块加载时即被计算，之后在整个程序生命周期内保持不变。

## 4. 核心算法流程图

```
程序启动
  │
  ▼
加载 env.py 模块
  │
  ▼
读取 sys.platform
  │
  ├── 'win32'  → IS_WINDOWS=True, IS_MACINTOSH=False, IS_LINUX=False
  ├── 'darwin' → IS_WINDOWS=False, IS_MACINTOSH=True, IS_LINUX=False
  ├── 'linux'  → IS_WINDOWS=False, IS_MACINTOSH=False, IS_LINUX=True
  └── 其他     → 三者均为 False
  │
  ▼
其他模块通过 from module.device.env import IS_WINDOWS 引用
```

## 5. 使用示例

```python
from module.device.env import IS_WINDOWS

if IS_WINDOWS:
    # 使用 Windows 专有的窗口截图方法
    method = 'window_background'
else:
    # 使用跨平台的 ADB 截图方法
    method = 'ADB'
```

在本项目中，`IS_WINDOWS` 被大量用于：
- `screenshot.py` 中判断是否启用 `window_background` 截图方法
- `control.py` 中判断是否启用 `window_message` 点击方法
- `device.py` 中判断是否自动填充模拟器信息

## 6. 设计模式总结

- **常量模块模式**: 将平台检测逻辑集中在一个模块中，避免各处重复编写 `sys.platform` 判断
- **模块级求值**: 常量在模块导入时一次性计算，后续使用无额外开销
- **参考来源**: 文件头部注释表明此文件参考自 [StarRailCopilot](https://github.com/LmeSzinc/StarRailCopilot/blob/master/module/device/env.py) 项目
