# context/add.py 代码详解

## 1. 文件概述

`context/add.py` 是脚本配置管理模块，提供脚本文件的创建、复制和命名功能。该模块处理 `config/` 目录下的 JSON 配置文件，支持从模板创建新配置。

**核心职责：**
- 列出所有可用的脚本配置文件
- 从模板复制创建新配置
- 自动生成唯一的脚本名称（oas1, oas2, ...）

---

## 2. 导入部分解释

```python
import re                                    # 正则表达式模块，用于提取文件名中的数字
from pathlib import Path                     # 路径处理库，用于跨平台路径构建
from PySide6.QtCore import QObject, Slot, Signal  # Qt 核心类：QObject 基类、槽函数、信号

from module.logger import logger             # 日志记录器
```

---

## 3. 类定义解释

```python
class Add(QObject):
    """
    脚本配置管理类
    继承 QObject 以支持 QML 调用
    """
    def __init__(self) -> None:
        super(Add, self).__init__()  # 初始化 QObject 基类
```

---

## 4. 每个方法的逐行解释

### 4.1 `all_script_files(self)` 方法

```python
@Slot(result="QVariantList")  # 声明为槽函数，返回 QVariantList 类型给 QML
def all_script_files(self) -> list:
    """
    获取所有的脚本文件（排除 template）
    :return: ['oas1', 'oas2'] 格式的列表
    """
    # 构建 config 目录路径
    config_path = Path.cwd() / 'config'

    # 使用 glob 匹配所有 .json 文件
    json_files = config_path.glob('*.json')

    result = []
    for json in json_files:
        # json.stem 获取不含扩展名的文件名
        # 跳过 template 文件
        if json.stem == 'template':
            continue
        result.append(json.stem)

    return result  # 返回文件名列表
```

### 4.2 `all_json_file(self)` 方法

```python
@Slot(result="QVariantList")  # 声明为槽函数，返回 QVariantList 类型给 QML
def all_json_file(self) -> list:
    """
    获取所有的 json 文件（包含 template）
    :return: ['template', 'oas1', 'oas2'] 格式的列表
    """
    # 构建 config 目录路径
    config_path = Path.cwd() / 'config'

    # 使用 glob 匹配所有 .json 文件
    json_files = config_path.glob('*.json')

    result = []
    for json in json_files:
        if json.stem == 'template':
            # template 文件插入到列表开头
            result.insert(0, json.stem)
        else:
            # 其他文件追加到列表末尾
            result.append(json.stem)

    return result
```

### 4.3 `copy(self, file, template)` 方法

```python
@Slot(str, str)  # 声明为槽函数，接收两个字符串参数
def copy(self, file: str, template: str = 'template') -> None:
    """
    复制一个配置文件
    :param file: 目标文件名（不带 .json 后缀）
    :param template: 模板文件名（默认为 'template'）
    :return: None
    """
    # 构建路径
    config_path = Path.cwd() / 'config'
    template_path = config_path / f'{template}.json'  # 模板文件路径
    file_path = config_path / f'{file}.json'          # 目标文件路径

    # 检查目标文件是否已存在
    if file_path.exists():
        logger.error(f'{file_path} is exists')
        return

    # 读取模板文件内容
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()

    # 将模板内容写入新文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(template_content)

    logger.info(f'copy {template_path} to {file_path}')
```

### 4.4 `generate_script_name(self)` 方法

```python
@Slot(result="QString")  # 声明为槽函数，返回 QString 类型给 QML
def generate_script_name(self) -> str:
    """
    生成一个新的配置名称
    :return: 如 'oas1', 'oas2' 等
    """
    # 获取所有脚本文件
    all_script_files = self.all_script_files()

    # 如果没有脚本文件，返回默认名称
    if not all_script_files:
        return 'oas1'

    # 提取所有文件名中的数字
    script_numbers = []
    for script_file in all_script_files:
        # 使用正则表达式匹配数字
        match = re.search(r'\d+', script_file)
        if match:
            script_number = int(match.group())
            script_numbers.append(script_number)

    # 如果没有找到数字，返回默认名称
    if not script_numbers:
        return 'oas1'

    # 排序并取最大值加 1
    script_numbers.sort()
    new_script_number = script_numbers[-1] + 1

    return f'oas{new_script_number}'
```

---

## 5. 核心算法流程图

### 5.1 脚本名称生成流程

```
generate_script_name()
    │
    ▼
┌─────────────────────────────────────┐
│  获取所有脚本文件列表                │
│  all_script_files()                  │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  列表是否为空？                      │
│  ├─ 是 → 返回 'oas1'               │
│  └─ 否 ↓                           │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  遍历文件名，提取数字                │
│  re.search(r'\d+', filename)        │
│  例: 'oas12' → 12                   │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  数字列表是否为空？                  │
│  ├─ 是 → 返回 'oas1'               │
│  └─ 否 ↓                           │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  排序取最大值，加 1                  │
│  [1, 3, 5] → max=5 → 6             │
│  返回 'oas6'                        │
└─────────────────────────────────────┘
```

### 5.2 配置文件复制流程

```
copy(file, template)
    │
    ▼
┌─────────────────────────────────────┐
│  构建模板路径和目标路径              │
│  config/{template}.json             │
│  config/{file}.json                 │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  目标文件是否已存在？                │
│  ├─ 是 → 记录错误，返回             │
│  └─ 否 ↓                           │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  读取模板文件内容                    │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  写入目标文件                        │
└─────────────────────────────────────┘
    │
    ▼
  记录日志，完成
```

---

## 6. 使用示例

### 6.1 在 Python 中使用

```python
from module.gui.context.add import Add

add = Add()

# 获取所有脚本文件
scripts = add.all_script_files()
print(scripts)  # ['oas1', 'oas2', 'oas3']

# 生成新脚本名称
new_name = add.generate_script_name()
print(new_name)  # 'oas4'

# 从模板复制创建新配置
add.copy('oas4')
```

### 6.2 在 QML 中使用

```qml
import QtQuick 2.15

Button {
    onClicked: {
        // 获取所有脚本文件
        var scripts = add.all_script_files()

        // 生成新名称
        var newName = add.generate_script_name()

        // 创建新配置
        add.copy(newName)
    }
}
```

---

## 7. 设计模式总结

| 设计模式 | 应用位置 | 说明 |
|---------|---------|------|
| **模板方法模式** | copy() | 从模板文件复制生成新配置 |
| **工厂方法模式** | generate_script_name() | 自动生成唯一名称 |
| **策略模式** | all_script_files/all_json_file | 提供不同的文件列表策略 |

**命名规则：**
- 脚本文件命名格式：`oas{数字}`
- 自动递增确保名称唯一
- template.json 作为模板文件被排除在脚本列表之外
