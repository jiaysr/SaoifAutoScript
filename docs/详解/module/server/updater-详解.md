# module/server/updater.py 详解

## 1. 文件概述

`updater.py` 是更新管理模块，负责：
- 检查 Git 仓库更新
- 执行 git pull 操作
- 获取提交历史信息
- 管理更新状态和调度

## 2. 导入部分解释

```python
import datetime                              # 日期时间处理
import subprocess                            # 子进程管理
import threading                             # 线程支持
import time                                  # 时间处理
import requests                              # HTTP 请求
from typing import Generator, List, Tuple    # 类型提示
from deploy.config import ExecutionError     # 执行错误
from deploy.git import GitManager            # Git 管理器
from deploy.pip import PipManager            # Pip 管理器
from deploy.utils import DEPLOY_CONFIG       # 部署配置路径
from module.logger import logger             # 日志模块
from module.base.retry import retry          # 重试装饰器
from module.server.config import DeployConfig  # 部署配置
```

## 3. 类定义解释

### Updater 类（第17-137行）
继承自 `DeployConfig`、`GitManager` 和 `PipManager`，更新管理器。

## 4. 每个方法的逐行解释

### Updater.__init__ 方法（第18-20行）
```python
def __init__(self, file=DEPLOY_CONFIG):
    super().__init__(file=file)  # 调用父类构造函数
    self.state = 0  # 初始状态
```

### Updater.delay 属性（第22-25行）
```python
@property
def delay(self):
    self.read()  # 读取配置
    return int(self.CheckUpdateInterval) * 60  # 返回检查间隔（秒）
```

### Updater.schedule_time 属性（第27-34行）
```python
@property
def schedule_time(self):
    self.read()  # 读取配置
    t = self.AutoRestartTime  # 获取自动重启时间
    if t is not None:
        return datetime.time.fromisoformat(t)  # 转换为时间对象
    else:
        return None
```

### Updater.execute_output 方法（第36-41行）
```python
def execute_output(self, command) -> str:
    command = command.replace(r"\\", "/").replace("\\", "/").replace('"', '"')  # 处理路径
    log = subprocess.run(
        command, capture_output=True, text=True, encoding="utf8", shell=True
    ).stdout  # 执行命令并获取输出
    return log
```

### Updater.get_commit 方法（第43-63行）
```python
def get_commit(self, revision="", n=1, short_sha1=False) -> Tuple:
    """
    Return:
        (sha1, author, isotime, message,)
    """
    ph = "h" if short_sha1 else "H"  # 选择哈希格式

    log = self.execute_output(
        f'"{self.git}" log {revision} --pretty=format:"%{ph}---%an---%ad---%s" --date=iso -{n}'
    )  # 执行 git log 命令

    if not log:
        return None, None, None, None  # 返回空结果

    logs = log.split("\n")  # 分割日志
    logs = list(map(lambda log: tuple(log.split("---")), logs))  # 解析日志

    if n == 1:
        return logs[0]  # 返回单条日志
    else:
        return logs  # 返回多条日志
```

### Updater.current_branch 方法（第65-66行）
```python
def current_branch(self) -> str:
    return self.Branch  # 返回当前分支
```

### Updater.current_commit 方法（第68-69行）
```python
def current_commit(self) -> str:
    return self.get_commit()  # 返回当前提交
```

### Updater.latest_commit 方法（第71-73行）
```python
def latest_commit(self) -> str:
    source = "origin"
    return self.get_commit(f"{source}/{self.Branch}")  # 返回最新提交
```

### Updater.check_update 方法（第75-117行）
```python
def check_update(self) -> bool:
    self.state = "checking"  # 设置状态为检查中

    source = "origin"
    for _ in range(3):  # 重试3次
        if self.execute(
                f'"{self.git}" fetch {source} {self.Branch}', allow_failure=True
        ):
            break  # 成功则跳出
    else:
        logger.warning("Git fetch failed")
        return False  # 失败返回 False

    log = self.execute_output(
        f'"{self.git}" log --not --remotes={source}/* -1 --oneline'
    )  # 检查本地提交
    if log:
        logger.info(
            f"Cannot find local commit {log.split()[0]} in upstream, skip update"
        )
        return False  # 本地有未推送的提交

    sha1, _, _, message = self.get_commit(f"..{source}/{self.Branch}")  # 获取差异提交

    if sha1:
        logger.info(f"New update available")
        logger.info(f"{sha1[:8]} - {message}")
        return True  # 有更新
    else:
        logger.info(f"No update")
        return False  # 无更新
```

### Updater.execute_pull 方法（第119-128行）
```python
def execute_pull(self) -> bool:
    source = "origin"
    for _ in range(3):  # 重试3次
        if self.execute(
                f'"{self.git}" pull {source} {self.Branch} --no-rebase', allow_failure=True
        ):
            break  # 成功则跳出
    else:
        logger.warning("Git fetch failed")
        return False  # 失败返回 False
```

### __main__ 测试代码（第132-136行）
```python
if __name__ == "__main__":
    updater = Updater()  # 创建更新器
    print(updater.latest_commit())  # 打印最新提交
```

## 5. 核心算法流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    更新检查流程                               │
├─────────────────────────────────────────────────────────────┤
│  1. 设置状态为检查中                                         │
│     ↓                                                        │
│  2. 执行 git fetch（重试3次）                                │
│     ├─ 成功                                                  │
│     └─ 失败，返回 False                                      │
│     ↓                                                        │
│  3. 检查本地提交                                             │
│     ├─ 有未推送的提交                                        │
│     └─ 返回 False                                            │
│     ↓                                                        │
│  4. 获取差异提交                                             │
│     ├─ 有差异                                                │
│     │   ├─ 记录更新信息                                      │
│     │   └─ 返回 True                                         │
│     └─ 无差异                                                │
│         └─ 返回 False                                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    执行更新流程                               │
├─────────────────────────────────────────────────────────────┤
│  1. 执行 git pull（重试3次）                                 │
│     ├─ 成功                                                  │
│     └─ 失败，返回 False                                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    提交信息获取流程                           │
├─────────────────────────────────────────────────────────────┤
│  1. 构建 git log 命令                                        │
│     ↓                                                        │
│  2. 执行命令获取输出                                         │
│     ↓                                                        │
│  3. 解析输出                                                 │
│     ├─ 分割日志行                                            │
│     └─ 解析字段                                              │
│     ↓                                                        │
│  4. 返回结果                                                 │
│     ├─ 单条日志                                              │
│     └─ 多条日志                                              │
└─────────────────────────────────────────────────────────────┘
```

## 6. 使用示例

### 创建更新器
```python
from module.server.updater import Updater

updater = Updater()
```

### 检查更新
```python
has_update = updater.check_update()
if has_update:
    print("有新更新可用")
else:
    print("已是最新版本")
```

### 获取提交信息
```python
# 获取当前提交
current = updater.current_commit()
print(f"当前提交: {current}")

# 获取最新提交
latest = updater.latest_commit()
print(f"最新提交: {latest}")

# 获取提交历史
commits = updater.get_commit(n=10)
for sha1, author, time, message in commits:
    print(f"{sha1[:8]} - {message}")
```

### 执行更新
```python
success = updater.execute_pull()
if success:
    print("更新成功")
else:
    print("更新失败")
```

### 获取分支信息
```python
branch = updater.current_branch()
print(f"当前分支: {branch}")
```

## 7. 设计模式总结

1. **多继承模式**: 继承多个管理器类，组合功能
2. **重试模式**: 使用循环实现操作重试
3. **命令执行模式**: 通过 subprocess 执行 Git 命令
4. **状态管理模式**: 使用状态变量跟踪更新过程
5. **配置驱动模式**: 通过配置文件控制更新行为
6. **日志记录模式**: 记录所有操作和结果