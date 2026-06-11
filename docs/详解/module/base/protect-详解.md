# protect.py 逐行代码详解

> 源文件路径：`module/base/protect.py`

---

## 1. 文件概述

`protect.py` 提供了防封号（anti-ban）相关的随机延迟工具，用于模拟人类操作行为：
- **random_delay**：随机延迟指定范围的时间
- **random_sleep**：按概率触发随机延迟

---

## 2. 导入部分解释

```python
import random                       # 随机数生成
from time import sleep             # 线程休眠
from module.logger import logger   # 项目日志模块
```

---

## 3. 函数逐行解释

### 3.1 `random_delay(min_value, max_value, decimal)` — 随机延迟

```python
def random_delay(min_value: float = 2.0, max_value: float = 6.0, decimal: int = 1):
```

**第 7 行**：定义函数，参数说明：
- `min_value`：最小延迟秒数，默认 2.0
- `max_value`：最大延迟秒数，默认 6.0
- `decimal`：保留小数位数，默认 1

```python
    random_float_in_range = random.uniform(min_value, max_value)
```

**第 11 行**：在 `[min_value, max_value]` 范围内生成均匀分布的随机浮点数。

```python
    sleep(round(random_float_in_range, decimal))
```

**第 12 行**：四舍五入到指定小数位后执行休眠。

### 3.2 `random_sleep(probability)` — 概率性随机休眠

```python
def random_sleep(probability: float = 0.05):
```

**第 15 行**：定义函数，`probability` 为触发概率，默认 5%。

```python
    if random.random() <= probability:
        logger.info('Tigger random sleep')
        random_delay()
```

**第 16-18 行**：
- `random.random()` 生成 `[0, 1)` 的随机数
- 如果小于等于 `probability`，记录日志并调用 `random_delay()` 执行 2~6 秒的随机延迟

---

## 4. 核心算法流程图

```
random_sleep(probability=0.05)
 │
 ▼
random() <= 0.05 ?
 ├─ 否 (95%) → 直接返回，无延迟
 └─ 是 (5%) → logger.info(...)
               │
               ▼
               random_delay()
               │
               ▼
               uniform(2.0, 6.0) → 例如 3.7
               │
               ▼
               round(3.7, 1) = 3.7
               │
               ▼
               sleep(3.7)
```

---

## 5. 使用示例

```python
# 在自动化操作之间添加随机延迟
def perform_action():
    click(button)
    random_delay(1.0, 3.0)  # 等待 1~3 秒

# 以 5% 概率触发随机休眠
def main_loop():
    while True:
        do_something()
        random_sleep(0.05)        # 5% 概率休眠 2~6 秒
        random_sleep(probability=0.1)  # 10% 概率
```

---

## 6. 设计模式总结

| 模式 | 说明 |
|------|------|
| **随机化策略** | 通过随机延迟模拟人类操作节奏，降低被检测风险 |
| **概率触发** | `random_sleep` 使用概率控制触发频率，避免规律性行为 |
| **默认值设计** | 合理的默认参数（2~6秒延迟，5%概率）开箱即用 |
