# config_model.py 代码详解

## 1. 文件概述

`config_model.py` 定义了配置系统的数据模型层，使用 Pydantic 库实现数据验证和序列化。`ConfigModel` 类是所有任务配置的容器，包含了游戏脚本中所有任务的配置定义。

**主要职责：**
- 定义所有任务的配置模型结构
- 提供 JSON 配置文件的读写功能
- 实现配置参数的 GUI 交互接口
- 支持配置的深拷贝和重置功能

## 2. 导入部分解释

```python
from tasks.GuildActivityMonitor.config import GuildActivityMonitor  # 寮活动监控配置
from typing import Dict, Any  # 类型注解

import re                    # 正则表达式
import inflection            # 命名风格转换（驼峰<->下划线）

from pathlib import Path     # 路径处理
from pydantic import BaseModel, ValidationError, Field  # Pydantic 数据模型

from module.config.utils import *  # 工具函数
from module.logger import logger   # 日志记录器

# 导入各个任务的配置类
from tasks.Component.config_base import ConfigBase, TimeDelta
from tasks.Exploration.config import Exploration
from tasks.RyouToppa.config import RyouToppa
# ... 更多任务配置导入
```

**任务配置分类：**
- **基础配置**: Script, Restart, GlobalGame
- **每日任务**: AreaBoss, ExperienceYoukai, GoldYoukai, Nian 等
- **御魂副本**: Orochi, OrochiMoans, Sougenbi, FallenSun 等
- **活动任务**: ActivityShikigami, MetaDemon, FrogBoss 等
- **肝帝专属**: BondlingFairyland, EvoZone, GoryouRealm 等
- **每周任务**: TrueOrochi, RichMan, Secret 等
- **阴阳寮**: CollectiveMissions, Hunt, Dokan 等

## 3. 类定义解释

### 3.1 ConfigModel 类

```python
class ConfigModel(ConfigBase):
    config_name: str = "oas"           # 配置文件名
    running_task: str = ''             # 当前运行的任务名
    script: Script = Field(default_factory=Script)      # 脚本配置
    restart: Restart = Field(default_factory=Restart)    # 重启配置
    global_game: GlobalGame = Field(default_factory=GlobalGame)  # 全局游戏配置
    
    # 每日任务配置
    area_boss: AreaBoss = Field(default_factory=AreaBoss)
    experience_youkai: ExperienceYoukai = Field(default_factory=ExperienceYoukai)
    # ... 更多字段定义
```

**字段说明：**
- 使用 `Field(default_factory=...)` 创建默认值工厂，确保每个实例获得独立的配置对象
- 所有任务配置都继承自 `BaseModel`，支持自动验证和序列化

## 4. 每个方法的逐行解释

### 4.1 ConfigModel.__init__

```python
def __init__(self, config_name: str=None) -> None:
    if not config_name:
        super().__init__()  # 无配置名时使用默认值
        return
    
    data = self.read_json(config_name)  # 读取 JSON 配置文件
    data["config_name"] = config_name   # 添加配置名到数据中
    super().__init__(**data)            # 使用配置数据初始化
```

### 4.2 ConfigModel.__setattr__

```python
def __setattr__(self, key, value):
    super().__setattr__(key, value)  # 调用父类设置属性
    logger.info("auto save config")  # 记录日志
    self.save()                      # 自动保存到文件
```

**注意：** 这个方法会在每次属性修改时自动触发保存，实现了配置的持久化。

### 4.3 ConfigModel.read_json

```python
@staticmethod
def read_json(config_name: str) -> dict:
    # 构建配置文件路径: ./config/{config_name}.json
    filepath = Path.cwd() / "config" / f"{config_name}.json"
    return read_file(filepath)  # 调用工具函数读取文件
```

### 4.4 ConfigModel.write_json

```python
@staticmethod
def write_json(config_name: str, data) -> None:
    filepath = Path.cwd() / "config" / f"{config_name}.json"
    write_file(filepath, data)  # 调用工具函数写入文件
```

### 4.5 ConfigModel.gui_args

```python
def gui_args(self, task: str) -> str:
    # 转换任务名为下划线格式
    task = convert_to_underscore(task)
    task_gui = getattr(self, task, None)
    
    if task_gui is None:
        logger.warning(f'{task} is no inexistence')
        return ''
    
    # 获取 Pydantic 模型的 JSON Schema
    schema2 = task_gui.schema()
    
    # 特殊处理 Scheduler 类型的字段
    if 'definitions' in schema2:
        if 'Scheduler' in schema2['definitions']:
            if 'properties' in schema2['definitions']['Scheduler']:
                properties = schema2['definitions']['Scheduler']['properties']
                # 将时间间隔字段类型改为 string
                if 'success_interval' in properties:
                    properties['success_interval']['type'] = 'string'
                if 'failure_interval' in properties:
                    properties['failure_interval']['type'] = 'string'
    
    return json.dumps(schema2)  # 返回 JSON 字符串
```

### 4.6 ConfigModel.gui_task

```python
def gui_task(self, task: str) -> str:
    task_name = convert_to_underscore(task)
    task = getattr(self, task_name, None)
    
    if task is None:
        logger.warning(f'{task_name} is no inexistence')
        return ''
    
    return task.json()  # 返回任务配置的 JSON 字符串
```

### 4.7 ConfigModel.save

```python
def save(self) -> None:
    # 将模型数据转为字典并写入 JSON 文件
    self.write_json(self.config_name, self.model_dump())
```

### 4.8 ConfigModel.type

```python
@staticmethod
def type(key: str) -> str:
    # 获取字段的类型注解字符串
    field_type: str = str(ConfigModel.__annotations__[key])
    
    # 处理带模块路径的类型名
    if '.' in field_type:
        classname = field_type.split('.')[-1][:-2]  # 提取类名
        return classname
    else:
        # 使用正则提取引号内的类名
        classname = re.findall(r"'([^']*)'", field_type)[0]
        return classname
```

### 4.9 ConfigModel.deep_get

```python
@staticmethod
def deep_get(obj, keys: str, default=None):
    # 将字符串键路径转为列表
    if not isinstance(keys, list):
        keys = keys.split('.')
    
    value = obj
    try:
        # 逐层获取属性
        for key in keys:
            value = getattr(value, key)
    except AttributeError:
        return default  # 属性不存在时返回默认值
    return value
```

**示例：**
```python
# 获取 model.script.error.notify_config
value = ConfigModel.deep_get(model, 'script.error.notify_config')
```

### 4.10 ConfigModel.deep_set

```python
@staticmethod
def deep_set(obj, keys: str, value) -> bool:
    if not isinstance(keys, list):
        keys = keys.split('.')
    
    current_obj = obj
    try:
        # 遍历到倒数第二层
        for key in keys[:-1]:
            current_obj = getattr(current_obj, key)
        # 设置最后一层的值
        setattr(current_obj, keys[-1], value)
        return True
    except (AttributeError, KeyError):
        return False
```

### 4.11 ConfigModel.script_task

```python
def script_task(self, task: str) -> dict:
    task = convert_to_underscore(task)
    task = getattr(self, task, None)
    
    if task is None:
        return {}
    
    def extract_groups(sch):
        """从 schema 中提取分组数据"""
        results = {}
        properties = {}
        for key, value in sch["properties"].items():
            if 'items' in value:
                # 处理数组类型
                properties[key] = re.search(r"/([^/]+)$", value['items']['$ref']).group(1)
            else:
                # 处理对象类型
                properties[key] = re.search(r"/([^/]+)$", value['$ref']).group(1)
        
        for key, value in properties.items():
            results[key] = sch["$defs"][value]
        return results

    def merge_value(groups, jsons, definitions) -> list[dict]:
        """将 schema 定义与实际值合并"""
        result = []
        for key, value in groups["properties"].items():
            # 跳过排除的字段
            if key in jsons and jsons[key] == 0xABCDEF:
                continue
            
            item = {
                "name": key,
                "title": value.get("title", inflection.underscore(key)),
                "default": value["default"],
                "value": jsons.get(key, value["default"]),
                "type": value.get("type", "enum")
            }
            
            if "description" in value:
                item["description"] = value["description"]
            
            # 处理枚举类型
            if '$ref' in value:
                enum_key = re.search(r"/([^/]+)$", value['$ref']).group(1)
                item["enumEnum"] = definitions[enum_key]["enum"]
            
            result.append(item)
        return result

    # 获取 schema 并处理
    schema = task.model_json_schema()
    groups = extract_groups(schema)
    groups_value = groups.copy()

    # 合并每个分组的值
    result: dict[str, list] = {}
    for key, value in task.model_dump(context={'hide': True}).items():
        if key not in groups:
            for group_name in groups.keys():
                if group_name in key:
                    groups_value[key] = groups[group_name]
        result[key] = merge_value(groups_value[key], value, schema["$defs"])

    return result
```

### 4.12 ConfigModel.script_set_arg

```python
def script_set_arg(self, task: str, group: str, argument: str, value) -> bool:
    # 参数名格式转换
    task = convert_to_underscore(task)
    group = convert_to_underscore(group)
    argument = convert_to_underscore(argument)

    # 值类型自动转换
    if isinstance(value, str) and len(value) == 8:
        try:
            value = datetime.strptime(value, '%H:%M:%S').time()
        except ValueError:
            pass
    
    if isinstance(value, str) and len(value) == 11:
        try:
            date_time = datetime.strptime(value, '%d %H:%M:%S')
            value = TimeDelta(days=date_time.day, hours=date_time.hour,
                            minutes=date_time.minute, seconds=date_time.second)
        except ValueError:
            pass
    
    if isinstance(value, str) and len(value) == 19:
        try:
            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            pass
    
    if isinstance(value, str) and value == 'true':
        value = True
    if isinstance(value, str) and value == 'false':
        value = False

    # 获取配置对象
    task_object = getattr(self, task, None)
    group_object = getattr(task_object, group, None)
    
    # 处理列表类型
    if group_object is None:
        matchs = re.findall(r'\d+', group)
        index = int(matchs[-1]) - 1 if matchs else None
        task_object_list = list(dict(task_object))
        for k, v in dict(task_object).items():
            if k not in group:
                continue
            group_object = v[index] if group_object is None else None
    
    argument_object = getattr(group_object, argument, None)

    if argument_object is None:
        logger.error(f'Set arg {task}.{group}.{argument}.{value} failed')
        return False

    # 特殊处理：重置所有任务时间
    if (task == "restart" and group == "task_config" and 
        argument == "reset_task_datetime_enable" and value == True):
        date_time = self.restart.task_config.reset_task_datetime
        self.reset_datetime_for_all_enabled_tasks(date_time)

    # 设置参数值
    try:
        setattr(group_object, argument, value)
        logger.info(f'Set arg {self.config_name}.{task}.{group}.{argument}.{value}')
        self.save()
        return True
    except ValidationError as e:
        logger.error(e)
        return False
```

### 4.13 ConfigModel.reset_datetime_for_all_enabled_tasks

```python
def reset_datetime_for_all_enabled_tasks(self, task_datetime: datetime):
    logger.warn(f"trying to reset datetime of all tasks to: {task_datetime}")
    
    data = self.dict()  # 获取所有配置的字典形式
    self.replace_next_run(data, task_datetime)  # 递归替换所有 next_run
    
    # 写入文件
    self.write_json(self.config_name, data)
    
    # 重新加载配置
    data = self.read_json(self.config_name)
    super().__init__(**data)
```

### 4.14 ConfigModel.replace_next_run

```python
def replace_next_run(self, d, dt: datetime):
    for k, v in d.items():
        if isinstance(v, dict):
            self.replace_next_run(v, dt=dt)  # 递归处理嵌套字典
        elif k == "next_run":
            d[k] = dt
            # 处理字符串格式的时间
            if isinstance(v, str):
                current_time = datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
                if current_time != dt:
                    d[k] = dt.strftime("%Y-%m-%d %H:%M:%S")
            # 处理 datetime 格式的时间
            elif isinstance(v, datetime) and v != dt:
                d[k] = dt.strftime("%Y-%m-%d %H:%M:%S")
```

## 5. 核心算法流程图

### 5.1 配置加载流程

```
┌─────────────────────────────────────────────────────────────┐
│                 ConfigModel.__init__()                       │
├─────────────────────────────────────────────────────────────┤
│  1. 检查 config_name 是否为空                                │
│     ├─ 为空 ──→ 使用默认值初始化                              │
│     └─ 不为空 ──→ 继续                                      │
│                                                              │
│  2. 调用 read_json() 读取配置文件                            │
│     └─ 返回字典格式的配置数据                                 │
│                                                              │
│  3. 将 config_name 添加到数据中                              │
│                                                              │
│  4. 调用 super().__init__(**data) 初始化所有字段              │
│     └─ Pydantic 自动验证数据类型                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 参数设置流程

```
┌─────────────────────────────────────────────────────────────┐
│               script_set_arg() 流程                          │
├─────────────────────────────────────────────────────────────┤
│  1. 参数名格式转换（大驼峰 → 下划线）                         │
│                                                              │
│  2. 值类型自动转换                                            │
│     ├─ "HH:MM:SS" → time 对象                               │
│     ├─ "DD HH:MM:SS" → TimeDelta 对象                       │
│     ├─ "YYYY-MM-DD HH:MM:SS" → datetime 对象                │
│     └─ "true"/"false" → bool 值                              │
│                                                              │
│  3. 获取配置对象层级                                          │
│     task_object → group_object → argument_object             │
│                                                              │
│  4. 特殊处理（如重置所有任务时间）                            │
│                                                              │
│  5. 设置参数值并保存                                          │
└─────────────────────────────────────────────────────────────┘
```

## 6. 使用示例

```python
# 创建配置模型
model = ConfigModel(config_name='oas1')

# 读取配置
model = ConfigModel.read_json('oas1')

# 获取 GUI 参数
gui_args = model.gui_args('Orochi')

# 获取任务配置
task_config = model.gui_task('Orochi')

# 设置参数
model.script_set_arg(
    task='Orochi',
    group='Scheduler',
    argument='Enable',
    value=True
)

# 深获取配置值
value = ConfigModel.deep_get(model, 'script.error.notify_config')

# 深设置配置值
ConfigModel.deep_set(model, 'script.error.notify_enable', True)

# 获取字段类型
task_type = ConfigModel.type('orochi')  # 返回 'Orochi'

# 保存配置
model.save()

# 重置所有任务时间
from datetime import datetime
model.reset_datetime_for_all_enabled_tasks(
    datetime(2024, 1, 1, 0, 0, 0)
)
```

## 7. 设计模式总结

### 7.1 数据模型模式（Data Model）
使用 Pydantic `BaseModel` 定义强类型的数据结构，自动进行数据验证和序列化。

### 7.2 工厂模式（Factory）
`Field(default_factory=...)` 确保每个配置实例获得独立的默认值对象。

### 7.3 访问者模式（Visitor）
`gui_args` 和 `script_task` 方法遍历模型结构，提取特定格式的数据用于 GUI 显示。

### 7.4 递归模式
`deep_get`、`deep_set`、`replace_next_run` 使用递归处理嵌套的数据结构。

### 7.5 自动保存模式
通过重写 `__setattr__` 方法，实现属性修改时自动保存到文件。

### 7.6 类型转换策略
`script_set_arg` 方法根据值的长度和格式自动推断并转换类型，提供了灵活的参数设置接口。
