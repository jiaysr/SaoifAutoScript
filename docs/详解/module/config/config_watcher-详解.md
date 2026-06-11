# config_watcher.py 代码详解

## 1. 文件概述

`config_watcher.py` 定义了 `ConfigWatcher` 类，用于监视配置文件的修改状态。通过跟踪文件的修改时间，判断配置文件是否被外部修改，从而决定是否需要重新加载配置。

**主要职责：**
- 记录配置文件的初始修改时间
- 检测配置文件是否被修改
- 提供文件修改时间查询接口

## 2. 导入部分解释

```python
import os                        # 操作系统接口，用于获取文件状态
from datetime import datetime    # 日期时间处理

from module.config.utils import filepath_config, DEFAULT_TIME  # 配置文件路径工具
from module.logger import logger  # 日志记录器
```

**导入说明：**
- `os`: 用于 `os.stat()` 获取文件的修改时间戳
- `datetime`: 将时间戳转换为可读的日期时间格式
- `filepath_config`: 获取配置文件的完整路径
- `DEFAULT_TIME`: 默认时间常量，用于初始化

## 3. 类定义解释

### 3.1 ConfigWatcher 类

```python
class ConfigWatcher:
    """
    监视特定配置文件修改的功能。
    它跟踪了初始修改时间,(start_mtime)
    并提供了方法来检查文件是否被修改(should_reload)
    和获取当前修改时间(get_mtime)。
    """
    config_name = 'script'              # 默认配置名
    start_mtime = DEFAULT_TIME          # 初始修改时间
```

**类属性说明：**
- `config_name`: 要监视的配置文件名
- `start_mtime`: 开始监视时的文件修改时间

## 4. 每个方法的逐行解释

### 4.1 start_watching

```python
def start_watching(self) -> None:
    # 记录当前文件的修改时间作为基准
    self.start_mtime = self.get_mtime()
```

**功能：** 开始监视配置文件，记录当前修改时间作为比较基准。

### 4.2 get_mtime

```python
def get_mtime(self) -> datetime:
    """
    Last modify time of the file
    """
    # 获取文件的状态信息
    timestamp = os.stat(filepath_config(self.config_name)).st_mtime
    
    # 将时间戳转换为 datetime 对象，去除微秒
    mtime = datetime.fromtimestamp(timestamp).replace(microsecond=0)
    
    return mtime
```

**功能：** 获取配置文件的最后修改时间。

**参数说明：**
- `filepath_config(self.config_name)`: 返回 `./config/{config_name}.json`
- `os.stat()`: 获取文件的状态信息
- `.st_mtime`: 文件的最后修改时间戳（Unix 时间戳）
- `datetime.fromtimestamp()`: 将时间戳转为 datetime 对象
- `.replace(microsecond=0)`: 去除微秒部分，简化比较

### 4.3 should_reload

```python
def should_reload(self) -> bool:
    """
    Returns:
        bool: Whether the file has been modified and configs should reload
    """
    # 获取当前文件修改时间
    mtime = self.get_mtime()
    
    # 与开始监视时的时间比较
    if mtime > self.start_mtime:
        logger.info(f'Config "{self.config_name}" changed at {mtime}')
        return True  # 文件已修改，需要重新加载
    else:
        return False  # 文件未修改
```

**功能：** 检查配置文件是否被修改，决定是否需要重新加载。

## 5. 核心算法流程图

### 5.1 文件监视流程

```
┌─────────────────────────────────────────────────────────────┐
│                   ConfigWatcher 工作流程                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 初始化阶段                                               │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────────┐                                        │
│  │ start_watching() │                                        │
│  │ 记录 start_mtime │                                        │
│  └─────────────────┘                                        │
│     │                                                        │
│     ▼                                                        │
│  2. 轮询阶段（循环执行）                                      │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────────┐     ┌─────────────┐                    │
│  │ should_reload()  │────→│ 比较时间戳   │                    │
│  └─────────────────┘     └─────────────┘                    │
│     │                           │                            │
│     │                           ▼                            │
│     │                    ┌─────────────────┐                │
│     │                    │ mtime > start?  │                │
│     │                    └─────────────────┘                │
│     │                           │                            │
│     │              ┌────────────┴────────────┐              │
│     │              ▼                         ▼              │
│     │         ┌────────┐               ┌────────┐          │
│     │         │  True  │               │ False  │          │
│     │         │ 需要重载│               │ 不需要  │          │
│     │         └────────┘               └────────┘          │
│     │              │                                         │
│     ▼              ▼                                         │
│  3. 重载配置                                                  │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────────┐                                        │
│  │ 重新加载配置文件  │                                        │
│  │ 更新 start_mtime │                                        │
│  └─────────────────┘                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 时间比较逻辑

```
时间轴：
─────────────────────────────────────────────────────→

start_mtime          file_modified         current_time
    │                      │                     │
    ▼                      ▼                     ▼
────┬──────────────────────┬─────────────────────┬────
    │                      │                     │
    │                      │                     │
    │←──── 这段时间内 ────→│                     │
    │    文件未被修改       │                     │
    │                      │←── 文件被修改 ─────→│
    │                      │                     │
    │                      │    mtime > start_mtime
    │                      │    should_reload() = True
```

## 6. 使用示例

```python
from module.config.config_watcher import ConfigWatcher

# 创建监视器实例
watcher = ConfigWatcher()
watcher.config_name = 'oas1'  # 设置要监视的配置文件

# 开始监视
watcher.start_watching()
print(f"开始监视配置文件: {watcher.config_name}")
print(f"初始修改时间: {watcher.start_mtime}")

# 在主循环中检查配置是否更新
import time

while True:
    # 检查配置是否被修改
    if watcher.should_reload():
        print("配置文件已修改，重新加载...")
        # 重新加载配置
        config.reload()
        # 更新监视器的基准时间
        watcher.start_watching()
    
    # 其他业务逻辑...
    time.sleep(1)  # 每秒检查一次

# 获取当前文件修改时间
current_mtime = watcher.get_mtime()
print(f"当前修改时间: {current_mtime}")

# 在 Config 类中的使用方式
class Config(ConfigWatcher):
    def __init__(self, config_name):
        super().__init__()
        self.config_name = config_name
        self.start_watching()  # 初始化时开始监视
    
    def check_and_reload(self):
        if self.should_reload():
            self.reload()
            self.start_watching()  # 更新基准时间
```

## 7. 设计模式总结

### 7.1 观察者模式（Observer）
`ConfigWatcher` 充当观察者角色，监视配置文件的变化并做出响应。

### 7.2 轮询模式（Polling）
通过定期调用 `should_reload()` 检查文件状态，实现变化检测。

### 7.3 状态快照模式
使用 `start_mtime` 保存初始状态快照，用于后续比较。

### 7.4 Mixin 模式
作为 Mixin 类，可以与其他配置类组合使用。

**设计优点：**
- 简单高效：只依赖文件系统的时间戳
- 低开销：`os.stat()` 是轻量级操作
- 可靠：文件系统保证时间戳的准确性
- 解耦：监视逻辑与业务逻辑分离

**使用场景：**
- 外部工具修改配置文件后，脚本自动感知并重载
- 多进程环境下配置同步
- 用户手动编辑配置文件后无需重启脚本

**注意事项：**
- 时间比较精度为秒级（去除了微秒）
- 文件必须存在，否则 `os.stat()` 会抛出异常
- 仅检测修改时间，不检测文件内容变化
