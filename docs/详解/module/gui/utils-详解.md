# utils.py 代码详解

## 1. 文件概述

`utils.py` 是 GUI 模块的工具函数文件，提供系统级的实用功能，包括获取工作路径、检查管理员权限等。该模块主要处理 Windows 平台特定的操作。

**核心职责：**
- 获取应用程序工作目录
- 检查和提升管理员权限
- Windows 平台特定的系统操作

---

## 2. 导入部分解释

```python
import ctypes                                    # Python 外部函数库，用于调用 DLL
import win32gui                                  # Windows GUI API，用于窗口操作
import win32con                                  # Windows 常量定义
import sys                                       # 系统参数，用于获取可执行文件路径
import time                                      # 时间函数，用于延迟

from pathlib import Path                         # 路径处理库
from module.logger import logger                 # 日志记录器
```

---

## 3. 函数定义解释

### 3.1 `get_work_path()` 函数

```python
def get_work_path() -> Path:
    """
    返回程序工作的目录
    如果没有问题的话就是根目录
    :return: Path 对象，表示工作目录
    """
    # Path.cwd() 返回当前工作目录
    # 通常是程序启动时所在的目录
    return Path.cwd()
```

### 3.2 `is_admin()` 函数

```python
def is_admin():
    """
    检查程序是否以管理员身份运行
    :return: True 表示是管理员，False 表示不是
    """
    try:
        # 调用 Windows Shell32.dll 的 IsUserAnAdmin 函数
        # 返回值为 1 表示是管理员
        result = ctypes.windll.shell32.IsUserAnAdmin()
        return result == 1
    except:
        # 如果调用失败（非 Windows 系统等），返回 False
        return False
```

### 3.3 `check_admin()` 函数

```python
def check_admin():
    """
    检查是不是管理员权限
    如果不是管理员权限则使用管理员权限重启
    """
    if not is_admin():
        logger.info('非管理员身份运行，已尝试以管理员身份运行')

        # 等待 5 秒（让用户看到日志）
        time.sleep(5)

        # 获取命令行参数
        args = ' '.join(sys.argv)

        # 使用 ShellExecuteW 以管理员权限重新启动程序
        # None: 父窗口句柄
        # "runas": 动词，表示以管理员身份运行
        # sys.executable: Python 解释器路径
        # __file__: 当前脚本路径
        # None: 参数（这里用 args 变量但未传入）
        # 1: 显示窗口
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            __file__,
            None,
            1
        )

        # 退出当前非管理员进程
        sys.exit(0)

    logger.log('管理员身份运行')
```

---

## 4. 核心算法流程图

### 4.1 管理员权限检查流程

```
check_admin()
    │
    ▼
┌─────────────────────────────────────┐
│  is_admin()                         │
│  调用 Shell32.IsUserAnAdmin()       │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  是否是管理员？                      │
│  ├─ 是 → 记录日志，继续执行         │
│  └─ 否 ↓                           │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  记录日志：非管理员身份运行          │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  time.sleep(5) 等待 5 秒            │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  ShellExecuteW("runas", ...)        │
│  以管理员权限重新启动程序            │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  sys.exit(0)                        │
│  退出当前非管理员进程                │
└─────────────────────────────────────┘
```

### 4.2 is_admin() 调用链

```
is_admin()
    │
    ▼
┌─────────────────────────────────────┐
│  ctypes.windll.shell32              │
│  加载 Shell32.dll                   │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  IsUserAnAdmin()                    │
│  Windows API 函数                   │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  返回值检查                          │
│  result == 1 → True (是管理员)      │
│  否则 → False                       │
└─────────────────────────────────────┘
```

### 4.3 权限提升流程

```
用户双击运行程序
    │
    ▼
┌─────────────────────────────────────┐
│  程序启动（普通权限）                │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  check_admin()                      │
│  检测到非管理员权限                  │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  Windows UAC 弹窗                   │
│  "是否允许此应用对设备进行更改？"    │
└─────────────────────────────────────┘
    │
    ├─ 用户点击"是"
    │       │
    │       ▼
    │   ┌───────────────────────────┐
    │   │ 新进程启动（管理员权限）    │
    │   │ 继续执行 check_admin()     │
    │   │ is_admin() 返回 True       │
    │   │ 记录日志，正常运行          │
    │   └───────────────────────────┘
    │
    └─ 用户点击"否"
            │
            ▼
        ┌───────────────────────────┐
        │ ShellExecuteW 失败         │
        │ 原进程 sys.exit(0) 退出    │
        └───────────────────────────┘
```

---

## 5. 使用示例

### 5.1 在程序启动时检查权限

```python
from module.gui.utils import check_admin, get_work_path

# 程序入口处调用
check_admin()  # 如果不是管理员会自动提升权限

# 获取工作目录
work_path = get_work_path()
print(f"工作目录: {work_path}")
```

### 5.2 在主程序中使用

```python
from module.gui.fluent_app import FluentApp
from module.gui.utils import check_admin

def main():
    # 检查管理员权限
    check_admin()

    # 启动 GUI 应用
    app = FluentApp()
    FluentApp.run()

if __name__ == "__main__":
    main()
```

### 5.3 仅检查权限不提升

```python
from module.gui.utils import is_admin

if is_admin():
    print("以管理员身份运行")
else:
    print("以普通用户身份运行")
```

---

## 6. 平台兼容性说明

| 函数 | Windows | Linux | macOS |
|------|---------|-------|-------|
| get_work_path() | ✓ | ✓ | ✓ |
| is_admin() | ✓ | ✗ | ✗ |
| check_admin() | ✓ | ✗ | ✗ |

**注意：**
- `is_admin()` 和 `check_admin()` 使用了 Windows 特有的 API
- 在非 Windows 系统上会抛出异常或返回 False
- 如果需要跨平台支持，应该添加平台检查

---

## 7. 设计模式总结

| 设计模式 | 应用位置 | 说明 |
|---------|---------|------|
| **工具函数模式** | 所有函数 | 提供无状态的实用功能 |
| **平台适配模式** | ctypes 调用 | 封装平台特定的 API 调用 |
| **自我提升模式** | check_admin() | 程序自动提升权限 |

**安全考虑：**
- 权限提升需要用户确认（UAC 弹窗）
- 使用 `sys.exit(0)` 确保非管理员进程正确退出
- `time.sleep(5)` 给用户时间查看日志信息

**依赖项：**
- `pywin32`：提供 `win32gui` 和 `win32con` 模块
- Windows 操作系统：`ctypes.windll` 仅在 Windows 上可用
