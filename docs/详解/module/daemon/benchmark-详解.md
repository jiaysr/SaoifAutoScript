# module/daemon/benchmark.py 代码详解

## 1. 文件概述

`benchmark.py` 是设备性能基准测试模块，用于测试和评估不同截图方法和点击方法的性能表现。通过多次测试取最优结果的平均值，为用户推荐最快的截图和控制方式。

**文件路径**: `module/daemon/benchmark.py`
**代码行数**: 247 行
**主要功能**:
- 测试各种截图方法的响应速度
- 测试各种点击方法的响应速度
- 生成性能评估报告并推荐最优方案

---

## 2. 导入部分解释

```python
import time
import typing as t
import numpy as np
from rich.table import Table
from rich.text import Text
from module.base.utils import float2str as float2str_
from module.base.utils import random_rectangle_point
from module.daemon.daemon_base import DaemonBase
from module.config.config import Config
from module.device.device import Device
from module.exception import RequestHumanTakeover
from module.logger import logger
```

| 导入项 | 来源模块 | 说明 |
|--------|----------|------|
| `time` | Python标准库 | 用于计时测量 |
| `typing` | Python标准库 | 类型注解支持 |
| `numpy` | NumPy | 数值计算，用于求平均值和排序 |
| `Table`, `Text` | rich | 终端表格和文本样式渲染 |
| `float2str_` | module.base.utils | 浮点数转字符串工具函数 |
| `random_rectangle_point` | module.base.utils | 在矩形区域内随机生成点击坐标 |
| `DaemonBase` | module.daemon.daemon_base | 守护进程基类 |
| `Config` | module.config.config | 配置管理类 |
| `Device` | module.device.device | 设备操作类 |
| `RequestHumanTakeover` | module.exception | 请求人工接管异常 |
| `logger` | module.logger | 日志记录器 |

---

## 3. 类定义解释

### 辅助函数 float2str

```python
def float2str(n, decimal=3):
    if not isinstance(n, (float, int)):
        return str(n)
    else:
        return float2str_(n, decimal=decimal) + 's'
```

将数值格式化为带秒单位的字符串，非数值类型直接转字符串。

### Benchmark 类

```python
 class Benchmark(DaemonBase):
    TEST_TOTAL = 15
    TEST_BEST = int(TEST_TOTAL * 0.8)
```

- **继承关系**: `Benchmark` → `DaemonBase` → `BaseTask`
- **类常量**:
  - `TEST_TOTAL = 15`: 每项测试总次数
  - `TEST_BEST = 12`: 取最优的测试次数（80%）

---

## 4. 每个方法的逐行解释

### benchmark_test 方法

```python
def benchmark_test(self, func, *args, **kwargs):
```

**功能**: 对指定函数进行多次性能测试，返回平均耗时

| 行号 | 代码 | 说明 |
|------|------|------|
| 38 | `logger.hr(f'Benchmark test', level=2)` | 打印二级标题分隔线 |
| 39 | `logger.info(f'Testing function: {func.__name__}')` | 记录正在测试的函数名 |
| 40 | `record = []` | 初始化耗时记录列表 |
| 42 | `for n in range(1, self.TEST_TOTAL + 1):` | 循环执行测试（1到15次） |
| 43 | `start = time.time()` | 记录开始时间 |
| 45-54 | `try: func(*args, **kwargs) except...` | 执行被测试函数，捕获异常 |
| 56 | `cost = time.time() - start` | 计算本次耗时 |
| 57-60 | `logger.attr(...)` | 记录测试进度和耗时 |
| 61 | `record.append(cost)` | 将耗时添加到记录列表 |
| 64 | `average = float(np.mean(np.sort(record)[:self.TEST_BEST]))` | 排序后取最优12次计算平均值 |
| 65 | `logger.info(...)` | 记录最终测试结果 |
| 66 | `return average` | 返回平均耗时 |

### evaluate_screenshot 方法

```python
@staticmethod
def evaluate_screenshot(cost):
```

**功能**: 根据截图耗时评估性能等级

| 耗时范围 | 评级 | 样式 |
|----------|------|------|
| < 0.10s | Ultra Fast | bold bright_green |
| < 0.20s | Very Fast | bright_green |
| < 0.30s | Fast | green |
| < 0.50s | Medium | yellow |
| < 0.75s | Slow | red |
| < 1.00s | Very Slow | bright_red |
| >= 1.00s | Ultra Slow | bold bright_red |

### evaluate_click 方法

```python
@staticmethod
def evaluate_click(cost):
```

**功能**: 根据点击耗时评估性能等级

| 耗时范围 | 评级 | 样式 |
|----------|------|------|
| < 0.1s | Fast | bright_green |
| < 0.2s | Medium | yellow |
| < 0.4s | Slow | red |
| >= 0.4s | Very Slow | bright_red |

### show 方法

```python
@staticmethod
def show(test, data, evaluate_func):
```

**功能**: 使用 Rich 库生成格式化的性能测试结果表格

| 行号 | 代码 | 说明 |
|------|------|------|
| 118 | `table = Table(show_lines=True)` | 创建表格对象，显示边框线 |
| 119-123 | `table.add_column(...)` | 添加三列：测试项、时间、速度评级 |
| 124-129 | `for row in data: table.add_row(...)` | 遍历数据添加表格行 |
| 130 | `logger.print(table, justify='center')` | 居中打印表格 |

### benchmark 方法

```python
def benchmark(self, screenshot: t.Tuple[str] = (), click: t.Tuple[str] = ()):
```

**功能**: 执行完整的基准测试流程

| 行号 | 代码 | 说明 |
|------|------|------|
| 133 | `logger.hr('Benchmark', level=1)` | 打印一级标题 |
| 137-140 | 截图测试循环 | 遍历测试所有截图方法 |
| 142 | `area = (120, 20, 200, 50)` | 定义安全点击区域 |
| 143-147 | 点击测试循环 | 遍历测试所有点击方法 |
| 149-154 | `compare` 函数 | 排序辅助函数，非数值返回100 |
| 157-168 | 结果展示 | 显示表格并推荐最快方法 |
| 170 | `return fastest_screenshot, fastest_click` | 返回推荐的最快方法 |

### get_test_methods 方法

```python
def get_test_methods(self) -> t.Tuple[t.Tuple[str], t.Tuple[str]]:
```

**功能**: 根据设备类型返回需要测试的方法列表

| 设备类型 | 特殊处理 |
|----------|----------|
| emulator_android_12, android_phone_12 | 移除 aScreenCap 系列（Android 9+不支持） |
| plone_cloud_with_adb | 移除 nc 系列（云手机不支持） |
| android_phone_vmos | 使用特定方法集 |

### run 方法

```python
def run(self):
```

**功能**: 主执行入口，执行完整的基准测试流程

### run_simple_screenshot_benchmark 方法

```python
def run_simple_screenshot_benchmark(self):
```

**功能**: 简化版截图基准测试，仅测试3次取最优1次，用于快速获取推荐截图方法

---

## 5. 核心算法流程图

```
┌─────────────────────────────────────┐
│            benchmark.run            │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   配置覆盖为 ADB 模式               │
│   卸载 minicap                      │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   get_test_methods()                │
│   根据设备类型获取测试方法列表        │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│         benchmark() 主测试           │
├─────────────────────────────────────┤
│  ┌─────────────────────────────┐   │
│  │   截图方法测试循环           │   │
│  │   for method in screenshot: │   │
│  │     benchmark_test(method)  │   │
│  └─────────────────────────────┘   │
│              │                      │
│              ▼                      │
│  ┌─────────────────────────────┐   │
│  │   点击方法测试循环           │   │
│  │   for method in click:      │   │
│  │     benchmark_test(method)  │   │
│  └─────────────────────────────┘   │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   结果排序，推荐最快方法             │
│   生成 Rich 表格展示                 │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   return fastest_screenshot,        │
│          fastest_click              │
└─────────────────────────────────────┘
```

### benchmark_test 子流程

```
┌─────────────────────────────────────┐
│       benchmark_test(func)          │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   for n in 1..TEST_TOTAL (15次):    │
│     ┌───────────────────────────┐   │
│     │ start = time.time()       │   │
│     │ func(*args, **kwargs)     │   │
│     │ cost = time.time() - start│   │
│     │ record.append(cost)       │   │
│     └───────────────────────────┘   │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   排序 record                       │
│   取前 TEST_BEST (12) 个            │
│   计算平均值                         │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│         return average              │
└─────────────────────────────────────┘
```

---

## 6. 使用示例

### 完整基准测试

```python
from module.config.config import Config
from module.device.device import Device
from module.daemon.benchmark import Benchmark

# 初始化
config = Config('oas1')
device = Device(config)
benchmark = Benchmark(config=config, device=device)

# 执行完整测试
benchmark.run()
```

### 快速截图测试

```python
# 仅测试截图方法
fastest_method = benchmark.run_simple_screenshot_benchmark()
print(f"推荐截图方法: {fastest_method}")
```

### 自定义测试

```python
# 自定义测试方法列表
screenshot_methods = ('ADB', 'ADB_nc', 'uiautomator2')
click_methods = ('ADB', 'minitouch')

fastest_screenshot, fastest_click = benchmark.benchmark(
    screenshot=screenshot_methods,
    click=click_methods
)
```

### 命令行直接运行

```python
# 在文件末尾的 __main__ 中
if __name__ == '__main__':
    config = Config('oas1')
    device = Device(config)
    b = Benchmark(config=config, device=device)
    print(b.run_simple_screenshot_benchmark())
```

---

## 7. 设计模式总结

| 设计模式 | 应用说明 |
|----------|----------|
| **策略模式** | 不同的截图/点击方法作为可互换的策略进行测试 |
| **模板方法** | `benchmark_test` 定义了测试流程模板，被测函数作为参数传入 |
| **工厂方法** | `get_test_methods` 根据设备类型生产不同的测试方法集 |
| **装饰器模式** | `@staticmethod` 将评估函数标记为静态方法 |

**设计优点**:
- 统一的测试框架，易于扩展新的测试方法
- 取最优80%结果平均值，排除异常值干扰
- Rich 表格输出，结果直观易读
- 根据设备类型智能选择测试方法

**性能评估标准**:
- 截图: Ultra Fast (<0.1s) 到 Ultra Slow (>=1s)
- 点击: Fast (<0.1s) 到 Very Slow (>=0.4s)
