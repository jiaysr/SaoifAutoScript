# Bridge.py 代码详解

## 1. 文件概述

`Bridge.py` 是 QML 与 Python 之间的桥接模块，定义了一个继承自 QObject 的桥接类。该类作为全局通信中枢，用于在 QML 前端和 Python 后端之间传递数据和调用方法。

**核心职责：**
- 提供 QML 可访问的 Python 对象
- 作为全局单例桥接实例
- 预留扩展点用于添加自定义槽函数和信号

---

## 2. 导入部分解释

```python
from PySide6.QtCore import Qt, QObject  # Qt 核心类：标志位和 QObject 基类
                                        # QObject 是所有 Qt 对象的基类，支持信号槽机制
```

---

## 3. 类定义解释

```python
class Bridge(QObject):
    """
    桥接类，继承自 QObject
    QObject 是 Qt 对象模型的核心，提供：
    - 信号与槽机制
    - 对象树所有权管理
    - QML 属性系统支持
    """
    def __init__(self):
        super().__init__()  # 调用 QObject 的构造函数，注册到 Qt 对象系统
```

**设计意图：**
- 继承 QObject 使其可以被注册为 QML 上下文属性
- 可以在此类中添加 `@Slot` 装饰器的方法供 QML 调用
- 可以定义 `Signal` 用于向 QML 发送通知

---

## 4. 每个方法的逐行解释

### 4.1 `__init__(self)` 构造函数

```python
def __init__(self):
    super().__init__()  # 必须调用父类构造函数
                        # 否则 Qt 对象系统无法正确初始化
                        # 信号槽机制将无法工作
```

---

## 5. 核心算法流程图

```
Bridge 模块加载
    │
    ▼
┌─────────────────────────────────────┐
│  定义 Bridge 类                      │
│  └─ 继承 QObject                     │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  创建全局实例 bridge = Bridge()      │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  在 fluent_app.py 中导入并使用       │
│  from module.gui.Bridge import bridge│
│                                      │
│  可注册为 QML 上下文属性：           │
│  set_context_property(bridge, "bridge")│
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  QML 中访问：                        │
│  bridge.someMethod()                 │
└─────────────────────────────────────┘
```

---

## 6. 使用示例

### 6.1 在 QML 中使用桥接对象

```python
# Python 端：注册桥接对象
from module.gui.fluent_app import FluentApp
from module.gui.Bridge import bridge

app = FluentApp()
FluentApp.set_context_property(context=bridge, name='bridge')
FluentApp.run()
```

```qml
// QML 端：调用桥接方法
import QtQuick 2.15

Button {
    onClicked: {
        // 调用桥接对象的方法（如果有定义的话）
        bridge.someMethod()
    }
}
```

### 6.2 扩展桥接类

```python
from PySide6.QtCore import QObject, Slot, Signal

class Bridge(QObject):
    # 定义信号
    data_changed = Signal(str)

    def __init__(self):
        super().__init__()

    # 定义槽函数供 QML 调用
    @Slot(str, result=str)
    def process_data(self, data: str) -> str:
        """处理数据并返回结果"""
        result = data.upper()
        self.data_changed.emit(result)  # 发送信号通知 QML
        return result

    @Slot(result=str)
    def get_status(self) -> str:
        """获取当前状态"""
        return "running"

bridge = Bridge()
```

---

## 7. 设计模式总结

| 设计模式 | 应用位置 | 说明 |
|---------|---------|------|
| **桥接模式** | Bridge 类本身 | 连接 QML 前端和 Python 后端两个抽象 |
| **单例模式** | 模块级实例 `bridge` | 整个应用共享一个桥接实例 |
| **观察者模式** | Signal 信号机制 | QML 可监听 Python 状态变化 |

**架构作用：**
- 作为 QML 和 Python 之间的通信桥梁
- 遵循 Qt 的信号槽通信机制
- 支持双向数据传递和方法调用
- 通过继承 QObject 获得 Qt 元对象系统支持
