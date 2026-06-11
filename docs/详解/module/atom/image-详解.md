# module/atom/image.py 代码详解

## 1. 文件概述

`module/atom/image.py` 是一个基于 OpenCV 的图像匹配模块，封装了模板匹配（Template Matching）和特征匹配（SIFT + FLANN）两大核心算法。该模块主要用于游戏自动化脚本中，通过截图与预存模板图片的比对，判断游戏界面当前状态并定位目标区域的坐标。

**核心能力：**
- 模板匹配（单尺度/多尺度）
- SIFT + FLANN 特征匹配
- 批量匹配 + NMS 去重
- 均值颜色匹配
- ROI 区域裁剪与坐标计算

**文件位置：** `module/atom/image.py`
**作者：** runhey（GitHub: https://github.com/runhey）

---

## 2. 导入部分解释

```python
import cv2                          # OpenCV 库，核心图像处理引擎
import numpy as np                  # NumPy 数组计算库

from numpy import float32, int32, uint8, fromfile  # 从 NumPy 导入常用类型和文件读取函数
from pathlib import Path            # 路径处理工具

from module.atom.RuleImageMallResourceMixin import RuleImageMallResourceMixin  # 混入类，提供资源管理能力
from module.base.decorator import cached_property   # 缓存属性装饰器，避免重复计算
from module.logger import logger    # 日志模块
from module.base.utils import is_approx_rectangle  # 工具函数：判断四边形是否近似矩形
```

**导入依赖关系：**

```
cv2 (OpenCV)
├── imdecode          → 图片解码
├── cvtColor          → 颜色空间转换
├── matchTemplate     → 模板匹配
├── SIFT_create       → SIFT 特征检测器
├── FlannBasedMatcher → FLANN 特征匹配器
├── findHomography    → 透视变换矩阵
├── perspectiveTransform → 透视变换
└── dnn.NMSBoxes      → 非极大值抑制

numpy
├── float32 / int32 / uint8 → 数据类型
├── fromfile          → 文件读取
├── where             → 条件索引
└── random.randint    → 随机坐标生成
```

---

## 3. 类定义解释

```python
class RuleImage(RuleImageMallResourceMixin):
```

`RuleImage` 继承自 `RuleImageMallResourceMixin` 混入类，表示一条图像匹配规则。每个实例对应一张模板图片及其匹配参数。

**类属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `debug_mode` | `bool` | 调试模式开关，开启后输出匹配分数 |

**构造函数参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `roi_front` | `tuple` | 前置 ROI，格式 `(x, y, w, h)`，匹配成功后更新为实际位置 |
| `roi_back` | `tuple` | 后置 ROI，格式 `(x, y, w, h)`，在截图中裁剪的搜索区域 |
| `method` | `str` | 匹配方法：`"Template matching"` 或 `"Sift Flann"` |
| `threshold` | `float` | 匹配阈值，如 `0.8` |
| `file` | `str` | 模板图片的相对路径，带后缀 |

**实例属性初始化：**

```python
self._match_init = False   # 匹配初始化标志，用于等待图片稳定
self._image = None         # 缓存的模板图片（延迟加载）
self._kp = None            # SIFT 关键点（KeyPoints）
self._des = None           # SIFT 描述符（Descriptors）
self.method = method       # 匹配方法名
self.roi_front = list(roi_front)  # 前置 ROI（可变列表，匹配后会更新）
self.roi_back = roi_back          # 后置 ROI（固定搜索区域）
self.threshold = threshold        # 匹配阈值
self.file = file                  # 模板图片路径
```

**`roi_front` vs `roi_back` 的区别：**

```
┌─────────────────────────────────────┐
│ 游戏截图                            │
│  ┌───────────────────────┐          │
│  │ roi_back (搜索区域)    │          │
│  │  ┌─────────┐          │          │
│  │  │roi_front│          │          │
│  │  │(模板位置)│          │          │
│  │  └─────────┘          │          │
│  └───────────────────────┘          │
└─────────────────────────────────────┘
```

- `roi_back`：固定的搜索范围，在大图中裁剪出一块区域进行匹配
- `roi_front`：模板匹配成功后，会更新为模板在全图中的实际位置坐标

---

## 4. 每个方法的逐行解释

### 4.1 `name` 属性（第 41-47 行）

```python
@cached_property
def name(self) -> str:
    return Path(self.file).stem.upper()
```

- 使用 `@cached_property` 装饰器，首次访问后缓存结果
- 从文件路径中提取不含后缀的文件名，并转为大写
- 例如：`"./assets/button.png"` → `"BUTTON"`

### 4.2 `__str__` / `__repr__` / `__eq__` / `__hash__` / `__bool__`（第 49-61 行）

```python
def __str__(self):
    return self.name              # 打印时显示大写文件名

__repr__ = __str__               # repr 与 str 相同

def __eq__(self, other):
    return str(self) == str(other)  # 通过名称比较相等性

def __hash__(self):
    return hash(self.name)        # 基于名称的哈希，支持放入字典/集合

def __bool__(self):
    return True                   # RuleImage 实例始终为真
```

### 4.3 `load_image` 方法（第 65-80 行）

```python
def load_image(self) -> None:
    if self._image is not None:       # 已加载则跳过（懒加载模式）
        return
    img = cv2.imdecode(fromfile(self.file, dtype=uint8), -1)
    # fromfile: 用 numpy 读取文件字节（支持中文路径）
    # imdecode: 将字节流解码为图像矩阵
    # -1: 以原始格式读取（包含 Alpha 通道）

    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    # OpenCV 默认 BGR，转为 RGB 统一色彩空间

    self._image = img

    height, width, channels = self._image.shape
    if height != self.roi_front[3] or width != self.roi_front[2]:
        self.roi_front[2] = width     # 自动修正 roi_front 的宽高
        self.roi_front[3] = height
        logger.debug(f"{self.name} roi_front size changed to {width}x{height}")
```

**关键点：** 使用 `fromfile` + `imdecode` 组合而非 `cv2.imread`，是因为 `imread` 不支持中文路径。

### 4.4 `load_kp_des` 方法（第 82-85 行）

```python
def load_kp_des(self) -> None:
    if self._kp is not None and self._des is not None:
        return                        # 已计算则跳过
    self._kp, self._des = self.sift.detectAndCompute(self.image, None)
    # SIFT 检测器同时计算关键点和描述符
    # _kp: 关键点列表，包含位置、尺度、方向等信息
    # _des: 描述符矩阵，每个关键点对应一个 128 维向量
```

### 4.5 `image` 属性（第 88-96 行）

```python
@property
def image(self):
    if self._image is None:
        self.load_image()             # 延迟加载
    return self._image
```

### 4.6 匹配方法判断属性（第 98-108 行）

```python
@cached_property
def is_template_match(self) -> bool:
    return self.method == "Template matching"  # 是否为模板匹配

@cached_property
def is_sift_flann(self) -> bool:
    return self.method == "Sift Flann"         # 是否为 SIFT 特征匹配
```

### 4.7 SIFT 相关缓存属性（第 110-124 行）

```python
@cached_property
def sift(self):
    return cv2.SIFT_create()          # 创建 SIFT 检测器实例（缓存）

@cached_property
def kp(self):
    if self._kp is None:
        self.load_kp_des()            # 懒加载关键点
    return self._kp

@cached_property
def des(self):
    if self._des is None:
        self.load_kp_des()            # 懒加载描述符
    return self._des
```

### 4.8 `corp` 方法 — ROI 裁剪（第 126-138 行）

```python
def corp(self, image: np.array, roi: list = None) -> np.array:
    if roi is None:
        x, y, w, h = self.roi_back   # 默认使用 roi_back
    else:
        x, y, w, h = roi             # 或使用指定的 ROI
    x, y, w, h = int(x), int(y), int(w), int(h)
    return image[y:y + h, x:x + w]   # NumPy 数组切片裁剪
```

**注意：** `image[y:y+h, x:x+w]` 是 NumPy 的行优先切片语法，先行（y）后列（x）。

### 4.9 `match` 方法 — 单尺度模板匹配（第 140-170 行）

```python
def match(self, image: np.array, threshold: float = None) -> bool:
    if threshold is None:
        threshold = self.threshold    # 使用默认阈值

    if not self.is_template_match:
        return self.sift_match(image) # 非模板匹配则走 SIFT 流程

    source = self.corp(image)         # 从截图中裁剪搜索区域
    mat = self.image                  # 获取模板图片

    # 安全检查：模板有效性
    if mat is None or mat.shape[0] == 0 or mat.shape[1] == 0:
        logger.error(f"Template image is invalid: {mat.shape}")
        return False

    res = cv2.matchTemplate(source, mat, cv2.TM_CCOEFF_NORMED)
    # TM_CCOEFF_NORMED: 归一化相关系数法
    # 返回值范围 [-1, 1]，越接近 1 匹配越好

    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    # 获取匹配结果中的最大值及其位置

    if self.debug_mode:
        logger.attr(self.name, f'matching score {max_val:.5f}')

    if max_val > threshold:
        # 匹配成功，更新 roi_front 为实际位置（全图坐标）
        self.roi_front[0] = max_loc[0] + self.roi_back[0]
        self.roi_front[1] = max_loc[1] + self.roi_back[1]
        return True
    else:
        return False
```

**`cv2.matchTemplate` 的匹配方法对比：**

| 方法 | 值范围 | 最佳值 | 说明 |
|------|--------|--------|------|
| `TM_CCOEFF_NORMED` | [-1, 1] | 1 | 归一化相关系数（本项目使用） |
| `TM_CCORR_NORMED` | [0, 1] | 1 | 归一化相关 |
| `TM_SQDIFF_NORMED` | [0, 1] | 0 | 归一化平方差 |

### 4.10 `match_multi_scale` 方法 — 多尺度模板匹配（第 172-241 行）

```python
def match_multi_scale(self, image: np.array, threshold: float = None,
                      scales: list = None, scale_range: tuple = None) -> bool:
```

**参数说明：**
- `scales`：直接指定缩放比例列表，如 `[0.8, 0.9, 1.0, 1.1, 1.2]`
- `scale_range`：自动生成 scales，格式 `(start, end, step)`

**核心逻辑：**

```python
# 1. 处理 scale_range 参数
if scale_range is not None:
    start, end = scale_range[:2]
    step = scale_range[2] if len(scale_range) > 2 else 0.1
    scales = sorted(set(round(x, 1) for x in np.arange(start, end + step, step)))

# 2. 默认 scales
if scales is None:
    scales = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2]

# 3. 遍历每个缩放比例
best_score = 0
best_loc = None
best_scale = 1.0

for scale in scales:
    scaled_w = int(mat_w * scale)
    scaled_h = int(mat_h * scale)

    if scaled_w < 10 or scaled_h < 10:    # 跳过过小的缩放
        continue

    scaled_mat = cv2.resize(mat, (scaled_w, scaled_h))  # 缩放模板
    res = cv2.matchTemplate(source, scaled_mat, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)

    if max_val > best_score:              # 记录最佳结果
        best_score = max_val
        best_loc = max_loc
        best_scale = scale

# 4. 阈值判断并更新 roi_front
if best_score > threshold and best_loc is not None:
    self.roi_front[0] = best_loc[0] + self.roi_back[0]
    self.roi_front[1] = best_loc[1] + self.roi_back[1]
    self.roi_front[2] = scaled_w          # 更新宽高为缩放后的尺寸
    self.roi_front[3] = scaled_h
    return True
```

### 4.11 `match_all` 方法 — 批量匹配（第 243-268 行）

```python
def match_all(self, image: np.array, threshold: float = None, roi: list = None) -> list[tuple]:
```

返回所有匹配结果，每个结果格式为 `(score, x, y, w, h)`。

```python
results = cv2.matchTemplate(source, mat, cv2.TM_CCOEFF_NORMED)
locations = np.where(results >= threshold)  # 找到所有超过阈值的位置

matches = []
for pt in zip(*locations[::-1]):     # locations[::-1] 将 (行,列) 转为 (x,y)
    score = results[pt[1], pt[0]]
    x = self.roi_back[0] + pt[0]     # 转换为全图坐标
    y = self.roi_back[1] + pt[1]
    matches.append((score, x, y, mat.shape[1], mat.shape[0]))
```

### 4.12 `match_all_any` 方法 — NMS 去重批量匹配（第 270-302 行）

```python
def match_all_any(self, image: np.array, threshold: float = None,
                  roi: list = None, nms_threshold: float = 0.3) -> list[tuple]:
```

在 `match_all` 基础上增加了 NMS（非极大值抑制）去重：

```python
scores = np.array([m[0] for m in matches])
boxes = np.array([[m[1], m[2], m[3], m[4]] for m in matches])

indices = cv2.dnn.NMSBoxes(
    boxes.tolist(),
    scores.tolist(),
    score_threshold=threshold,   # 分数阈值
    nms_threshold=nms_threshold  # IoU 重叠阈值，重叠超过此值的框被抑制
)
filtered_matches = [matches[i] for i in indices]
```

**NMS 原理：** 保留得分最高的框，删除与其 IoU（交并比）超过阈值的其他框。

### 4.13 坐标计算方法（第 304-326 行）

```python
def coord(self) -> tuple:
    """roi_front 内随机点击坐标"""
    x, y, w, h = self.roi_front
    return x + np.random.randint(0, w), y + np.random.randint(0, h)

def coord_more(self) -> tuple:
    """roi_back 内随机点击坐标"""
    x, y, w, h = self.roi_back
    return x + np.random.randint(0, w), y + np.random.randint(0, h)

def front_center(self) -> tuple:
    """roi_front 中心坐标"""
    x, y, w, h = self.roi_front
    return int(x + w//2), int(y + h//2)
```

**随机坐标的用途：** 模拟人类点击行为，避免每次点击完全相同的位置。

### 4.14 `test_match` 方法（第 328-333 行）

```python
def test_match(self, image: np.array):
    self.debug_mode = True
    if self.is_template_match:
        return self.match(image)
    if self.is_sift_flann:
        return self.sift_match(image, show=True)  # show=True 显示可视化窗口
```

### 4.15 `sift_match` 方法 — SIFT + FLANN 特征匹配（第 335-400 行）

```python
def sift_match(self, image: np.array, show=False) -> bool:
```

**完整流程：**

```python
# 第 1 步：裁剪搜索区域并提取特征
source = self.corp(image)
kp, des = self.sift.detectAndCompute(source, None)

# 第 2 步：配置 FLANN 匹配器
index_params = dict(algorithm=1, trees=5)    # KD-Tree 算法，5 棵树
search_params = dict(checks=50)              # 搜索 50 次递归

flann = cv2.FlannBasedMatcher(index_params, search_params)

# 第 3 步：KNN 匹配（k=2，返回最近的 2 个匹配）
matches = flann.knnMatch(self.des, des, k=2)

# 第 4 步：Lowe's 比率测试 — 过滤不良匹配
good = []
for i, (m, n) in enumerate(matches):
    if m.distance < 0.6 * n.distance:   # 最佳匹配距离 < 次佳的 0.6 倍
        good.append(m)

# 第 5 步：计算透视变换
if len(good) >= 10:                      # 至少需要 10 个好匹配点
    src_pts = float32([self.kp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst_pts = float32([kp[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

    m, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    # RANSAC 随机采样一致性，排除离群点

    # 第 6 步：透视变换定位模板四角
    w, h = self.roi_front[2], self.roi_front[3]
    pts = float32([[0, 0], [0, h-1], [w-1, h-1], [w-1, 0]]).reshape(-1, 1, 2)

    if m is None:
        result = False
    else:
        dst = int32(cv2.perspectiveTransform(pts, m))
        self.roi_front[0] = dst[0, 0, 0] + self.roi_back[0]
        self.roi_front[1] = dst[0, 0, 1] + self.roi_back[1]

        # 第 7 步：验证结果是否为近似矩形
        if not is_approx_rectangle(np.array([pos[0] for pos in dst])):
            result = False
```

**Lowe's 比率测试原理：**

```
好匹配：最佳距离远小于次佳距离 → m.distance << n.distance
坏匹配：最佳和次佳距离相近 → 可能是误匹配

阈值 0.6（比经典的 0.7 更严格）→ 减少误匹配但可能漏检
```

### 4.16 `match_mean_color` 方法 — 均值颜色匹配（第 402-416 行）

```python
def match_mean_color(self, image, color: tuple, bias=10) -> bool:
    image = self.corp(image)              # 裁剪 ROI 区域
    average_color = cv2.mean(image)       # 计算区域平均颜色 (B, G, R, A)
    for i in range(3):                    # 检查 RGB 三通道
        if abs(average_color[i] - color[i]) > bias:
            return False                  # 任一通道偏差超过 bias 则不匹配
    return True
```

**用途：** 判断某个区域的颜色是否接近预期值，常用于检测按钮高亮状态、加载画面等。

### 4.17 `__main__` 测试代码（第 418-431 行）

```python
if __name__ == "__main__":
    from dev_tools.assets_test import detect_image

    IMAGE_FILE = './log/test/QQ截图20240223151924.png'
    from tasks.Restart.assets import RestartAssets
    jade = RestartAssets.I_HARVEST_JADE
    jade.method = 'Sift Flann'            # 切换为 SIFT 匹配
    sign = RestartAssets.I_HARVEST_SIGN
    sign.method = 'Sift Flann'
    print(jade.roi_front)

    detect_image(IMAGE_FILE, jade)        # 测试匹配
    detect_image(IMAGE_FILE, sign)
    print(jade.roi_front)                 # 匹配后 roi_front 已更新
```

---

## 5. 核心算法流程图

### 5.1 模板匹配流程

```
输入：游戏截图 image
        │
        ▼
┌─────────────────────┐
│  corp(image)        │ ← 使用 roi_back 裁剪搜索区域
│  得到 source        │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  获取模板图片        │ ← self.image（懒加载）
│  得到 mat           │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────────────────────┐
│  cv2.matchTemplate(source, mat,     │
│                    TM_CCOEFF_NORMED) │
│  得到匹配结果矩阵 res               │
└─────────┬───────────────────────────┘
          │
          ▼
┌─────────────────────┐
│  cv2.minMaxLoc(res) │ ← 获取最大匹配值 max_val
│  及其位置 max_loc   │   和坐标
└─────────┬───────────┘
          │
          ▼
    ┌─────────────┐     是     ┌──────────────────────┐
    │ max_val >   │───────────▶│ 更新 roi_front       │
    │ threshold?  │            │ roi_front[0] =       │
    └──────┬──────┘            │   max_loc[0] +       │
           │ 否                │   roi_back[0]        │
           ▼                   │ roi_front[1] =       │
      返回 False               │   max_loc[1] +       │
                               │   roi_back[1]        │
                               │ 返回 True            │
                               └──────────────────────┘
```

### 5.2 SIFT + FLANN 特征匹配流程

```
输入：游戏截图 image
        │
        ▼
┌───────────────────────────────┐
│ corp(image) 裁剪 source       │
│ SIFT 检测 source 的 kp, des   │
└─────────┬─────────────────────┘
          │
          ▼
┌───────────────────────────────┐
│ FLANN KNN 匹配 (k=2)          │
│ 模板 des ↔ source des         │
│ 返回每对最近邻 (m, n)         │
└─────────┬─────────────────────┘
          │
          ▼
┌───────────────────────────────┐
│ Lowe's 比率测试               │
│ m.distance < 0.6 * n.distance │
│ 过滤得到 good 列表            │
└─────────┬─────────────────────┘
          │
          ▼
    ┌──────────────┐     否     ┌─────────────┐
    │ len(good)    │───────────▶│ 返回 False  │
    │ >= 10 ?      │            └─────────────┘
    └──────┬───────┘
           │ 是
           ▼
┌───────────────────────────────┐
│ cv2.findHomography            │
│ (RANSAC) 计算透视变换矩阵     │
└─────────┬─────────────────────┘
          │
          ▼
    ┌──────────────┐     否     ┌─────────────┐
    │ 矩阵 m      │───────────▶│ 返回 False  │
    │ 有效？       │            └─────────────┘
    └──────┬───────┘
           │ 是
           ▼
┌───────────────────────────────┐
│ perspectiveTransform          │
│ 变换模板四角坐标              │
└─────────┬─────────────────────┘
          │
          ▼
    ┌──────────────┐     否     ┌─────────────┐
    │ 近似矩形？   │───────────▶│ 返回 False  │
    └──────┬───────┘            └─────────────┘
           │ 是
           ▼
┌───────────────────────────────┐
│ 更新 roi_front               │
│ 返回 True                     │
└───────────────────────────────┘
```

### 5.3 多尺度匹配流程

```
输入：截图 image, scales 列表
        │
        ▼
┌─────────────────────────┐
│ 初始化 best_score = 0   │
│ best_loc = None         │
└─────────┬───────────────┘
          │
          ▼
    ┌─────────────────────┐
    │ for scale in scales │◀──────────────┐
    └─────────┬───────────┘               │
              │                           │
              ▼                           │
    ┌─────────────────────┐               │
    │ 缩放模板            │               │
    │ cv2.resize(mat,     │               │
    │   (w*scale, h*scale))│              │
    └─────────┬───────────┘               │
              │                           │
              ▼                           │
    ┌─────────────────────┐               │
    │ matchTemplate       │               │
    │ 获取 max_val        │               │
    └─────────┬───────────┘               │
              │                           │
              ▼                           │
    ┌─────────────────────┐    是         │
    │ max_val >           │──────▶ 更新   │
    │ best_score ?        │  best_score   │
    └─────────┬───────────┘  best_loc     │
              │ 否           best_scale   │
              └───────────────────────────┘
                          │
                          ▼
              ┌─────────────────────┐
              │ best_score >        │
              │ threshold ?         │
              └──────┬──────┬───────┘
                是   │      │ 否
                     ▼      ▼
              更新roi_front  返回False
              返回True
```

---

## 6. 使用示例

### 6.1 基本模板匹配

```python
# 创建匹配规则
button = RuleImage(
    roi_front=(100, 200, 80, 30),    # 模板预期位置
    roi_back=(50, 100, 500, 400),    # 搜索区域
    method="Template matching",
    threshold=0.8,
    file="./assets/start_button.png"
)

# 执行匹配
screenshot = get_screenshot()  # 获取游戏截图
if button.match(screenshot):
    print(f"找到按钮，位置：{button.roi_front}")
    x, y = button.coord()      # 获取随机点击坐标
    click(x, y)
```

### 6.2 SIFT 特征匹配

```python
icon = RuleImage(
    roi_front=(0, 0, 100, 100),
    roi_back=(0, 0, 1920, 1080),
    method="Sift Flann",
    threshold=0.8,
    file="./assets/game_icon.png"
)

if icon.match(screenshot):
    cx, cy = icon.front_center()  # 获取中心坐标
    click(cx, cy)
```

### 6.3 多尺度匹配

```python
# 当目标可能因分辨率/缩放而大小变化时使用
result = button.match_multi_scale(
    screenshot,
    threshold=0.75,
    scale_range=(0.7, 1.3, 0.1)  # 从 70% 到 130%，步长 10%
)
```

### 6.4 批量匹配 + NMS

```python
# 查找屏幕上所有相同的图标
items = icon.match_all_any(screenshot, threshold=0.8, nms_threshold=0.3)
for score, x, y, w, h in items:
    print(f"匹配项：({x}, {y}), 得分: {score:.3f}")
    click(x + w // 2, y + h // 2)
```

### 6.5 颜色匹配

```python
# 检测某个区域是否为绿色（如"已选中"状态）
is_selected = button.match_mean_color(
    screenshot,
    color=(0, 255, 0),  # 绿色 (RGB)
    bias=30              # 允许偏差
)
```

### 6.6 调试模式

```python
button.debug_mode = True
button.match(screenshot)
# 输出: BUTTON matching score 0.92345

# 或使用 test_match 自动开启调试
button.test_match(screenshot)
```

---

## 7. 设计模式总结

### 7.1 延迟加载模式（Lazy Loading）

图片和 SIFT 特征均采用延迟加载策略：

```python
@property
def image(self):
    if self._image is None:
        self.load_image()     # 首次访问时才加载
    return self._image
```

**优势：** 避免启动时一次性加载所有模板图片，节省内存和启动时间。

### 7.2 缓存属性模式（Cached Property）

```python
@cached_property
def sift(self):
    return cv2.SIFT_create()
```

**优势：** 计算一次后缓存结果，后续访问直接返回缓存值。适用于 `sift`、`name`、`is_template_match` 等不变属性。

### 7.3 策略模式（Strategy Pattern）

通过 `method` 字段切换匹配算法：

```
match() 方法
├── method == "Template matching" → 调用模板匹配逻辑
└── method == "Sift Flann"       → 调用 sift_match()
```

**优势：** 同一接口支持不同算法，调用方无需关心具体实现。

### 7.4 模板方法模式（Template Method）

`match` → `corp` → `matchTemplate` / `sift_match` 形成固定的算法骨架，子步骤可独立变化。

### 7.5 ROI 双区设计

```
roi_back（只读搜索区）  →  裁剪范围，缩小匹配搜索空间
roi_front（可写结果区） →  匹配后更新为实际位置，供后续坐标计算
```

**设计意图：** `roi_back` 限定搜索范围提高效率，`roi_front` 在匹配后反映真实位置，形成"搜索-定位"分离。

### 7.6 防御性编程

- 模板图片有效性检查（`mat is None or shape[0] == 0`）
- SIFT 匹配结果矩形性验证（`is_approx_rectangle`）
- 缩放过小跳过（`scaled_w < 10`）
- 多层 fallback（good 点不足 → 返回 False，变换矩阵无效 → 返回 False）

### 7.7 坐标转换一致性

所有匹配方法都遵循同一坐标转换规则：

```
全图坐标 = roi_back 偏移 + 模板内偏移
roi_front[0] = max_loc[0] + roi_back[0]   # x
roi_front[1] = max_loc[1] + roi_back[1]   # y
```

这保证了无论使用哪种匹配方法，`roi_front` 始终存储全图坐标系下的位置。
