# context/utils.py 代码详解

## 1. 文件概述

`context/utils.py` 是 GUI 上下文工具模块，提供通用的工具函数，包括获取当前时间和测试通知功能。该模块作为 QML 可调用的工具类。

**核心职责：**
- 提供当前时间获取功能
- 提供通知推送测试功能

---

## 2. 导入部分解释

```python
import re                                    # 正则表达式（当前未使用）
from pathlib import Path                     # 路径处理库（当前未使用）
from datetime import datetime                # 日期时间类，用于获取当前时间
from PySide6.QtCore import QObject, Slot, Signal  # Qt 核心类

from module.logger import logger             # 日志记录器
```

---

## 3. 类定义解释

```python
class Utils(QObject):
    """
    工具类
    继承 QObject 以支持 QML 调用
    提供通用工具函数
    """
    def __init__(self) -> None:
        super(Utils, self).__init__()  # 初始化 QObject 基类
```

---

## 4. 每个方法的逐行解释

### 4.1 `current_datetime(self)` 方法

```python
@Slot(result="QString")  # 声明为槽函数，返回 QString 类型给 QML
def current_datetime(self) -> str:
    """
    获取当前的时间
    :return: 格式化的时间字符串，如 '2024-01-15 14:30:45'
    """
    # datetime.now() 获取当前时间
    # strftime() 格式化时间字符串
    # %Y: 四位年份, %m: 月份, %d: 日
    # %H: 24小时制小时, %M: 分钟, %S: 秒
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
```

### 4.2 `test_notify(self, _config, title, content)` 方法

```python
@Slot(str, str, str, result="QString")  # 声明为槽函数，返回 QString 类型给 QML
def test_notify(self, _config: str, title: str, content: str) -> bool:
    """
    测试通知推送
    :param _config: 配置名称
    :param title: 通知标题
    :param content: 通知内容
    :return: "true" 或 "false" 字符串
    """
    # 延迟导入，避免循环依赖
    from module.notify.notify import Notifier

    try:
        # 创建通知器实例
        # 第二个参数 True 表示启用通知
        notifier = Notifier(_config, True)

        # 推送通知
        if notifier.push(title=title, content=content):
            return "true"
        else:
            return "false"
    except Exception as e:
        logger.exception(e)
        return "false"
```

---

## 5. 核心算法流程图

### 5.1 通知测试流程

```
test_notify(_config, title, content)
    │
    ▼
┌─────────────────────────────────────┐
│  导入 Notifier 类                    │
│  from module.notify.notify import    │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  创建 Notifier 实例                  │
│  Notifier(_config, True)            │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  推送通知                            │
│  notifier.push(title, content)      │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  返回结果                            │
│  ├─ 成功 → "true"                   │
│  └─ 失败 → "false"                  │
└─────────────────────────────────────┘
```

---

## 6. 使用示例

### 6.1 在 Python 中使用

```python
from module.gui.context.utils import Utils

utils = Utils()

# 获取当前时间
current_time = utils.current_datetime()
print(current_time)  # '2024-01-15 14:30:45'

# 测试通知
result = utils.test_notify('oas1', '测试标题', '测试内容')
print(result)  # 'true' 或 'false'
```

### 6.2 在 QML 中使用

```qml
import QtQuick 2.15

Text {
    // 显示当前时间
    text: utils.current_datetime()
}

Button {
    onClicked: {
        // 测试通知推送
        var result = utils.test_notify("oas1", "任务完成", "脚本已运行结束")
        console.log(result)  // "true" 或 "false"
    }
}
```

---

## 7. 设计模式总结

| 设计模式 | 应用位置 | 说明 |
|---------|---------|------|
| **工具类模式** | Utils 类 | 提供无状态的工具函数 |
| **延迟导入** | test_notify() | 避免模块循环依赖 |
| **门面模式** | test_notify() | 封装通知系统的复杂性 |

**注意事项：**
- `test_notify()` 使用延迟导入避免循环依赖
- 返回字符串 "true"/"false" 而非布尔值，是为了兼容 QML 类型系统
- 异常处理确保通知失败时不会崩溃
