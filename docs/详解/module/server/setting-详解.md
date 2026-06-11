# module/server/setting.py 详解

## 1. 文件概述

`setting.py` 是全局状态管理模块，负责：
- 提供共享设置和状态管理
- 实现缓存类属性装饰器
- 管理部署配置和配置更新器
- 支持多进程同步管理器

## 2. 导入部分解释

```python
import multiprocessing                      # 多进程支持
import threading                            # 线程支持
from multiprocessing.managers import SyncManager  # 同步管理器
from typing import TYPE_CHECKING, Callable, Generic, TypeVar  # 类型提示

if TYPE_CHECKING:
    from module.config.config_updater import ConfigUpdater  # 配置更新器
    from module.server.config import DeployConfig  # 部署配置
```

## 3. 类定义解释

### cached_class_property 类（第16-50行）
```python
class cached_class_property(Generic[T]):
    """
    Code from https://github.com/dssg/dickens
    Add typing support

    Descriptor decorator implementing a class-level, read-only
    property, which caches its results on the class(es) on which it
    operates.
    Inheritance is supported, insofar as the descriptor is never hidden
    by its cache; rather, it stores values under its access name with
    added underscores. For example, when wrapping getters named
    "choices", "choices_" or "_choices", each class's result is stored
    on the class at "_choices_"; decoration of a getter named
    "_choices_" would raise an exception.
    """

    class AliasConflict(ValueError):
        pass

    def __init__(self, func: Callable[..., T]):
        self.__func__ = func
        self.__cache_name__ = '_{}_'.format(func.__name__.strip('_'))
        if self.__cache_name__ == func.__name__:
            raise self.AliasConflict(self.__cache_name__)

    def __get__(self, instance, cls=None) -> T:
        if cls is None:
            cls = type(instance)

        try:
            return vars(cls)[self.__cache_name__]
        except KeyError:
            result = self.__func__(cls)
            setattr(cls, self.__cache_name__, result)
            return result
```

### State 类（第53-92行）
```python
class State:
    """
    Shared settings
    """

    _init = False
    _clearup = False

    restart_event: threading.Event = None
    manager: SyncManager = None

    @classmethod
    def init(cls):
        cls.manager = multiprocessing.Manager()
        cls._init = True

    @classmethod
    def clearup(cls):
        cls.manager.shutdown()
        cls._clearup = True

    @cached_class_property
    def deploy_config(self) -> "DeployConfig":
        """
        Returns:
            DeployConfig：
        """
        from module.server.config import DeployConfig

        return DeployConfig()

    @cached_class_property
    def config_updater(self) -> "ConfigUpdater":
        """
        Returns:
            ConfigUpdater：
        """
        from module.config.config_updater import ConfigUpdater

        return ConfigUpdater()
```

## 4. 每个方法的逐行解释

### cached_class_property.__init__ 方法（第35-39行）
```python
def __init__(self, func: Callable[..., T]):
    self.__func__ = func  # 被装饰的函数
    self.__cache_name__ = '_{}_'.format(func.__name__.strip('_'))  # 缓存名称
    if self.__cache_name__ == func.__name__:  # 检查名称冲突
        raise self.AliasConflict(self.__cache_name__)
```

### cached_class_property.__get__ 方法（第41-50行）
```python
def __get__(self, instance, cls=None) -> T:
    if cls is None:
        cls = type(instance)  # 获取类

    try:
        return vars(cls)[self.__cache_name__]  # 尝试从缓存获取
    except KeyError:
        result = self.__func__(cls)  # 调用函数计算结果
        setattr(cls, self.__cache_name__, result)  # 缓存结果
        return result
```

### State.init 类方法（第64-66行）
```python
@classmethod
def init(cls):
    cls.manager = multiprocessing.Manager()  # 创建同步管理器
    cls._init = True  # 设置初始化标志
```

### State.clearup 类方法（第68-70行）
```python
@classmethod
def clearup(cls):
    cls.manager.shutdown()  # 关闭同步管理器
    cls._clearup = True  # 设置清理标志
```

### State.deploy_config 属性（第72-82行）
```python
@cached_class_property
def deploy_config(self) -> "DeployConfig":
    """
    Returns:
        DeployConfig：
    """
    from module.server.config import DeployConfig  # 延迟导入

    return DeployConfig()  # 创建部署配置实例
```

### State.config_updater 属性（第84-92行）
```python
@cached_class_property
def config_updater(self) -> "ConfigUpdater":
    """
    Returns:
        ConfigUpdater：
    """
    from module.config.config_updater import ConfigUpdater  # 延迟导入

    return ConfigUpdater()  # 创建配置更新器实例
```

## 5. 核心算法流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    缓存属性工作流程                           │
├─────────────────────────────────────────────────────────────┤
│  1. 首次访问属性                                             │
│     ├─ 检查缓存                                              │
│     ├─ 缓存未命中                                            │
│     ├─ 调用函数计算结果                                      │
│     └─ 缓存结果                                              │
│                                                             │
│  2. 再次访问属性                                             │
│     ├─ 检查缓存                                              │
│     └─ 缓存命中，直接返回                                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    状态管理流程                               │
├─────────────────────────────────────────────────────────────┤
│  初始化                                                      │
│  ├─ 创建同步管理器                                           │
│  └─ 设置初始化标志                                           │
│                                                             │
│  访问配置                                                    │
│  ├─ 使用缓存属性装饰器                                       │
│  ├─ 延迟导入模块                                             │
│  └─ 创建配置实例                                             │
│                                                             │
│  清理                                                        │
│  ├─ 关闭同步管理器                                           │
│  └─ 设置清理标志                                             │
└─────────────────────────────────────────────────────────────┘
```

## 6. 使用示例

### 访问部署配置
```python
from module.server.setting import State

# 访问部署配置（自动缓存）
config = State.deploy_config
print(config.Branch)  # 获取分支名

# 访问配置更新器
updater = State.config_updater
```

### 初始化和清理
```python
from module.server.setting import State

# 初始化
State.init()

# 使用状态...

# 清理
State.clearup()
```

### 使用缓存属性装饰器
```python
from module.server.setting import cached_class_property

class MyClass:
    @cached_class_property
    def expensive_property(self):
        # 耗时计算
        return sum(range(1000000))

# 首次访问会计算
obj = MyClass()
print(obj.expensive_property)  # 计算并缓存

# 再次访问直接返回缓存
print(obj.expensive_property)  # 直接返回
```

## 7. 设计模式总结

1. **单例模式**: 使用缓存属性确保只创建一次实例
2. **延迟加载模式**: 使用延迟导入避免循环依赖
3. **描述符模式**: 使用描述符实现缓存属性
4. **状态管理模式**: 使用类变量管理全局状态
5. **资源管理模式**: 提供初始化和清理方法管理资源生命周期