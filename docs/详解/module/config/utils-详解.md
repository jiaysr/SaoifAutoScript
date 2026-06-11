# utils.py 代码详解

## 1. 文件概述

`utils.py` 是配置系统的工具函数库，提供了文件读写、路径处理、时间计算、字典操作等通用功能。这些工具函数被配置系统的其他模块广泛使用。

**主要职责：**
- 提供配置文件的读写功能
- 处理文件路径和目录
- 实现时间相关的计算函数
- 提供字典的深拷贝操作
- 命名风格转换

## 2. 导入部分解释

```python
import os                                    # 操作系统接口
import json                                  # JSON 处理
import yaml                                  # YAML 处理

from filelock import FileLock                # 文件锁
from datetime import datetime, timedelta, timezone, time  # 日期时间

from module.config.atomicwrites import atomic_write  # 原子写入
from module.logger import logger             # 日志记录器
```

**导入说明：**
- `os`: 文件路径和目录操作
- `json`: JSON 序列化和反序列化
- `yaml`: YAML 序列化和反序列化
- `FileLock`: 文件锁，防止并发写入冲突
- `datetime`: 日期时间处理
- `atomic_write`: 原子写入，确保写入完整性

## 3. 类定义解释

```python
# 本文件没有定义类
# 使用模块级常量和函数实现功能
```

## 4. 每个方法的逐行解释

### 4.1 常量定义

```python
DEFAULT_TIME = datetime(2023, 1, 1, 0, 0)  # 默认时间
```

### 4.2 filepath_config 函数

```python
def filepath_config(filename, mod_name='script') -> str:
    """
    返回配置文件的路径
    """
    if mod_name == 'script':
        return os.path.join('./config', f'{filename}.json')
    else:
        return os.path.join('./config', f'{filename}.{mod_name}.json')
```

**功能：** 生成配置文件的路径。

**参数说明：**
- `filename`: 文件名（不带扩展名）
- `mod_name`: 模块名，默认为 'script'

**返回值示例：**
- `filepath_config('oas1')` → `./config/oas1.json`
- `filepath_config('oas1', 'alas')` → `./config/oas1.alas.json`

### 4.3 filepath_args 函数

```python
def filepath_args(filename='args', mod_name='alas'):
    return f'./module/config/argument/{filename}.json'
```

**功能：** 返回参数定义文件的路径。

**返回值示例：**
- `filepath_args()` → `./module/config/argument/args.json`

### 4.4 filepath_argument 函数

```python
def filepath_argument(filename):
    return f'./module/config/argument/{filename}.yaml'
```

**功能：** 返回 YAML 格式参数文件的路径。

### 4.5 read_file 函数

```python
def read_file(file: str):
    """
    Read a file, support both .yaml and .json format.
    Return empty dict if file not exists.

    Args:
        file (str):

    Returns:
        dict, list:
    """
    # 确保目录存在
    folder = os.path.dirname(file)
    if not os.path.exists(folder):
        os.mkdir(folder)

    # 文件不存在返回空字典
    if not os.path.exists(file):
        return {}

    # 获取文件扩展名
    _, ext = os.path.splitext(file)
    
    # 使用文件锁防止并发读取
    lock = FileLock(f"{file}.lock")
    with lock:
        logger.debug(f'read: {file}')
        
        # YAML 格式
        if ext == '.yaml':
            with open(file, mode='r', encoding='utf-8') as f:
                s = f.read()
                data = list(yaml.safe_load_all(s))
                if len(data) == 1:
                    data = data[0]
                if not data:
                    data = {}
                return data
        
        # JSON 格式
        elif ext == '.json':
            with open(file, mode='r', encoding='utf-8') as f:
                s = f.read()
                return json.loads(s)
        
        # 不支持的格式
        else:
            logger.warning(f'Unsupported config file extension: {ext}')
            return {}
```

**功能：** 读取配置文件，支持 YAML 和 JSON 格式。

**处理流程：**
1. 确保目录存在
2. 检查文件是否存在
3. 获取文件扩展名
4. 使用文件锁
5. 根据扩展名选择解析器
6. 返回解析后的数据

### 4.6 write_file 函数

```python
def write_file(file: str, data):
    """
    Write data into a file, supports both .yaml and .json format.

    Args:
        file (str):
        data (dict, list):
    """
    # 确保目录存在
    folder = os.path.dirname(file)
    if not os.path.exists(folder):
        os.mkdir(folder)

    # 获取文件扩展名
    _, ext = os.path.splitext(file)
    
    # 使用文件锁防止并发写入
    lock = FileLock(f"{file}.lock")
    with lock:
        logger.debug(f'write: {file}')
        
        # YAML 格式
        if ext == '.yaml':
            with atomic_write(file, overwrite=True, encoding='utf-8', newline='') as f:
                if isinstance(data, list):
                    yaml.safe_dump_all(data, f, default_flow_style=False, 
                                       encoding='utf-8', allow_unicode=True, sort_keys=False)
                else:
                    yaml.safe_dump(data, f, default_flow_style=False, 
                                   encoding='utf-8', allow_unicode=True, sort_keys=False)
        
        # JSON 格式
        elif ext == '.json':
            with atomic_write(file, overwrite=True, encoding='utf-8', newline='') as f:
                s = json.dumps(data, indent=2, ensure_ascii=False, 
                              sort_keys=False, default=str)
                f.write(s)
        
        # 不支持的格式
        else:
            logger.warning(f'Unsupported config file extension: {ext}')
```

**功能：** 写入配置文件，支持 YAML 和 JSON 格式。

**特性：**
- 使用原子写入确保写入完整性
- 使用文件锁防止并发冲突
- JSON 格式化输出便于阅读
- YAML 支持中文字符

### 4.7 deep_iter 函数

```python
def deep_iter(data, depth=0, current_depth=1):
    """
    Iter a dictionary safely.

    Args:
        data (dict):
        depth (int): Maximum depth to iter
        current_depth (int):

    Returns:
        list: Key path
        Any:
    """
    if isinstance(data, dict) \
            and (depth and current_depth <= depth):
        for key, value in data.items():
            for child_path, child_value in deep_iter(value, depth=depth, 
                                                      current_depth=current_depth + 1):
                yield [key] + child_path, child_value
    else:
        yield [], data
```

**功能：** 安全地迭代嵌套字典。

**参数说明：**
- `data`: 要迭代的字典
- `depth`: 最大迭代深度（0 表示无限制）
- `current_depth`: 当前深度

**返回值：** 生成器，产出 (键路径, 值) 元组

**示例：**
```python
data = {'a': {'b': {'c': 1}}}
for path, value in deep_iter(data, depth=2):
    print(f"{'.'.join(path)}: {value}")
# 输出:
# a.b: {'c': 1}
```

### 4.8 server_timezone 函数

```python
def server_timezone() -> timedelta:
    return timedelta(hours=8)
```

**功能：** 返回服务器时区偏移（东八区）。

### 4.9 server_time_offset 函数

```python
def server_time_offset() -> timedelta:
    """
    To convert local time to server time:
        server_time = local_time + server_time_offset()
    To convert server time to local time:
        local_time = server_time - server_time_offset()
    """
    return datetime.now(timezone.utc).astimezone().utcoffset() - server_timezone()
```

**功能：** 计算本地时间与服务器时间的偏移量。

**转换公式：**
- 本地 → 服务器：`server_time = local_time + offset`
- 服务器 → 本地：`local_time = server_time - offset`

### 4.10 get_server_next_update 函数

```python
def get_server_next_update(daily_trigger):
    """
    Args:
        daily_trigger (list[str], str): [ "00:00", "12:00", "18:00",]

    Returns:
        datetime.datetime
    """
    # 解析触发时间
    if isinstance(daily_trigger, str):
        daily_trigger = daily_trigger.replace(' ', '').split(',')

    # 计算时区偏移
    diff = server_time_offset()
    local_now = datetime.now()
    trigger = []
    
    # 计算每个触发时间
    for t in daily_trigger:
        h, m = [int(x) for x in t.split(':')]
        future = local_now.replace(hour=h, minute=m, second=0, microsecond=0) + diff
        s = (future - local_now).total_seconds() % 86400
        future = local_now + timedelta(seconds=s)
        trigger.append(future)
    
    # 返回最近的触发时间
    update = sorted(trigger)[0]
    return update
```

**功能：** 获取服务器下次更新时间。

**参数说明：**
- `daily_trigger`: 每日触发时间列表，如 `["00:00", "12:00", "18:00"]`

**返回值：** 下次更新的 datetime

### 4.11 convert_to_underscore 函数

```python
def convert_to_underscore(text: str) -> str:
    """
    大驼峰形式的字符串转换为下划线形式的字符串，
    并在数字前插入下划线。如果字符串中已经包含下划线，
    则会直接返回原始字符串。
    """
    # 已经是下划线格式，直接返回
    if '_' in text:
        return text
    
    # 去除空格
    text = text.replace(' ', '')

    result = ''
    for i, char in enumerate(text):
        if char.isupper():
            # 在大写字母前插入下划线（除了首字母）
            if i > 0 and (text[i-1].islower() or 
                         (i < len(text) - 1 and text[i+1].islower())):
                result += '_'
            result += char.lower()
        elif char.isdigit():
            # 在数字前插入下划线（除了首字符）
            if i > 0 and (text[i-1].isalpha() or 
                         (i < len(text) - 1 and text[i+1].isalpha())):
                result += '_'
            result += char
        else:
            result += char

    return result
```

**功能：** 将大驼峰命名转换为下划线命名。

**转换规则：**
1. 已有下划线则直接返回
2. 大写字母前插入下划线
3. 数字前插入下划线
4. 所有字母转为小写

**示例：**
```python
convert_to_underscore('Orochi')      # → 'orochi'
convert_to_underscore('AreaBoss')    # → 'area_boss'
convert_to_underscore('GoldYoukai')  # → 'gold_youkai'
convert_to_underscore('SixRealms')   # → 'six_realms'
convert_to_underscore('orochi')      # → 'orochi'（已有下划线）
```

### 4.12 get_server_last_update 函数

```python
def get_server_last_update(daily_trigger):
    """
    Args:
        daily_trigger (list[str], str): [ "00:00", "12:00", "18:00",]

    Returns:
        datetime.datetime
    """
    # 解析触发时间
    if isinstance(daily_trigger, str):
        daily_trigger = daily_trigger.replace(' ', '').split(',')

    # 计算时区偏移
    diff = server_time_offset()
    local_now = datetime.now()
    trigger = []
    
    # 计算每个触发时间（减去一天）
    for t in daily_trigger:
        h, m = [int(x) for x in t.split(':')]
        future = local_now.replace(hour=h, minute=m, second=0, microsecond=0) + diff
        s = (future - local_now).total_seconds() % 86400 - 86400
        future = local_now + timedelta(seconds=s)
        trigger.append(future)
    
    # 返回最晚的触发时间
    update = sorted(trigger)[-1]
    return update
```

**功能：** 获取服务器上次更新时间。

### 4.13 nearest_future 函数

```python
def nearest_future(future, interval=120):
    """
    Get the neatest future time.
    Return the last one if two things will finish within `interval`.

    Args:
        future (list[datetime.datetime]):
        interval (int): Seconds

    Returns:
        datetime.datetime:
    """
    # 转换字符串为 datetime
    future = [datetime.fromisoformat(f) if isinstance(f, str) else f for f in future]
    future = sorted(future)
    
    # 找到最近的未来时间
    next_run = future[0]
    for finish in future:
        if finish - next_run < timedelta(seconds=interval):
            next_run = finish

    return next_run
```

**功能：** 获取最近的未来时间。

**参数说明：**
- `future`: 时间列表
- `interval`: 时间间隔阈值（秒）

**返回值：** 最近的 datetime

### 4.14 dict_to_kv 函数

```python
def dict_to_kv(dictionary, allow_none=True):
    """
    Args:
        dictionary: Such as `{'path': 'Scheduler.ServerUpdate', 'value': True}`
        allow_none (bool):

    Returns:
        str: Such as `path='Scheduler.ServerUpdate', value=True`
    """
    return ', '.join([f'{k}={repr(v)}' for k, v in dictionary.items() 
                      if allow_none or v is not None])
```

**功能：** 将字典转换为键值对字符串。

**示例：**
```python
dict_to_kv({'a': 1, 'b': 'hello'})
# → "a=1, b='hello'"
```

### 4.15 parse_tomorrow_server 函数

```python
def parse_tomorrow_server(server_update: time, delay_date: int = 1, 
                           float_seconds: int = 0) -> datetime:
    """
    获取明天的日期，给这个日期加上server_update的时间，返回datetime
    """
    # 解析时间
    if isinstance(server_update, str):
        server_update = time.fromisoformat(server_update)
    
    # 计算目标日期
    now = datetime.now()
    tomorrow = now + timedelta(days=delay_date)
    next_run = datetime.combine(tomorrow, server_update)
    
    # 应用浮动时间
    if float_seconds != 0:
        next_run += timedelta(seconds=float_seconds)

        # 确保时间在目标日期内
        start_of_tomorrow = datetime.combine(tomorrow, time.min)
        end_of_tomorrow = datetime.combine(tomorrow, time(hour=23, minute=50))
    
        if next_run < start_of_tomorrow:
            next_run = start_of_tomorrow
        elif next_run > end_of_tomorrow:
            next_run = end_of_tomorrow
    
    return next_run
```

**功能：** 计算服务器下次更新时间。

**参数说明：**
- `server_update`: 服务器更新时间
- `delay_date`: 延迟天数（默认 1 天）
- `float_seconds`: 浮动秒数

**返回值：** 计算后的 datetime

### 4.16 deep_get 函数

```python
def deep_get(d, keys, default=None):
    """
    Get values in dictionary safely.
    """
    if isinstance(keys, str):
        keys = keys.split('.')
    assert type(keys) is list
    if d is None:
        return default
    if not keys:
        return d
    return deep_get(d.get(keys[0]), keys[1:], default)
```

**功能：** 安全地获取嵌套字典的值。

**示例：**
```python
data = {'a': {'b': {'c': 1}}}
deep_get(data, 'a.b.c')  # → 1
deep_get(data, 'a.b.d', default=0)  # → 0
```

### 4.17 deep_set 函数

```python
def deep_set(d, keys, value):
    """
    Set value into dictionary safely, imitating deep_get().
    """
    if isinstance(keys, str):
        keys = keys.split('.')
    assert type(keys) is list
    if not keys:
        return value
    if not isinstance(d, dict):
        d = {}
    d[keys[0]] = deep_set(d.get(keys[0], {}), keys[1:], value)
    return d
```

**功能：** 安全地设置嵌套字典的值。

### 4.18 deep_pop 函数

```python
def deep_pop(d, keys, default=None):
    """
    Pop value from dictionary safely, imitating deep_get().
    """
    if isinstance(keys, str):
        keys = keys.split('.')
    assert type(keys) is list
    if not isinstance(d, dict):
        return default
    if not keys:
        return default
    elif len(keys) == 1:
        return d.pop(keys[0], default)
    return deep_pop(d.get(keys[0]), keys[1:], default)
```

**功能：** 安全地弹出嵌套字典的值。

## 5. 核心算法流程图

### 5.1 文件读写流程

```
┌─────────────────────────────────────────────────────────────┐
│                   文件读写流程                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  read_file(file)                                             │
│     │                                                        │
│     ├─ 1. 确保目录存在                                       │
│     ├─ 2. 检查文件是否存在                                    │
│     ├─ 3. 获取文件锁                                         │
│     ├─ 4. 根据扩展名选择解析器                                │
│     │     ├─ .yaml → yaml.safe_load_all                     │
│     │     └─ .json → json.loads                             │
│     └─ 5. 返回解析结果                                       │
│                                                              │
│  write_file(file, data)                                      │
│     │                                                        │
│     ├─ 1. 确保目录存在                                       │
│     ├─ 2. 获取文件锁                                         │
│     ├─ 3. 使用原子写入                                       │
│     ├─ 4. 根据扩展名选择序列化器                              │
│     │     ├─ .yaml → yaml.safe_dump                         │
│     │     └─ .json → json.dumps                             │
│     └─ 5. 写入文件                                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 命名转换流程

```
┌─────────────────────────────────────────────────────────────┐
│               convert_to_underscore 流程                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  输入: "AreaBoss"                                            │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 检查是否已有下划线                                    │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                        │
│     └─ 否 ──→ 遍历每个字符                                  │
│              │                                               │
│              ├─ 大写字母                                     │
│              │   └─ 前一个字符是小写 → 插入下划线            │
│              │   └─ 转为小写                                 │
│              │                                               │
│              ├─ 数字                                         │
│              │   └─ 前一个字符是字母 → 插入下划线            │
│              │                                               │
│              └─ 其他字符 → 保持不变                          │
│                                                              │
│  输出: "area_boss"                                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 6. 使用示例

```python
from module.config.utils import *
from datetime import datetime, time

# 文件路径
config_path = filepath_config('oas1')
print(f"配置文件路径: {config_path}")

# 读取配置文件
data = read_file('./config/oas1.json')
print(f"配置数据: {data}")

# 写入配置文件
write_file('./config/oas1.json', {'key': 'value'})

# 命名转换
print(convert_to_underscore('Orochi'))      # 'orochi'
print(convert_to_underscore('AreaBoss'))    # 'area_boss'
print(convert_to_underscore('GoldYoukai'))  # 'gold_youkai'

# 深度字典操作
data = {'a': {'b': {'c': 1}}}
print(deep_get(data, 'a.b.c'))  # 1
deep_set(data, 'a.b.d', 2)
print(data)  # {'a': {'b': {'c': 1, 'd': 2}}}

# 服务器时间
print(server_timezone())  # 8:00:00
print(server_time_offset())  # 0:00:00（假设本地是东八区）

# 获取下次更新时间
next_update = get_server_next_update(["00:00", "12:00", "18:00"])
print(f"下次更新: {next_update}")

# 计算明天的服务器时间
tomorrow = parse_tomorrow_server(time(9, 0, 0))
print(f"明天9点: {tomorrow}")

# 字典转键值对
print(dict_to_kv({'a': 1, 'b': 'hello'}))
# → "a=1, b='hello'"

# 最近的未来时间
times = [
    datetime(2024, 1, 1, 12, 0),
    datetime(2024, 1, 1, 12, 1),
    datetime(2024, 1, 1, 12, 2)
]
print(nearest_future(times))  # 2024-01-01 12:00:00

# 深度迭代
data = {'a': {'b': 1, 'c': 2}, 'd': 3}
for path, value in deep_iter(data):
    print(f"{'.'.join(path)}: {value}")
```

## 7. 设计模式总结

### 7.1 工具函数模式
将通用功能封装为独立的工具函数，便于复用。

### 7.2 原子操作模式
使用 `atomic_write` 确保文件写入的原子性。

### 7.3 文件锁模式
使用 `FileLock` 防止并发读写冲突。

### 7.4 递归模式
`deep_get`、`deep_set`、`deep_pop` 使用递归处理嵌套结构。

### 7.5 生成器模式
`deep_iter` 使用生成器惰性产出结果。

**设计优点：**
- 通用性强：函数可独立使用
- 安全性高：使用文件锁和原子写入
- 易于测试：纯函数便于单元测试
- 文档完善：每个函数都有详细的文档字符串

**使用场景：**
- 配置文件读写
- 命名风格转换
- 嵌套字典操作
- 服务器时间计算
