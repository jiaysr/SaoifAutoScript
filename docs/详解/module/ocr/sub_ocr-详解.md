# module/ocr/sub_ocr.py 代码详解

## 1. 文件概述

`sub_ocr.py` 是 OCR 模块的具体实现文件，继承自 `BaseCor` 基类，提供了多种专用的 OCR 识别类：

- `Full`：大范围文本检测，支持多文本识别和关键字定位
- `Single`：单行文本识别，支持横向和竖向文本
- `Digit`：纯数字识别，带字符纠错功能
- `DigitCounter`：数字计数器识别（如 "14/15" 格式）
- `Duration`：时间时长识别（如 "01:30:00" 格式）
- `Quantity`：大数量识别（如 "6.33亿"、"1.2万" 格式）

该文件体现了**继承层次设计**，通过逐层继承和方法重写实现不同场景的 OCR 需求。

---

## 2. 导入部分解释

```python
import cv2              # OpenCV 图像处理库
import re               # 正则表达式库，用于文本解析
import cn2an            # 中文数字转阿拉伯数字库（如 "六" -> 6）

from datetime import timedelta  # 时间差类，用于表示时长

from module.ocr.ppocr import TextSystem           # PaddleOCR 文本识别系统
from module.exception import ScriptError          # 自定义脚本异常
from module.base.utils import area_pad, crop, float2str  # 工具函数
from module.ocr.base_ocr import BaseCor, OcrMode, OcrMethod  # 基类和枚举
from module.ocr.utils import merge_area           # 区域合并工具函数
from module.logger import logger                  # 日志记录器
```

---

## 3. 类定义解释

### 3.1 类继承关系

```
BaseCor (base_ocr.py)
    │
    ├── Full          # 全文检测
    │
    ├── Single        # 单行识别
    │   │
    │   ├── Digit     # 数字识别
    │   │
    │   └── DigitCounter  # 数字计数器
    │
    └── Quantity      # 大数量识别
```

---

## 4. 每个方法的逐行解释

### 4.1 `Full` 类 - 全文检测

```python
class Full(BaseCor):
    """大 ROI 范围的文本识别，支持多条文本识别，默认不支持竖方向文本"""

    def after_process(self, result):
        return result  # 不做额外后处理，直接返回

    def ocr_full(self, image, keyword: str=None) -> tuple:
        """
        检测整个图片的文本，并对结果进行过滤
        返回匹配到的 keyword 的坐标，无匹配返回 (0, 0, 0, 0)
        """
        if keyword is None:
            keyword = self.keyword  # 使用默认关键字

        boxed_results = self.detect_and_ocr(image)  # 调用基类的检测方法
        if not boxed_results:
            return 0, 0, 0, 0  # 无检测结果

        index_list = self.filter(boxed_results, keyword)  # 过滤匹配结果
        logger.info(f"OCR [{self.name}] detected in {index_list}")

        if not index_list:
            return 0, 0, 0, 0  # 无匹配

        # 匹配到多个结果时，合并坐标
        if len(index_list) > 1:
            # 构建区域列表：(x, y, width, height)
            area_list = [(
                boxed_results[index].box[0, 0],  # 左上角 x
                boxed_results[index].box[0, 1],  # 左上角 y
                boxed_results[index].box[1, 0] - boxed_results[index].box[0, 0],  # 宽度
                boxed_results[index].box[2, 1] - boxed_results[index].box[0, 1],  # 高度
            ) for index in index_list]
            area = merge_area(area_list)  # 合并所有区域
            # 转换为绝对坐标（加上 ROI 偏移）
            self.area = area[0]+self.roi[0], area[1]+self.roi[1], area[2], area[3]
        else:
            # 单个匹配结果
            box = boxed_results[index_list[0]].box
            self.area = box[0, 0]+self.roi[0], box[0, 1]+self.roi[1], box[1, 0] - box[0, 0], box[2, 1] - box[0, 1]

        logger.info(f"OCR [{self.name}] detected in {self.area}")
        return self.area
```

**设计说明**：`Full` 类的核心功能是定位关键字在图像中的位置，返回的坐标可以用于后续的点击操作。

### 4.2 `Single` 类 - 单行识别

```python
class Single(BaseCor):
    """单行文本识别，ROI 固定不动"""

    def after_process(self, result):
        return result  # 不做额外后处理

    def ocr_single(self, image) -> str:
        """
        检测固定位置 ROI 的文本，支持横向和竖向
        返回识别的文字，无结果返回空字符串
        """
        if self.roi:
            # 策略1：尝试横向单行识别
            result = self.ocr_single_line(image)
            if result != "":
                return result  # 成功识别，直接返回

            # 策略2：横向失败，尝试竖向识别
            logger.info(f"[{self.name}] Try to detect vertically")
            result = self.detect_and_ocr(image)
            if not result:
                logger.info(f"[{self.name}]: No text detected in ROI")
                return ""  # 确实无文本

            # 检查竖向识别结果的置信度
            if result[0].ocr_text != "" and result[0].score > self.score:
                return result[0].ocr_text

            return ""  # 所有策略都失败
        else:
            raise ScriptError("Roi is empty")  # ROI 未设置，抛出异常
```

**设计说明**：采用两阶段识别策略，先尝试效率更高的单行识别，失败后再使用通用检测。

### 4.3 `Digit` 类 - 数字识别

```python
class Digit(Single):
    """纯数字识别，带字符纠错"""

    def after_process(self, result):
        result = super().after_process(result)  # 调用父类后处理

        # 字符替换映射表：OCR 常见错误 -> 正确数字
        replacements = {
            'I': '1',   # 大写 I -> 1
            'D': '0',   # D -> 0
            'S': '5',   # S -> 5
            'B': '8',   # B -> 8
            '？': '2',  # 中文问号 -> 2
            '?': '2',   # 英文问号 -> 2
            'd': '6',   # 小写 d -> 6
            'o': '0',   # 小写 o -> 0
            'O': '0',   # 大写 O -> 0
            '→': '1'    # 箭头 -> 1
        }

        # 执行替换
        for old, new in replacements.items():
            result = result.replace(old, new)

        # 只保留数字字符
        result = [char for char in result if char.isdigit()]
        result = ''.join(result)

        # 转为整数
        prev = result
        result = int(result) if result else 0
        if str(result) != prev:
            logger.warning(f'OCR {self.name}: Result "{prev}" is revised to "{result}"')

        return result

    def ocr_digit(self, image) -> int:
        """返回数字，无结果返回 0"""
        result = self.ocr_single(image)
        if result == "":
            return 0
        else:
            return int(result)
```

**关键设计**：字符替换表是基于 OCR 实践经验总结的，这些字符在视觉上与数字相似，容易被误识别。

### 4.4 `DigitCounter` 类 - 数字计数器

```python
class DigitCounter(Single):
    """数字计数器识别，如 "14/15" 格式"""

    def after_process(self, result):
        result = super().after_process(result)

        # 同样的字符替换表
        replacements = {
            'I': '1', 'D': '0', 'S': '5',
            'B': '8', '？': '2', '?': '2',
            'd': '6', 'o': '0', 'O': '0',
            '→': '1'
        }

        for old, new in replacements.items():
            result = result.replace(old, new)

        # 只保留数字和斜杠
        result = [char for char in result if char.isdigit() or char == '/']
        result = ''.join(result)
        return result

    @classmethod
    def ocr_str_digit_counter(cls, result: str) ->tuple[int, int, int]:
        """
        解析数字计数器字符串
        输入: "14/15"
        输出: (14, 1, 15)  # (当前值, 剩余值, 总值)
        """
        result = re.search(r'(\d+)/(\d+)', result)  # 正则匹配 "数字/数字"
        if result:
            result = [int(s) for s in result.groups()]
            current, total = int(result[0]), int(result[1])
            if current > total:
                logger.warning(f'[{cls.name}]: Current {current} is greater than total {total}')
            return current, total - current, total  # (当前, 剩余, 总计)
        else:
            logger.warning(f'Unexpected ocr result: {result}')
            return 0, 0, 0

    def ocr_digit_counter(self, image) -> tuple[int, int, int]:
        """
        获取计数结果
        例如 "14/15" 返回 (14, 1, 15)
        无结果返回 (0, 0, 0)
        """
        result = self.ocr_single(image)
        if result == "":
            return 0, 0, 0
        return self.ocr_str_digit_counter(result)
```

**返回值说明**：`(current, remaining, total)` 三元组，其中 `remaining = total - current`，方便判断是否完成。

### 4.5 `Duration` 类 - 时长识别

```python
class Duration(Single):
    """时长识别，如 "01:30:00" 格式"""

    def after_process(self, result):
        # 字符替换：针对时间格式的常见错误
        result = result.replace('I', '1').replace('D', '0').replace('S', '5')
        result = result.replace('o', '0').replace('l', '1').replace('O', '0')
        result = result.replace('B', '8').replace('：', ':').replace(' ', '').replace('.', ':')
        result = super().after_process(result)
        return result

    @staticmethod
    def parse_time(string):
        """
        解析时间字符串
        输入: "01:30:00"
        输出: timedelta(hours=1, minutes=30, seconds=0)
        """
        result = re.search(r'(\d{1,2}):?(\d{2}):?(\d{2})', string)
        if result:
            result = [int(s) for s in result.groups()]
            return timedelta(hours=result[0], minutes=result[1], seconds=result[2])
        else:
            logger.warning(f'Invalid duration: {string}')
            return timedelta(hours=0, minutes=0, seconds=0)

    def ocr_duration(self, image) -> timedelta:
        """返回 timedelta 对象，无结果返回零时长"""
        result = self.ocr_single(image)
        if result == "":
            return timedelta(hours=0, minutes=0, seconds=0)
        return self.parse_time(result)
```

**设计说明**：使用 `timedelta` 对象而非字符串，便于后续的时间比较和计算。

### 4.6 `Quantity` 类 - 大数量识别

```python
class Quantity(BaseCor):
    """
    专门用于识别大数量
    支持格式："6.33亿"、"1.2万"、"53万/100"
    可支持负数
    """

    def after_process(self, result):
        result = super().after_process(result)

        # 字符替换
        result = result.replace('I', '1').replace('D', '0').replace('S', '5')
        result = result.replace('B', '8').replace('？', '2').replace('?', '2').replace('d', '6')

        # 只保留数字、小数点、斜杠和中文单位
        result = [char
                  for char in result
                  if char.isdigit() or char == '.' or char == '/' or char == '万' or char == '亿' or char == '千']
        result = ''.join(result)

        # 处理 "53万/100" 格式，只取斜杠前的部分
        if '/' in result:
            result_split = result.split('/')
            result = result_split[0]

        # 使用 cn2an 库将中文数字转为阿拉伯数字
        # 'smart' 模式支持 "6.33亿" -> 633000000
        result = cn2an.cn2an(result, 'smart')

        try:
            result = int(result)
        except ValueError:
            logger.warning(f'[{self.name}]: Invalid quantity: {result}')
            result = 0
        return result

    def ocr_quantity(self, image) -> int:
        """返回数量，无结果返回 0"""
        boxed_results = self.detect_and_ocr(image)
        if not boxed_results:
            logger.warning(f'[{self.name}]: No text detected')
            return 0

        # 记录检测到的区域位置
        box = boxed_results[0].box
        self.area = box[0, 0] + self.roi[0], box[0, 1] + self.roi[1], box[1, 0] - box[0, 0], box[2, 1] - box[0, 1]
        return boxed_results[0].ocr_text
```

**关键依赖**：`cn2an` 库是处理中文数字的核心，支持：
- "六" -> 6
- "六十三" -> 63
- "6.33亿" -> 633000000
- "1.2万" -> 12000

---

## 5. 核心算法流程图

### 5.1 单行识别流程 (`Single.ocr_single`)

```
输入图像
    │
    ▼
┌─────────────────┐
│  ROI 是否为空?   │──是──▶ 抛出 ScriptError
└────────┬────────┘
         │否
         ▼
┌─────────────────┐
│ 尝试横向单行识别 │
│ ocr_single_line │
└────────┬────────┘
         │
    结果非空? ──是──▶ 返回结果
         │否
         ▼
┌─────────────────┐
│ 尝试竖向识别     │
│ detect_and_ocr  │
└────────┬────────┘
         │
    有结果且置信度足够? ──是──▶ 返回结果
         │否
         ▼
    返回空字符串
```

### 5.2 数字后处理流程 (`Digit.after_process`)

```
输入: OCR 原始结果
    │
    ▼
┌─────────────────┐
│  字符替换        │
│  I→1, D→0, S→5  │
│  B→8, ?→2, o→0  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  过滤非数字字符  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   转为整数       │
└────────┬────────┘
         │
         ▼
    返回 int 结果
```

### 5.3 数量识别流程 (`Quantity.after_process`)

```
输入: OCR 原始结果
    │
    ▼
┌─────────────────┐
│  字符替换        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  保留数字、小数点│
│  斜杠和中文单位  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  处理斜杠格式    │
│  "53万/100"     │
│   -> "53万"     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  cn2an 转换      │
│  "6.33亿"       │
│   -> 633000000  │
└────────┬────────┘
         │
         ▼
    返回 int 结果
```

---

## 6. 使用示例

### 6.1 数字识别

```python
from module.ocr.sub_ocr import Digit
import cv2

# 创建数字识别器
digit_ocr = Digit(
    name="gold_amount",
    mode="DIGIT",
    method="DEFAULT",
    roi=(100, 200, 150, 40),  # 金币数量区域
    area=(0, 0, 0, 0),
    keyword=""
)

# 识别金币数量
image = cv2.imread("game_screenshot.png")
gold = digit_ocr.ocr_digit(image)
print(f"金币数量: {gold}")
# 输出: 金币数量: 12345
```

### 6.2 数字计数器

```python
from module.ocr.sub_ocr import DigitCounter
import cv2

# 创建计数器识别器
counter_ocr = DigitCounter(
    name="quest_progress",
    mode="DIGITCOUNTER",
    method="DEFAULT",
    roi=(500, 300, 100, 30),
    area=(0, 0, 0, 0),
    keyword=""
)

# 识别任务进度
image = cv2.imread("quest_screen.png")
current, remaining, total = counter_ocr.ocr_digit_counter(image)
print(f"进度: {current}/{total}, 剩余: {remaining}")
# 输出: 进度: 14/15, 剩余: 1
```

### 6.3 时长识别

```python
from module.ocr.sub_ocr import Duration
import cv2

# 创建时长识别器
duration_ocr = Duration(
    name="cooldown",
    mode="DURATION",
    method="DEFAULT",
    roi=(800, 100, 120, 35),
    area=(0, 0, 0, 0),
    keyword=""
)

# 识别冷却时间
image = cv2.imread("skill_cooldown.png")
cooldown = duration_ocr.ocr_duration(image)
print(f"冷却时间: {cooldown}")
# 输出: 冷却时间: 0:01:30
```

### 6.4 大数量识别

```python
from module.ocr.sub_ocr import Quantity
import cv2

# 创建数量识别器
qty_ocr = Quantity(
    name="gold_display",
    mode="QUANTITY",
    method="DEFAULT",
    roi=(200, 50, 200, 50),
    area=(0, 0, 0, 0),
    keyword=""
)

# 识别显示的金币
image = cv2.imread("gold_display.png")
amount = qty_ocr.ocr_quantity(image)
print(f"金币: {amount}")
# 输出: 金币: 633000000 (如果显示 "6.33亿")
```

### 6.5 全文检测定位

```python
from module.ocr.sub_ocr import Full
import cv2

# 创建全文检测器
full_ocr = Full(
    name="menu_detector",
    mode="FULL",
    method="DEFAULT",
    roi=(0, 0, 1920, 1080),  # 全屏
    area=(0, 0, 0, 0),
    keyword="探索"
)

# 检测 "探索" 按钮位置
image = cv2.imread("main_menu.png")
x, y, w, h = full_ocr.ocr_full(image, keyword="探索")
if x != 0:
    print(f"找到 '探索' 按钮: ({x}, {y}), 大小: {w}x{h}")
    # 可以用于自动化点击
```

---

## 7. 设计模式总结

| 设计模式 | 应用位置 | 说明 |
|---------|---------|------|
| **继承层次** | Full → Single → Digit/DigitCounter | 通过继承复用代码，每层添加特定功能 |
| **模板方法** | `after_process` 重写 | 子类重写后处理方法实现不同的清理逻辑 |
| **策略模式** | 不同的 `after_process` 实现 | 每个子类实现不同的文本清理策略 |
| **两阶段识别** | `Single.ocr_single` | 先尝试高效方法，失败后使用通用方法 |
| **容错设计** | 字符替换表 | 通过替换常见 OCR 错误提高识别准确率 |

### 核心设计思想

1. **渐进式识别**：从简单到复杂，先尝试单行识别，失败后再使用全文检测
2. **领域特定优化**：针对数字、时间、数量等不同领域设计专门的后处理逻辑
3. **中文数字支持**：集成 `cn2an` 库，支持游戏中的大数量显示格式
4. **错误容忍**：通过字符替换表处理 OCR 常见错误，提高实用性
