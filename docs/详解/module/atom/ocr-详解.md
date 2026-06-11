# `module/atom/ocr.py` 逐行代码详解

## 1. 文件概述

`ocr.py` 是 OCR（光学字符识别）模块的**顶层调度器**，定义了 `RuleOcr` 类。该类通过**多重继承**聚合了 6 种 OCR 识别模式（全文、单行、数字、计数器、时长、数量），并使用 Python 3.10 的 `match...case` 语法在运行时根据 `self.mode` 动态分派到对应的子类实现。

在项目架构中，`RuleOcr` 是面向业务层的统一接口，业务代码只需创建一个 `RuleOcr` 实例并指定 `mode`，即可调用不同类型的 OCR 识别能力，无需关心底层实现细节。

### 类继承关系图

```
                    BaseCor              (基础 OCR 引擎)
                   /   |   \
                Full  Single  Quantity   (三种基础模式)
                    /   |   \
              Digit  DigitCounter  Duration  (三种派生模式)
                   \   |   /
                    RuleOcr              (聚合所有模式的顶层类)
```

---

## 2. 导入部分解释

```python
import numpy as np
import cv2
```

- **`numpy`**：用于数值计算。在 `RuleOcr` 中主要用于 `np.random.randint` 生成随机坐标。
- **`cv2`（OpenCV）**：用于图像处理。在 `__main__` 测试代码中用于读取图片文件。

```python
from module.ocr.base_ocr import BaseCor, OcrMode, OcrMethod
```

- **`BaseCor`**：OCR 基类，提供 `ocr_single_line`、`detect_and_ocr`、`crop`、`filter` 等核心方法。
- **`OcrMode`**：枚举类，定义 6 种 OCR 模式：`FULL`、`SINGLE`、`DIGIT`、`DIGITCOUNTER`、`DURATION`、`QUANTITY`。
- **`OcrMethod`**：枚举类，目前仅有 `DEFAULT` 一种方法（占位符，便于未来扩展）。

```python
from module.ocr.sub_ocr import Full, Single, Digit, DigitCounter, Duration, Quantity
```

导入 6 个子模式类，每个类封装了特定模式的 `after_process`（后处理）和专用 OCR 方法（如 `ocr_digit`、`ocr_duration` 等）。

```python
from module.logger import logger
```

日志模块，用于记录 OCR 识别结果和调试信息。

---

## 3. 类定义解释

```python
class RuleOcr(Digit, DigitCounter, Duration, Single, Full, Quantity):
```

`RuleOcr` 使用**多重继承**同时继承了 6 个子模式类。MRO（方法解析顺序）决定了方法查找的优先级：

```
RuleOcr → Digit → DigitCounter → Duration → Single → Full → Quantity → BaseCor → object
```

### 设计意图

这种设计的核心思想是：**将不同 OCR 模式的实现分散到独立的子类中，通过组合而非条件分支来实现多态**。`RuleOcr` 本身只负责根据 `mode` 进行分派，具体的识别逻辑和后处理逻辑由各子类实现。

---

## 4. 每个方法的逐行解释

### 4.1 `__init__` 方法

```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
```

- **第 1 行**：接收任意位置参数和关键字参数。
- **第 2 行**：调用 `super().__init__()`，按照 MRO 链最终调用到 `BaseCor.__init__()`。
- `BaseCor.__init__()` 接收 `name`、`mode`、`method`、`roi`、`area`、`keyword` 六个参数，并将 `mode` 和 `method` 字符串转换为对应的枚举值。

```python
# BaseCor.__init__ 中的关键逻辑：
self.name = name.upper()                          # 名称转大写
self.mode = OcrMode[mode.upper()]                 # 字符串 → 枚举
self.method = OcrMethod[method.upper()]           # 字符串 → 枚举
self.roi = list(roi)                              # 感兴趣区域 [x, y, w, h]
self.area = list(area)                            # 完整区域 [x, y, w, h]
self.keyword = keyword                            # 关键词（用于文本匹配）
```

### 4.2 `after_process` 方法

```python
def after_process(self, result):
    match self.mode:
        case OcrMode.FULL: return Full.after_process(self, result)
        case OcrMode.SINGLE: return Single.after_process(self, result)
        case OcrMode.DIGIT: return Digit.after_process(self, result)
        case OcrMode.DIGITCOUNTER: return DigitCounter.after_process(self, result)
        case OcrMode.DURATION: return Duration.after_process(self, result)
        case OcrMode.QUANTITY: return Quantity.after_process(self, result)
        case _: return result
```

**作用**：对 OCR 原始识别结果进行后处理（清洗、修正、格式化）。

**逐行解释**：

| 行号 | 代码 | 说明 |
|------|------|------|
| 20 | `match self.mode:` | Python 3.10 结构化模式匹配，根据 `self.mode` 枚举值分支 |
| 21 | `case OcrMode.FULL:` | 全文模式：直接返回原文（`Full.after_process` 是恒等函数） |
| 22 | `case OcrMode.SINGLE:` | 单行模式：直接返回原文（`Single.after_process` 也是恒等函数） |
| 23 | `case OcrMode.DIGIT:` | 数字模式：调用 `Digit.after_process`，将易混淆字符替换为数字（如 `I→1`、`O→0`），过滤非数字字符 |
| 24 | `case OcrMode.DIGITCOUNTER:` | 计数器模式：类似数字模式，但保留 `/` 字符（如 `14/15`） |
| 25 | `case OcrMode.DURATION:` | 时长模式：修正时长格式中的易混淆字符（如 `：→:`），保留时间格式 |
| 26 | `case OcrMode.QUANTITY:` | 数量模式：支持中文单位转换（如 `6.33亿` → `633000000`），使用 `cn2an` 库 |
| 27 | `case _:` | 默认分支：未匹配时原样返回 |

**为什么要显式调用子类方法**：由于多重继承，直接调用 `super().after_process()` 会按 MRO 链调用，导致只有一个子类的 `after_process` 被执行。因此使用 `ClassName.method(self, result)` 的形式显式指定调用哪个子类的实现。

### 4.3 `ocr` 方法

```python
def ocr(self, image, keyword=None):
    match self.mode:
        case OcrMode.FULL: return Full.ocr_full(self, image, keyword)
        case OcrMode.SINGLE: return Single.ocr_single(self, image)
        case OcrMode.DIGIT: return Digit.ocr_digit(self, image)
        case OcrMode.DIGITCOUNTER: return DigitCounter.ocr_digit_counter(self, image)
        case OcrMode.DURATION: return Duration.ocr_duration(self, image)
        case OcrMode.QUANTITY: return Quantity.ocr_quantity(self, image)
        case _: return None
```

**作用**：统一的 OCR 识别入口方法，根据模式分派到不同的专用识别方法。

**逐行解释**：

| 行号 | 代码 | 说明 |
|------|------|------|
| 30 | `def ocr(self, image, keyword=None):` | 接收图像（numpy 数组）和可选的关键词 |
| 32 | `match self.mode:` | 根据模式分派 |
| 33 | `case OcrMode.FULL:` | 全文模式：调用 `ocr_full`，检测整个区域的文本并匹配关键词，返回匹配到的区域坐标 `(x, y, w, h)` |
| 34 | `case OcrMode.SINGLE:` | 单行模式：调用 `ocr_single`，返回识别到的文本字符串 |
| 35 | `case OcrMode.DIGIT:` | 数字模式：调用 `ocr_digit`，返回整数 |
| 36 | `case OcrMode.DIGITCOUNTER:` | 计数器模式：调用 `ocr_digit_counter`，返回 `(当前, 剩余, 总数)` 三元组 |
| 37 | `case OcrMode.DURATION:` | 时长模式：调用 `ocr_duration`，返回 `timedelta` 对象 |
| 38 | `case OcrMode.QUANTITY:` | 数量模式：调用 `ocr_quantity`，返回整数（支持万/亿单位） |
| 39 | `case _:` | 未知模式返回 `None` |

### 4.4 `coord` 方法

```python
def coord(self) -> tuple:
    """
    获取一个区域，随机返回一个坐标
    :return:
    """
    area = None
    if self.mode == OcrMode.FULL:
        area = self.area
    else:
        area = self.roi

    x, y, w, h = self.area
    x = np.random.randint(x, x + w)
    y = np.random.randint(y, y + h)
    return x, y
```

**作用**：在 OCR 识别区域内生成一个随机坐标，通常用于模拟人类点击行为（防检测）。

**逐行解释**：

| 行号 | 代码 | 说明 |
|------|------|------|
| 46 | `area = None` | 初始化区域变量 |
| 47-50 | `if/else` | 全文模式使用 `self.area`（完整区域），其他模式使用 `self.roi`（感兴趣区域） |
| 52 | `x, y, w, h = self.area` | **注意**：这里实际使用的是 `self.area` 而非上面设置的 `area` 变量，这是一个潜在的 bug——`area` 变量被赋值后未被使用 |
| 53 | `x = np.random.randint(x, x + w)` | 在区域宽度范围内生成随机 x 坐标 |
| 54 | `y = np.random.randint(y, y + h)` | 在区域高度范围内生成随机 y 坐标 |
| 55 | `return x, y` | 返回随机坐标元组 |

> **代码注意点**：第 52 行使用了 `self.area` 而非局部变量 `area`，这意味着 `if/else` 分支实际上没有生效。如果 `self.area` 和 `self.roi` 不同，实际行为与预期不符。

---

## 5. 核心算法流程图

### 5.1 OCR 识别主流程

```
┌─────────────────────────────────────────────────┐
│              业务层调用 RuleOcr.ocr(image)        │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│         检查 self.mode 枚举值                     │
│  ┌──────┬──────┬──────┬────────┬────────┬─────┐ │
│  │ FULL │SINGLE│DIGIT │DIGITCN │DURATION│QTY  │ │
│  └──┬───┴──┬───┴──┬───┴───┬────┴───┬────┴──┬──┘ │
└─────┼──────┼──────┼───────┼────────┼───────┼────┘
      │      │      │       │        │       │
      ▼      ▼      ▼       ▼        ▼       ▼
  ocr_full ocr_single ocr_digit ocr_digit ocr_dur ocr_qty
                      _counter  ation
      │      │      │       │        │       │
      │      ▼      │       │        │       │
      │  ┌──────────┤       │        │       │
      │  │ 裁剪 ROI │       │        │       │
      │  │ 预处理   │       │        │       │
      │  │ OCR 识别 │       │        │       │
      │  └────┬─────┘       │        │       │
      │       │              │        │       │
      │       ▼              │        │       │
      │  ┌──────────────────┴────────┴───────┤
      │  │        after_process 后处理        │
      │  │  ┌─────────────────────────────┐  │
      │  │  │ FULL: 原样返回              │  │
      │  │  │ SINGLE: 原样返回            │  │
      │  │  │ DIGIT: 字符修正→过滤→int    │  │
      │  │  │ DIGITCN: 字符修正→保留/     │  │
      │  │  │ DURATION: 字符修正→timedelta│  │
      │  │  │ QTY: 字符修正→cn2an→int    │  │
      │  │  └─────────────────────────────┘  │
      │  └───────────────┬───────────────────┤
      │                  │                   │
      ▼                  ▼                   ▼
  返回坐标        返回字符串/数字      返回数字/timedelta
```

### 5.2 数字后处理算法（Digit.after_process）

```
┌─────────────────────────────┐
│    输入: OCR 原始字符串       │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│    字符替换映射表:            │
│    I→1, D→0, S→5, B→8      │
│    ？→2, ?→2, d→6           │
│    o→0, O→0, →→1            │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│    过滤非数字字符            │
│    仅保留 0-9               │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│    转换为 int               │
│    空字符串 → 0             │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│    输出: 整数               │
└─────────────────────────────┘
```

### 5.3 数量后处理算法（Quantity.after_process）

```
┌─────────────────────────────┐
│    输入: OCR 原始字符串       │
│    如 "6.33亿" "1.2万"      │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│    字符替换 + 过滤           │
│    保留: 数字 . / 万 亿 千   │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│    处理 "/" 分隔符           │
│    "53万/100" → "53万"      │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│    cn2an 中文数字转阿拉伯数字 │
│    "6.33亿" → 633000000     │
│    "1.2万" → 12000          │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│    转换为 int               │
│    失败则返回 0             │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│    输出: 整数               │
└─────────────────────────────┘
```

---

## 6. 使用示例

### 6.1 基本用法：识别数字

```python
from module.atom.ocr import RuleOcr
import cv2

# 创建一个数字识别的 OCR 规则
ocr_rule = RuleOcr(
    roi=(144, 7, 100, 43),       # 识别区域 [x, y, width, height]
    area=(144, 7, 100, 43),      # 完整区域
    mode="Digit",                 # 数字模式
    method="Default",             # 默认方法
    keyword="",                   # 无关键词
    name="gold_amount"            # 规则名称
)

# 读取截图并识别
image = cv2.imread("screenshot.png")
result = ocr_rule.ocr(image)     # 返回 int，如 12345
print(f"识别结果: {result}")
```

### 6.2 识别数量（支持中文单位）

```python
# 识别类似 "6.33亿"、"1.2万" 的数量文本
ocr_qty = RuleOcr(
    roi=(144, 7, 100, 43),
    area=(144, 7, 100, 43),
    mode="Quantity",
    method="Default",
    keyword="",
    name="resource_count"
)

result = ocr_qty.ocr(image)      # 返回 int，如 633000000
```

### 6.3 识别计数器（如 "14/15"）

```python
ocr_counter = RuleOcr(
    roi=(100, 200, 80, 30),
    area=(100, 200, 80, 30),
    mode="DigitCounter",
    method="Default",
    keyword="",
    name="quest_progress"
)

result = ocr_counter.ocr(image)  # 返回 (14, 1, 15) → (当前, 剩余, 总数)
current, remaining, total = result
```

### 6.4 识别时长（如 "01:30:00"）

```python
ocr_duration = RuleOcr(
    roi=(50, 50, 120, 25),
    area=(50, 50, 120, 25),
    mode="Duration",
    method="Default",
    keyword="",
    name="cooldown"
)

result = ocr_duration.ocr(image)  # 返回 timedelta(hours=1, minutes=30)
```

### 6.5 全文模式匹配关键词

```python
ocr_full = RuleOcr(
    roi=(0, 0, 800, 600),
    area=(0, 0, 800, 600),
    mode="Full",
    method="Default",
    keyword="探索",
    name="explore_text"
)

result = ocr_full.ocr(image)     # 返回匹配到的区域坐标 (x, y, w, h)
```

### 6.6 结合 RuleImage 动态定位 OCR 区域

```python
from module.atom.image import RuleImage
from module.atom.ocr import RuleOcr

# 先用图像匹配定位图标
icon = RuleImage(
    roi_front=(155, 8, 42, 42),
    roi_back=(155, 7, 1115, 90),
    threshold=0.7,
    method="Template matching",
    file="navbar_icon.png"
)

# 根据图标位置动态构建 OCR 规则
image = cv2.imread("screenshot.png")
ocr_rule = icon.build_mall_resource_ocr(image, threshold=0.7, name="resource_1")
if ocr_rule:
    result = ocr_rule.ocr_quantity(image)  # 识别资源数量
    print(f"资源数量: {result}")
```

---

## 7. 设计模式总结

### 7.1 策略模式（Strategy Pattern）

`RuleOcr` 的核心设计思想是**策略模式**。`self.mode` 作为策略选择器，`match...case` 语句根据模式选择不同的识别策略（`ocr_full`、`ocr_digit`、`ocr_duration` 等）。每种策略封装了独立的识别逻辑和后处理逻辑。

**优势**：新增 OCR 模式只需添加一个新的子类并在 `match...case` 中注册，符合开闭原则。

### 7.2 多重继承 + 显式方法调用

与传统的单继承 + 虚方法重写不同，`RuleOcr` 使用多重继承聚合所有子模式，并通过 `ClassName.method(self, ...)` 显式调用指定子类的方法。这种设计：

- **避免了 MRO 链上的方法覆盖问题**：多重继承时 `super().method()` 只会调用 MRO 链上的下一个类，无法灵活选择。
- **保持了子类的独立性**：每个子类可以独立测试和使用。

### 7.3 模板方法模式（Template Method Pattern）

`BaseCor` 定义了 OCR 处理的骨架流程：

```
pre_process → OCR 识别 → 阈值判断 → after_process → 日志记录
```

子类通过重写 `after_process` 和提供专用 OCR 方法来定制行为，而不改变整体流程结构。

### 7.4 组合优于继承

虽然 `RuleOcr` 使用了继承，但其核心目的是**组合**——将 6 种独立的 OCR 能力组合到一个统一的接口中。这比在一个类中写大量 `if/elif` 分支更清晰、更易维护。

### 7.5 关键类职责总结

| 类 | 职责 |
|---|------|
| `BaseCor` | OCR 引擎封装、图像裁剪、阈值过滤、关键词匹配 |
| `Full` | 大范围多行文本检测，返回关键词匹配区域坐标 |
| `Single` | 固定位置单行文本识别，支持横/竖方向 |
| `Digit` | 数字识别，字符修正 + 非数字过滤 |
| `DigitCounter` | 计数器识别（如 `14/15`），返回三元组 |
| `Duration` | 时长识别（如 `01:30:00`），返回 `timedelta` |
| `Quantity` | 大数量识别（如 `6.33亿`），中文数字转换 |
| `RuleOcr` | 顶层调度器，根据 `mode` 分派到对应子类 |
