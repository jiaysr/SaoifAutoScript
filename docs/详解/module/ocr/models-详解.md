# module/ocr/models.py 代码详解

## 1. 文件概述

`models.py` 是 OCR 模型的管理模块，负责：

1. **模型实例管理**：创建和缓存 OCR 模型实例
2. **工厂函数**：根据语言和配置返回对应的模型
3. **代理支持**：根据配置决定使用本地模型或远程代理

该文件是 OCR 模块的入口点，上层代码通过 `get_ocr_model` 函数获取模型实例。

---

## 2. 导入部分解释

```python
from typing import Dict               # 类型注解：字典类型

from module.base.decorator import cached_property  # 缓存属性装饰器
from module.ocr.ppocr import TextSystem            # 本地 OCR 模型
from module.ocr.rpc import ModelProxy              # 远程代理
from module.server.setting import State            # 全局配置状态
```

---

## 3. 类定义解释

### 3.1 `OcrModel` 类

```python
class OcrModel:
    """
    OCR 模型容器类
    使用 @cached_property 实现懒加载和缓存
    """
    
    @cached_property
    def ch(self):
        """中文模型（懒加载，首次访问时创建）"""
        return TextSystem()
```

**设计说明**：
- 使用 `@cached_property` 装饰器，`ch` 属性只在首次访问时创建 `TextSystem` 实例
- 后续访问直接返回缓存的实例，避免重复创建
- 模型加载是耗时操作（加载 ONNX 模型），懒加载可以延迟启动时间

### 3.2 模块级变量

```python
OCR_MODEL = OcrModel()  # 全局模型容器单例

_OCR_PROXY_CACHE: Dict[str, ModelProxy] = {}  # 代理缓存，key=地址
```

---

## 4. 每个方法的逐行解释

### 4.1 `get_ocr_model` 工厂函数

```python
def get_ocr_model(lang: str = "ch"):
    """
    获取 OCR 模型实例
    
    参数:
        lang: 语言代码，默认 "ch"（中文）
    
    返回:
        TextSystem 或 ModelProxy 实例
    
    决策逻辑:
        - 如果配置启用 OCR 服务，返回 ModelProxy（远程代理）
        - 否则返回本地 TextSystem 实例
    """
    deploy_config = State.deploy_config  # 获取部署配置
    
    if deploy_config.UseOcrServer:
        # 使用远程 OCR 服务
        address = deploy_config.OcrClientAddress or "127.0.0.1:22268"
        
        # 检查缓存，避免重复创建代理
        if address not in _OCR_PROXY_CACHE:
            _OCR_PROXY_CACHE[address] = ModelProxy(address)
        return _OCR_PROXY_CACHE[address]
    
    # 使用本地模型
    return getattr(OCR_MODEL, lang)  # 动态获取语言对应的模型
```

**关键逻辑**：
1. 读取配置判断是否使用远程服务
2. 如果使用远程服务，从缓存获取或创建代理
3. 如果使用本地模型，通过 `getattr` 动态获取

### 4.2 测试代码

```python
if __name__ == "__main__":
    model = OCR_MODEL.ch  # 获取中文模型
    import cv2
    import time
    from memory_profiler import profile
    
    image = cv2.imread(r"E:\Project\OnmyojiAutoScript-assets\jade.png")

    @profile
    def test_memory():
        """内存性能测试"""
        for i in range(2):
            start_time = time.time()
            result = model.detect_and_ocr(image)
            print(result)
            end_time = time.time()
            print(f'耗时：{end_time-start_time}')

    test_memory()
```

**测试说明**：
- 使用 `memory_profiler` 分析内存占用
- 注释提到 "引入 ocr 会导致非常巨大的内存开销"，这是 ONNX 模型的特性

---

## 5. 核心算法流程图

### 5.1 模型获取流程 (`get_ocr_model`)

```
输入: lang="ch"
    │
    ▼
┌─────────────────┐
│  读取配置        │
│  UseOcrServer?  │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
   是         否
    │         │
    ▼         ▼
┌────────┐ ┌─────────────────┐
│ 获取   │ │ getattr(         │
│ 地址   │ │   OCR_MODEL, lang)│
└───┬────┘ └────────┬────────┘
    │               │
    ▼               │
┌──────────────┐    │
│ 缓存中有?    │    │
└──────┬───────┘    │
       │            │
  ┌────┴────┐       │
  │         │       │
 是         否      │
  │         │       │
  ▼         ▼       │
┌──────┐ ┌────────┐ │
│返回  │ │创建    │ │
│缓存  │ │Model   │ │
│代理  │ │Proxy   │ │
└──────┘ └───┬────┘ │
             │      │
             ▼      ▼
         ┌────────────┐
         │  返回模型   │
         └────────────┘
```

### 5.2 模型实例化流程

```
首次调用 get_ocr_model("ch")
    │
    ▼
┌─────────────────┐
│  getattr(        │
│    OCR_MODEL,    │
│    "ch"          │
│  )               │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  @cached_property│
│  检查缓存        │
└────────┬────────┘
         │
    无缓存
         │
         ▼
┌─────────────────┐
│  调用 ch() 方法  │
│  创建 TextSystem │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  缓存实例        │
└────────┬────────┘
         │
         ▼
    返回实例
```

---

## 6. 使用示例

### 6.1 基本使用

```python
from module.ocr.models import get_ocr_model
import cv2

# 获取模型（自动判断本地/远程）
model = get_ocr_model("ch")

# 读取图像
image = cv2.imread("screenshot.png")

# 单行识别
text, score = model.ocr_single_line(image)
print(f"识别结果: {text}, 置信度: {score:.2f}")

# 多文本检测
results = model.detect_and_ocr(image)
for r in results:
    print(f"文本: {r.ocr_text}, 位置: {r.box}")
```

### 6.2 直接访问本地模型

```python
from module.ocr.models import OCR_MODEL

# 直接访问本地模型（跳过配置检查）
model = OCR_MODEL.ch

# 后续使用相同
results = model.detect_and_ocr(image)
```

### 6.3 多语言扩展（预留）

```python
from module.ocr.models import OcrModel, get_ocr_model

# 扩展 OcrModel 类以支持更多语言
class ExtendedOcrModel(OcrModel):
    @cached_property
    def en(self):
        # 返回英文模型
        return TextSystem(rec_model_path="models/en_rec.onnx")
    
    @cached_property
    def jp(self):
        # 返回日文模型
        return TextSystem(rec_model_path="models/jp_rec.onnx")

# 替换全局模型容器
import module.ocr.models as models_module
models_module.OCR_MODEL = ExtendedOcrModel()

# 使用不同语言
zh_model = get_ocr_model("ch")
en_model = get_ocr_model("en")
jp_model = get_ocr_model("jp")
```

---

## 7. 设计模式总结

| 设计模式 | 应用位置 | 说明 |
|---------|---------|------|
| **工厂模式** | `get_ocr_model` | 根据配置和语言参数创建/返回合适的模型 |
| **单例模式** | `OCR_MODEL` | 全局唯一的模型容器 |
| **代理模式** | `ModelProxy` | 远程服务的本地代理 |
| **缓存模式** | `@cached_property` / `_OCR_PROXY_CACHE` | 缓存实例避免重复创建 |
| **策略模式** | 本地/远程选择 | 根据配置选择不同的模型提供者 |

### 核心设计思想

1. **延迟初始化**：模型只在首次使用时创建，减少启动时间
2. **透明切换**：上层代码无需关心模型是本地还是远程
3. **配置驱动**：通过配置文件控制行为，无需修改代码
4. **缓存优化**：避免重复创建昂贵的模型实例
5. **可扩展性**：易于添加新的语言模型支持

### 模块依赖关系

```
上层代码 (sub_ocr.py, base_ocr.py)
    │
    ▼
┌─────────────────┐
│  models.py      │  ← 入口点
│  get_ocr_model  │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌────────┐
│本地模型│ │远程代理│
│ppocr.py│ │rpc.py  │
└────────┘ └────────┘
```
