# config_updater.py 代码详解

## 1. 文件概述

`config_updater.py` 定义了 `ConfigUpdater` 类，负责配置文件的更新和维护。它提供了从模板更新配置、读写配置文件等功能。

**主要职责：**
- 从 args.json 更新模板配置
- 从 template 更新用户配置
- 提供配置文件的读写接口

## 2. 导入部分解释

```python
import re                              # 正则表达式
from copy import deepcopy             # 深拷贝

from cached_property import cached_property  # 缓存属性

from deploy.utils import DEPLOY_TEMPLATE, poor_yaml_read, poor_yaml_write  # 部署工具
from module.base.timer import timer   # 计时器装饰器
from module.config.utils import *     # 配置工具函数
```

**导入说明：**
- `re`: 用于正则表达式处理
- `deepcopy`: 深拷贝配置对象
- `cached_property`: 缓存属性计算结果
- `deploy.utils`: 部署相关的工具函数
- `timer`: 性能计时装饰器

## 3. 类定义解释

### 3.1 ConfigUpdater 类

```python
class ConfigUpdater:
    # 配置更新器
```

这个类提供了配置文件的更新和维护功能。

## 4. 每个方法的逐行解释

### 4.1 args 属性

```python
@cached_property
def args(self):
    # 读取 args.json 文件并返回
    return read_file(filepath_args(filename='args'))
```

**功能：** 缓存并返回 args.json 的内容。

**说明：**
- `filepath_args(filename='args')` 返回 `./module/config/argument/args.json`
- 使用 `cached_property` 确保只读取一次

### 4.2 update_template 方法

```python
@timer
def update_template(self, template_name: str = "template") -> None:
    """
    更新模板 。从args.json更新
    :param template_name:
    :return:
    """
    pass  # 当前为空实现
```

**功能：** 从 args.json 更新模板配置。

**装饰器说明：**
- `@timer`: 记录方法执行时间

**注意：** 当前方法为空实现（pass），可能是预留接口。

### 4.3 update_config 方法

```python
@timer
def update_config(self, config_name: str) -> None:
    """
    更新配置文件.从template更新
    :param config_name:
    :return:
    """
    pass  # 当前为空实现
```

**功能：** 从 template 更新用户配置文件。

**注意：** 当前方法为空实现（pass），可能是预留接口。

### 4.4 read_file 方法

```python
def read_file(self, config_name, is_template=False):
    """
    Read and update config file.

    Args:
        config_name (str): ./config/{file}.json
        is_template (bool):

    Returns:
        dict:
    """
    # 读取配置文件
    old = read_file(filepath_config(config_name))
    
    # 原始代码中有更新逻辑，但因性能问题被注释
    # new = self.config_update(old, is_template=is_template)
    # self.write_file(config_name, new)
    
    return old
```

**功能：** 读取配置文件。

**参数说明：**
- `config_name`: 配置文件名（不带扩展名）
- `is_template`: 是否为模板文件（当前未使用）

**说明：** 注释掉的代码表明原本有更新逻辑，但因性能问题被移除。

### 4.5 write_file 方法

```python
@staticmethod
def write_file(config_name, data, mod_name='alas'):
    """
    Write config file.

    Args:
        config_name (str): ./config/{file}.json
        data (dict):
        mod_name (str):
    """
    # 构建文件路径并写入
    write_file(filepath_config(config_name, mod_name), data)
```

**功能：** 写入配置文件。

**参数说明：**
- `config_name`: 配置文件名
- `data`: 要写入的数据字典
- `mod_name`: 模块名，默认为 'alas'

## 5. 核心算法流程图

### 5.1 配置更新流程

```
┌─────────────────────────────────────────────────────────────┐
│                   配置更新流程                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 更新模板流程（update_template）                          │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │ 读取 args   │────→│ 解析配置项   │────→│ 更新模板     │   │
│  │   .json     │     │             │     │   .json     │   │
│  └─────────────┘     └─────────────┘     └─────────────┘   │
│                                                              │
│  2. 更新用户配置流程（update_config）                        │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │ 读取模板    │────→│ 对比差异     │────→│ 更新用户     │   │
│  │ 配置文件    │     │             │     │ 配置文件     │   │
│  └─────────────┘     └─────────────┘     └─────────────┘   │
│                                                              │
│  3. 读取配置流程（read_file）                                │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────┐     ┌─────────────┐                        │
│  │ 构建文件路径 │────→│ 调用工具函数 │────→ 返回字典          │
│  └─────────────┘     │   read_file │                        │
│                      └─────────────┘                        │
│                                                              │
│  4. 写入配置流程（write_file）                               │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────┐     ┌─────────────┐                        │
│  │ 构建文件路径 │────→│ 调用工具函数 │────→ 写入完成          │
│  └─────────────┘     │  write_file │                        │
│                      └─────────────┘                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 配置文件结构

```
配置文件目录结构：
.
├── config/
│   ├── oas1.json          # 用户配置文件 1
│   ├── oas2.json          # 用户配置文件 2
│   └── template.json      # 模板配置文件
│
└── module/
    └── config/
        └── argument/
            └── args.json  # 参数定义文件
```

## 6. 使用示例

```python
from module.config.config_updater import ConfigUpdater

# 创建更新器实例
updater = ConfigUpdater()

# 读取 args 配置
args_data = updater.args
print(f"Args: {args_data}")

# 读取配置文件
config_data = updater.read_file('oas1')
print(f"Config: {config_data}")

# 写入配置文件
new_data = {
    'script': {
        'optimization': {
            'schedule_rule': 'FIFO'
        }
    }
}
ConfigUpdater.write_file('oas1', new_data)

# 更新模板（当前为空实现）
updater.update_template('template')

# 更新用户配置（当前为空实现）
updater.update_config('oas1')

# 使用 timer 装饰器查看执行时间
# 输出类似：update_template: 0.001s
```

## 7. 设计模式总结

### 7.1 模板方法模式（Template Method）
定义了配置更新的算法骨架，具体实现由子类或后续代码补充。

### 7.2 缓存模式（Caching）
使用 `cached_property` 缓存 args 数据，避免重复读取文件。

### 7.3 静态方法模式
`write_file` 使用 `@staticmethod`，不依赖实例状态。

### 7.4 性能监控模式
使用 `@timer` 装饰器监控方法执行时间。

**设计优点：**
- 接口清晰：读写操作分离
- 性能优化：使用缓存减少 IO 操作
- 可扩展：预留了更新接口
- 可监控：使用计时器跟踪性能

**当前状态：**
- `update_template` 和 `update_config` 方法为空实现
- `read_file` 中的更新逻辑被注释
- 可能是项目早期代码，功能尚未完全实现

**注意事项：**
- `read_file` 函数名与 Python 内置函数同名，但作用域不同
- `mod_name='alas'` 是历史遗留参数
- 文件路径使用相对路径，依赖工作目录
