# module/exception.py 代码详解

## 1. 文件概述

`exception.py` 是项目自定义异常模块，定义了自动化脚本运行过程中可能出现的各种异常类型。这些异常用于精确捕获和处理不同类型的错误场景，便于上层逻辑进行针对性的错误恢复。

**文件路径**: `module/exception.py`
**代码行数**: 62 行
**主要功能**:
- 定义游戏相关异常（地图、战斗、页面等）
- 定义设备相关异常（模拟器、游戏进程等）
- 定义脚本相关异常（脚本错误、任务结束等）
- 定义人工接管异常

---

## 2. 导入部分解释

本模块没有导入任何外部依赖，仅使用 Python 内置的 `Exception` 基类。

---

## 3. 类定义解释

本模块定义了 14 个自定义异常类，全部继承自 Python 内置的 `Exception` 类。

### 异常分类

| 类别 | 异常类 | 说明 |
|------|--------|------|
| **地图相关** | `CampaignEnd` | 关卡结束 |
| | `MapDetectionError` | 地图检测错误 |
| | `MapWalkError` | 地图行走错误 |
| | `MapEnemyMoved` | 敌人移动 |
| | `CampaignNameError` | 关卡名称错误 |
| **脚本相关** | `ScriptError` | 脚本错误（可能是开发者的错误） |
| | `ScriptEnd` | 脚本结束 |
| | `TaskEnd` | 任务结束 |
| **游戏相关** | `GameStuckError` | 游戏卡顿 |
| | `GameBugError` | 游戏客户端错误 |
| | `GameTooManyClickError` | 点击次数过多 |
| | `GamePageUnknownError` | 未知游戏页面 |
| **设备相关** | `EmulatorNotRunningError` | 模拟器未运行 |
| | `GameNotRunningError` | 游戏未运行 |
| **人工介入** | `RequestHumanTakeover` | 请求人工接管 |

---

## 4. 每个方法的逐行解释

本模块仅包含异常类定义，没有方法实现。每个异常类都是简单的 `pass` 继承。

### 地图相关异常

```python
class CampaignEnd(Exception):
    pass
```

**用途**: 当关卡正常结束时抛出，表示当前关卡已完成。

```python
class MapDetectionError(Exception):
    pass
```

**用途**: 地图识别失败时抛出，可能是图像识别算法无法正确解析地图状态。

```python
class MapWalkError(Exception):
    pass
```

**用途**: 角色在地图上移动失败时抛出，可能是路径被阻挡或移动超时。

```python
class MapEnemyMoved(Exception):
    pass
```

**用途**: 检测到敌人位置发生变化时抛出，需要重新计算路径。

```python
class CampaignNameError(Exception):
    pass
```

**用途**: 关卡名称配置错误时抛出，可能是用户输入了不存在的关卡名称。

### 脚本相关异常

```python
class ScriptError(Exception):
    # This is likely to be a mistake of developers, but sometimes a random issue
    pass
```

**用途**: 脚本内部错误，通常是开发者代码逻辑错误，也可能是偶发性问题。

```python
class ScriptEnd(Exception):
    pass
```

**用途**: 脚本正常结束时抛出，表示整个脚本执行流程已完成。

```python
class TaskEnd(Exception):
    pass
```

**用途**: 单个任务结束时抛出，表示当前任务已完成，可以执行下一个任务。

### 游戏相关异常

```python
class GameStuckError(Exception):
    pass
```

**用途**: 游戏界面卡住无响应时抛出，可能需要重启游戏。

```python
class GameBugError(Exception):
    # An error has occurred in Azur Lane game client. Alas is unable to handle.
    # A restart should fix it.
    pass
```

**用途**: 游戏客户端出现 bug 时抛出，脚本无法处理，通常需要重启游戏。

```python
class GameTooManyClickError(Exception):
    pass
```

**用途**: 短时间内点击次数过多时抛出，防止被游戏检测为异常操作。

```python
class GamePageUnknownError(Exception):
    pass
```

**用途**: 当前游戏页面无法识别时抛出，脚本不知道如何处理当前界面。

### 设备相关异常

```python
class EmulatorNotRunningError(Exception):
    pass
```

**用途**: 模拟器未启动时抛出，需要用户先启动模拟器。

```python
class GameNotRunningError(Exception):
    pass
```

**用途**: 游戏未运行时抛出，需要用户先启动游戏。

### 人工介入异常

```python
class RequestHumanTakeover(Exception):
    # Request human takeover
    # Alas is unable to handle such error, probably because of wrong settings.
    pass
```

**用途**: 脚本无法自动处理的错误，需要人工介入。通常是配置错误或系统环境问题。

---

## 5. 核心算法流程图

### 异常层次结构

```
                        Exception
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  地图相关      │   │  脚本相关      │   │  游戏相关      │
├───────────────┤   ├───────────────┤   ├───────────────┤
│ CampaignEnd   │   │ ScriptError   │   │ GameStuckError│
│ MapDetection  │   │ ScriptEnd     │   │ GameBugError  │
│ MapWalkError  │   │ TaskEnd       │   │ GameTooMany   │
│ MapEnemyMoved │   │               │   │ GamePageUnknown│
│ CampaignName  │   │               │   │               │
└───────────────┘   └───────────────┘   └───────────────┘
                                                │
                            ┌───────────────────┤
                            ▼                   ▼
                    ┌───────────────┐   ┌───────────────┐
                    │  设备相关      │   │  人工介入      │
                    ├───────────────┤   ├───────────────┤
                    │ EmulatorNot   │   │ RequestHuman  │
                    │ GameNot       │   │ Takeover      │
                    └───────────────┘   └───────────────┘
```

### 异常处理流程

```
┌─────────────────────────────────────┐
│         脚本执行过程中               │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   发生错误                           │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   抛出相应异常                       │
│   ├─ 地图问题 → MapDetectionError   │
│   ├─ 游戏卡住 → GameStuckError      │
│   ├─ 设备问题 → EmulatorNotRunning  │
│   └─ 无法处理 → RequestHumanTakeover│
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   上层捕获异常                       │
│   ├─ 可恢复 → 重试/跳过             │
│   ├─ 需重启 → 重启游戏/模拟器       │
│   └─ 需人工 → 停止脚本，通知用户    │
└─────────────────────────────────────┘
```

---

## 6. 使用示例

### 基本抛出和捕获

```python
from module.exception import (
    MapDetectionError,
    GameStuckError,
    RequestHumanTakeover
)

# 抛出异常
def detect_map():
    # 地图识别失败
    raise MapDetectionError("无法识别当前地图状态")

# 捕获异常
try:
    detect_map()
except MapDetectionError:
    print("地图识别失败，尝试重新截图")
except GameStuckError:
    print("游戏卡住，尝试重启")
except RequestHumanTakeover:
    print("需要人工介入")
```

### 在任务中使用

```python
from module.exception import TaskEnd, ScriptEnd

def run_task():
    try:
        # 执行任务逻辑
        while True:
            # ...
            if task_complete:
                raise TaskEnd
    except TaskEnd:
        print("当前任务完成，执行下一个任务")
    except ScriptEnd:
        print("所有任务完成")
```

### 设备检查

```python
from module.exception import EmulatorNotRunningError, GameNotRunningError

def check_environment():
    if not emulator.is_running():
        raise EmulatorNotRunningError("模拟器未启动")
    
    if not game.is_running():
        raise GameNotRunningError("游戏未运行")
```

### 游戏异常处理

```python
from module.exception import GameBugError, GameStuckError

def safe_click(x, y):
    try:
        device.click(x, y)
    except GameStuckError:
        logger.warning("游戏卡住，尝试重启")
        restart_game()
    except GameBugError:
        logger.error("游戏 bug，需要重启模拟器")
        restart_emulator()
```

### 请求人工接管

```python
from module.exception import RequestHumanTakeover

def validate_config():
    if config.invalid:
        raise RequestHumanTakeover(
            "配置无效，请检查设置"
        )
```

---

## 7. 设计模式总结

| 设计模式 | 应用说明 |
|----------|----------|
| **异常层次结构** | 按照功能领域组织异常类，便于分类处理 |
| **语义化异常** | 每个异常类有明确的语义，代码自解释 |
| **防御性编程** | 通过异常机制实现错误隔离和恢复 |
| **关注点分离** | 不同类型的错误使用不同的异常类 |

**设计优点**:
- 异常分类清晰，便于针对性处理
- 语义化命名，代码可读性强
- 继承自标准 Exception，兼容 Python 异常处理机制
- 注释说明异常用途，便于理解和使用

**异常处理策略**:

| 异常类型 | 推荐处理方式 |
|----------|--------------|
| `CampaignEnd` | 正常流程，继续下一关 |
| `MapDetectionError` | 重试截图或重启游戏 |
| `GameStuckError` | 等待或重启游戏 |
| `GameBugError` | 重启游戏或模拟器 |
| `EmulatorNotRunningError` | 启动模拟器 |
| `GameNotRunningError` | 启动游戏 |
| `RequestHumanTakeover` | 停止脚本，通知用户 |

**使用建议**:
- 在可能发生错误的地方抛出具体异常
- 在上层统一捕获并处理
- 记录异常日志便于调试
- 对于可恢复异常，实现重试机制
- 对于不可恢复异常，使用 `RequestHumanTakeover`
