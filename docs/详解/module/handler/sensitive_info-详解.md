# module/handler/sensitive_info.py 代码详解

## 1. 文件概述

`sensitive_info.py` 是敏感信息处理模块，用于在日志和图像中隐藏用户的本地文件路径等隐私信息。通过正则表达式替换和图像遮罩技术，保护用户隐私数据不被泄露。

**文件路径**: `module/handler/sensitive_info.py`
**代码行数**: 40 行
**主要功能**:
- 处理敏感图像（应用遮罩）
- 处理敏感文本（路径替换）
- 处理敏感日志（批量替换）

---

## 2. 导入部分解释

```python
import re
```

| 导入项 | 来源模块 | 说明 |
|--------|----------|------|
| `re` | Python标准库 | 正则表达式模块，用于文本模式匹配和替换 |

**注释掉的导入**:
```python
# from module.base.mask import Mask
# from module.ui.page import *
# MASK_MAIN = Mask('./assets/mask/MASK_MAIN.png')
# MASK_PLAYER = Mask('./assets/mask/MASK_PLAYER.png')
```

这些是图像遮罩相关的导入，当前版本已禁用，但保留代码以备后续使用。

---

## 3. 类定义解释

本模块没有类定义，仅包含三个独立的函数：
- `handle_sensitive_image`: 图像敏感信息处理
- `handle_sensitive_text`: 文本敏感信息处理
- `handle_sensitive_logs`: 日志敏感信息处理

---

## 4. 每个方法的逐行解释

### handle_sensitive_image 函数

```python
def handle_sensitive_image(image):
    """
    Args:
        image:
    Returns:
        np.ndarray:
    """
    return image
```

| 行号 | 代码 | 说明 |
|------|------|------|
| 10 | `def handle_sensitive_image(image):` | 函数定义，接收图像作为参数 |
| 11-17 | 文档字符串 | 说明参数为图像，返回 numpy 数组 |
| 18-21 | 注释代码 | 预留的图像遮罩逻辑（当前禁用） |
| 23 | `return image` | 直接返回原图像（当前未做处理） |

**设计说明**: 函数预留了图像遮罩处理接口，当前版本直接返回原图。注释中的代码显示计划对玩家界面和主界面应用遮罩。

### handle_sensitive_text 函数

```python
def handle_sensitive_text(text):
    """
    Args:
        text (str):
    Returns:
        str:
    """
    text = re.sub('File \"(.*?)AzurLaneAutoScript', 'File \"C:\\\\fakepath\\\\AzurLaneAutoScript', text)
    text = re.sub('\[Adb_binary\] (.*?)AzurLaneAutoScript', '[Adb_binary] C:\\\\fakepath\\\\AzurLaneAutoScript', text)
    return text
```

| 行号 | 代码 | 说明 |
|------|------|------|
| 26 | `def handle_sensitive_text(text):` | 函数定义，接收文本字符串 |
| 34 | `text = re.sub(...)` | 第一次替换：将 `File "xxx/AzurLaneAutoScript` 替换为 `File "C:\fakepath\AzurLaneAutoScript` |
| 35 | `text = re.sub(...)` | 第二次替换：将 `[Adb_binary] xxx/AzurLaneAutoScript` 替换为 `[Adb_binary] C:\fakepath\AzurLaneAutoScript` |
| 36 | `return text` | 返回处理后的文本 |

**正则表达式解析**:
- `'File \"(.*?)AzurLaneAutoScript'`: 匹配以 `File "` 开头，到 `AzurLaneAutoScript` 结束的字符串
  - `(.*?)`: 非贪婪匹配，捕获任意字符（即用户的真实路径）
- `'\[Adb_binary\] (.*?)AzurLaneAutoScript'`: 匹配 ADB 二进制路径
  - `\[Adb_binary\]`: 转义的方括号，匹配字面量 `[Adb_binary]`

### handle_sensitive_logs 函数

```python
def handle_sensitive_logs(logs):
    return [handle_sensitive_text(line) for line in logs]
```

| 行号 | 代码 | 说明 |
|------|------|------|
| 39 | `def handle_sensitive_logs(logs):` | 函数定义，接收日志列表 |
| 40 | `return [handle_sensitive_text(line) for line in logs]` | 列表推导式，对每行日志调用 `handle_sensitive_text` 处理 |

---

## 5. 核心算法流程图

```
┌─────────────────────────────────────────────────┐
│              敏感信息处理流程                     │
└───────────────────────┬─────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│   图像处理     │ │   文本处理     │ │   日志处理     │
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘
        │                 │                 │
        ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ 直接返回原图   │ │ 正则替换路径   │ │ 批量处理每行   │
│ （预留接口）   │ │               │ │               │
└───────────────┘ └───────┬───────┘ └───────┬───────┘
                          │                 │
                          ▼                 ▼
                  ┌───────────────┐ ┌───────────────┐
                  │ File "xxx/... │ │ 对每行调用     │
                  │  → File "C:\  │ │ handle_       │
                  │  fakepath\... │ │ sensitive_text│
                  └───────────────┘ └───────────────┘
```

### 文本替换流程

```
输入: 'File "/home/user/AzurLaneAutoScript/main.py"'
                │
                ▼
┌───────────────────────────────────────┐
│ re.sub('File "(.*?)AzurLaneAutoScript │
│        → 'File "C:\\fakepath\\...     │
└───────────────────┬───────────────────┘
                    │
                    ▼
输出: 'File "C:\fakepath\AzurLaneAutoScript/main.py"'
```

---

## 6. 使用示例

### 处理单条文本

```python
from module.handler.sensitive_info import handle_sensitive_text

# 原始文本包含用户真实路径
original = 'File "/home/username/AzurLaneAutoScript/module/main.py", line 42'
safe_text = handle_sensitive_text(original)
print(safe_text)
# 输出: File "C:\fakepath\AzurLaneAutoScript/module/main.py", line 42
```

### 处理日志列表

```python
from module.handler.sensitive_info import handle_sensitive_logs

logs = [
    'File "/home/user/AzurLaneAutoScript/main.py", line 10',
    '[Adb_binary] /home/user/AzurLaneAutoScript/adb',
    'Normal log message without path'
]

safe_logs = handle_sensitive_logs(logs)
for log in safe_logs:
    print(log)
# 输出:
# File "C:\fakepath\AzurLaneAutoScript/main.py", line 10
# [Adb_binary] C:\fakepath\AzurLaneAutoScript/adb
# Normal log message without path
```

### 处理图像（当前版本直接返回）

```python
from module.handler.sensitive_info import handle_sensitive_image
import numpy as np

image = np.zeros((100, 100, 3), dtype=np.uint8)
safe_image = handle_sensitive_image(image)
# 当前版本直接返回原图
```

---

## 7. 设计模式总结

| 设计模式 | 应用说明 |
|----------|----------|
| **函数式编程** | 使用纯函数处理数据，无副作用 |
| **策略模式** | 不同类型的敏感信息使用不同的处理策略 |
| **门面模式** | 提供统一的 `handle_sensitive_*` 接口简化调用 |
| **列表推导式** | `handle_sensitive_logs` 使用列表推导式实现批量处理 |

**设计优点**:
- 职责单一，每个函数只处理一种类型的敏感信息
- 正则表达式精确匹配，避免误替换
- 预留图像处理接口，便于后续扩展
- 代码简洁，易于维护

**隐私保护策略**:
- 将用户真实路径替换为 `C:\fakepath\` 虚假路径
- 保持路径后半部分不变，便于调试定位
- 支持多种路径格式的识别和替换

**待完成功能**:
- 图像遮罩处理（代码已预留，当前禁用）
- 可能需要扩展支持更多路径格式
