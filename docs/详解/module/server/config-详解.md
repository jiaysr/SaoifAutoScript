# module/server/config.py 详解

## 1. 文件概述

`config.py` 是部署配置管理模块，负责：
- 提供带文件锁的 YAML 配置读写功能
- 继承并扩展 `DeployConfig` 类
- 实现配置的读取、写入和属性同步
- 支持多进程安全的配置访问

## 2. 导入部分解释

```python
from typing import Optional, Union  # 类型提示
from filelock import FileLock        # 文件锁，用于多进程安全
from deploy.config import DeployConfig as _DeployConfig  # 基础部署配置类
from deploy.utils import *           # 部署工具函数（包括 poor_yaml_read, poor_yaml_write, DEPLOY_TEMPLATE 等）
```

## 3. 类定义解释

### DeployConfig 类（第29-57行）
继承自 `_DeployConfig`，扩展了配置读写功能。

## 4. 每个方法的逐行解释

### poor_yaml_read_with_lock 函数（第11-16行）
```python
def poor_yaml_read_with_lock(file):
    if not os.path.exists(file):  # 如果文件不存在
        return {}                  # 返回空字典

    with FileLock(f"{file}.lock"):  # 获取文件锁
        return poor_yaml_read(file)  # 读取 YAML 文件
```
带文件锁的 YAML 文件读取，确保多进程安全。

### poor_yaml_write_with_lock 函数（第19-26行）
```python
def poor_yaml_write_with_lock(data, file, template_file=DEPLOY_TEMPLATE):
    folder = os.path.dirname(file)  # 获取文件所在目录
    if not os.path.exists(folder):  # 如果目录不存在
        os.mkdir(folder)            # 创建目录

    with FileLock(f"{file}.lock"):  # 获取数据文件锁
        with FileLock(f"{DEPLOY_TEMPLATE}.lock"):  # 获取模板文件锁
            return poor_yaml_write(data, file, template_file)  # 写入 YAML 文件
```
带文件锁的 YAML 文件写入，同时锁定数据文件和模板文件。

### DeployConfig 类的 read 方法（第33-42行）
```python
def read(self):
    """
    Read and update deploy config, copy `self.configs` to properties.
    """
    self.config = poor_yaml_read_with_lock(DEPLOY_TEMPLATE)  # 读取模板配置
    self.config.update(poor_yaml_read_with_lock(self.file))  # 用用户配置覆盖

    for key, value in self.config.items():  # 遍历配置项
        if hasattr(self, key):              # 如果属性存在
            super().__setattr__(key, value) # 设置属性值
```
读取并更新部署配置，将配置项复制到对象属性。

### DeployConfig 类的 write 方法（第44-48行）
```python
def write(self):
    """
    Write `self.config` into deploy config.
    """
    poor_yaml_write_with_lock(self.config, self.file)  # 写入配置到文件
```

### DeployConfig 类的 __setattr__ 方法（第50-57行）
```python
def __setattr__(self, key: str, value):
    """
    Catch __setattr__, copy to `self.config`, write deploy config.
    """
    super().__setattr__(key, value)  # 调用父类的 __setattr__
    if key[0].isupper() and key in self.config:  # 如果键以大写字母开头且在配置中存在
        self.config[key] = value  # 更新配置字典
        self.write()              # 写入文件
```
拦截属性设置操作，自动同步到配置文件。

## 5. 核心算法流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    配置读取流程                               │
├─────────────────────────────────────────────────────────────┤
│  1. 调用 read() 方法                                         │
│     ↓                                                        │
│  2. 读取模板配置文件 (DEPLOY_TEMPLATE)                       │
│     ├─ 获取模板文件锁                                        │
│     └─ 解析 YAML 内容                                        │
│     ↓                                                        │
│  3. 读取用户配置文件                                          │
│     ├─ 获取用户文件锁                                        │
│     └─ 解析 YAML 内容                                        │
│     ↓                                                        │
│  4. 合并配置（用户配置覆盖模板配置）                           │
│     ↓                                                        │
│  5. 将配置项复制到对象属性                                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    配置写入流程                               │
├─────────────────────────────────────────────────────────────┤
│  1. 设置对象属性（触发 __setattr__）                         │
│     ↓                                                        │
│  2. 检查属性名是否以大写字母开头                              │
│     ↓                                                        │
│  3. 检查属性是否在配置字典中存在                              │
│     ↓                                                        │
│  4. 更新配置字典                                              │
│     ↓                                                        │
│  5. 调用 write() 方法                                        │
│     ├─ 获取用户文件锁                                        │
│     ├─ 获取模板文件锁                                        │
│     └─ 写入 YAML 文件                                        │
└─────────────────────────────────────────────────────────────┘
```

## 6. 使用示例

### 读取配置
```python
from module.server.config import DeployConfig

config = DeployConfig()  # 创建配置对象
config.read()            # 读取配置
print(config.Branch)     # 访问配置项
```

### 修改配置
```python
config = DeployConfig()
config.Branch = "main"  # 设置配置项，自动触发写入
```

### 多进程安全读取
```python
from module.server.config import poor_yaml_read_with_lock

data = poor_yaml_read_with_lock("config/deploy.yaml")  # 带锁读取
```

## 7. 设计模式总结

1. **模板方法模式**: 继承 `_DeployConfig` 并扩展功能
2. **代理模式**: 通过 `__setattr__` 拦截属性设置，自动同步到配置文件
3. **文件锁模式**: 使用 `FileLock` 确保多进程安全
4. **配置合并模式**: 模板配置 + 用户配置的合并策略
5. **原子写入模式**: 使用文件锁确保写入操作的原子性