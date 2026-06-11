# module/server/config_manager.py 详解

## 1. 文件概述

`config_manager.py` 是配置文件管理模块，负责：
- 管理脚本配置文件（JSON 格式）
- 提供配置文件的增删改查操作
- 生成新的配置文件名
- 复制和重命名配置文件

## 2. 导入部分解释

```python
import re                    # 正则表达式模块
from pathlib import Path     # 文件路径操作
from module.logger import logger  # 项目日志模块
```

## 3. 类定义解释

### ConfigManager 类（第9-136行）
配置文件管理器，提供静态方法管理 `config` 目录下的 JSON 配置文件。

## 4. 每个方法的逐行解释

### all_script_files 静态方法（第11-29行）
```python
@staticmethod
def all_script_files() -> list[str]:
    """
    获取所有的脚本文件 除了tmplate
    :return: ['oas1', 'oas2']
    """
    # 获取某个路径的所有json文件名
    config_path = Path.cwd() / 'config'  # 配置文件目录
    json_files = config_path.glob('*.json')  # 获取所有 JSON 文件
    result = []
    for json in json_files:
        if json.stem == 'template':  # 跳过模板文件
            continue
        result.append(json.stem)  # 添加文件名（不含扩展名）
    if len(result) == 0:
        # 如果没有脚本文件 则创建一个
        ConfigManager.copy(file='oas1', template='template')
        result.append('oas1')
    return result
```

### all_json_file 静态方法（第31-46行）
```python
@staticmethod
def all_json_file() -> list:
    """
    获取所有的json文件
    :return: ['oas1', 'oas2']
    """
    # 获取某个路径的所有json文件名
    config_path = Path.cwd() / 'config'
    json_files = config_path.glob('*.json')
    result = []
    for json in json_files:
        if json.stem == 'template':  # 模板文件放在列表开头
            result.insert(0, json.stem)
        else:
            result.append(json.stem)
    return result
```

### copy 静态方法（第48-67行）
```python
@staticmethod
def copy(file: str, template: str = 'template') -> None:
    """
    复制一个配置文件
    :param file:  不带json后缀
    :param template:
    :return:
    """
    config_path = Path.cwd() / 'config'  # 配置目录
    template_path = config_path / f'{template}.json'  # 模板文件路径
    file_path = config_path / f'{file}.json'  # 目标文件路径
    if file_path.exists():  # 如果目标文件已存在
        logger.error(f'{file_path} is exists')
        return

    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()  # 读取模板内容
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(template_content)  # 写入新文件
    logger.info(f'copy {template_path} to {file_path}')
```

### generate_script_name 静态方法（第70-91行）
```python
@staticmethod
def generate_script_name() -> str:
    """
    生成一个新的配置的名字
    :return:
    """
    all_script_files = ConfigManager.all_script_files()  # 获取所有脚本文件
    if not all_script_files:
        return 'oas1'  # 默认名称

    script_numbers = []
    for script_file in all_script_files:
        match = re.search(r'\d+', script_file)  # 提取文件名中的数字
        if match:
            script_number = int(match.group())
            script_numbers.append(script_number)

    if not script_numbers:
        return 'oas1'  # 如果没有数字，返回默认名称
    script_numbers.sort()  # 排序
    new_script_number = script_numbers[-1] + 1  # 最大数字 +1
    return f'oas{new_script_number}'  # 生成新名称
```

### rename 静态方法（第93-116行）
```python
@staticmethod
def rename(old_name: str, new_name: str) -> bool:
    """
    重命名一个配置文件
    :param old_name: 旧的配置文件名称
    :param new_name: 新的配置文件名称
    :return: True or False
    """
    config_path = Path.cwd() / 'config'
    old_path = config_path / f'{old_name}.json'  # 旧文件路径
    new_path = config_path / f'{new_name}.json'  # 新文件路径
    if not old_path.exists():  # 检查旧文件是否存在
        logger.error(f'{old_path} is not exists')
        return False
    if new_path.exists():  # 检查新文件是否已存在
        logger.error(f'{new_path} is exists')
        return False
    try:
        old_path.rename(new_path)  # 重命名文件
        logger.info(f'rename {old_path} to {new_path}')
        return True
    except Exception as e:
        logger.error(f'rename {old_path} to {new_path} failed: {e}')
        return False
```

### delete 静态方法（第118-136行）
```python
@staticmethod
def delete(file: str) -> bool:
    """
    删除一个配置文件
    :param file:  不带json后缀
    :return: True or False
    """
    config_path = Path.cwd() / 'config'
    file_path = config_path / f'{file}.json'  # 文件路径
    if not file_path.exists():  # 检查文件是否存在
        logger.error(f'{file_path} is not exists')
        return False
    try:
        file_path.unlink()  # 删除文件
        logger.info(f'delete {file_path}')
        return True
    except Exception as e:
        logger.error(f'delete {file_path} failed: {e}')
        return False
```

## 5. 核心算法流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    配置文件管理流程                           │
├─────────────────────────────────────────────────────────────┤
│  获取配置文件列表                                             │
│  ├─ all_script_files(): 获取除 template 外的所有配置         │
│  └─ all_json_file(): 获取所有配置（template 排在前面）        │
│                                                             │
│  创建配置文件                                                 │
│  ├─ copy(): 从模板复制新配置                                 │
│  └─ generate_script_name(): 生成唯一配置名                   │
│                                                             │
│  修改配置文件                                                 │
│  └─ rename(): 重命名配置文件                                 │
│                                                             │
│  删除配置文件                                                 │
│  └─ delete(): 删除指定配置文件                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    配置名生成算法                             │
├─────────────────────────────────────────────────────────────┤
│  1. 获取所有现有配置文件名                                    │
│     ↓                                                        │
│  2. 提取文件名中的数字部分                                    │
│     ├─ oas1 → 1                                              │
│     ├─ oas2 → 2                                              │
│     └─ oas10 → 10                                            │
│     ↓                                                        │
│  3. 找到最大数字                                              │
│     ↓                                                        │
│  4. 新配置名 = "oas" + (最大数字 + 1)                        │
└─────────────────────────────────────────────────────────────┘
```

## 6. 使用示例

### 获取所有配置文件
```python
from module.server.config_manager import ConfigManager

# 获取所有脚本配置（不含 template）
scripts = ConfigManager.all_script_files()
print(scripts)  # ['oas1', 'oas2', ...]

# 获取所有 JSON 配置（含 template）
all_configs = ConfigManager.all_json_file()
print(all_configs)  # ['template', 'oas1', 'oas2', ...]
```

### 创建新配置
```python
# 从模板复制创建新配置
ConfigManager.copy(file='oas3', template='template')

# 生成新的配置名
new_name = ConfigManager.generate_script_name()
print(new_name)  # 'oas3'（如果 oas1, oas2 已存在）
```

### 重命名和删除配置
```python
# 重命名配置
success = ConfigManager.rename('oas1', 'my_config')
print(success)  # True

# 删除配置
success = ConfigManager.delete('oas2')
print(success)  # True
```

## 7. 设计模式总结

1. **静态工具类模式**: 所有方法都是静态方法，无需实例化
2. **文件管理模式**: 提供完整的文件 CRUD 操作
3. **命名生成模式**: 自动生成唯一的配置文件名
4. **防御性编程**: 检查文件是否存在，处理异常情况
5. **日志记录模式**: 所有操作都记录日志