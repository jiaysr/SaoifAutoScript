# image_grid.py 逐行代码详解

> 源文件路径：`module/atom/image_grid.py`
> 作者：runhey
> GitHub：https://github.com/runhey

---

## 1. 文件概述

`image_grid.py` 定义了 `ImageGrid` 类，用于对一组 `RuleImage` 图像模板进行**批量匹配管理**。它封装了两个核心能力：

- **`find_anyone`**：在一组模板中找到第一个匹配项（逻辑 OR）
- **`find_everyone`**：找出所有模板的所有匹配结果，并按屏幕位置排序

该类是一个典型的**策略容器模式**，将多个图像匹配规则聚合为一个可统一调度的网格对象，常用于游戏自动化脚本中对多个 UI 元素的并发识别。

---

## 2. 导入部分解释

```python
# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import numpy as np

from module.atom.image import RuleImage
```

| 行号 | 内容 | 说明 |
|------|------|------|
| 1-3 | 注释 | 声明文件编码为 UTF-8，标注作者信息和 GitHub 地址 |
| 4 | `import numpy as np` | 导入 NumPy 库，用于图像数组处理。虽然本文件未直接使用 `np`，但 `RuleImage` 的方法接收 `np.array` 类型参数 |
| 6 | `from module.atom.image import RuleImage` | 从同模块导入 `RuleImage` 类，它是图像模板匹配的核心类，提供 `match()`、`match_all_any()` 等方法 |

---

## 3. 类定义解释

```python
class ImageGrid:
    def __init__(self, images: list[RuleImage]):
        self.images = images
```

| 行号 | 内容 | 说明 |
|------|------|------|
| 10 | `class ImageGrid:` | 定义 `ImageGrid` 类，无继承，是一个独立的工具类 |
| 12 | `def __init__(self, images: list[RuleImage]):` | 构造函数，接收一个 `RuleImage` 对象列表作为参数。类型注解 `list[RuleImage]` 表明这是一个泛型列表（Python 3.9+ 语法） |
| 13 | `self.images = images` | 将传入的图像列表保存为实例属性，供后续方法遍历使用 |

**设计意图**：`ImageGrid` 本身不持有图像数据，而是持有一组已配置好的 `RuleImage` 对象的引用。这是一种**组合模式**，将多个匹配规则聚合为一个统一的调度单元。

---

## 4. 方法逐行解释

### 4.1 `find_anyone` 方法

```python
def find_anyone(self, img: np.array) -> RuleImage or None:
    """
    在这些图片中找到其中一个
    :param img:
    :return: 如果没有找到返回None
    """
    for image in self.images:
        if image.match(img):
            return image
    return None
```

| 行号 | 代码 | 说明 |
|------|------|------|
| 16 | `def find_anyone(self, img: np.array) -> RuleImage or None:` | 方法签名。参数 `img` 是待匹配的截图（NumPy 数组），返回值为匹配到的 `RuleImage` 对象或 `None`。注意 `RuleImage or None` 在 Python 中实际等价于 `RuleImage`（因为 `or` 是运行时运算符），规范写法应为 `RuleImage \| None`，但此处作为文档意图仍然清晰 |
| 17-21 | 文档字符串 | 描述方法功能：在所有模板中找到第一个匹配的 |
| 22 | `for image in self.images:` | 遍历所有已注册的 `RuleImage` 模板对象 |
| 23 | `if image.match(img):` | 调用 `RuleImage.match()` 方法，该方法内部会根据配置的匹配方式（模板匹配或 SIFT 特征匹配）判断当前模板是否在截图中出现。匹配成功返回 `True`，同时会更新 `roi_front` 记录匹配位置 |
| 24 | `return image` | 一旦找到匹配项，**立即返回**对应的 `RuleImage` 对象。这是短路求值，不会继续检查后续模板 |
| 25 | `return None` | 遍历完所有模板均未匹配，返回 `None` |

**算法复杂度**：O(n)，n 为模板数量。最坏情况需遍历全部模板。

**使用场景**：当你有一组互斥的 UI 元素（如不同的弹窗），只需确认出现的是哪一个时使用。

---

### 4.2 `find_everyone` 方法

```python
def find_everyone(self, img: np.array) -> list or None:
    """
    自下而上查找所有匹配项，返回带对应image对象的排序结果
    :param img: 待匹配图像
    :return: 排序后的列表，每个元素为(image对象, (x, y, w, h))，无匹配返回None
    """
    matched = []
    # 收集匹配结果时保留来源image
    for image in self.images:
        matches = image.match_all_any(img, threshold=0.8, nms_threshold=0.3)
        for (score, x, y, w, h) in matches:
            matched.append( (image, score, (x, y, w, h)) )

    # 按y坐标升序排列（屏幕坐标系从上到下）
    sorted_results = sorted(
        matched,
        key=lambda item: item[2][1]  # item[1]是坐标元组，取y值
    )

    return sorted_results if sorted_results else None
```

| 行号 | 代码 | 说明 |
|------|------|------|
| 27 | `def find_everyone(self, img: np.array) -> list or None:` | 方法签名。返回排序后的列表或 `None` |
| 28-32 | 文档字符串 | 说明功能：查找所有匹配项并按位置排序返回 |
| 33 | `matched = []` | 初始化空列表，用于收集所有模板的匹配结果 |
| 35 | `for image in self.images:` | 遍历所有已注册的 `RuleImage` 模板对象 |
| 36 | `matches = image.match_all_any(img, threshold=0.8, nms_threshold=0.3)` | 调用 `RuleImage.match_all_any()` 方法，该方法会在截图中查找当前模板的**所有出现位置**，并通过 NMS（非极大值抑制）去除重叠的冗余匹配。参数说明：`threshold=0.8` 表示匹配相似度阈值为 80%；`nms_threshold=0.3` 表示 IoU 超过 30% 的重叠框会被抑制 |
| 37 | `for (score, x, y, w, h) in matches:` | 遍历当前模板的所有匹配结果。每个结果是一个五元组：匹配得分、x 坐标、y 坐标、宽度、高度 |
| 38 | `matched.append( (image, score, (x, y, w, h)) )` | 将匹配结果与来源模板对象打包为三元组 `(RuleImage, score, (x, y, w, h))` 并加入结果列表。保留来源 `image` 对象以便调用方知道匹配到的是哪个模板 |
| 41-44 | `sorted_results = sorted(...)` | 对所有匹配结果按 **y 坐标升序** 排序。`key=lambda item: item[2][1]` 中：`item[2]` 是坐标元组 `(x, y, w, h)`，`item[2][1]` 取 y 值。y 值越小表示在屏幕越上方，因此排序结果是从上到下的顺序 |
| 46 | `return sorted_results if sorted_results else None` | 如果有匹配结果则返回排序后的列表，否则返回 `None` |

**算法复杂度**：O(n × m + k log k)，其中 n 为模板数量，m 为每个模板的平均匹配结果数，k 为总匹配结果数。

**使用场景**：当你需要识别屏幕上所有出现的同类元素（如多个相同的按钮、列表项）并按位置处理时使用。

---

## 5. 核心算法流程图

### 5.1 `find_anyone` 流程

```
┌─────────────────────────┐
│     输入: 截图 img       │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  遍历 self.images 列表    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  当前 image.match(img)?  │
│  (调用 RuleImage 匹配)    │
└─────┬───────────┬───────┘
      │ 匹配成功   │ 匹配失败
      ▼           ▼
┌──────────┐  ┌──────────────┐
│return    │  │ 还有下一个模板? │
│ image    │  └──┬────────┬──┘
└──────────┘     │ 是     │ 否
                 ▼        ▼
           ┌─────────┐ ┌──────────┐
           │ 继续遍历  │ │return    │
           │ 下一个    │ │ None     │
           └─────────┘ └──────────┘
```

### 5.2 `find_everyone` 流程

```
┌──────────────────────────────┐
│       输入: 截图 img           │
└──────────────┬────────────────┘
               │
               ▼
┌──────────────────────────────┐
│  初始化 matched = []          │
└──────────────┬────────────────┘
               │
               ▼
┌──────────────────────────────┐
│  遍历 self.images 中每个模板    │◄──┐
└──────────────┬────────────────┘   │
               │                    │
               ▼                    │
┌──────────────────────────────┐   │
│ image.match_all_any(img)     │   │
│ threshold=0.8                │   │
│ nms_threshold=0.3            │   │
│ (模板匹配 + NMS 去重)         │   │
└──────────────┬────────────────┘   │
               │                    │
               ▼                    │
┌──────────────────────────────┐   │
│ 遍历每个匹配结果               │   │
│ (score, x, y, w, h)         │   │
│ → 追加到 matched 列表         │   │
└──────────────┬────────────────┘   │
               │                    │
               ▼                    │
┌──────────────────────────────┐   │
│ 还有下一个模板?                │───┘
│  是 → 继续  否 → 下一步        │
└──────────────┬────────────────┘
               │
               ▼
┌──────────────────────────────┐
│  按 y 坐标升序排序             │
│  (屏幕从上到下)               │
└──────────────┬────────────────┘
               │
               ▼
┌──────────────────────────────┐
│  sorted_results 非空?         │
│  是 → 返回排序列表             │
│  否 → 返回 None               │
└──────────────────────────────┘
```

### 5.3 NMS（非极大值抑制）在 `match_all_any` 中的流程

```
┌────────────────────────────┐
│  cv2.matchTemplate 获得     │
│  所有得分 >= threshold 的点  │
└─────────────┬──────────────┘
              │
              ▼
┌────────────────────────────┐
│  构建 boxes 和 scores 数组   │
│  boxes: [x, y, w, h]       │
│  scores: 匹配得分            │
└─────────────┬──────────────┘
              │
              ▼
┌────────────────────────────┐
│  cv2.dnn.NMSBoxes           │
│  score_threshold=0.8        │
│  nms_threshold=0.3          │
│  → 去除 IoU > 0.3 的重叠框   │
└─────────────┬──────────────┘
              │
              ▼
┌────────────────────────────┐
│  返回去重后的匹配结果列表     │
└────────────────────────────┘
```

---

## 6. 使用示例

### 6.1 基本用法：查找任意匹配

```python
from module.atom.image import RuleImage
from module.atom.image_grid import ImageGrid
import cv2
import numpy as np

# 定义多个图像模板
btn_ok = RuleImage(
    roi_front=(0, 0, 100, 40),
    roi_back=(200, 300, 400, 100),
    method="Template matching",
    threshold=0.8,
    file="./assets/btn_ok.png"
)

btn_cancel = RuleImage(
    roi_front=(0, 0, 100, 40),
    roi_back=(200, 300, 400, 100),
    method="Template matching",
    threshold=0.8,
    file="./assets/btn_cancel.png"
)

# 创建 ImageGrid
grid = ImageGrid([btn_ok, btn_cancel])

# 读取截图
screenshot = cv2.cvtColor(cv2.imread("screenshot.png"), cv2.COLOR_BGR2RGB)

# 查找第一个匹配的按钮
result = grid.find_anyone(screenshot)
if result:
    print(f"找到按钮: {result.name}")
    print(f"位置: {result.roi_front}")
else:
    print("未找到任何按钮")
```

### 6.2 查找所有匹配项

```python
# 假设有多个相同的图标需要识别
icon = RuleImage(
    roi_front=(0, 0, 32, 32),
    roi_back=(0, 0, 1280, 720),  # 全屏搜索
    method="Template matching",
    threshold=0.8,
    file="./assets/icon_gold.png"
)

grid = ImageGrid([icon])

# 查找屏幕上所有出现的图标
results = grid.find_everyone(screenshot)
if results:
    for image_obj, score, (x, y, w, h) in results:
        print(f"模板 {image_obj.name} 在 ({x}, {y}) 匹配，得分: {score:.3f}")
```

### 6.3 多模板混合查找

```python
# 定义多种 UI 元素模板
templates = [
    RuleImage(roi_front=(0,0,80,30), roi_back=(0,0,1280,720),
              method="Template matching", threshold=0.8, file="./assets/hp_bar.png"),
    RuleImage(roi_front=(0,0,80,30), roi_back=(0,0,1280,720),
              method="Template matching", threshold=0.8, file="./assets/mp_bar.png"),
    RuleImage(roi_front=(0,0,50,50), roi_back=(0,0,1280,720),
              method="Template matching", threshold=0.8, file="./assets/enemy_icon.png"),
]

grid = ImageGrid(templates)

# 快速判断屏幕上出现了哪种元素
found = grid.find_anyone(screenshot)
if found and found.name == "HP_BAR":
    print("检测到生命值条")
```

---

## 7. 设计模式总结

### 7.1 组合模式（Composite）

`ImageGrid` 将多个 `RuleImage` 对象组合为一个统一的整体，对外提供一致的查找接口。调用方无需关心内部有多少个模板、每个模板如何匹配。

### 7.2 迭代器模式（Iterator）

两个核心方法都通过 `for image in self.images` 遍历模板集合，逐个执行匹配逻辑，是典型的迭代处理模式。

### 7.3 短路求值（Short-circuit Evaluation）

`find_anyone` 采用短路策略：找到第一个匹配项立即返回，不做多余计算。这在模板数量较多时能显著提升效率。

### 7.4 关注点分离（Separation of Concerns）

- `RuleImage` 负责**单个模板**的匹配逻辑（模板匹配、SIFT 特征匹配、NMS 去重等）
- `ImageGrid` 负责**多个模板**的编排和结果聚合（遍历、收集、排序）

两者职责清晰，互不耦合。

### 7.5 依赖注入（Dependency Injection）

`ImageGrid` 通过构造函数接收 `RuleImage` 列表，不自行创建模板对象。这使得模板的配置（阈值、ROI、匹配方式）可以在外部灵活定义和注入。

### 7.6 类型提示（Type Hints）

代码使用了 Python 3.9+ 的内置泛型类型注解（`list[RuleImage]`），提高了代码可读性和 IDE 支持。但 `RuleImage or None` 的写法在类型系统层面不规范，更规范的写法是 `RuleImage | None`（Python 3.10+）或 `Optional[RuleImage]`。
