# register_type/paint_image.py 代码详解

## 1. 文件概述

`register_type/paint_image.py` 是 QML 自定义绘图组件模块，实现了可在 QML 中使用的图像绘制组件。该组件基于 `QQuickPaintedItem`，支持图像显示、加载和裁剪保存功能。

**核心职责：**
- 在 QML 中显示图像
- 支持从本地文件加载图像
- 支持裁剪图像区域并保存

---

## 2. 导入部分解释

```python
import cv2                                            # OpenCV 图像处理库

from numpy import float32, int32, uint8, fromfile     # NumPy 数据类型和文件读取
from PySide6.QtCore import QUrl, Property             # Qt 核心：URL 和属性系统
from PySide6.QtGui import QImage, QPainter            # Qt 图像和画笔类
from PySide6.QtQuick import QQuickPaintedItem         # Qt Quick 可绘制项基类
from PySide6.QtCore import QObject, Slot, Signal      # Qt 核心类

from module.logger import logger                      # 日志记录器
```

---

## 3. 类定义解释

```python
class PaintImage(QQuickPaintedItem):
    """
    可绘制图像的 QML 组件
    继承 QQuickPaintedItem 以支持自定义绘制
    可在 QML 中作为可视项使用
    """
    def __init__(self, parent=None):
        super().__init__(parent)      # 初始化 QQuickPaintedItem
        self._image = QImage()        # 创建空的 QImage 对象
```

---

## 4. 每个方法的逐行解释

### 4.1 `paint(self, painter)` 方法

```python
def paint(self, painter: QPainter):
    """
    绘制函数（由 Qt 框架自动调用）
    当组件需要重绘时，Qt 会调用此方法
    :param painter: QPainter 画笔对象
    """
    # 检查图像是否为空
    if self._image.isNull():
        logger.error("image is null")
        return

    # 在组件的边界矩形内绘制图像
    # self.boundingRect() 返回组件的矩形区域
    # drawImage 会自动缩放图像以适应区域
    painter.drawImage(self.boundingRect(), self._image)
```

### 4.2 `image(self)` 方法

```python
def image(self):
    """
    获取当前图像（Property 的 getter）
    :return: QImage 对象
    """
    return self._image
```

### 4.3 `set_image(self, image)` 方法

```python
def set_image(self, image: QImage):
    """
    设置图像（Property 的 setter）
    :param image: QImage 对象
    """
    # 避免重复设置相同图像
    if self._image == image:
        return None

    self._image = image

    # update() 触发重绘，Qt 会自动调用 paint()
    self.update()
```

### 4.4 `set_local(self, image_name)` 方法

```python
@Slot(str)
def set_local(self, image_name: str):
    """
    从本地文件加载图像
    :param image_name: 文件路径，必须以 'file:///' 开头
    """
    # 验证路径格式
    if not image_name.startswith("file:///"):
        logger.error("image path must start with file:///")
        return None

    # 移除 'file:///' 前缀，获取本地路径
    image_name = image_name.lstrip("file:///")

    # 加载图像
    if self._image.load(image_name):
        logger.info("load image success")
        self.update()  # 触发重绘
    else:
        logger.error("load image failed")
        return None
```

### 4.5 `save_target_image(self, roi, file)` 方法

```python
@Slot(str, str)
def save_target_image(self, roi: str, file: str) -> None:
    """
    保存目标图片（裁剪指定区域）
    :param roi: 截图范围，格式如 "0,0,100,100"（x,y,width,height）
    :param file: 保存的文件路径
    """
    # 验证参数
    if not roi:
        return
    if not isinstance(roi, str):
        logger.error("roi must be str")
    if not file:
        return
    if not isinstance(file, str):
        logger.error("file must be str")
        return

    # 解析 ROI 参数
    x, y, width, height = map(int, roi.split(','))

    # 裁剪图像
    # QImage.copy(x, y, width, height) 从指定区域复制图像
    roi_image = self._image.copy(x, y, width, height)

    # 保存图像
    roi_image.save(file)

    logger.info(f"save target image {file} success")
```

### 4.6 Property 定义

```python
# 定义 QML 属性
# 在 QML 中可以这样使用：
# PaintImage {
#     image: someImage  // 设置图像
#     onImageChanged: console.log("changed")  // 监听变化
# }
image = Property(QImage, fget=image, fset=set_image, notify=logger.info)
```

---

## 5. 核心算法流程图

### 5.1 图像绘制流程

```
Qt 框架请求重绘
    │
    ▼
┌─────────────────────────────────────┐
│  paint(painter) 被调用               │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  图像是否为空？                      │
│  ├─ 是 → 记录错误，返回             │
│  └─ 否 ↓                           │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  painter.drawImage(boundingRect, _image)│
│  在组件区域内绘制图像                │
└─────────────────────────────────────┘
```

### 5.2 本地图像加载流程

```
set_local(image_name)
    │
    ▼
┌─────────────────────────────────────┐
│  路径是否以 'file:///' 开头？       │
│  ├─ 否 → 记录错误，返回             │
│  └─ 是 ↓                           │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  移除 'file:///' 前缀               │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  _image.load(path)                  │
│  ├─ 成功 → update() 触发重绘        │
│  └─ 失败 → 记录错误                 │
└─────────────────────────────────────┘
```

### 5.3 图像裁剪保存流程

```
save_target_image(roi, file)
    │
    ▼
┌─────────────────────────────────────┐
│  验证参数 roi 和 file               │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  解析 ROI: "x,y,w,h"               │
│  x, y, width, height = map(int, roi.split(','))│
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  roi_image = _image.copy(x, y, w, h)│
│  裁剪指定区域                        │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  roi_image.save(file)               │
│  保存到文件                          │
└─────────────────────────────────────┘
```

---

## 6. 使用示例

### 6.1 在 QML 中使用

```qml
import QtQuick 2.15
import Oas 1.0

PaintImage {
    id: paintImage
    width: 800
    height: 600

    // 加载本地图像
    Component.onCompleted: {
        paintImage.set_local("file:///C:/images/screenshot.png")
    }

    // 保存裁剪区域
    Button {
        text: "保存区域"
        onClicked: {
            // 保存从 (100, 100) 开始，宽 200，高 150 的区域
            paintImage.save_target_image("100,100,200,150", "C:/output/crop.png")
        }
    }
}
```

### 6.2 在 Python 中注册类型

```python
from module.gui.fluent_app import FluentApp
from module.gui.register_type.paint_image import PaintImage

app = FluentApp()

# 注册 PaintImage 类型到 QML
# 注册后可以在 QML 中使用 import Oas 1.0
app.qml_register_type(PaintImage, "PaintImage")

FluentApp.run()
```

### 6.3 在 Python 中使用

```python
from PySide6.QtGui import QImage
from module.gui.register_type.paint_image import PaintImage

# 创建组件实例
paint = PaintImage()

# 加载图像
image = QImage("screenshot.png")
paint.set_image(image)

# 保存裁剪区域
paint.save_target_image("100,100,200,150", "crop.png")
```

---

## 7. 设计模式总结

| 设计模式 | 应用位置 | 说明 |
|---------|---------|------|
| **组件模式** | PaintImage 类 | 可复用的 QML 可视组件 |
| **属性模式** | Property 定义 | 支持 QML 属性绑定和变化通知 |
| **模板方法模式** | paint() | Qt 框架定义绘制流程，子类实现具体内容 |

**QML 集成要点：**
- 继承 `QQuickPaintedItem` 获得 QML 可视项能力
- 使用 `Property` 定义 QML 可绑定属性
- 使用 `@Slot` 暴露方法给 QML 调用
- `update()` 触发 `paint()` 重绘
- 支持文件 URL 格式 (`file:///`)
