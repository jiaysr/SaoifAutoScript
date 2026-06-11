# fluent_app.py 代码详解

## 1. 文件概述

`fluent_app.py` 是 GUI 应用程序的主入口文件，负责初始化 Qt/QML 应用程序引擎、设置国际化翻译、管理 DPI 缩放策略。该文件采用 PySide6 框架实现 FluentUI 风格的桌面应用。

**核心职责：**
- 初始化 QGuiApplication 和 QQmlApplicationEngine
- 管理应用程序的上下文属性（Context Property）
- 提供国际化语言切换功能
- 处理高 DPI 显示适配

---

## 2. 导入部分解释

```python
import sys                                          # 系统参数，用于传递命令行参数给 QApplication
import os                                           # 操作系统接口，用于环境变量和路径操作

from PySide6.QtGui import QGuiApplication, QIcon    # Qt GUI 核心类：应用实例和图标
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType  # QML 引擎和类型注册
from PySide6.QtCore import Qt, QObject, QTranslator, QLocale, Slot  # Qt 核心：标志位、基类、翻译器、区域设置、槽函数
from pathlib import Path                            # 路径处理库，用于跨平台路径构建

from module.gui.utils import get_work_path          # 获取工作目录路径的工具函数
from module.gui.Bridge import bridge                # QML 与 Python 的桥接对象
from module.logger import logger                    # 日志记录器

import module.gui.res_rcc                           # 资源文件编译模块（图标、图片等）
```

---

## 3. 类定义解释

### 3.1 FluentApp 类

```python
class FluentApp():
    app = None          # 类变量：QGuiApplication 实例
    engine = None       # 类变量：QQmlApplicationEngine 实例
    translator = None   # 类变量：Translator 翻译器实例
    dpi = None          # 类变量：DpiScale DPI缩放实例
```

**设计特点：**
- 使用类变量而非实例变量，确保全局唯一性
- 采用单例模式思想，整个应用只维护一个 QGuiApplication 实例

---

## 4. 每个方法的逐行解释

### 4.1 `__init__(self)` 构造函数

```python
def __init__(self):
    super().__init__()                              # 调用父类构造函数（object）

    # 设置 Qt Quick 控件样式为 "Basic"（基础样式，避免系统主题干扰）
    os.putenv("QT_QUICK_CONTROLS_STYLE", "Basic")

    # 创建 QGuiApplication 实例，传入命令行参数
    FluentApp.app = QGuiApplication(sys.argv)

    # 设置应用程序窗口图标
    # Path(__file__).resolve().parent 获取当前文件所在目录
    # / "res/icon.ico" 拼接图标路径
    QGuiApplication.setWindowIcon(QIcon(os.fspath(Path(__file__).resolve().parent / "res/icon.ico")))

    # 设置应用程序名称和组织名称（用于 QSettings 存储路径）
    QGuiApplication.setApplicationName("oas")
    QGuiApplication.setOrganizationName("oas")

    # 创建 QML 应用引擎
    FluentApp.engine = QQmlApplicationEngine()

    # 添加 QML 模块导入路径（让引擎能找到自定义 QML 组件）
    FluentApp.engine.addImportPath(os.fspath(Path(__file__).resolve().parent))

    # 创建翻译器实例
    FluentApp.translator = Translator(engine=FluentApp.engine, app=FluentApp.app)

    # 创建 DPI 缩放管理器实例
    FluentApp.dpi = DpiScale()

    # 将 translator 和 dpi 对象注册为 QML 上下文属性
    # 这样在 QML 中可以直接使用 translator.set_language("简体中文")
    self.set_context_property(context=FluentApp.translator, name='translator')
    self.set_context_property(context=FluentApp.dpi, name='dpi')
```

### 4.2 `run(cls)` 类方法

```python
@classmethod
def run(cls):
    # 加载主 QML 文件
    # get_work_path() 返回项目根目录
    # 拼接完整路径: {根目录}/module/gui/qml/app.qml
    FluentApp.engine.load(os.fspath(Path(get_work_path() / 'module' / 'gui' / 'qml' / 'app.qml')))

    # 检查是否成功加载了根对象
    # 如果 QML 文件有语法错误或路径错误，rootObjects() 会为空
    if not FluentApp.engine.rootObjects():
        sys.exit(-1)                                # 加载失败，退出程序

    # 进入 Qt 事件循环，等待用户交互
    # app.exec() 会阻塞直到应用程序退出
    # sys.exit() 确保返回正确的退出码
    sys.exit(FluentApp.app.exec())
```

### 4.3 `set_context_property(cls, context, name)` 类方法

```python
@classmethod
def set_context_property(cls, context, name: str) -> None:
    """
    设置上下文属性
    :param context: 要暴露给 QML 的 Python 对象
    :param name: 在 QML 中访问该对象的名称
    :return: None
    """
    # 获取根上下文并设置属性
    # 设置后在 QML 中可以直接通过 name 访问 context 对象的方法
    FluentApp.engine.rootContext().setContextProperty(name, context)
```

### 4.4 `qml_register_type(self, Class, qml_class)` 方法

```python
def qml_register_type(self, Class, qml_class: str) -> None:
    """
    注册 QML 类型
    :param Class: Python 类
    :param qml_class: 在 QML 中使用的类型名称
    :return: None
    """
    # 注册 Python 类为 QML 可用类型
    # "Oas" 是模块名，1, 0 是版本号
    # 在 QML 中可以这样使用: import Oas 1.0
    qmlRegisterType(Class, "Oas", 1, 0, qml_class)
```

---

## 5. 核心算法流程图

```
应用程序启动
    │
    ▼
┌─────────────────────────────────────┐
│  FluentApp.__init__()               │
│  ├─ 设置环境变量 QT_QUICK_CONTROLS_STYLE  │
│  ├─ 创建 QGuiApplication            │
│  ├─ 设置图标、应用名、组织名          │
│  ├─ 创建 QQmlApplicationEngine      │
│  ├─ 添加 QML 导入路径               │
│  ├─ 创建 Translator 实例            │
│  ├─ 创建 DpiScale 实例              │
│  └─ 注册上下文属性                   │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  FluentApp.run()                    │
│  ├─ 加载 app.qml 主文件             │
│  ├─ 检查根对象是否加载成功           │
│  └─ 进入 Qt 事件循环                │
└─────────────────────────────────────┘
    │
    ▼
  应用程序运行中（等待用户交互）
    │
    ▼
  应用程序退出
```

---

## 6. 使用示例

### 6.1 基本启动

```python
from module.gui.fluent_app import FluentApp

# 创建应用实例
app = FluentApp()

# 运行应用（进入事件循环）
FluentApp.run()
```

### 6.2 注册自定义 QML 类型

```python
from module.gui.fluent_app import FluentApp
from module.gui.register_type.paint_image import PaintImage

app = FluentApp()

# 注册 PaintImage 类，使其在 QML 中可用
app.qml_register_type(PaintImage, "PaintImage")

FluentApp.run()
```

### 6.3 在 QML 中使用上下文属性

```qml
// app.qml
import QtQuick 2.15

Button {
    onClicked: {
        // 调用 Python 中注册的 translator 对象
        translator.set_language("简体中文")

        // 调用 Python 中注册的 dpi 对象
        dpi.set_dpi_scale("round")
    }
}
```

---

## 7. 设计模式总结

| 设计模式 | 应用位置 | 说明 |
|---------|---------|------|
| **单例模式** | FluentApp 类变量 | 通过类变量确保全局只有一个 QApplication 实例 |
| **上下文属性模式** | set_context_property | Qt/QML 桥接的标准方式，将 Python 对象暴露给 QML |
| **工厂方法模式** | qml_register_type | 封装 QML 类型注册逻辑 |
| **模板方法模式** | run() | 定义应用启动的标准流程 |

**架构特点：**
- 采用 PySide6 + QML 的前后端分离架构
- Python 负责业务逻辑，QML 负责 UI 渲染
- 通过上下文属性和信号槽机制实现双向通信
