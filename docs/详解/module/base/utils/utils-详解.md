# utils/utils.py 逐行代码详解

> 源文件路径：`module/base/utils/utils.py`

---

## 1. 文件概述

`utils.py` 是项目的基础工具库，提供了大量实用函数，涵盖：
- **随机数工具**：正态分布随机数、矩形区域随机点、随机向量
- **区域/坐标操作**：区域偏移、裁剪、限制、碰撞检测
- **颜色处理**：颜色相似度比较、颜色空间转换（RGB/HSV/YUV）
- **图像处理**：图像加载、保存、裁剪、缩放、通道操作
- **坐标转换**：Excel 风格列名与数字互转、节点位置转换
- **几何判断**：角度计算、近似矩形判断

---

## 2. 导入部分解释

```python
import re                              # 正则表达式
import cv2                             # OpenCV 图像处理
import sys                             # 系统模块
import numpy as np                     # 数值计算
import importlib                       # 动态模块加载
from PIL import Image                  # Pillow 图像处理
```

```python
REGEX_NODE = re.compile(r'(-?[A-Za-z]+)(-?\d+)')
```

**第 9 行**：编译正则表达式，匹配节点名称格式（如 `E3`、`A-1`），捕获字母部分和数字部分。

---

## 3. 随机数工具函数

### 3.1 `random_normal_distribution_int(a, b, n=3)` — 正态分布随机整数

```python
def random_normal_distribution_int(a, b, n=3):
    if a < b:
        output = np.mean(np.random.randint(a, b, size=n))
        return int(output.round())
    else:
        return b
```

**第 12-28 行**：通过取 n 个均匀分布随机数的均值来模拟正态分布。均值趋向区间中央，更符合人类行为。

### 3.2 `random_rectangle_point(area, n=3)` — 矩形区域随机点

```python
def random_rectangle_point(area, n=3):
    x = random_normal_distribution_int(area[0], area[2], n=n)
    y = random_normal_distribution_int(area[1], area[3], n=n)
    return x, y
```

**第 31-43 行**：在矩形区域内随机选取一个点，x 和 y 各自独立使用正态分布。

### 3.3 `random_rectangle_vector(vector, box, random_range, padding)` — 随机放置向量

```python
def random_rectangle_vector(vector, box, random_range=(0, 0, 0, 0), padding=15):
    vector = np.array(vector) + random_rectangle_point(random_range)
    vector = np.round(vector).astype(np.int)
    half_vector = np.round(vector / 2).astype(np.int)
    box = np.array(box) + np.append(np.abs(half_vector) + padding, -np.abs(half_vector) - padding)
    center = random_rectangle_point(box)
    start_point = center - half_vector
    end_point = start_point + vector
    return tuple(start_point), tuple(end_point)
```

**第 46-65 行**：将一个向量随机放置在盒子区域内，确保起止点都在区域内（考虑 padding）。

### 3.4 `random_rectangle_vector_opted(...)` — 增强版随机向量放置

```python
def random_rectangle_vector_opted(vector, box, random_range=(0, 0, 0, 0),
                                   padding=15, whitelist_area=None, blacklist_area=None):
```

**第 68-124 行**：增强版，支持白名单区域（安全点击区）和黑名单区域（禁止终点区），防止模拟器卡顿时误触。

### 3.5 `random_line_segments(p1, p2, n, random_range)` — 线段分段

```python
def random_line_segments(p1, p2, n, random_range=(0, 0, 0, 0)):
    return [tuple((((n - index) * p1 + index * p2) / n).astype(int) + random_rectangle_point(random_range))
            for index in range(0, n + 1)]
```

**第 127-140 行**：将线段等分为 n 段，每段端点添加随机偏移。

---

## 4. 时间和类型工具

### 4.1 `ensure_time(second, n=3, precision=3)` — 确保时间值

```python
def ensure_time(second, n=3, precision=3):
    if isinstance(second, tuple):          # (10, 30) → 随机 10~30
        multiply = 10 ** precision
        result = random_normal_distribution_int(second[0] * multiply, second[1] * multiply, n) / multiply
        return round(result, precision)
    elif isinstance(second, str):          # "10,30" 或 "10-30" → 随机
        if ',' in second:
            lower, upper = second.replace(' ', '').split(',')
            return ensure_time((int(lower), int(upper)), n=n, precision=precision)
        if '-' in second:
            lower, upper = second.replace(' ', '').split('-')
            return ensure_time((int(lower), int(upper)), n=n, precision=precision)
        else:
            return int(second)
    else:                                  # 直接返回数值
        return second
```

**第 143-170 行**：灵活的时间值解析器，支持元组、字符串范围、纯数值。

### 4.2 `ensure_int(*args)` — 递归转整数

```python
def ensure_int(*args):
    def to_int(item):
        try:
            return int(item)
        except TypeError:
            result = [to_int(i) for i in item]
            if len(result) == 1:
                result = result[0]
            return result
    return to_int(args)
```

**第 173-194 行**：递归地将嵌套结构中的所有元素转为整数。

---

## 5. 区域操作函数

### 5.1 `area_offset(area, offset)` — 区域偏移

```python
def area_offset(area, offset):
    upper_left_x, upper_left_y, bottom_right_x, bottom_right_y = area
    x, y = offset
    return upper_left_x + x, upper_left_y + y, bottom_right_x + x, bottom_right_y + y
```

**第 197-210 行**：将区域整体平移 `(x, y)`。

### 5.2 `area_pad(area, pad=10)` — 区域内缩

```python
def area_pad(area, pad=10):
    upper_left_x, upper_left_y, bottom_right_x, bottom_right_y = area
    return upper_left_x + pad, upper_left_y + pad, bottom_right_x - pad, bottom_right_y - pad
```

**第 213-225 行**：将区域四边各向内收缩 `pad` 像素。

### 5.3 `limit_in(x, lower, upper)` — 值限制

```python
def limit_in(x, lower, upper):
    return max(min(x, upper), lower)
```

**第 228-240 行**：将 x 限制在 `[lower, upper]` 范围内。

### 5.4 `area_limit(area1, area2)` — 区域限制

```python
def area_limit(area1, area2):
    x_lower, y_lower, x_upper, y_upper = area2
    return (
        limit_in(area1[0], x_lower, x_upper),
        limit_in(area1[1], y_lower, y_upper),
        limit_in(area1[2], x_lower, x_upper),
        limit_in(area1[3], y_lower, y_upper),
    )
```

**第 243-260 行**：将 area1 限制在 area2 范围内。

### 5.5 `area_size(area)` — 区域尺寸

```python
def area_size(area):
    return (max(area[2] - area[0], 0), max(area[3] - area[1], 0))
```

**第 263-276 行**：返回区域的宽高。

### 5.6 `point_limit(point, area)` — 点限制

```python
def point_limit(point, area):
    return (limit_in(point[0], area[0], area[2]), limit_in(point[1], area[1], area[3]))
```

**第 279-293 行**：将点限制在区域内。

### 5.7 `point_in_area(point, area, threshold=5)` — 点是否在区域内

```python
def point_in_area(point, area, threshold=5):
    return area[0] - threshold < point[0] < area[2] + threshold and \
           area[1] - threshold < point[1] < area[3] + threshold
```

**第 296-307 行**：判断点是否在区域内，支持阈值扩展。

### 5.8 `area_in_area / area_cross_area` — 区域包含/交叉判断

```python
def area_in_area(area1, area2, threshold=5):    # area1 是否完全在 area2 内
def area_cross_area(area1, area2, threshold=5):  # 两个区域是否交叉
```

**第 310-342 行**：区域关系判断，使用阈值容差。

---

## 6. 格式化工具

### 6.1 `float2str(n, decimal=3)` — 浮点数转字符串

```python
def float2str(n, decimal=3):
    return str(round(n, decimal)).ljust(decimal + 2, "0")
```

**第 345-354 行**：将浮点数转为固定小数位的字符串（如 `1.5` → `"1.500"`）。

### 6.2 `point2str(x, y, length=4)` — 坐标转字符串

```python
def point2str(x, y, length=4):
    return '(%s, %s)' % (str(int(x)).rjust(length), str(int(y)).rjust(length))
```

**第 357-367 行**：格式化输出坐标，右对齐（如 `( 100,  80)`）。

---

## 7. 坐标转换工具

### 7.1 `col2name(col)` — 列号转字母

```python
def col2name(col):
```

**第 370-410 行**：将零索引列号转为 Excel 风格字母（0→A, 3→D, 35→AJ, -1→-A）。使用 26 进制转换。

### 7.2 `name2col(col_str)` — 字母转列号

```python
def name2col(col_str):
```

**第 413-436 行**：将 Excel 风格字母转为零索引列号（A→0, D→3, AJ→35）。

### 7.3 `node2location(node)` / `location2node(location)` — 节点位置转换

```python
def node2location(node):       # 'E3' → (4, 2)
def location2node(location):   # (4, 2) → 'E3'
```

**第 439-499 行**：在节点名称和坐标元组之间转换，支持负坐标。

---

## 8. 图像处理函数

### 8.1 `load_image(file, area)` — 加载图像

```python
def load_image(file, area=None):
    image = Image.open(file)
    if area is not None:
        image = image.crop(area)
    image = np.array(image)
    channel = image.shape[2] if len(image.shape) > 2 else 1
    if channel > 3:
        image = image[:, :, :3].copy()    # 去除 alpha 通道
    return image
```

**第 502-520 行**：使用 Pillow 加载图像，可选裁剪区域，去除 alpha 通道后转为 numpy 数组。

### 8.2 `save_image(image, file)` — 保存图像

```python
def save_image(image, file):
    Image.fromarray(image).save(file)
```

**第 523-533 行**：将 numpy 数组保存为图像文件。

### 8.3 `crop(image, area, copy=True)` — 图像裁剪

```python
def crop(image, area, copy=True):
    x1, y1, x2, y2 = map(int, map(round, area))
    h, w = image.shape[:2]
    border = np.maximum((0 - y1, y2 - h, 0 - x1, x2 - w), 0)
    x1, y1, x2, y2 = np.maximum((x1, y1, x2, y2), 0)
    image = image[y1:y2, x1:x2]
    if sum(border) > 0:
        image = cv2.copyMakeBorder(image, *border, borderType=cv2.BORDER_CONSTANT, value=(0, 0, 0))
    if copy:
        image = image.copy()
    return image
```

**第 536-558 行**：类似 Pillow 的裁剪，但使用 OpenCV。如果裁剪区域超出图像边界，用黑色填充。

### 8.4 `resize(image, size)` — 图像缩放

```python
def resize(image, size):
    return cv2.resize(image, size, interpolation=cv2.INTER_NEAREST)
```

**第 561-573 行**：使用最近邻插值缩放（与 Pillow 默认行为一致）。

### 8.5 图像信息函数

```python
def image_channel(image):    # 返回通道数（灰度=0, RGB=3）
def image_size(image):       # 返回 (width, height)
```

**第 576-596 行**。

---

## 9. 颜色处理函数

### 9.1 `rgb2gray(image)` — RGB 转灰度

```python
def rgb2gray(image):
    r, g, b = cv2.split(image)
    return cv2.add(cv2.multiply(cv2.max(cv2.max(r, g), b), 0.5),
                   cv2.multiply(cv2.min(cv2.min(r, g), b), 0.5))
```

**第 599-611 行**：灰度 = (max(R,G,B) + min(R,G,B)) / 2，不是标准加权平均但计算更快。

### 9.2 `rgb2hsv(image)` — RGB 转 HSV

```python
def rgb2hsv(image):
    image = cv2.cvtColor(image, cv2.COLOR_RGB2HSV).astype(np.float)
    image *= (360 / 180, 100 / 255, 100 / 255)
    return image
```

**第 614-627 行**：转换为 HSV 并归一化到 H:0~360, S:0~100, V:0~100。

### 9.3 `color_similarity / color_similar` — 颜色相似度

```python
def color_similarity(color1, color2):
    diff = np.array(color1).astype(int) - np.array(color2).astype(int)
    diff = np.max(np.maximum(diff, 0)) - np.min(np.minimum(diff, 0))
    return diff

def color_similar(color1, color2, threshold=10):
    return color_similarity(color1, color2) <= threshold
```

**第 692-722 行**：使用 Photoshop 风格的容差计算——最大正差 + 最大负差。

### 9.4 2D 颜色相似度

```python
def color_similarity_2d(image, color):    # 对整个图像计算颜色相似度
def color_similar_1d(image, color, threshold=10):  # 1D 数组的颜色匹配
```

**第 725-753 行**：向量化的颜色比较，用于批量处理。

---

## 10. 其他工具函数

### 10.1 `get_color(image, area)` — 获取区域平均颜色

```python
def get_color(image, area):
    temp = crop(image, area, copy=False)
    color = cv2.mean(temp)
    return color[:3]
```

**第 659-671 行**：裁剪区域后计算平均 RGB 颜色。

### 10.2 `get_bbox(image, threshold=0)` — 获取边界框

```python
def get_bbox(image, threshold=0):
    if image_channel(image) == 3:
        image = np.max(image, axis=2)
    x = np.where(np.max(image, axis=0) > threshold)[0]
    y = np.where(np.max(image, axis=1) > threshold)[0]
    return x[0], y[0], x[-1] + 1, y[-1] + 1
```

**第 674-689 行**：找到非黑色区域的边界框（类似 Pillow 的 `getbbox()`）。

### 10.3 `extract_letters / extract_white_letters` — 文字提取

```python
def extract_letters(image, letter=(255, 255, 255), threshold=128):    # 提取指定颜色文字
def extract_white_letters(image, threshold=128):                       # 提取白色文字
```

**第 756-788 行**：将文字区域转为黑色，背景转为白色，用于 OCR 前处理。

### 10.4 `color_mapping(image, max_multiply=2)` — 颜色映射

```python
def color_mapping(image, max_multiply=2):
```

**第 791-810 行**：将图像颜色线性映射到 0~255，增强对比度。

### 10.5 `load_module(moduleName, moduleFile)` — 动态加载模块

```python
def load_module(moduleName, moduleFile):
    spec = importlib.util.spec_from_file_location(moduleName, moduleFile)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[moduleName] = module
    return module
```

**第 891-902 行**：从文件路径动态加载 Python 模块。

### 10.6 `angle(p1, p2, p3)` — 三点角度

```python
def angle(p1, p2, p3):
    v1 = p2 - p1
    v2 = p3 - p2
    cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    return np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))
```

**第 905-910 行**：计算 p1→p2→p3 形成的角度（度）。

### 10.7 `is_approx_rectangle(points, tolerance=30)` — 近似矩形判断

```python
def is_approx_rectangle(points, tolerance=30):
    if points.shape[0] != 4:
        return False
    angles = [angle(points[0], points[1], points[2]), ...]
    return all(np.isclose(a, 90, atol=tolerance) for a in angles)
```

**第 913-940 行**：判断四个点是否近似构成矩形（各角度接近 90 度）。

---

## 11. 核心算法流程图

### 颜色相似度计算（Photoshop 容差）

```
color1 = (R1, G1, B1), color2 = (R2, G2, B2)
 │
 ▼
diff = color1 - color2 = (dR, dG, dB)
 │
 ▼
positive = max(dR, 0), max(dG, 0), max(dB, 0)
negative = min(dR, 0), min(dG, 0), min(dB, 0)
 │
 ▼
tolerance = max(positive) - min(negative)
 │
 ▼
tolerance <= threshold → 相似
```

### 裁剪边界处理

```
输入: image(h,w), area(x1,y1,x2,y2)
 │
 ▼
计算超出边界的像素数:
  border = (max(0-y1,0), max(y2-h,0), max(0-x1,0), max(x2-w,0))
 │
 ▼
将坐标限制在 [0, max] 范围
 │
 ▼
裁剪图像: image[y1:y2, x1:x2]
 │
 ▼
border > 0 ?
 ├─ 是 → cv2.copyMakeBorder 黑色填充
 └─ 否 → 直接返回
```

---

## 12. 使用示例

```python
# 随机点击区域内的点
point = random_rectangle_point((100, 200, 300, 400))

# 颜色比较
if color_similar(get_color(screenshot, (10, 20, 50, 60)), (255, 0, 0), threshold=20):
    print("检测到红色区域")

# 裁剪图像
cropped = crop(screenshot, (100, 100, 200, 200))

# 坐标转换
col2name(35)          # 'AJ'
name2col('AJ')        # 35
location2node((4, 2)) # 'E3'
node2location('E3')   # (4, 2)

# 动态加载模块
my_module = load_module('my_module', '/path/to/my_module.py')
```

---

## 13. 设计模式总结

| 模式 | 说明 |
|------|------|
| **向量化计算** | 大量使用 numpy 进行批量操作，避免 Python 循环 |
| **函数式设计** | 纯函数为主，无副作用，易于测试和组合 |
| **容错设计** | 裁剪超出边界时自动填充黑色，而非报错 |
| **阈值参数** | 大量函数提供 `threshold` 参数，调用方根据场景调整精度 |
| **多格式兼容** | `ensure_time` 支持元组、字符串、数值多种输入格式 |
| **OpenCV/Pillow 混用** | 利用两者各自优势（Pillow 加载/保存，OpenCV 计算） |
