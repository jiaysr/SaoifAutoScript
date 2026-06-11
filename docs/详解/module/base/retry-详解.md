# retry.py 逐行代码详解

> 源文件路径：`module/base/retry.py`
> 参考来源：复制自 Alas 项目

---

## 1. 文件概述

`retry.py` 实现了函数重试机制，提供：
- **重试装饰器**：函数失败时自动重试，支持指数退避和抖动
- **重试调用函数**：直接对函数进行带重试的调用
- **内部重试引擎**：统一的重试逻辑实现

---

## 2. 导入部分解释

```python
import functools                        # functools.wraps 保留函数元数据
import random                           # 随机数，用于 jitter 抖动
import time                             # time.sleep 实现重试间隔
from functools import partial           # partial 绑定函数参数
from module.logger import logger as logging_logger  # 日志记录器
```

---

## 3. decorator 兼容层

```python
try:
    from decorator import decorator
except ImportError:
    def decorator(caller):
        def decor(f):
            @functools.wraps(f)
            def wrapper(*args, **kwargs):
                return caller(f, *args, **kwargs)
            return wrapper
        return decor
```

**第 12-29 行**：
- 尝试导入第三方 `decorator` 库（保留函数签名）
- 如果不可用，使用简易替代实现（不保留签名但功能正确）

---

## 4. `__retry_internal()` — 重试核心引擎

```python
def __retry_internal(f, exceptions=Exception, tries=-1, delay=0,
                     max_delay=None, backoff=1, jitter=0,
                     logger=logging_logger):
```

**第 32-33 行**：参数说明：
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `f` | 要执行的函数（无参数包装） | 必填 |
| `exceptions` | 需要捕获的异常类型 | `Exception` |
| `tries` | 最大尝试次数，-1 为无限 | `-1` |
| `delay` | 初始重试延迟（秒） | `0` |
| `max_delay` | 最大延迟上限 | `None` |
| `backoff` | 延迟倍增因子 | `1`（不退避） |
| `jitter` | 额外随机延迟 | `0` |
| `logger` | 日志记录器 | `logging_logger` |

```python
    _tries, _delay = tries, delay
```

**第 49 行**：保存初始值的副本（避免修改默认参数）。

```python
    while _tries:
        try:
            return f()
        except exceptions as e:
            _tries -= 1
            if not _tries:
                raise e
```

**第 50-57 行**：
- `while _tries`：-1 为真值（无限重试），正数递减到 0 停止
- 尝试执行函数，成功则返回
- 捕获指定异常，减少剩余次数
- 次数用尽时重新抛出**原始异常**（保留堆栈信息）

```python
            if logger is not None:
                logger.exception(e)
                logger.warning(f'{type(e).__name__}({e}), retrying in {_delay} seconds...')
```

**第 59-62 行**：记录异常详情和重试警告。

```python
            time.sleep(_delay)
            _delay *= backoff
```

**第 64-65 行**：等待指定延迟，然后将延迟乘以退避因子（指数退避）。

```python
            if isinstance(jitter, tuple):
                _delay += random.uniform(*jitter)
            else:
                _delay += jitter
```

**第 67-70 行**：
- 如果 `jitter` 是元组 `(min, max)`，添加随机范围内的值
- 否则添加固定值

```python
            if max_delay is not None:
                _delay = min(_delay, max_delay)
```

**第 72-73 行**：限制延迟不超过最大值。

---

## 5. `retry()` — 重试装饰器工厂

```python
def retry(exceptions=Exception, tries=-1, delay=0, max_delay=None,
          backoff=1, jitter=0, logger=logging_logger):
```

**第 76-77 行**：参数与 `__retry_internal` 相同。

```python
    @decorator
    def retry_decorator(f, *fargs, **fkwargs):
        args = fargs if fargs else list()
        kwargs = fkwargs if fkwargs else dict()
        return __retry_internal(
            partial(f, *args, **kwargs),
            exceptions, tries, delay, max_delay, backoff, jitter, logger
        )
    return retry_decorator
```

**第 91-98 行**：
- 使用 `@decorator` 装饰 `retry_decorator`，保留原函数签名
- `retry_decorator` 将原函数和参数用 `partial` 绑定，传入重试引擎
- 返回装饰器

---

## 6. `retry_call()` — 直接重试调用

```python
def retry_call(f, fargs=None, fkwargs=None, exceptions=Exception,
               tries=-1, delay=0, max_delay=None, backoff=1,
               jitter=0, logger=logging_logger):
```

**第 101-103 行**：不使用装饰器语法，直接调用函数并重试。

```python
    args = fargs if fargs else list()
    kwargs = fkwargs if fkwargs else dict()
    return __retry_internal(
        partial(f, *args, **kwargs),
        exceptions, tries, delay, max_delay, backoff, jitter, logger
    )
```

**第 121-123 行**：与 `retry` 逻辑相同，但直接执行而非返回装饰器。

---

## 7. 核心算法流程图

### 重试引擎流程

```
开始
 │
 ▼
_tries = tries, _delay = delay
 │
 ▼
┌─▶ while _tries != 0:
│    │
│    ▼
│    try: return f()
│    │
│    ▼ (异常)
│    _tries -= 1
│    │
│    ▼
│    _tries == 0? ──是──▶ raise 原始异常
│    │
│    否
│    │
│    ▼
│    logger.exception(e)
│    logger.warning("重试...")
│    │
│    ▼
│    sleep(_delay)
│    │
│    ▼
│    _delay = _delay * backoff + jitter
│    │
│    ▼
│    _delay = min(_delay, max_delay)
│    │
└────┘
```

### 延迟退避示意（backoff=2, delay=1）

```
尝试1 ──失败──▶ 等待 1s
尝试2 ──失败──▶ 等待 2s
尝试3 ──失败──▶ 等待 4s
尝试4 ──失败──▶ 等待 8s
...
```

---

## 8. 使用示例

```python
# 装饰器用法
@retry(exceptions=ConnectionError, tries=3, delay=1, backoff=2)
def connect_to_server():
    # 可能抛出 ConnectionError
    pass

# 直接调用用法
result = retry_call(
    fetch_data,
    fargs=["https://api.example.com"],
    exceptions=TimeoutError,
    tries=5,
    delay=0.5,
    jitter=(0.1, 0.5)  # 随机抖动
)

# 无限重试
@retry(tries=-1, delay=1)
def always_retry():
    pass
```

---

## 9. 设计模式总结

| 模式 | 说明 |
|------|------|
| **装饰器工厂** | `retry()` 返回装饰器，支持参数化配置 |
| **指数退避** | `backoff` 参数实现延迟指数增长，减轻服务端压力 |
| **抖动机制** | `jitter` 防止重试风暴（多个客户端同时重试） |
| **Partial 绑定** | 使用 `functools.partial` 将函数和参数打包为无参函数 |
| **兼容层** | `try/except` 导入第三方库，提供降级替代方案 |
| **原始异常传播** | 重试耗尽时 `raise e` 而非 `raise`，保留完整异常链 |
