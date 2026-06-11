# module/ocr/utils.py 代码详解

## 1. 文件概述

`utils.py` 是 OCR 模块的工具函数文件，提供区域合并功能。主要用于：

- 合并多个矩形区域为一个包含所有区域的最小矩形
- 支持 Full 类的多文本区域合并

该文件非常简洁，只包含两个函数，但提供了 OCR 模块所需的关键几何计算功能。

---

## 2. 导入部分解释

```python
# 无外部依赖
# 该文件是纯 Python 实现，不依赖任何第三方库
```

---

## 3. 类定义解释

```python
# 该文件没有类定义，只包含函数
```

---

## 4. 每个方法的逐行解释

### 4.1 `_merge_area` 内部函数

```python
def _merge_area(area1, area2):
    """
    合并两个矩形区域
    
    参数:
        area1: 第一个区域 (x1, y1, x2, y2)
               (x1, y1) 是左上角坐标
               (x2, y2) 是右下角坐标
        area2: 第二个区域 (x1, y1, x2, y2)
    
    返回:
        合并后的区域 (x1, y1, x2, y2)
        包含两个输入区域的最小矩形
    
    算法:
        - 取两个区域左上角的最小 x, y
        - 取两个区域右下角的最大 x, y
    """
    xa1, ya1, xa2, ya2 = area1  # 解构第一个区域
    xb1, yb1, xb2, yb2 = area2  # 解构第二个区域
    
    # 计算合并后的边界
    return (
        min(xa1, xb1),  # 左边界：取较小的 x
        min(ya1, yb1),  # 上边界：取较小的 y
        max(xa2, xb2),  # 右边界：取较大的 x
        max(ya2, yb2)   # 下边界：取较大的 y
    )
```

**坐标系说明**：
```
(0,0) ──────────────> x
  │
  │   (x1,y1)┌─────────┐
  │          │  区域    │
  │          │         │
  │          └─────────┘(x2,y2)
  │
  ▼ y
```

### 4.2 `merge_area` 公开函数

```python
def merge_area(areas: list[tuple]) -> tuple:
    """
    合并多个矩形区域
    
    参数:
        areas: 区域列表，每个区域为 (x, y, width, height) 格式
               注意：输入是 (x, y, w, h) 格式，不是 (x1, y1, x2, y2)
    
    返回:
        合并后的区域 (x, y, width, height)
        如果输入为空，返回 (0, 0, 0, 0)
    
    算法:
        1. 将 (x, y, w, h) 转换为 (x1, y1, x2, y2)
        2. 使用 _merge_area 逐个合并
        3. 将结果转换回 (x, y, w, h) 格式
    """
    if not areas:
        return 0, 0, 0, 0  # 空列表返回零区域
    
    # 转换第一个区域为 (x1, y1, x2, y2) 格式
    # 注意：这里直接使用 areas[0]，假设已经是 (x1, y1, x2, y2) 格式
    # 但实际上输入是 (x, y, w, h) 格式，这是一个潜在的 bug
    area = areas[0]
    
    # 逐个合并剩余区域
    for i in range(1, len(areas)):
        area = _merge_area(area, areas[i])
    
    return area
```

**重要说明**：

查看 `sub_ocr.py` 中的调用方式：
```python
area_list = [(
    boxed_results[index].box[0, 0],  # x (左上角)
    boxed_results[index].box[0, 1],  # y (左上角)
    boxed_results[index].box[1, 0] - boxed_results[index].box[0, 0],  # width
    boxed_results[index].box[2, 1] - boxed_results[index].box[0, 1],  # height
) for index in index_list]
area = merge_area(area_list)
```

输入确实是 `(x, y, width, height)` 格式，但 `_merge_area` 期望 `(x1, y1, x2, y2)` 格式。

**实际行为分析**：
- 输入：`(x, y, width, height)`
- `_merge_area` 将其视为 `(x1, y1, x2, y2)`
- `min(xa1, xb1)` = 较小的 x（正确）
- `min(ya1, yb1)` = 较小的 y（正确）
- `max(xa2, xb2)` = 较大的 width（**错误**，应该是 x + width）
- `max(ya2, yb2)` = 较大的 height（**错误**，应该是 y + height）

**这是一个 bug**，但在实际使用中可能因为后续处理而没有明显问题。

---

## 5. 核心算法流程图

### 5.1 区域合并算法

```
输入: areas = [(x1,y1,w1,h1), (x2,y2,w2,h2), ...]
    │
    ▼
┌─────────────────┐
│  空列表检查      │──是──▶ 返回 (0,0,0,0)
└────────┬────────┘
         │否
         ▼
┌─────────────────┐
│  初始化 area     │
│  = areas[0]     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  for i in 1..len(areas)-1:          │
│    area = _merge_area(area, areas[i])│
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  _merge_area 算法:                   │
│                                     │
│    ┌──────────┐                     │
│    │ area1    │    ┌──────────┐     │
│    │          │    │ area2    │     │
│    └──────────┘    │          │     │
│                    └──────────┘     │
│                                     │
│    ┌────────────────────────┐       │
│    │     合并结果            │       │
│    │  (包含两个区域的最小框) │       │
│    └────────────────────────┘       │
│                                     │
│  x1 = min(xa1, xb1)                │
│  y1 = min(ya1, yb1)                │
│  x2 = max(xa2, xb2)                │
│  y2 = max(ya2, yb2)                │
└────────┬────────────────────────────┘
         │
         ▼
    返回合并后的 area
```

### 5.2 区域合并可视化

```
区域1 (蓝色):        区域2 (红色):
┌─────────┐         ┌─────────┐
│ (10,20) │         │ (50,10) │
│  30x20  │         │  20x30  │
└─────────┘         └─────────┘

合并结果 (绿色):
┌───────────────────────┐
│ (10,10)               │
│                       │
│   ┌─────────┐         │
│   │ 区域1   │ ┌─────┐ │
│   └─────────┘ │区域2│ │
│               └─────┘ │
│                       │
└───────────────────────┘
结果: (10, 10, 60, 40)  → (x1, y1, x2, y2)
```

---

## 6. 使用示例

### 6.1 基本使用

```python
from module.ocr.utils import merge_area

# 定义多个区域 (x, y, width, height)
areas = [
    (10, 20, 30, 20),  # 区域1: x=10, y=20, w=30, h=20
    (50, 10, 20, 30),  # 区域2: x=50, y=10, w=20, h=30
    (25, 35, 40, 15),  # 区域3: x=25, y=35, w=40, h=15
]

# 合并所有区域
merged = merge_area(areas)
print(f"合并结果: {merged}")
# 输出: 合并结果: (10, 10, 20, 30)
# 注意：由于 bug，输出可能不正确
```

### 6.2 在 Full 类中的应用

```python
from module.ocr.sub_ocr import Full
import cv2

# 创建全文检测器
full_ocr = Full(
    name="menu_detector",
    mode="FULL",
    method="DEFAULT",
    roi=(0, 0, 800, 600),
    area=(0, 0, 0, 0),
    keyword="探索"
)

# 检测并合并文本区域
image = cv2.imread("screenshot.png")
x, y, w, h = full_ocr.ocr_full(image, keyword="探索")
# 内部会调用 merge_area 合并多个匹配的文本框
```

### 6.3 直接使用 _merge_area

```python
from module.ocr.utils import _merge_area

# 合并两个区域 (x1, y1, x2, y2) 格式
area1 = (10, 20, 40, 40)  # 左上角(10,20), 右下角(40,40)
area2 = (30, 10, 60, 50)  # 左上角(30,10), 右下角(60,50)

merged = _merge_area(area1, area2)
print(f"合并结果: {merged}")
# 输出: 合并结果: (10, 10, 60, 50)
# 即左上角(10,10), 右下角(60,50)
```

---

## 7. 设计模式总结

| 设计模式 | 应用位置 | 说明 |
|---------|---------|------|
| **工具函数** | `_merge_area`, `merge_area` | 纯函数，无状态，易于测试 |
| **内部函数** | `_merge_area` 以下划线开头 | 表示为模块内部使用，不对外暴露 |

### 核心设计思想

1. **单一职责**：只负责区域合并这一项功能
2. **纯函数**：无副作用，输入相同则输出相同
3. **简洁实现**：算法简单直接，易于理解和维护

### 潜在改进

1. **修复格式 bug**：`merge_area` 的输入输出格式不一致
2. **添加类型注解**：使用 `Tuple[int, int, int, int]` 明确类型
3. **添加边界检查**：验证输入区域的有效性

修复后的实现：
```python
def merge_area(areas: list[tuple]) -> tuple:
    """合并多个 (x, y, w, h) 区域"""
    if not areas:
        return 0, 0, 0, 0
    
    # 转换为 (x1, y1, x2, y2) 格式
    x, y, w, h = areas[0]
    area = (x, y, x + w, y + h)
    
    for i in range(1, len(areas)):
        x, y, w, h = areas[i]
        area = _merge_area(area, (x, y, x + w, y + h))
    
    # 转换回 (x, y, w, h) 格式
    x1, y1, x2, y2 = area
    return x1, y1, x2 - x1, y2 - y1
```
