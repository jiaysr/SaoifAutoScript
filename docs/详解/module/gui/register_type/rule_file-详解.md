# register_type/rule_file.py 代码详解

## 1. 文件概述

`register_type/rule_file.py` 是规则文件管理模块，提供 JSON 配置文件的安全读写功能。该模块使用文件锁确保并发安全，使用原子写入防止数据损坏。

**核心职责：**
- 安全读取 JSON 配置文件
- 原子写入 JSON 配置文件
- 使用文件锁防止并发冲突
- 自动创建不存在的目录

---

## 2. 导入部分解释

```python
import os                                         # 操作系统接口，用于路径和目录操作
import json                                       # JSON 序列化（当前未直接使用）

from filelock import FileLock                      # 文件锁库，用于并发控制
from PySide6.QtCore import QObject, Slot          # Qt 核心类

from module.logger import logger                   # 日志记录器
from module.config.atomicwrites import atomic_write  # 原子写入工具
```

---

## 3. 类定义解释

```python
class RuleFile(QObject):
    """
    规则文件管理类
    继承 QObject 以支持 QML 调用
    提供安全的文件读写功能
    """
    def __init__(self):
        super().__init__()  # 初始化 QObject 基类
```

---

## 4. 每个方法的逐行解释

### 4.1 `read_file(self, file)` 方法

```python
@Slot(str, result="QString")  # 声明为槽函数，返回 QString 类型给 QML
def read_file(self, file: str) -> str:
    """
    读取 json 文件
    :param file: 文件完整路径
    :return: 文件内容字符串，如果文件不存在返回空字符串
    """
    # 获取文件所在目录
    folder = os.path.dirname(file)

    # 如果目录不存在，创建目录
    if not os.path.exists(folder):
        os.mkdir(folder)

    # 如果文件不存在，返回空字符串
    if not os.path.exists(file):
        return ""

    # 获取文件扩展名
    _, ext = os.path.splitext(file)

    # 创建文件锁（锁文件名为 {file}.lock）
    lock = FileLock(f"{file}.lock")

    # 使用锁保护读取操作
    with lock:
        logger.info(f'read: {file}')

        # 只支持 .json 文件
        if ext == '.json':
            with open(file, mode='r', encoding='utf-8') as f:
                return f.read()
        else:
            logger.error(f"not support {ext} file")
            return ""
```

### 4.2 `write_file(self, file, data)` 方法

```python
@Slot(str, str)  # 声明为槽函数，接收两个字符串参数
def write_file(self, file: str, data: str) -> None:
    """
    写入 json 文件
    :param file: 文件完整路径
    :param data: 要写入的 JSON 字符串
    """
    # 获取文件所在目录
    folder = os.path.dirname(file)

    # 如果目录不存在，创建目录
    if not os.path.exists(folder):
        os.mkdir(folder)

    # 获取文件扩展名
    _, ext = os.path.splitext(file)

    # 创建文件锁
    lock = FileLock(f"{file}.lock")

    # 使用锁保护写入操作
    with lock:
        logger.info(f'write: {file}')

        # 只支持 .json 文件
        if ext == '.json':
            # 使用原子写入，防止写入过程中断导致数据损坏
            # overwrite=True 表示覆盖已有文件
            with atomic_write(file, overwrite=True, encoding='utf-8') as f:
                f.write(data)
        else:
            logger.error(f"not support {ext} file")
```

---

## 5. 核心算法流程图

### 5.1 文件读取流程

```
read_file(file)
    │
    ▼
┌─────────────────────────────────────┐
│  获取目录路径                        │
│  folder = os.path.dirname(file)     │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  目录是否存在？                      │
│  ├─ 否 → os.mkdir(folder) 创建目录  │
│  └─ 是 ↓                           │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  文件是否存在？                      │
│  ├─ 否 → 返回 ""                    │
│  └─ 是 ↓                           │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  获取扩展名 ext                      │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  创建文件锁 FileLock({file}.lock)   │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  获取锁                              │
│  with lock:                          │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  扩展名是否为 .json？               │
│  ├─ 是 → 读取文件内容并返回         │
│  └─ 否 → 记录错误，返回 ""          │
└─────────────────────────────────────┘
```

### 5.2 文件写入流程

```
write_file(file, data)
    │
    ▼
┌─────────────────────────────────────┐
│  获取目录路径                        │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  目录是否存在？                      │
│  ├─ 否 → os.mkdir(folder) 创建目录  │
│  └─ 是 ↓                           │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  获取扩展名 ext                      │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  创建文件锁 FileLock({file}.lock)   │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  获取锁                              │
│  with lock:                          │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  扩展名是否为 .json？               │
│  ├─ 是 → 原子写入文件               │
│  │        atomic_write(file, overwrite=True)│
│  └─ 否 → 记录错误                   │
└─────────────────────────────────────┘
```

### 5.3 文件锁机制

```
进程 A                          进程 B
    │                               │
    ▼                               ▼
┌───────────────┐            ┌───────────────┐
│ 获取锁         │            │ 尝试获取锁     │
│ FileLock.lock()│            │ FileLock.lock()│
└───────────────┘            └───────────────┘
    │                               │
    ▼                               ▼
┌───────────────┐            ┌───────────────┐
│ 读写文件       │            │ 阻塞等待...    │
│ (独占访问)     │            │               │
└───────────────┘            └───────────────┘
    │                               │
    ▼                               │
┌───────────────┐                   │
│ 释放锁         │                   │
│ FileLock.unlock()│                 │
└───────────────┘                   │
    │                               │
    ▼                               ▼
                              ┌───────────────┐
                              │ 获取锁成功     │
                              │ 读写文件       │
                              └───────────────┘
```

### 5.4 原子写入机制

```
原子写入 (atomic_write)
    │
    ▼
┌─────────────────────────────────────┐
│  创建临时文件 {file}.tmp            │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  写入数据到临时文件                  │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  写入完成？                          │
│  ├─ 是 → 重命名临时文件为目标文件   │
│  │        os.rename(tmp, file)       │
│  └─ 否 → 删除临时文件               │
└─────────────────────────────────────┘

优点：
- 如果写入过程中断，原文件保持不变
- 只有写入成功才会替换原文件
- 避免数据损坏
```

---

## 6. 使用示例

### 6.1 在 Python 中使用

```python
from module.gui.register_type.rule_file import RuleFile

rule_file = RuleFile()

# 读取文件
content = rule_file.read_file("C:/config/rules.json")
print(content)

# 写入文件
data = '{"name": "test", "value": 123}'
rule_file.write_file("C:/config/rules.json", data)
```

### 6.2 在 QML 中使用

```qml
import QtQuick 2.15

Button {
    onClicked: {
        // 读取规则文件
        var content = ruleFile.read_file("C:/config/rules.json")
        console.log(content)

        // 写入规则文件
        ruleFile.write_file("C:/config/rules.json", '{"key": "value"}')
    }
}
```

---

## 7. 设计模式总结

| 设计模式 | 应用位置 | 说明 |
|---------|---------|------|
| **锁模式** | FileLock | 使用文件锁确保并发安全 |
| **原子操作模式** | atomic_write | 原子写入防止数据损坏 |
| **防御性编程** | 目录创建 | 自动创建不存在的目录 |

**安全特性：**
- **文件锁**：防止多个进程同时读写同一文件
- **原子写入**：写入过程中断不会损坏原文件
- **目录自动创建**：确保目标目录存在
- **扩展名检查**：只处理支持的文件类型

**文件锁文件：**
- 锁文件命名：`{原文件名}.lock`
- 例如：`rules.json` 的锁文件为 `rules.json.lock`
- 锁文件是空文件，仅用于协调并发访问
