# module/ocr/base_ocr.py 代码详解

## 1. 文件概述

`base_ocr.py` 是 OCR 模块的基础核心文件，定义了 OCR 识别的基类 `BaseCor` 和相关的枚举类型。该文件提供了：
- 图像预处理工具函数 `enlarge_canvas`
- OCR 模式枚举 `OcrMode`（全文、单行、数字等模式）
- OCR 方法枚举 `OcrMethod`
- 基类 `BaseCor`，封装了 OCR 识别的核心流程（裁剪、预处理、识别、后处理、匹配）

该文件的设计采用了**模板方法模式**，基类定义了 OCR 的标准流程，子类可以重写 `pre_process` 和 `after_process` 来定制行为。

---

## 2. 导入部分解释

```python
import time          # 用于计时，记录 OCR 处理耗时
import cv2           # OpenCV 库，用于图像处理（裁剪、添加边框等）
import numpy as np   # NumPy 库，用于数组操作，OpenCV 图像本质是 NumPy 数组

from ppocronnx.predict_system import BoxedResult  # PaddleOCR ONNX 推理结果的数据类，包含 box、ocr_text、score
from enum import Enum  # 枚举基类

from module.base.decorator import cached_property  # 自定义的缓存属性装饰器，实现懒加载和缓存
from module.base.utils import area_pad, crop, float2str  # 工具函数：区域扩展、裁剪、浮点数转字符串
from typing import Any  # 类型注解

from module.ocr.models import get_ocr_model  # 获取 OCR 模型的工厂函数
from module.exception import ScriptError      # 自定义脚本异常
from module.logger import logger              # 日志记录器
```

---

## 3. 类定义解释

### 3.1 `OcrMode` 枚举类

```python
class OcrMode(Enum):
    FULL = 1           # 全文模式：识别整个区域的所有文本
    SINGLE = 2         # 单行模式：识别单行文本
    DIGIT = 3          # 数字模式：只识别数字
    DIGITCOUNTER = 4   # 数字计数器模式：识别 "14/15" 格式
    DURATION = 5       # 时长模式：识别 "01:30:00" 格式
    QUANTITY = 6       # 数量模式：识别带单位的大数字如 "6.33亿"
```

**用途**：不同模式决定了 OCR 结果的后处理方式。

### 3.2 `OcrMethod` 枚举类

```python
class OcrMethod(Enum):
    DEFAULT = 1  # 默认方法（占位符，预留扩展）
```

**用途**：预留的 OCR 方法选择，当前只有默认方法。

### 3.3 `BaseCor` 基类

```python
class BaseCor:
    # 类属性
    lang: str = "ch"                    # 语言，默认中文
    score: float = 0.6                  # 置信度阈值，低于此值的结果被丢弃
    min_score: float = 0.3             # 宽松阈值，用于挽救包含数字的结果
    
    name: str = "ocr"                   # OCR 实例名称，用于日志标识
    mode: OcrMode = OcrMode.FULL       # OCR 模式
    method: OcrMethod = OcrMethod.DEFAULT  # OCR 方法
    roi: list = []                      # 感兴趣区域 [x, y, width, height]
    area: list = []                     # 检测到的文本区域
    keyword: str = ""                   # 匹配关键字
```

---

## 4. 每个方法的逐行解释

### 4.1 `enlarge_canvas(image)` 函数

```python
def enlarge_canvas(image):
    """
    将图像放大为正方形，填充黑色背景。
    PaddleOCR 在 w:h=1:1 的图像上性能最佳，3:1 的矩形需要 3 倍时间。
    同时放大到 32 的整数倍，因为 PaddleOCR 会将图像缩小 1/32。
    """
    height, width = image.shape[:2]  # 获取图像高度和宽度
    # 计算目标边长：取宽高的最大值，向下取整到 32 的倍数，再加 32
    length = int(max(width, height) // 32 * 32 + 32)
    # 计算四个方向需要添加的边框宽度：(上, 下, 左, 右)
    border = (0, length - height, 0, length - width)
    if sum(border) > 0:  # 如果需要添加边框
        # 使用 OpenCV 添加黑色边框
        image = cv2.copyMakeBorder(image, *border, borderType=cv2.BORDER_CONSTANT, value=(0, 0, 0))
    return image
```

**算法流程**：
1. 获取图像尺寸
2. 计算目标正方形边长（32 的整数倍）
3. 计算需要填充的边框大小
4. 使用黑色填充使图像变为正方形

### 4.2 `BaseCor.__init__` 构造方法

```python
def __init__(self,
             name: str,      # OCR 实例名称
             mode: str,      # OCR 模式（字符串或枚举）
             method: str,    # OCR 方法（字符串或枚举）
             roi: tuple,     # 感兴趣区域 (x, y, w, h)
             area: tuple,    # 初始区域
             keyword: str) -> None:  # 匹配关键字
    self.name = name.upper()  # 名称转大写
    
    # 处理 mode 参数：支持字符串和枚举两种输入
    if isinstance(mode, str):
        self.mode = OcrMode[mode.upper()]  # 字符串转枚举
    elif isinstance(mode, OcrMode):
        self.mode = mode  # 直接使用枚举
    
    # 处理 method 参数：同上
    if isinstance(method, str):
        self.method = OcrMethod[method.upper()]
    elif isinstance(method, OcrMethod):
        self.method = method
    
    self.roi: list = list(roi)      # 转为列表存储
    self.area: list = list(area)
    self.keyword = keyword
```

### 4.3 `model` 缓存属性

```python
@cached_property
def model(self) -> Any:
    return get_ocr_model(self.lang)  # 懒加载 OCR 模型，首次访问时创建并缓存
```

**设计说明**：使用 `@cached_property` 装饰器实现单例模式，避免重复创建模型实例。

### 4.4 `pre_process` 和 `after_process` 钩子方法

```python
def pre_process(self, image):
    """图像预处理钩子，子类可重写以添加自定义预处理逻辑"""
    return image  # 默认直接返回原图

def after_process(self, result):
    """结果后处理钩子，子类可重写以添加自定义后处理逻辑"""
    return result  # 默认直接返回原结果
```

### 4.5 `crop` 类方法

```python
@classmethod
def crop(cls, image: np.array, roi: tuple) -> np.array:
    """
    根据 ROI 裁剪图像
    :param roi: (x, y, width, height) 格式的区域
    :param image: 输入图像
    :return: 裁剪后的图像
    """
    x, y, w, h = roi
    return image[y:y + h, x:x + w]  # NumPy 数组切片：[y范围, x范围]
```

### 4.6 `ocr_item` 方法

```python
def ocr_item(self, image):
    """
    识别图像中的文本（不裁剪，直接识别整张图）
    与 ocr_single_line 的区别：不对图像进行裁剪
    """
    start_time = time.time()          # 记录开始时间
    image = self.pre_process(image)   # 预处理
    
    result, score = self.model.ocr_single_line(image)  # 调用模型进行单行 OCR
    if score < self.score:            # 置信度低于阈值
        result = ""                   # 结果置空
    
    result = self.after_process(result)  # 后处理
    
    # 记录日志：名称 + 耗时 + 结果
    logger.attr(name='%s %ss' % (self.name, float2str(time.time() - start_time)),
                text=f'[{result}]')
    return result
```

### 4.7 `ocr_single_line` 方法

```python
def ocr_single_line(self, image):
    """
    单行 OCR 识别（只支持横向文本）
    流程：裁剪 -> 预处理 -> OCR -> 置信度过滤 -> 后处理
    """
    start_time = time.time()
    image = self.crop(image, self.roi)      # 步骤1：根据 ROI 裁剪
    image = self.pre_process(image)          # 步骤2：预处理
    
    result, score = self.model.ocr_single_line(image)  # 步骤3：OCR 识别
    contains_digit = any(char.isdigit() for char in result)  # 检查是否包含数字
    
    # 步骤4：置信度过滤
    if score >= self.score:
        pass  # 置信度足够，保留结果
    elif score >= self.min_score and contains_digit and self.mode in [
        OcrMode.DIGIT, OcrMode.DIGITCOUNTER, OcrMode.QUANTITY
    ]:
        # 置信度较低但包含数字，且是数字相关模式，保留结果并警告
        logger.warning(f'[{self.name}] Score {score:.2f} is low, but result "{result}" contains a digit. Accepting it.')
    else:
        result = ""  # 置信度不足，丢弃结果
    
    result = self.after_process(result)  # 步骤5：后处理
    
    logger.attr(name='%s %ss' % (self.name, float2str(time.time() - start_time)),
                text=f'[{result}]')
    return result
```

**关键逻辑**：对于数字相关的模式，即使置信度较低，只要结果包含数字就保留，这是为了提高数字识别的召回率。

### 4.8 `detect_and_ocr` 方法

```python
def detect_and_ocr(self, image, logDisplay: bool = True) -> list[BoxedResult]:
    """
    检测并识别图像中的所有文本
    返回 BoxedResult 列表，每个包含：box（坐标）、ocr_text（文本）、score（置信度）
    """
    start_time = time.time()
    image = self.crop(image, self.roi)      # 裁剪
    image = self.pre_process(image)          # 预处理
    image = enlarge_canvas(image)            # 放大为正方形（优化 OCR 性能）
    
    boxed_results: list[BoxedResult] = self.model.detect_and_ocr(image)  # 检测并识别
    results = []
    
    for result in boxed_results:
        if result.score < self.score:        # 过滤低置信度结果
            continue
        result.ocr_text = self.after_process(result.ocr_text)  # 后处理每个结果
        results.append(result)
    
    if logDisplay:
        # 记录日志
        logger.attr(name='%s %ss' % (self.name, float2str(time.time() - start_time)),
                    text=str([result.ocr_text for result in results]))
    return results
```

### 4.9 `match` 方法

```python
def match(self, result: str, included: bool=False) -> bool:
    """
    将 OCR 结果与关键字进行匹配
    :param result: OCR 识别结果
    :param included: True=包含关系，False=相等关系
    """
    if included:
        return self.keyword in result  # 关键字是否在结果中
    else:
        return self.keyword == result  # 结果是否完全等于关键字
```

### 4.10 `filter` 方法

```python
def filter(self, boxed_results: list[BoxedResult], keyword: str=None) -> list or None:
    """
    从多个 OCR 结果中过滤出包含关键字的结果
    返回匹配结果的索引列表，无匹配返回 None
    """
    strings = [boxed_result.ocr_text for boxed_result in boxed_results]  # 提取所有文本
    concatenated_string = "".join(strings)  # 拼接所有文本
    
    if keyword is None:
        keyword = self.keyword
    
    # 策略1：在拼接后的字符串中匹配
    if keyword in concatenated_string:
        result = [index for index, word in enumerate(strings) if keyword in word]
    else:
        result = None
    
    if result is not None:
        return result
    
    # 策略2：逐字符匹配（处理竖排文本）
    indices = []
    max_index = len(strings) - 1
    for index, char in enumerate(keyword):
        for i, string in enumerate(strings):
            if char not in string:
                continue
            if i <= max_index:
                indices.append(i)
                break
    
    if indices:
        indices = list(set(indices))  # 去重
        return indices
    else:
        return None
```

**设计说明**：先尝试整体匹配，失败后逐字符匹配，后者是为了处理竖排文本被拆分成多个识别结果的情况。

### 4.11 `detect_text` 方法

```python
def detect_text(self, image) -> str:
    """
    识别图像中的所有文本，按顺序拼接返回
    """
    start_time = time.time()
    image = self.crop(image, self.roi)
    image = self.pre_process(image)
    image = enlarge_canvas(image)
    
    boxed_results: list[BoxedResult] = self.model.detect_and_ocr(image)
    results = ''
    
    for result in boxed_results:
        if result.score < self.score:
            continue
        results += result.ocr_text  # 拼接所有文本
    
    logger.attr(name='%s %ss' % (self.name, float2str(time.time() - start_time)),
                text=f'[{results}]')
    return results
```

---

## 5. 核心算法流程图

### 5.1 单行 OCR 流程 (`ocr_single_line`)

```
输入图像
    │
    ▼
┌─────────────────┐
│  根据 ROI 裁剪   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    预处理        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  OCR 模型识别    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 置信度 >= 0.6?  │──是──▶ 保留结果
└────────┬────────┘
         │否
         ▼
┌─────────────────────────────────────┐
│ 置信度 >= 0.3 且包含数字             │
│ 且模式为 DIGIT/DIGITCOUNTER/QUANTITY?│──是──▶ 保留结果（警告）
└────────┬────────────────────────────┘
         │否
         ▼
    丢弃结果（返回空）
         │
         ▼
┌─────────────────┐
│    后处理        │
└────────┬────────┘
         │
         ▼
    返回结果
```

### 5.2 多文本检测流程 (`detect_and_ocr`)

```
输入图像
    │
    ▼
┌─────────────────┐
│  根据 ROI 裁剪   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    预处理        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  放大为正方形    │  ← optimize: 1:1 比例性能最佳
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  检测并识别所有  │
│     文本区域     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 过滤低置信度结果 │  ← threshold: 0.6
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  对每个结果      │
│  执行后处理      │
└────────┬────────┘
         │
         ▼
    返回结果列表
```

### 5.3 关键字匹配流程 (`filter`)

```
输入: boxed_results, keyword
    │
    ▼
┌─────────────────┐
│  拼接所有文本    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 拼接串中包含     │
│    keyword?      │──是──▶ 返回匹配的索引列表
└────────┬────────┘
         │否
         ▼
┌─────────────────┐
│  逐字符匹配      │  ← 处理竖排文本
│  (keyword 每个字 │
│   在 strings 中  │
│   查找)          │
└────────┬────────┘
         │
         ▼
    返回索引列表或 None
```

---

## 6. 使用示例

### 6.1 基本使用

```python
from module.ocr.base_ocr import BaseCor, OcrMode
import cv2

# 创建 OCR 实例
ocr = BaseCor(
    name="test_ocr",
    mode="SINGLE",
    method="DEFAULT",
    roi=(100, 200, 300, 50),  # x=100, y=200, width=300, height=50
    area=(0, 0, 0, 0),
    keyword="确认"
)

# 读取图像
image = cv2.imread("screenshot.png")

# 单行识别
text = ocr.ocr_single_line(image)
print(f"识别结果: {text}")

# 检测并识别所有文本
results = ocr.detect_and_ocr(image)
for r in results:
    print(f"文本: {r.ocr_text}, 置信度: {r.score}, 位置: {r.box}")
```

### 6.2 关键字匹配

```python
# 假设已识别到多个文本框
results = ocr.detect_and_ocr(image)

# 过滤包含关键字的结果
indices = ocr.filter(results, keyword="探索")
if indices:
    print(f"在索引 {indices} 处找到关键字")
    for i in indices:
        print(f"  位置: {results[i].box}")
```

### 6.3 自定义子类

```python
class CustomOcr(BaseCor):
    def pre_process(self, image):
        """自定义预处理：灰度化 + 二值化"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
        return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    
    def after_process(self, result):
        """自定义后处理：去除空格和换行"""
        return result.strip().replace('\n', '')
```

---

## 7. 设计模式总结

| 设计模式 | 应用位置 | 说明 |
|---------|---------|------|
| **模板方法模式** | `BaseCor` 类 | 基类定义 OCR 标准流程（裁剪→预处理→识别→后处理），子类通过重写 `pre_process` 和 `after_process` 定制行为 |
| **策略模式** | `OcrMode` 枚举 | 不同的 OCR 模式对应不同的后处理策略 |
| **单例模式（懒加载）** | `@cached_property model` | 模型实例只在首次访问时创建，后续访问返回缓存 |
| **工厂模式** | `get_ocr_model` | 通过语言参数获取对应的 OCR 模型 |
| **钩子方法模式** | `pre_process` / `after_process` | 提供扩展点，子类可以插入自定义逻辑 |

### 核心设计思想

1. **关注点分离**：将 OCR 流程分解为裁剪、预处理、识别、后处理四个独立步骤
2. **开闭原则**：通过钩子方法实现扩展，无需修改基类代码
3. **容错设计**：使用双阈值（严格阈值 + 宽松阈值）提高数字识别的召回率
4. **性能优化**：`enlarge_canvas` 将图像调整为 1:1 正方形，显著提升 PaddleOCR 性能
