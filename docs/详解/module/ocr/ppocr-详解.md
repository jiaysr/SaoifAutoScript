# module/ocr/ppocr.py 代码详解

## 1. 文件概述

`ppocr.py` 是 PaddleOCR ONNX 推理引擎的封装文件，主要功能：

1. **TextSystem 类**：继承自 `ppocronnx.predict_system.TextSystem`，提供 OCR 识别的核心能力
2. **sorted_boxes 函数**：优化文本框排序算法，替换 ppocr-onnx 库中的默认实现

该文件是整个 OCR 模块的底层引擎，负责实际的文本检测和识别。

---

## 2. 导入部分解释

```python
import ppocronnx.predict_system  # PaddleOCR ONNX 推理库
                                 # 提供文本检测和识别的完整流程
```

**依赖说明**：`ppocronnx` 是 PaddleOCR 的 ONNX Runtime 版本，相比原版 PaddleOCR：
- 更轻量，不需要 PaddlePaddle 框架
- 推理速度更快
- 内存占用更小

---

## 3. 类定义解释

### 3.1 `TextSystem` 类

```python
class TextSystem(ppocronnx.predict_system.TextSystem):
    """
    继承自 ppocronnx 的 TextSystem，提供 OCR 识别能力
    
    功能：
    - 文本检测：定位图像中的文本区域
    - 文本识别：识别文本区域中的文字
    - 单行识别：快速识别单行文本
    """
    
    def __init__(
            self,
            use_angle_cls=False,      # 是否使用角度分类器（检测文本方向）
            box_thresh=0.6,           # 文本框置信度阈值
            unclip_ratio=1.6,         # 文本框扩展比例
            rec_model_path=None,      # 识别模型路径（默认使用内置模型）
            det_model_path=None,      # 检测模型路径（默认使用内置模型）
            ort_providers=None        # ONNX Runtime 执行提供者
    ):
        super().__init__(
            use_angle_cls=use_angle_cls,
            box_thresh=box_thresh,
            unclip_ratio=unclip_ratio,
            rec_model_path=rec_model_path,
            det_model_path=det_model_path,
            ort_providers=ort_providers
        )
```

**参数说明**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `use_angle_cls` | `False` | 是否启用角度分类。启用后可以识别旋转文本，但会增加推理时间 |
| `box_thresh` | `0.6` | 文本框置信度阈值。低于此值的文本框会被过滤 |
| `unclip_ratio` | `1.6` | 文本框扩展比例。值越大，文本框越宽松 |
| `rec_model_path` | `None` | 识别模型路径。None 时使用 ppocronnx 内置的中文模型 |
| `det_model_path` | `None` | 检测模型路径。None 时使用 ppocronnx 内置的检测模型 |
| `ort_providers` | `None` | ONNX Runtime 执行提供者。可选 ['CUDAExecutionProvider', 'CPUExecutionProvider'] |

**继承说明**：当前类没有添加额外方法，主要是为了：
1. 提供统一的接口入口
2. 预留未来扩展点
3. 便于 monkey-patch 排序函数

---

## 4. 每个方法的逐行解释

### 4.1 `sorted_boxes` 函数

```python
def sorted_boxes(dt_boxes):
    """
    对文本框进行排序：从上到下，从左到右
    
    参数:
        dt_boxes(array): 检测到的文本框，形状为 [N, 4, 2]
                         N 个文本框，每个框 4 个顶点，每个顶点 (x, y)
    
    返回:
        sorted_boxes(array): 排序后的文本框，形状相同
    
    排序规则：
    1. 首先按 y 坐标（行位置）排序
    2. 同一行内按 x 坐标（列位置）排序
    """
    num_boxes = dt_boxes.shape[0]  # 获取文本框数量
    
    # 第一步：按左上角顶点排序 (y, x)
    sorted_boxes = sorted(dt_boxes, key=lambda x: (x[0][1], x[0][0]))
    _boxes = list(sorted_boxes)
    
    # 第二步：修正同行内的顺序
    # 使用插入排序思想，对相邻文本框进行微调
    for i in range(num_boxes - 1):
        for j in range(i, -1, -1):  # 向前遍历
            # 判断是否在同一行（y 坐标差值 < 10 像素）
            if abs(_boxes[j + 1][0][1] - _boxes[j][0][1]) < 10 and \
                    (_boxes[j + 1][0][0] < _boxes[j][0][0]):
                # 同一行且右边的框在左边，交换位置
                tmp = _boxes[j]
                _boxes[j] = _boxes[j + 1]
                _boxes[j + 1] = tmp
            else:
                break  # 不在同一行或已有序，停止
    return _boxes
```

**算法详解**：

1. **主排序**：使用 Python 的 `sorted` 函数，按 `(y, x)` 元组排序
   - `x[0][1]`：左上角顶点的 y 坐标（行位置）
   - `x[0][0]`：左上角顶点的 x 坐标（列位置）

2. **微调排序**：处理同一行内的文本框
   - 判断条件：`abs(y1 - y2) < 10`（同一行）
   - 交换条件：右边的框 x 坐标更小（顺序错误）
   - 使用插入排序思想，从后向前修正

**为什么需要微调**：
- 主排序使用的是左上角顶点，但对于倾斜或不规则的文本框，左上角可能不是最佳参考点
- 微调可以处理同一行内文本框的轻微上下偏移

### 4.2 Monkey-Patch 排序函数

```python
# 使用 PaddleOCR 2.6 版本的 sorted_boxes 替换 ppocr-onnx 中的实现
# 新版本的排序算法更准确，特别是在处理多行文本时
ppocronnx.predict_system.sorted_boxes = sorted_boxes
```

**设计说明**：
- `ppocronnx` 库内部使用 `sorted_boxes` 函数对检测到的文本框排序
- 通过 monkey-patch 替换为更优的实现
- 这是一种常见的优化策略，无需修改第三方库源码

---

## 5. 核心算法流程图

### 5.1 OCR 识别流程（TextSystem 继承的方法）

```
输入图像
    │
    ▼
┌─────────────────────────────────────┐
│         文本检测 (Detection)         │
│  使用检测模型定位文本区域            │
│  输出: dt_boxes [N, 4, 2]           │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│         文本框排序                   │
│  使用 sorted_boxes 进行排序          │
│  从上到下，从左到右                  │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│         文本框裁剪                   │
│  从原图中裁剪出每个文本区域          │
│  输出: img_crop_list [N, H, W, C]   │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│         文本识别 (Recognition)       │
│  使用识别模型识别每个裁剪区域        │
│  输出: rec_res [(text, score), ...] │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│         结果整合                     │
│  合并 boxes、texts、scores          │
│  输出: BoxedResult 列表             │
└─────────────────────────────────────┘
```

### 5.2 排序算法流程 (`sorted_boxes`)

```
输入: dt_boxes [N, 4, 2]
    │
    ▼
┌─────────────────┐
│  获取框数量 N    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  主排序: sorted(key=(y, x))         │
│  按左上角顶点的 y 坐标排序           │
│  y 相同时按 x 坐标排序              │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│  微调排序: 插入排序修正同行顺序      │
│                                     │
│  for i in range(N-1):               │
│    for j in range(i, -1, -1):       │
│      if 同一行 and 顺序错误:        │
│        交换 _boxes[j] 和 _boxes[j+1]│
│      else:                          │
│        break                        │
└────────────────┬────────────────────┘
                 │
                 ▼
输出: 排序后的 _boxes
```

**同行判断**：`abs(y1 - y2) < 10` 像素

**顺序判断**：`x1 > x2`（右边的框在左边，需要交换）

---

## 6. 使用示例

### 6.1 基本使用（通过 models.py）

```python
from module.ocr.models import get_ocr_model
import cv2

# 获取 OCR 模型
model = get_ocr_model("ch")  # 获取中文模型

# 读取图像
image = cv2.imread("text_image.png")

# 单行识别
text, score = model.ocr_single_line(image)
print(f"识别结果: {text}, 置信度: {score:.2f}")

# 多文本检测和识别
results = model.detect_and_ocr(image)
for r in results:
    print(f"文本: {r.ocr_text}")
    print(f"置信度: {r.score:.2f}")
    print(f"位置: {r.box}")
    print("---")
```

### 6.2 自定义参数

```python
from module.ocr.ppocr import TextSystem

# 创建自定义配置的 TextSystem
ocr_system = TextSystem(
    use_angle_cls=True,    # 启用角度分类（识别旋转文本）
    box_thresh=0.5,        # 降低检测阈值（检测更多文本）
    unclip_ratio=2.0       # 增大扩展比例（更宽松的文本框）
)

# 使用自定义配置进行识别
results = ocr_system.detect_and_ocr(image)
```

### 6.3 GPU 加速

```python
from module.ocr.ppocr import TextSystem

# 使用 GPU 加速
ocr_system = TextSystem(
    ort_providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
)

# 第一次推理会稍慢（加载模型到 GPU），后续推理会显著加快
results = ocr_system.detect_and_ocr(image)
```

---

## 7. 设计模式总结

| 设计模式 | 应用位置 | 说明 |
|---------|---------|------|
| **继承扩展** | `TextSystem` 继承 | 继承第三方库类，提供统一入口和扩展点 |
| **Monkey-Patch** | `sorted_boxes` 替换 | 运行时替换第三方库函数，无需修改源码 |
| **策略模式** | `ort_providers` 参数 | 可选择不同的执行提供者（CPU/GPU） |

### 核心设计思想

1. **轻量封装**：不重复造轮子，复用 ppocronnx 的成熟实现
2. **性能优化**：使用更优的排序算法替换默认实现
3. **灵活性**：通过参数支持不同的配置（角度分类、阈值、GPU 加速等）
4. **统一接口**：为上层模块提供一致的调用方式

### OCR 技术栈

```
┌─────────────────────────────────────┐
│           应用层                     │
│  BaseCor, Full, Single, Digit...    │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│           模型管理层                 │
│  models.py (get_ocr_model)          │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│           推理引擎层                 │
│  ppocr.py (TextSystem)              │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│         ONNX Runtime                │
│  执行 ONNX 模型推理                 │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│         模型文件                     │
│  det_model.onnx (检测模型)          │
│  rec_model.onnx (识别模型)          │
└─────────────────────────────────────┘
```
