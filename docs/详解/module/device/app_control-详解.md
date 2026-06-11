# module.device.app_control 模块详解

## 1. 文件概述

`app_control.py` 定义了 `AppControl` 类，负责**应用生命周期管理**，包括：
- 检测应用是否正在运行
- 启动和停止应用
- 导出 UI 层级结构（dump hierarchy）
- 通过 XPath 查找 UI 元素

**文件路径**: `module/device/app_control.py`
**代码行数**: 67 行

## 2. 导入部分解释

```python
from lxml import etree                           # XML/HTML 解析库，用于解析 UI 层级
from module.device.method.adb import Adb          # ADB 应用控制方法
from module.device.method.uiautomator_2 import Uiautomator2  # u2 应用控制方法
from module.device.method.utils import HierarchyButton        # 层级按钮工具类
from module.logger import logger
```

## 3. 类定义解释

```python
class AppControl(Adb, Uiautomator2):
    hierarchy: etree._Element          # UI 层级树的 XML 元素
    _app_u2_family = ['uiautomator2', 'minitouch', 'scrcpy']  # 使用 u2 的方法族
```

**设计要点**: `_app_u2_family` 将 `minitouch` 和 `scrcpy` 归入 uiautomator2 族，因为它们底层都依赖 uiautomator2 的 ATX agent。

## 4. 方法逐行解释

### 4.1 `app_is_running(self)` — 检测应用是否运行（第 14-25 行）

```python
def app_is_running(self) -> bool:
    method = self.config.script.device.control_method
    if method in AppControl._app_u2_family:
        package = self.app_current_uiautomator2()  # 通过 u2 获取当前前台应用
    else:
        package = self.app_current_adb()           # 通过 ADB dumpsys 获取

    package = package.strip(' \t\r\n')  # 清理空白字符
    logger.attr('Package_name', package)
    return package == self.package      # 与目标包名比较
```

**逻辑**: 获取当前前台应用的包名，与配置中的目标包名比较。

### 4.2 `app_start(self)` — 启动应用（第 27-35 行）

```python
def app_start(self):
    method = self.config.script.device.screenshot_method  # 注意：用的是截图方法
    logger.info(f'App start: {self.package}')
    if method in AppControl._app_u2_family:
        self.app_start_uiautomator2()  # u2 启动
    else:
        self.app_start_adb()           # ADB am start 启动
```

**注意**: 这里使用的是 `screenshot_method` 而非 `control_method`，这是一个设计选择。

### 4.3 `app_stop(self)` — 停止应用（第 37-43 行）

```python
def app_stop(self):
    method = self.config.script.device.screenshot_method
    logger.info(f'App stop: {self.package}')
    if method in AppControl._app_u2_family:
        self.app_stop_uiautomator2()  # u2 停止
    else:
        self.app_stop_adb()           # ADB am force-stop 停止
```

### 4.4 `dump_hierarchy(self)` — 导出 UI 层级（第 45-55 行）

```python
def dump_hierarchy(self) -> etree._Element:
    method = self.config.script.device.screenshot_method
    if method in AppControl._app_u2_family:
        self.hierarchy = self.dump_hierarchy_uiautomator2()  # u2 dump
    else:
        self.hierarchy = self.dump_hierarchy_adb()           # ADB dump
    return self.hierarchy
```

**返回值**: lxml 的 `_Element` 对象，支持 XPath 查询。

### 4.5 `xpath_to_button(self, xpath)` — XPath 查找元素（第 57-67 行）

```python
def xpath_to_button(self, xpath: str) -> HierarchyButton:
    return HierarchyButton(self.hierarchy, xpath)
```

**返回值**: `HierarchyButton` 对象，类似 `Button` 的接口，支持点击等操作。如果元素未找到或找到多个，返回 `None`。

## 5. 核心算法流程图

```
应用控制方法选择:
  │
  ├── control_method ∈ ['uiautomator2', 'minitouch', 'scrcpy']
  │     ├── app_is_running → app_current_uiautomator2()
  │     ├── app_start      → app_start_uiautomator2()
  │     └── app_stop       → app_stop_uiautomator2()
  │
  └── 其他 control_method (如 'ADB')
        ├── app_is_running → app_current_adb()
        ├── app_start      → app_start_adb()
        └── app_stop       → app_stop_adb()

dump_hierarchy 流程:
  │
  ├── u2 族 → u2.dump_hierarchy() → XML 解析
  └── ADB 族 → adb shell uiautomator dump → XML 解析

xpath_to_button 使用:
  │
  ├── hierarchy.xpath(xpath) → 匹配元素
  ├── 0 个匹配 → 返回 None
  ├── 1 个匹配 → 返回 HierarchyButton
  └── 多个匹配 → 返回 None
```

## 6. 使用示例

```python
app = AppControl(config="oas1")

# 检查游戏是否在前台
if app.app_is_running():
    print("游戏正在运行")
else:
    app.app_start()  # 启动游戏

# 导出 UI 层级
hierarchy = app.dump_hierarchy()

# 查找按钮
btn = app.xpath_to_button('//*[@text="确认"]')
if btn is not None:
    btn.click()

# 停止游戏
app.app_stop()
```

## 7. 设计模式总结

- **策略模式**: 根据控制方法选择 u2 或 ADB 的具体实现
- **门面模式**: `AppControl` 为底层 u2 和 ADB 方法提供了统一的高级接口
- **族概念**: `_app_u2_family` 将依赖 u2 ATX agent 的方法归为一族，简化方法选择逻辑
- **XPath 查询**: 通过 `lxml` 的 XPath 支持实现灵活的 UI 元素定位
