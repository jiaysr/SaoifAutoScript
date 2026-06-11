# module/atom/animate.py 逐行代码详解

## 文件概述
这是一个**动画稳定性检测**模块，用于判断游戏界面的动画是否播放完毕。通过比较连续两帧截图的目标区域是否一致来实现。

---

## 导入部分 (第1-7行)

```python
from pathlib import Path                    # 导入路径处理库，用于处理文件路径
from module.logger import logger            # 导入项目的日志系统

from module.atom.image import RuleImage     # 导入图像匹配规则类
from module.atom.click import RuleClick     # 导入点击规则类
from module.atom.long_click import RuleLongClick  # 导入长按规则类
from module.atom.ocr import RuleOcr         # 导入OCR识别规则类
```

**作用**：导入所有需要的类和模块，用于后续的动画检测功能。

---

## 类定义 (第10行)

```python
class RuleAnimate(RuleImage):  # 定义RuleAnimate类，继承自RuleImage
```

**继承关系**：
- `RuleAnimate` 继承 `RuleImage`
- 获得图像匹配的所有能力（`match()`方法等）
- 在此基础上添加动画稳定性检测功能

---

## 构造函数 (第12-44行)

```python
def __init__(self,
             rule: RuleImage | RuleClick | RuleLongClick | RuleOcr,  # 参数类型：支持4种规则类型
             threshold: float = 0.75,  # 匹配阈值，默认0.75（75%相似度）
             name: str = None):        # 可选的自定义名称
```

### 参数处理逻辑 (第16-32行)

```python
if isinstance(rule, RuleImage):           # 如果传入的是RuleImage类型
    roi_front = rule.roi_front            # 获取前景区域（点击目标区域）
    roi_back = rule.roi_back              # 获取背景区域（搜索区域）
    self._name = Path(rule.file).stem.upper()  # 从文件路径提取名称，转大写
    threshold = threshold                 # 使用传入的阈值

elif isinstance(rule, RuleClick) or isinstance(rule, RuleLongClick):  # 如果是点击或长按规则
    roi_front = rule.roi_front            # 获取前景区域
    roi_back = rule.roi_back              # 获取背景区域
    self._name = rule.name                # 直接使用规则的名称

elif isinstance(rule, RuleOcr):           # 如果是OCR规则
    roi_front = rule.roi                  # OCR使用roi属性
    roi_back = rule.area                  # OCR使用area属性
    self._name = rule.name                # 使用规则名称

else:                                     # 其他类型
    roi_front = None                      # 前景区域为空
    roi_back = None                       # 背景区域为空
    self._name = 'RuleAnimate'            # 使用默认名称
```

**设计模式**：适配器模式 - 将不同类型的规则统一转换为RuleImage需要的格式

### 调用父类构造函数 (第34-40行)

```python
super().__init__(                    # 调用RuleImage的构造函数
    roi_front=list(roi_front),       # 转换为列表格式
    roi_back=list(roi_back),         # 转换为列表格式
    method='Template matching',      # 使用模板匹配方法
    threshold=threshold,             # 匹配阈值
    file=''                          # 文件路径为空（因为是动态比较，不需要模板图片）
)
```

**关键点**：`file=''` 表示这个类不需要预设的模板图片，而是动态比较两帧截图

### 初始化完成 (第42-44行)

```python
if name is not None:                 # 如果传入了自定义名称
    self._name = name                # 使用自定义名称
self._last_image = None              # 初始化上一帧图像为None
```

---

## name属性 (第46-48行)

```python
@property                            # 将方法转为属性装饰器
def name(self) -> str:               # 返回类型为字符串
    return self._name.upper()        # 返回大写的名称
```

**作用**：提供只读的name属性，自动转为大写

---

## stable方法 - 核心功能 (第50-70行)

```python
def stable(self, image, refresh_after_stable: bool = False) -> bool:
    """
    用于判断连续的两张截图，的目标区域是否一致
    @param image: 当前截图
    @param refresh_after_stable: 稳定后是否刷新缓存
    @return: True表示动画稳定（停止），False表示还在播放
    """
```

### 第一帧处理 (第57-59行)

```python
if self._last_image is None:         # 如果是第一帧（没有上一帧）
    self._last_image = image         # 保存当前帧作为上一帧
    return False                     # 返回False，因为无法比较
```

**逻辑**：第一帧无法比较，需要等待第二帧

### 后续帧处理 (第61-63行)

```python
self._image = self._last_image       # 将上一帧设置为匹配模板
matched = self.match(image)          # 用上一帧匹配当前帧
self._last_image = self.corp(image, self.roi_front)  # 裁剪当前帧的目标区域，保存为下一帧的模板
```

**关键逻辑**：
1. `self._image = self._last_image`：设置匹配模板为上一帧
2. `self.match(image)`：调用父类的match方法，比较上一帧和当前帧
3. `self.corp(image, self.roi_front)`：裁剪当前帧的目标区域，准备下次比较

### 结果判断 (第65-70行)

```python
if matched:                          # 如果匹配成功（两帧相似）
    if refresh_after_stable:         # 如果设置了稳定后刷新
        self.refresh()               # 刷新缓存
    logger.info(f'Animation Stable @ {self.name}')  # 记录日志
    return True                      # 返回True，动画稳定
return False                         # 不匹配，返回False，动画还在播放
```

---

## refresh方法 (第72-73行)

```python
def refresh(self):
    self._last_image = None          # 重置上一帧为None
```

**作用**：重置检测状态，重新开始检测

---

## 测试代码 (第76-88行)

```python
if __name__ == '__main__':           # 只有直接运行此文件时才执行
    from module.base.utils import load_image      # 导入图像加载函数
    from tasks.SixRealms.assets import SixRealmsAssets  # 导入六道之门资源
    
    ttt = RuleAnimate(SixRealmsAssets.C_MAIN_ANIMATE_KEEP, threshold=0.5)  # 创建动画检测实例
    
    imga = r'C:\Users\Ryland\Desktop\Desktop\37.png'  # 第一张测试图片路径
    imgb = r'C:\Users\Ryland\Desktop\Desktop\38.png'  # 第二张测试图片路径
    
    imga = load_image(imga)          # 加载图片
    imgb = load_image(imgb)          # 加载图片
    
    print(ttt.stable(imga))          # 第一帧：False（无法比较）
    print(ttt.stable(imgb))          # 第二帧：取决于是否相似
    print(ttt.stable(imgb))          # 第三帧：与第二帧相同，应该返回True
```

---

## 核心算法流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    stable() 方法执行流程                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 接收当前截图 image                                       │
│           ↓                                                 │
│  2. 检查 _last_image 是否为 None                             │
│      ├─ 是 → 保存 image 到 _last_image，返回 False           │
│      └─ 否 ↓                                                │
│                                                             │
│  3. 设置 self._image = _last_image（上一帧作为模板）          │
│           ↓                                                 │
│  4. 调用 self.match(image) 比较上一帧和当前帧                 │
│           ↓                                                 │
│  5. 裁剪当前帧的目标区域，保存到 _last_image                  │
│           ↓                                                 │
│  6. 判断匹配结果                                             │
│      ├─ 匹配成功 → 返回 True（动画稳定）                     │
│      └─ 匹配失败 → 返回 False（动画还在播放）                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 使用示例

```python
from module.atom.animate import RuleAnimate
from tasks.GameUi.assets import GameUiAssets

# 创建动画检测实例
animate = RuleAnimate(GameUiAssets.I_LOADING, threshold=0.8)

# 在任务中使用
def run(self):
    while True:
        self.screenshot()
        
        # 检测加载动画是否结束
        if animate.stable(self.device.image):
            logger.info("加载完成")
            break
        
        time.sleep(0.1)  # 等待100ms再检测
```

---

## 设计模式总结

| 模式 | 应用 | 说明 |
|------|------|------|
| **继承** | RuleAnimate → RuleImage | 复用图像匹配能力 |
| **适配器** | 支持4种规则类型 | 统一不同规则的接口 |
| **模板方法** | stable() 定义检测流程 | 子类可重写具体步骤 |
| **状态模式** | _last_image 管理状态 | 根据状态返回不同结果 |
