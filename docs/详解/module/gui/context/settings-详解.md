# context/settings.py 代码详解

## 1. 文件概述

`context/settings.py` 是应用程序设置管理模块，负责读取、更新和初始化全局配置文件 `setting.json`。该模块提供从模板创建默认配置的功能。

**核心职责：**
- 读取 setting.json 配置文件
- 更新配置文件内容
- 从模板文件初始化默认配置

---

## 2. 导入部分解释

```python
from pathlib import Path                     # 路径处理库，用于跨平台路径构建
from PySide6.QtCore import QObject, Slot, Signal  # Qt 核心类：QObject 基类、槽函数、信号

from module.logger import logger             # 日志记录器
```

---

## 3. 类定义解释

```python
class Setting(QObject):
    """
    设置管理类
    继承 QObject 以支持 QML 调用
    管理 module/config/argument/setting.json 配置文件
    """
```

---

## 4. 每个方法的逐行解释

### 4.1 `copy_from_template(cls)` 类方法

```python
@classmethod
def copy_from_template(cls) -> None:
    """
    从模板复制一个配置文件
    将 setting-template.json 复制为 setting.json
    :return: None
    """
    # 构建模板文件路径
    template_path = Path.cwd() / 'module' / 'config' / 'argument' / 'setting-template.json'

    # 检查模板文件是否存在
    if not template_path.exists():
        logger.error('template.json not exists')
        return

    # 读取模板文件内容
    with open(template_path, 'r', encoding='utf-8') as f:
        data = f.read()

    # 构建目标文件路径
    setting_path = Path.cwd() / 'module' / 'config' / 'argument' / 'setting.json'

    # 写入目标文件
    with open(setting_path, 'w', encoding='utf-8') as f:
        f.write(data)

    logger.info('setting.json copy from template.json success')
```

### 4.2 `read(self)` 方法

```python
@Slot(result="QString")  # 声明为槽函数，返回 QString 类型给 QML
def read(self) -> str:
    """
    读取配置文件的数据
    :return: JSON 格式的字符串
    """
    # 构建配置文件路径
    setting_path = Path.cwd() / 'module' / 'config' / 'argument' / 'setting.json'

    # 检查配置文件是否存在
    if not setting_path.exists():
        logger.error('setting.json not exists')
        self.copy_from_template()  # 不存在则从模板创建

    # 读取并返回配置内容
    with open(setting_path, 'r', encoding='utf-8') as f:
        return f.read()
```

### 4.3 `update(self, data)` 方法

```python
@Slot(str)  # 声明为槽函数，接收一个字符串参数
def update(self, data: str) -> None:
    """
    更新配置文件的数据
    :param data: 要写入的 JSON 字符串
    :return: None
    """
    # 构建配置文件路径
    setting_path = Path.cwd() / 'module' / 'config' / 'argument' / 'setting.json'

    # 检查配置文件是否存在
    if not setting_path.exists():
        logger.error('setting.json not exists')
        self.copy_from_template()  # 不存在则从模板创建

    # 写入新配置内容
    with open(setting_path, 'w', encoding='utf-8') as f:
        f.write(data)

    logger.info('setting.json update success')
```

---

## 5. 核心算法流程图

### 5.1 读取配置流程

```
read()
    │
    ▼
┌─────────────────────────────────────┐
│  构建配置文件路径                    │
│  module/config/argument/setting.json│
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  文件是否存在？                      │
│  ├─ 否 → copy_from_template()      │
│  └─ 是 ↓                           │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  读取文件内容                        │
│  return f.read()                     │
└─────────────────────────────────────┘
```

### 5.2 更新配置流程

```
update(data)
    │
    ▼
┌─────────────────────────────────────┐
│  构建配置文件路径                    │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  文件是否存在？                      │
│  ├─ 否 → copy_from_template()      │
│  └─ 是 ↓                           │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  写入新配置内容                      │
│  f.write(data)                       │
└─────────────────────────────────────┘
    │
    ▼
  记录日志，完成
```

### 5.3 从模板复制流程

```
copy_from_template()
    │
    ▼
┌─────────────────────────────────────┐
│  构建模板文件路径                    │
│  setting-template.json               │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  模板文件是否存在？                  │
│  ├─ 否 → 记录错误，返回             │
│  └─ 是 ↓                           │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  读取模板内容                        │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  写入 setting.json                   │
└─────────────────────────────────────┘
    │
    ▼
  记录日志，完成
```

---

## 6. 使用示例

### 6.1 在 Python 中使用

```python
from module.gui.context.settings import Setting

setting = Setting()

# 读取配置
config_json = setting.read()
print(config_json)

# 更新配置
new_config = '{"theme": "dark", "language": "zh_CN"}'
setting.update(new_config)

# 从模板重置配置
Setting.copy_from_template()
```

### 6.2 在 QML 中使用

```qml
import QtQuick 2.15

Button {
    onClicked: {
        // 读取配置
        var config = setting.read()
        console.log(config)

        // 更新配置
        setting.update('{"theme": "light"}')
    }
}
```

---

## 7. 设计模式总结

| 设计模式 | 应用位置 | 说明 |
|---------|---------|------|
| **模板方法模式** | copy_from_template() | 从模板文件初始化配置 |
| **空对象模式** | read()/update() | 文件不存在时自动从模板创建 |
| **单例模式** | 类设计 | Setting 类通常只实例化一次 |

**文件路径结构：**
```
module/config/argument/
├── setting-template.json  # 模板文件
└── setting.json           # 实际配置文件
```

**容错机制：**
- 如果 setting.json 不存在，自动从模板创建
- 确保配置文件始终可用
