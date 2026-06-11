# RuleImageMallResourceMixin 逐行代码详解

## 1. 文件概述

`RuleImageMallResourceMixin.py` 是一个 **Mixin 类**，为 `RuleImage` 提供"商城资源"（mall_resource）相关的扩展能力。它基于图片模板匹配的结果，自动推导出 OCR 文本识别区域（ROI），从而实现**先定位图标 → 再读取图标旁边文字**的两步式识别流程。

**设计意图**：在游戏自动化中，商城页面的资源数值（如金币、钻石数量）通常紧挨着对应的图标显示。本 Mixin 封装了"找到图标 → 偏移得到文字区域 → 构建 OCR 识别器"的通用逻辑，避免在每个调用点重复编写偏移计算代码。

**文件位置**：`module/atom/RuleImageMallResourceMixin.py`（共 91 行）

---

## 2. 导入部分解释

```python
# module/atom/image/image_mall_resource.py
```

> **第 1 行**：文件头注释，标注了该文件的原始路径（可能重构后路径已变化，注释保留了历史信息）。

```python
from module.logger import logger
```

> **第 3 行**：从项目日志模块导入 `logger` 实例。用于在匹配异常时输出错误日志。

```python
from module.atom.ocr import RuleOcr
```

> **第 4 行**：从 `module.atom.ocr` 导入 `RuleOcr` 类。`RuleOcr` 是一个多功能 OCR 识别器，继承了 `Digit`、`DigitCounter`、`Duration`、`Single`、`Full`、`Quantity` 等多种识别模式。本 Mixin 在 `build_mall_resource_ocr` 方法中使用它来构建最终的 OCR 实例。

---

## 3. 类定义解释

```python
class RuleImageMallResourceMixin:
    """
    RuleImage 的 mall_resource 能力扩展
    """
```

> **第 7-10 行**：定义 `RuleImageMallResourceMixin` 类。这是一个纯 Mixin 类，不独立使用，而是被 `RuleImage` 继承（`class RuleImage(RuleImageMallResourceMixin)`）。Mixin 模式允许将特定领域的逻辑从主类中分离出来，保持代码的模块化。

```python
    # mall_resource 专用偏移参数
    MALL_RESOURCE_X_OFFSET = 40
    MALL_RESOURCE_RIGHT_EXTEND = 70
```

> **第 12-14 行**：定义两个类级别的常量：
> - `MALL_RESOURCE_X_OFFSET = 40`：OCR 区域相对于图标 ROI 的**水平偏移量**（向右偏移 40 像素），用于跳过图标本身，定位到右侧的文字区域。
> - `MALL_RESOURCE_RIGHT_EXTEND = 70`：OCR 区域相对于图标 ROI 的**右侧扩展量**（额外增加 70 像素宽度），确保文字区域足够宽以包含完整的数值文本。

---

## 4. 每个方法的逐行解释

### 4.1 `match_and_get_roi` 方法

```python
def match_and_get_roi(self, image, threshold=None):
```

> **第 16 行**：方法签名。
> - `self`：实例对象，实际类型是 `RuleImage`（因为 Mixin 被 `RuleImage` 继承）。
> - `image`：待匹配的截图（numpy 数组，通常是游戏画面截图）。
> - `threshold`：匹配阈值，为 `None` 时使用 `self.threshold` 默认值。

```python
    """
    - match 成功 → 返回 (x, y, w, h)
    - match 失败 / 异常 → 返回 None
    """
```

> **第 17-20 行**：文档字符串，说明返回值语义——成功返回四元组 ROI，失败返回 `None`。

```python
    try:
        ok = self.match(image, threshold)
    except Exception as e:
        logger.error(f"match exception: {e}")
        return None
```

> **第 21-25 行**：调用 `self.match()` 进行模板匹配。
> - `self.match(image, threshold)` 是 `RuleImage` 类的核心方法，使用 OpenCV 的 `cv2.matchTemplate` 在截图中搜索模板图片。
> - 匹配成功时 `self.roi_front[0]` 和 `self.roi_front[1]` 会被更新为匹配位置的坐标（见 `image.py` 第 166-167 行）。
> - 如果抛出异常（如图像格式错误），记录错误日志并返回 `None`。

```python
    if not ok:
        return None
```

> **第 27-28 行**：匹配失败（未找到目标图标），直接返回 `None`。

```python
    try:
        mat = self.image
```

> **第 30-31 行**：获取模板图像 `self.image`。`self.image` 是 `RuleImage` 的一个属性，返回加载后的模板图片（numpy 数组）。

```python
        if mat is None or mat.shape[0] == 0 or mat.shape[1] == 0:
            return None
```

> **第 32-33 行**：安全检查——模板图像为空或尺寸为 0 时返回 `None`。防止后续计算出错。

```python
        h, w = mat.shape[:2]
```

> **第 35 行**：从模板图像的 shape 中提取高度 `h` 和宽度 `w`。`shape[:2]` 取前两个维度（高度, 宽度），忽略通道数。

```python
        x = int(self.roi_front[0])
        y = int(self.roi_front[1])
```

> **第 36-37 行**：获取匹配后更新的 `roi_front` 的 x、y 坐标。`roi_front` 在 `match` 方法中已被更新为匹配到的位置（`image.py` 第 166-167 行）：
> ```python
> self.roi_front[0] = max_loc[0] + self.roi_back[0]
> self.roi_front[1] = max_loc[1] + self.roi_back[1]
> ```

```python
        return (x, y, int(w), int(h))
```

> **第 39 行**：返回匹配区域的 ROI 元组 `(x, y, w, h)`，即图标在截图中的位置和尺寸。

```python
    except Exception:
        return None
```

> **第 40-41 行**：兜底异常处理，任何未预料的错误都返回 `None`。

---

### 4.2 `get_mall_resource_text_roi` 方法

```python
def get_mall_resource_text_roi(self, image, threshold=None):
```

> **第 43 行**：方法签名。参数与 `match_and_get_roi` 相同。

```python
    """
    mall_resource 专用：
    - 定位 icon
    - 推导文本 OCR ROI

    return: roi or None
    """
```

> **第 44-49 行**：文档字符串。说明本方法的核心逻辑是"先定位图标，再推导文字区域"。

```python
    try:
        icon_roi = self.match_and_get_roi(image, threshold)
```

> **第 51-52 行**：调用 `match_and_get_roi` 尝试匹配图标，获取图标的位置 ROI。

```python
        if icon_roi is None:
            # 回退 roi_front
            ix, iy, iw, ih = self.roi_front
        else:
            ix, iy, iw, ih = icon_roi
```

> **第 53-57 行**：解构 ROI 值。
> - 如果图标匹配失败（`icon_roi is None`），**回退使用 `self.roi_front` 的原始值**作为基准。这是一种容错策略——即使匹配失败，仍然使用默认的 ROI 区域来尝试 OCR。
> - 如果匹配成功，使用匹配结果 `icon_roi` 的坐标。

```python
        x = int(ix) + self.MALL_RESOURCE_X_OFFSET
```

> **第 59 行**：计算 OCR 区域的 x 坐标 = 图标 x 坐标 + 40 像素偏移。向右偏移以跳过图标本身，定位到文字起始位置。

```python
        y = int(iy)
```

> **第 60 行**：OCR 区域的 y 坐标与图标相同（文字和图标在同一水平线上）。

```python
        w = int(iw) + self.MALL_RESOURCE_RIGHT_EXTEND
```

> **第 61 行**：OCR 区域的宽度 = 图标宽度 + 70 像素扩展。确保足够宽以包含完整数值。

```python
        h = int(ih)
```

> **第 62 行**：OCR 区域的高度与图标相同。

```python
        return (x, y, w, h)
```

> **第 64 行**：返回推导出的文字 OCR 区域 ROI。

```python
    except Exception:
        return None
```

> **第 65-66 行**：兜底异常处理。

---

### 4.3 `build_mall_resource_ocr` 方法

```python
def build_mall_resource_ocr(self, image, threshold=None, name="mall_resource"):
```

> **第 68 行**：方法签名。
> - `name`：OCR 实例的名称标识，默认为 `"mall_resource"`。

```python
    """
    mall_resource 专用快捷方法：
    - 定位 icon
    - 推导 OCR ROI
    - 构造 RuleOcr

    return: RuleOcr | None
    """
```

> **第 69-75 行**：文档字符串。这是最高层的便捷方法，一步完成"图标定位 → ROI 推导 → OCR 构造"。

```python
    try:
        roi = self.get_mall_resource_text_roi(image, threshold)
```

> **第 77-78 行**：调用 `get_mall_resource_text_roi` 获取文字区域 ROI。

```python
        if roi is None:
            return None
```

> **第 79-80 行**：ROI 获取失败则返回 `None`。

```python
        return RuleOcr(
            roi=roi,
            area=roi,
            mode="Quantity",
            method="Default",
            keyword="",
            name=name
        )
```

> **第 82-89 行**：构造 `RuleOcr` 实例。
> - `roi=roi`：OCR 识别的目标区域。
> - `area=roi`：OCR 操作区域（在 `Quantity` 模式下 `roi` 和 `area` 通常一致）。
> - `mode="Quantity"`：使用数量识别模式，专门用于识别如 "1,234" 或 "999" 这样的数值。
> - `method="Default"`：使用默认 OCR 方法。
> - `keyword=""`：无关键词过滤。
> - `name=name`：实例名称，用于日志和调试。

```python
    except Exception:
        return None
```

> **第 90-91 行**：兜底异常处理。

---

## 5. 核心算法流程图

```
┌─────────────────────────────────────────────────────────┐
│                    调用入口                               │
│         build_mall_resource_ocr(image)                   │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  get_mall_resource_text_roi(image, threshold)            │
│                                                         │
│  ┌───────────────────────────────────────────────┐      │
│  │ match_and_get_roi(image, threshold)           │      │
│  │                                               │      │
│  │  self.match(image, threshold)                 │      │
│  │       │                                       │      │
│  │       ├── 异常 ──→ logger.error ──→ return None│      │
│  │       │                                       │      │
│  │       ├── 失败 ──→ return None                │      │
│  │       │                                       │      │
│  │       └── 成功 ──→ 读取 self.image            │      │
│  │                    获取 (x, y, w, h)          │      │
│  │                    return roi                  │      │
│  └───────────────────────────────────────────────┘      │
│       │                                                 │
│       ├── icon_roi is None ──→ 回退使用 self.roi_front  │
│       │                                                 │
│       └── icon_roi 有效 ──→ 使用匹配结果                │
│                                                         │
│  偏移计算:                                               │
│    x = ix + 40   (X_OFFSET)                             │
│    y = iy        (不变)                                  │
│    w = iw + 70   (RIGHT_EXTEND)                         │
│    h = ih        (不变)                                  │
│                                                         │
│  return (x, y, w, h)                                    │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  构造 RuleOcr 实例                                       │
│                                                         │
│  RuleOcr(                                               │
│      roi = 推导出的文字区域,                              │
│      area = 同上,                                        │
│      mode = "Quantity",    ← 数量识别模式                │
│      method = "Default",                                │
│      keyword = "",                                      │
│      name = "mall_resource"                             │
│  )                                                      │
│                                                         │
│  return RuleOcr | None                                  │
└─────────────────────────────────────────────────────────┘
```

---

## 6. 使用示例

### 6.1 基本用法

```python
from module.atom.image import RuleImage

# 创建 RuleImage 实例（表示一个商城金币图标）
gold_icon = RuleImage(
    roi_front=(100, 200, 30, 30),   # 初始 ROI（会被匹配结果覆盖）
    roi_back=(0, 0, 1280, 720),     # 搜索范围：整个屏幕
    method="Template matching",
    threshold=0.8,
    file="assets/mall/gold_icon.png"
)

# 方式一：仅获取图标位置
screenshot = get_screenshot()  # 获取游戏截图
icon_roi = gold_icon.match_and_get_roi(screenshot)
if icon_roi:
    x, y, w, h = icon_roi
    print(f"图标位置: ({x}, {y}), 尺寸: {w}x{h}")

# 方式二：获取文字 OCR 区域
text_roi = gold_icon.get_mall_resource_text_roi(screenshot)
if text_roi:
    print(f"文字区域: {text_roi}")

# 方式三：一步构建 OCR 识别器并读取数值
ocr = gold_icon.build_mall_resource_ocr(screenshot, name="gold_amount")
if ocr:
    amount = ocr.ocr(screenshot)
    print(f"金币数量: {amount}")
```

### 6.2 批量识别多种资源

```python
resources = {
    "gold":   ("assets/mall/gold_icon.png",   "gold_amount"),
    "diamond":("assets/mall/diamond_icon.png", "diamond_amount"),
    "ticket": ("assets/mall/ticket_icon.png",  "ticket_amount"),
}

screenshot = get_screenshot()
results = {}

for key, (icon_file, ocr_name) in resources.items():
    icon = RuleImage(
        roi_front=(0, 0, 30, 30),
        roi_back=(0, 0, 1280, 720),
        method="Template matching",
        threshold=0.8,
        file=icon_file
    )
    ocr = icon.build_mall_resource_ocr(screenshot, name=ocr_name)
    if ocr:
        results[key] = ocr.ocr(screenshot)

print(results)
# {'gold': '12,500', 'diamond': '350', 'ticket': '15'}
```

---

## 7. 设计模式总结

### 7.1 Mixin 模式

本文件采用 **Mixin 设计模式**，将"商城资源识别"这一特定领域的功能从主类 `RuleImage` 中分离出来。

| 特点 | 说明 |
|------|------|
| **职责分离** | `RuleImage` 负责通用的模板匹配能力，`RuleImageMallResourceMixin` 负责商城资源的特定偏移逻辑 |
| **多重继承** | Python 支持多继承，未来可以继续添加其他 Mixin（如 `RuleImageShopMixin`） |
| **无独立实例** | Mixin 类不单独使用，始终通过 `RuleImage` 继承来调用 |

### 7.2 两步式识别模式

```
图标定位（模板匹配） → 偏移推导（几何计算） → 文字识别（OCR）
```

这是一种常见的"锚点 + 偏移"模式：先通过可靠的图标匹配确定参考点，再通过固定的偏移量推导目标区域。

### 7.3 防御性编程

每个方法都采用 `try-except` 包裹，返回 `None` 表示失败。调用者只需检查返回值是否为 `None` 即可判断成功/失败，无需处理异常。这是一种**错误抑制**策略，适合自动化脚本场景——单个资源识别失败不应中断整体流程。

### 7.4 回退机制

`get_mall_resource_text_roi` 在图标匹配失败时回退使用 `self.roi_front` 的默认值，保证即使匹配失败也能尝试 OCR，提高了鲁棒性。

### 7.5 方法组合模式

三个方法形成**层级调用链**：

```
build_mall_resource_ocr  (高层便捷方法)
    └── get_mall_resource_text_roi  (中间层 ROI 推导)
            └── match_and_get_roi  (底层匹配)
```

调用者可以根据需要选择调用哪一层，既提供了简单易用的高层接口，也保留了底层的灵活性。
