# `module/atom/list.py` 逐行代码详解

## 1. 文件概述

`RuleList` 是一个用于**管理和操作列表型 UI 元素**的核心类。它封装了对游戏界面中可滚动列表（如关卡列表、菜单列表等）的统一操作逻辑，支持两种识别模式：

| 模式 | 说明 |
|------|------|
| `image` | 通过模板匹配图片来识别列表项 |
| `ocr` | 通过 OCR 文字识别来识别列表项 |

核心能力包括：
- 计算滑动位置（模拟手指滑动列表）
- 检测某个列表项是否出现在当前可视区域
- 通过 OCR 判断目标项相对于当前可视区域的位置（前/后），从而决定滑动方向
- 支持竖直（vertical）和水平（horizontal）两种滑动方向

**典型使用场景**：在阴阳师等手游的自动化脚本中，识别并点击副本列表中的特定关卡。

---

## 2. 导入部分解释

```python
# 第1-3行：文件头注释，声明编码和作者信息
# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
```

```python
# 第5行：导入 OpenCV 库，用于图像处理（读取截图、图像匹配等）
import cv2

# 第6行：导入 Python 标准库 random，用于生成随机数
import random

# 第7行：导入 NumPy 库，用于高效的多维数组运算（图像本质是 NumPy 数组）
import numpy as np
```

```python
# 第9行：从 random 模块中单独导入 randint 函数，用于生成指定范围内的随机整数
from random import randint
```

```python
# 第11行：从 ppocronnx 库导入 BoxedResult 类型
# BoxedResult 是 OCR 识别结果的数据结构，包含识别文字、置信度分数、边界框坐标等
from ppocronnx.predict_system import BoxedResult

# 第12行：导入自定义的 RuleOcr 类，封装了 OCR 文字识别的规则和方法
from module.atom.ocr import RuleOcr

# 第13行：导入自定义的 RuleImage 类，封装了模板图片匹配的规则和方法
from module.atom.image import RuleImage

# 第14行：导入自定义的日志记录器
from module.logger import logger
```

**依赖关系图**：
```
list.py
├── cv2 (OpenCV)
├── numpy
├── random / randint
├── ppocronnx.predict_system.BoxedResult
├── module.atom.ocr.RuleOcr       ← OCR 识别封装
├── module.atom.image.RuleImage   ← 图片模板匹配封装
└── module.logger.logger          ← 日志工具
```

---

## 3. 类定义解释

### 3.1 类声明

```python
class RuleList:
```

定义 `RuleList` 类，没有任何继承，是一个独立的工具类。

### 3.2 构造函数 `__init__`

```python
def __init__(self, folder: str, direction: str, mode: str,
             roi_back: tuple, size: tuple, array: list[str]) -> None:
```

**参数说明**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `folder` | `str` | 图片资源文件夹路径，如 `"./tasks/Orochi/res"` |
| `direction` | `str` | 滑动方向，`"vertical"` 表示竖直，其他值表示水平 |
| `mode` | `str` | 识别模式，`"image"` 或 `"ocr"` |
| `roi_back` | `tuple` | 列表区域的 ROI（Region of Interest），格式 `(x, y, w, h)`，表示列表在屏幕上的矩形区域 |
| `size` | `tuple` | 单个列表项的尺寸，格式 `(width, height)` |
| `array` | `list[str]` | 列表中所有项目的名称有序数组（用于 OCR 模式下判断位置关系） |

**逐行解析**：

```python
# 第29行：保存图片资源文件夹路径
self.folder = folder

# 第30行：判断是否为竖直方向滑动，结果存储为布尔值
self.is_vertical = direction == "vertical"

# 第31行：判断是否为图片匹配模式
self.is_image = mode == "image"

# 第32行：判断是否为 OCR 识别模式
self.is_ocr = mode == "ocr"

# 第33行：将 ROI 元组转为列表存储，格式 [x, y, w, h]
self.roi_back: list = list(roi_back)

# 第34行：将单个项目尺寸元组转为列表存储，格式 [width, height]
self.size: list = list(size)
```

```python
# 第36行：计算当前可视区域能显示的最大列表项数量
# 竖直方向：ROI 高度 ÷ 单项高度 = 最大显示行数
# 水平方向：ROI 宽度 ÷ 单项宽度 = 最大显示列数
self.max_show: int = self.roi_back[3] // self.size[1] \
    if self.is_vertical else self.roi_back[2] // self.size[0]
```

**示例计算**：
```
ROI = (160, 130, 317, 500)  →  高度 = 500
size = (301, 86)             →  单项高度 = 86
max_show = 500 // 86 = 5     →  可同时显示 5 个项目
```

```python
# 第38行：保存列表所有项目的名称数组
self.array: list = array

# 以下是需要在运行时计算/更新的状态变量：

# 第41行：出现的区域（当前匹配到的区域），初始化为 None
self.appear_area: list = None

# 第42行：是否已滑动到底部的标志位
self.is_bottom = False

# 第43行：当前匹配的目标对象（RuleImage 或 RuleOcr 实例）
self._target = None

# 第44行：目标列表缓存字典，键为名称，值为 RuleImage 实例（仅 image 模式使用）
self.targets = {}
```

---

## 4. 每个方法的逐行解释

### 4.1 `name` 属性（第46-48行）

```python
@property
def name(self):
    return f'RuleList[{self.__hash__()}]'
```

- 使用 `@property` 装饰器将其定义为只读属性
- 返回一个包含哈希值的格式化字符串，用于唯一标识此 `RuleList` 实例
- 常用于日志输出中区分不同的列表实例

### 4.2 `__hash__` 方法（第50-51行）

```python
def __hash__(self):
    return hash((self.folder, self.is_vertical, self.is_image,
                 self.is_ocr, tuple(self.roi_back), tuple(self.size),
                 tuple(self.array)))
```

- 将所有关键配置参数组合为一个元组，计算其哈希值
- 使 `RuleList` 实例可哈希，可用于字典键或集合元素
- 相同配置的两个 `RuleList` 会产生相同的哈希值

### 4.3 `swipe_pos` 方法（第53-87行）—— 计算滑动位置

```python
def swipe_pos(self, number: int=2, after: bool=True) -> tuple:
```

**参数**：
- `number`：滑动距离为多少个列表项的长度，默认 2
- `after`：`True` 表示向后（下/右）滑动，`False` 表示向前（上/左）滑动

**返回值**：`(x1, y1, x2, y2)` 起始坐标和终点坐标

**逐行解析**：

```python
# 第60行：计算 ROI 区域的中心点坐标
# roi_back = [x, y, w, h]
# center_x = x + w//2, center_y = y + h//2
center: tuple = (self.roi_back[0] + self.roi_back[2]) // 2, \
                (self.roi_back[1] + self.roi_back[3]) // 2
```

```python
# 第61行：计算滑动距离（像素）
# 竖直方向：单项高度 × 滑动项数
# 水平方向：单项宽度 × 滑动项数
distance: int = self.size[1] * number if self.is_vertical \
                else self.size[0] * number
```

```python
# 第62-63行：生成随机偏移量，模拟真实手指滑动的不精确性
# 偏移范围为 ±单项宽度/高度的 1/4
random_start: int = randint(-self.size[0]//4, self.size[0]//4) \
    if self.is_vertical else randint(-self.size[1]//4, self.size[1]//4)
random_end: int = randint(-self.size[0]//4, self.size[0]//4) \
    if self.is_vertical else randint(-self.size[1]//4, self.size[1]//4)
```

```python
# 第65行：初始化四个坐标值
x1, y1, x2, y2 = None, None, None, None
```

```python
# 第66-74行：竖直方向滑动
if self.is_vertical:
    if after:
        # 向下滑动：手指从下往上滑（起点在下方，终点在上方）
        x1, y1 = center[0]+random_start, center[1] + distance//2
        x2, y2 = center[0]+random_end,   center[1] - distance//2
    else:
        # 向上滑动：手指从上往下滑（起点在上方，终点在下方）
        x1, y1 = center[0]+random_start, center[1] - distance//2
        x2, y2 = center[0]+random_end,   center[1] + distance//2
```

```python
# 第75-83行：水平方向滑动
else:
    if after:
        # 向右滑动：手指从右往左滑（起点在右侧，终点在左侧）
        x1, y1 = center[0] + distance//2, center[1]+random_start
        x2, y2 = center[0] - distance//2, center[1]+random_end
    else:
        # 向左滑动：手指从左往右滑（起点在左侧，终点在右侧）
        x1, y1 = center[0] - distance//2, center[1]+random_start
        x2, y2 = center[0] + distance//2, center[1]+random_end
```

```python
# 第85-87行：安全检查 + 返回整数坐标
if x1 is None or y1 is None or x2 is None or y2 is None:
    raise Exception("滑动位置计算错误")
return int(x1), int(y1), int(x2), int(y2)
```

> **注意**：这里的"滑动"是游戏自动化的术语。`after=True` 向后滑动意味着用户手指从屏幕下方滑到上方（竖直）或从右滑到左（水平），这会让列表**显示后面的内容**。与 Android 的 `swipe` 手势方向一致。

### 4.4 `target_check` 方法（第89-124行）—— 检查并构建匹配目标

```python
def target_check(self, name: str) -> bool:
```

**作用**：根据传入的名称，确保 `_target` 是正确的匹配器对象。如果当前 `_target` 不匹配，就重新构建。

**逐行解析**：

```python
# 第104行：拼接目标图片的完整路径
file = self.folder + "/" + name + ".png"
```

```python
# 第107-114行：image 模式下的目标检查
if self.is_image:
    # 如果 _target 为 None，或者当前 _target 是 RuleOcr（类型不对），则重新创建 RuleImage
    if self._target is None or isinstance(self._target, RuleOcr):
        self._target = RuleImage(
            roi_front=self.roi_back,
            roi_back=self.roi_back,
            method="Template matching",
            threshold=0.8,
            file=file
        )
    # 如果类型正确但名称不匹配，也需要重新构建
    elif self._target.name != name:
        self._target = RuleImage(
            roi_front=self.roi_back,
            roi_back=self.roi_back,
            method="Template matching",
            threshold=0.8,
            file=file
        )
    else:
        pass  # 当前 _target 已经是正确的目标，无需操作
```

```python
# 第115-121行：ocr 模式下的目标检查
elif self.is_ocr:
    # 如果 _target 为 None，或者当前 _target 是 RuleImage（类型不对），则重新创建 RuleOcr
    if self._target is None or isinstance(self._target, RuleImage):
        self._target = RuleOcr(
            roi=self.roi_back,
            area=(0, 0, 10, 10),
            mode="Full",
            method="Default",
            keyword=name,
            name=name
        )
    # 类型正确但名称不匹配时，直接更新属性（避免重新创建对象的开销）
    elif self._target.name != name:
        self._target.name = name
        self._target.keyword = name
```

```python
# 第122-124行：既不是 image 也不是 ocr 模式，记录错误并返回 False
else:
    logger.error(f'Not found {name} in {self.array}')
    return False
```

### 4.5 `targets_check` 方法（第126-138行）—— 批量缓存匹配目标

```python
def targets_check(self, targets: list):
```

**作用**：为一组目标名称批量创建 `RuleImage` 实例并缓存到 `self.targets` 字典中。避免重复创建。

**逐行解析**：

```python
# 第132行：遍历所有目标名称
for item in targets:
    # 第133行：如果已经缓存过，跳过
    if item in self.targets:
        continue
    # 第136行：拼接图片路径
    file = self.folder + "/" + item + ".png"
    # 第137-138行：创建 RuleImage 实例并存入缓存字典
    self.targets[item] = RuleImage(
        roi_front=self.roi_back,
        roi_back=self.roi_back,
        method="Template matching",
        threshold=0.8,
        file=file
    )
```

### 4.6 `image_appear` 方法（第140-164行）—— 图片模式下检测目标

```python
def image_appear(self, image: np.array, name: str) -> bool | tuple:
```

**参数**：
- `image`：屏幕截图（NumPy 数组）
- `name`：要查找的目标名称（字符串）或名称列表

**返回值**：
- 找到时返回可点击坐标 `(x, y)` 的元组
- 未找到返回 `False`

**逐行解析**：

```python
# 第147-153行：单个目标查找（name 为字符串）
if self.is_image and isinstance(name, str):
    self.target_check(name)              # 确保 _target 正确
    appear = self._target.match(image)   # 执行模板匹配
    if appear:
        return self._target.coord()      # 匹配成功，返回可点击坐标
    else:
        return False                     # 匹配失败
```

```python
# 第154-160行：多个目标查找（name 为列表）
elif self.is_image and isinstance(name, list):
    self.targets_check(name)             # 批量缓存所有目标
    for item in name:                    # 逐个尝试匹配
        appear = self.targets[item].match(image)
        if appear:
            return self.targets[item].coord()  # 找到第一个匹配的就返回
    return False                         # 全部未匹配
```

```python
# 第162-164行：非 image 模式的错误处理
else:
    logger.error(f'Mode is not image')
    return False
```

### 4.7 `ocr_appear` 方法（第166-233行）—— OCR 模式下检测目标（核心方法）

```python
def ocr_appear(self, image: np.array, name: str):
```

**参数**：
- `image`：屏幕截图
- `name`：要查找的文字

**返回值**（三种情况）：
1. `(x, y)` 元组：目标在当前可视区域内，返回可点击坐标
2. 负整数：目标在当前可视区域**之前**（需要向上/向前滑动）
3. 正整数：目标在当前可视区域**之后**（需要向下/向后滑动）
4. `0, 0`：OCR 未识别到任何结果
5. `2`：识别到的文字不在预定义的 array 中

**逐行解析**：

```python
# 第174-175行：非 OCR 模式直接返回 False
if self.is_image:
    return False

# 第176行：确保 OCR 目标正确
self.target_check(name)
```

```python
# 第179行：执行 OCR 识别，获取所有识别结果列表
# boxed_results 中每个元素包含：ocr_text（文字）、score（置信度）、box（边界框坐标）
boxed_results: list[BoxedResult] = self._target.detect_and_ocr(image)

# 第180-182行：如果没有识别到任何文字，返回 (0, 0)
if not boxed_results:
    logger.warning(f'Not angy result in image')
    return 0, 0
```

```python
# 第187-191行：遍历所有 OCR 结果，精确匹配目标文字
box = None
for item in boxed_results:
    # 匹配条件：文字完全相同 且 置信度大于阈值
    if item.ocr_text == name and item.score > RuleOcr.score:
        box = item.box   # 获取边界框坐标（4个角的坐标）
        break
```

```python
# 第192-197行：找到了目标文字
if box is not None:
    # box 是 4×2 的数组，表示矩形 4 个顶点坐标
    # box[0] = 左上角, box[1] = 右上角, box[2] = 右下角, box[3] = 左下角
    rec_x = box[0, 0]                    # 左上角 x
    rec_y = box[0, 1]                    # 左上角 y
    rec_w = box[1, 0] - box[0, 0]       # 宽度 = 右上角x - 左上角x
    rec_h = box[2, 1] - box[0, 1]       # 高度 = 右下角y - 左上角y

    # 计算中心点坐标（加上 ROI 的偏移量，转换为屏幕绝对坐标）
    x = rec_x + rec_w // 2 + self.roi_back[0]
    y = rec_y + rec_h // 2 + self.roi_back[1]

    logger.info(f'Ocr {name} appear in current screen, do not need to scroll')
    return x, y   # 返回可点击的中心坐标
```

```python
# 第205-233行：未找到目标文字，需要判断滑动方向

# 第206行：提取所有置信度合格的文字列表
keyword_list: list = [item.ocr_text for item in boxed_results
                      if item.score > RuleOcr.score]

# 第209行：过滤，只保留属于预定义 array 中的文字
keyword_list = [keyword for keyword in keyword_list
                if keyword in self.array]

# 第210行：日志输出当前可视区域识别到的文字
logger.info(f'After list: {keyword_list}')

# 第211-213行：如果可视区域没有识别到任何已知列表项，返回 2（异常情况）
if not keyword_list:
    logger.warning(f'Not found {name} in {self.array}')
    return 2
```

```python
# 第215-216行：获取可视区域内第一个和最后一个识别项在 array 中的索引
start_index = self.array.index(keyword_list[0])
end_index = self.array.index(keyword_list[-1])
```

```python
# 第217-219行：这个条件判断块有逻辑问题（后面会详述）
if name in keyword_list:
    distance_start = 0
    distance_end = 0
```

```python
# 第221行：获取目标在 array 中的索引
current_index = self.array.index(name)

# 第222-223行：初始化距离值
distance_start = 0
distance_end = 0

# 第224-226行：如果目标不在当前可视范围的索引区间内，计算距离
if current_index < start_index or current_index > end_index:
    distance_start = current_index - start_index  # 与可视起始项的距离
    distance_end = current_index - end_index      # 与可视结束项的距离
```

```python
# 第230-231行：如果距离都为 0 但目标不在 keyword_list 中，记录错误
if distance_start == 0 and distance_end == 0:
    logger.error(f'{name} not found in {keyword_list}')

# 第233行：返回平均距离
# 负值 → 目标在可视区域前面（需要向上/向前滑动）
# 正值 → 目标在可视区域后面（需要向下/向后滑动）
return (distance_start + distance_end) // 2
```

> **代码注意**：第217-219行的 `if name in keyword_list` 分支设置了 `distance_start = 0` 和 `distance_end = 0`，但没有 `return`，会继续执行到第221行。这意味着即使 `name` 在 `keyword_list` 中，`distance_start` 和 `distance_end` 也会在第224行被重新赋值。这可能是一个**潜在的逻辑 bug**——如果目标已在可视区域内，本应提前返回坐标，但此处已被上面的 `box is not None` 分支覆盖（因为该分支已处理了"找到"的情况）。

---

## 5. 核心算法流程图

### 5.1 `ocr_appear` 完整流程

```
开始 ocr_appear(image, name)
│
├── 模式检查：is_image? ──→ return False
│
├── target_check(name)  ← 确保 OCR 目标正确
│
├── detect_and_ocr(image)  ← 执行 OCR 识别
│   │
├── 识别结果为空? ──→ return (0, 0)
│
├── 遍历识别结果，查找 name
│   │
│   ├── [找到] ──→ 计算中心坐标 ──→ return (x, y)
│   │
│   └── [未找到] ──→ 提取可视区域的文字列表
│       │
│       ├── 过滤：只保留在 array 中的文字
│       │
│       ├── 过滤结果为空? ──→ return 2（异常）
│       │
│       ├── 获取可视区域在 array 中的索引范围 [start, end]
│       │
│       ├── 获取目标在 array 中的索引 current
│       │
│       ├── 计算距离：
│       │   distance_start = current - start
│       │   distance_end = current - end
│       │
│       └── return (distance_start + distance_end) // 2
│           ├── 负值 → 目标在前面，向上滑
│           └── 正值 → 目标在后面，向下滑
│
结束
```

### 5.2 滑动位置计算流程

```
开始 swipe_pos(number, after)
│
├── 计算 ROI 中心点 center
│
├── 计算滑动距离 distance = size × number
│
├── 生成随机偏移 random_start, random_end
│
├── 判断方向：
│   │
│   ├── 竖直(vertical)：
│   │   ├── after=True  → 起点在下，终点在上（向后滑）
│   │   └── after=False → 起点在上，终点在下（向前滑）
│   │
│   └── 水平(horizontal)：
│       ├── after=True  → 起点在右，终点在左（向后滑）
│       └── after=False → 起点在左，终点在右（向前滑）
│
├── 安全检查（坐标不为 None）
│
└── return (x1, y1, x2, y2)
```

### 5.3 自动滚动查找目标的完整使用流程

```
用户调用方代码流程：

初始化 RuleList
│
├── 循环（最多 N 次）：
│   │
│   ├── 截图 image
│   │
│   ├── result = ocr_appear(image, target_name)
│   │
│   ├── isinstance(result, tuple)?
│   │   └── [是] → 找到了！点击 (x, y) → break
│   │
│   ├── result < 0?
│   │   └── [是] → 目标在前面 → swipe_pos(after=False) → 向前滑
│   │
│   ├── result > 0?
│   │   └── [是] → 目标在后面 → swipe_pos(after=True) → 向后滑
│   │
│   └── result == 0 or result == 2?
│       └── [是] → 未识别到 → 尝试默认滑动 / 报错
│
结束
```

---

## 6. 使用示例

### 6.1 基本用法（OCR 模式）

```python
import cv2
from module.atom.list import RuleList

# 创建 RuleList 实例
# 场景：阴阳师副本列表，竖直滚动，OCR 识别模式
rule_list = RuleList(
    folder="./tasks/Orochi/res",           # 图片资源文件夹
    direction="vertical",                   # 竖直滚动
    mode="ocr",                             # OCR 识别模式
    roi_back=(160, 130, 317, 500),          # 列表区域 (x, y, w, h)
    size=(301, 86),                         # 单项尺寸 (w, h)
    array=["壹层", "贰层", "叁层", "肆层",   # 所有列表项（有序）
           "伍层", "陆层", "柒层", "捌层",
           "玖层", "拾层", "悲鸣", "神罚"]
)

# 读取屏幕截图
image = cv2.imread("screenshot.png")

# 检测目标是否在当前可视区域
result = rule_list.ocr_appear(image, "柒层")

if isinstance(result, tuple):
    # 找到了，result 是可点击坐标
    x, y = result
    print(f"目标位置: ({x}, {y})")
elif isinstance(result, int):
    if result < 0:
        # 目标在前面，需要向上滑动
        x1, y1, x2, y2 = rule_list.swipe_pos(number=2, after=False)
        print(f"向前滑动: ({x1},{y1}) → ({x2},{y2})")
    elif result > 0:
        # 目标在后面，需要向下滑动
        x1, y1, x2, y2 = rule_list.swipe_pos(number=2, after=True)
        print(f"向后滑动: ({x1},{y1}) → ({x2},{y2})")
```

### 6.2 图片匹配模式

```python
from module.atom.list import RuleList

# 创建图片模式的 RuleList
skill_list = RuleList(
    folder="./tasks/Skill/res",
    direction="vertical",
    mode="image",                           # 图片匹配模式
    roi_back=(100, 200, 400, 600),
    size=(350, 100),
    array=["skill_01", "skill_02", "skill_03"]
)

image = cv2.imread("screenshot.png")

# 单目标匹配
result = skill_list.image_appear(image, "skill_01")

# 多目标匹配（返回第一个匹配到的）
result = skill_list.image_appear(image, ["skill_01", "skill_02", "skill_03"])
```

### 6.3 自动滚动查找的完整循环

```python
from module.atom.list import RuleList
import cv2
import time

rule_list = RuleList(
    folder="./tasks/Orochi/res",
    direction="vertical",
    mode="ocr",
    roi_back=(160, 130, 317, 500),
    size=(301, 86),
    array=["壹层", "贰层", "叁层", "肆层", "伍层",
           "陆层", "柒层", "捌层", "玖层", "拾层",
           "悲鸣", "神罚"]
)

target = "神罚"
max_scroll = 10  # 最大滑动次数

for i in range(max_scroll):
    image = capture_screen()  # 截取屏幕（伪函数）
    result = rule_list.ocr_appear(image, target)

    if isinstance(result, tuple):
        x, y = result
        click(x, y)  # 点击目标（伪函数）
        print(f"成功点击 {target}，位于 ({x}, {y})")
        break
    elif isinstance(result, int) and result != 0:
        direction = result > 0  # True=向后滑，False=向前滑
        pos = rule_list.swipe_pos(number=2, after=direction)
        swipe(*pos)  # 执行滑动（伪函数）
        time.sleep(0.5)  # 等待滑动动画
    else:
        print(f"第 {i+1} 次尝试未找到 {target}")
```

---

## 7. 设计模式总结

### 7.1 策略模式（Strategy Pattern）

`RuleList` 通过 `mode` 参数（`"image"` / `"ocr"`）在运行时选择不同的识别策略：

```
         ┌─────────────┐
         │  RuleList    │
         │  mode: str   │
         └──────┬───────┘
                │
       ┌────────┴────────┐
       ▼                  ▼
 ┌──────────┐      ┌──────────┐
 │ RuleImage │      │  RuleOcr  │
 │ 模板匹配  │      │ 文字识别   │
 └──────────┘      └──────────┘
```

### 7.2 缓存模式（Caching Pattern）

- `_target`：单目标缓存，只在名称变化时重建
- `targets`：多目标缓存字典，按需创建并持久化

```python
# 单目标缓存策略：类型检查 + 名称检查
if self._target is None or isinstance(self._target, RuleOcr):
    self._target = RuleImage(...)       # 类型不对，重建
elif self._target.name != name:
    self._target = RuleImage(...)       # 名称不对，重建
else:
    pass                                # 命中缓存，跳过
```

### 7.3 位置索引模式（Index-Based Position Detection）

OCR 模式下通过 **array 索引差值** 判断目标位置，而非像素坐标：

```
array = [A, B, C, D, E, F, G, H]
              ↑ 可视区域 ↑
              [C, D, E]

目标 = H → index(H) - index(E) = +3 → 目标在后面
目标 = A → index(A) - index(C) = -2 → 目标在前面
```

### 7.4 随机化防检测

滑动坐标加入随机偏移，模拟人类操作的不精确性：

```python
random_start = randint(-size//4, size//4)  # ±25% 单项尺寸的随机偏移
```

### 7.5 统一接口模式

无论 `image` 模式还是 `ocr` 模式，对外暴露统一的方法签名：
- `image_appear(image, name)` → `bool | tuple`
- `ocr_appear(image, name)` → `tuple | int`

调用方无需关心底层识别方式。

### 7.6 文件结构总结

```
RuleList
│
├── 配置属性
│   ├── folder          图片资源路径
│   ├── is_vertical     滑动方向
│   ├── is_image        图片模式标志
│   ├── is_ocr          OCR 模式标志
│   ├── roi_back        列表区域
│   ├── size            单项尺寸
│   ├── max_show        最大显示数量
│   └── array           列表项名称数组
│
├── 状态属性
│   ├── _target         当前匹配目标（单例缓存）
│   ├── targets         目标缓存字典（多例缓存）
│   ├── appear_area     出现区域
│   └── is_bottom       是否到底
│
└── 方法
    ├── name            唯一标识（property）
    ├── __hash__        哈希值计算
    ├── swipe_pos()     计算滑动坐标
    ├── target_check()  单目标校验与构建
    ├── targets_check() 多目标批量缓存
    ├── image_appear()  图片模式检测
    └── ocr_appear()    OCR 模式检测（核心）
```
