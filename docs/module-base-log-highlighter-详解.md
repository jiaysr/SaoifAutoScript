# log_highlighter.py 逐行代码详解

> 源文件路径：`module/base/log_highlighter.py`
> 作者：runhey（GitHub: https://github.com/runhey）

---

## 1. 文件概述

`log_highlighter.py` 提供日志文本的 HTML 高亮功能，用于将日志输出转换为带颜色的 HTML 格式，便于在 Web 界面或报告中展示。主要功能：
- 将日志中的时间戳、布尔值、日志级别等关键字着色
- 将换行符转换为 HTML `<br>` 标签

---

## 2. 导入部分解释

```python
import re                    # 正则表达式，用于模式匹配和替换
from html import escape      # HTML 转义（当前代码未直接使用，但作为安全导入）
```

---

## 3. 函数逐行解释

### 3.1 `replace_newline_with_br(input_text)` — 换行符转换

```python
def replace_newline_with_br(input_text):
    replaced_text = input_text.replace('\n', '<br>')
    return replaced_text
```

**第 7-9 行**：将文本中的 `\n` 替换为 HTML 换行标签 `<br>`。

### 3.2 `highlight_text(input_text)` — 日志高亮

```python
def highlight_text(input_text):
```

**第 11 行**：定义高亮函数。

```python
    color_mapping = {
        r'\d{2}:\d{2}:\d{2}\.\d{3}': 'cyan',       # 时间戳 13:20:36.411
        r'\bTrue\b': 'lime',                         # True 值
        r'\bFalse\b': 'red',                         # False 值
        r'DEBUG': 'cyan',                            # DEBUG 级别
        r'INFO': 'green',                            # INFO 级别
        r'WARNING': 'yellow',                        # WARNING 级别
        r'ERROR': 'red',                             # ERROR 级别
        r'CRITICAL': 'darkred'                       # CRITICAL 级别
    }
```

**第 12-21 行**：定义正则模式到颜色的映射表：
| 模式 | 颜色 | 匹配内容 |
|------|------|----------|
| `\d{2}:\d{2}:\d{2}\.\d{3}` | cyan（青色） | 时间戳格式 |
| `\bTrue\b` | lime（亮绿色） | 单词 True |
| `\bFalse\b` | red（红色） | 单词 False |
| `DEBUG` | cyan | DEBUG 日志级别 |
| `INFO` | green | INFO 日志级别 |
| `WARNING` | yellow | WARNING 日志级别 |
| `ERROR` | red | ERROR 日志级别 |
| `CRITICAL` | darkred | CRITICAL 日志级别 |

```python
    for pattern, color in color_mapping.items():
        input_text = re.sub(
            pattern,
            f'<span style="color: {color}">\\g<0></span>',
            input_text
        )
```

**第 23-24 行**：
- 遍历每个模式-颜色对
- 使用 `re.sub` 将匹配的文本包裹在 `<span style="color: ...">` 标签中
- `\\g<0>` 引用整个匹配的文本

```python
    return replace_newline_with_br(input_text)
```

**第 26 行**：最后将换行符转为 `<br>` 并返回。

---

## 4. 核心算法流程图

```
输入: "13:20:36.411 INFO: Task completed. Result: True"
 │
 ▼
遍历 color_mapping:
  步骤1: 匹配 \d{2}:\d{2}:\d{2}\.\d{3}
    → "<span style='color:cyan'>13:20:36.411</span> INFO: Task completed. Result: True"
  步骤2: 匹配 INFO
    → "<span style='color:cyan'>13:20:36.411</span> <span style='color:green'>INFO</span>: Task completed. Result: True"
  步骤3: 匹配 True
    → "...Result: <span style='color:lime'>True</span>"
  ... (其他模式)
 │
 ▼
替换 \n → <br>
 │
 ▼
输出 HTML 高亮文本
```

---

## 5. 使用示例

```python
# 基本用法
log_line = "13:20:36.411 INFO: Task completed. Result: True"
html = highlight_text(log_line)
# 结果: '<span style="color: cyan">13:20:36.411</span> <span style="color: green">INFO</span>: Task completed. Result: <span style="color: lime">True</span>'

# 包装为完整 HTML
html_page = f'<html><body>{highlight_text(log_text)}</body></html>'

# 多行日志
multi_line = "10:00:00.000 INFO: Start\n10:00:01.000 ERROR: Failed"
html = highlight_text(multi_line)
# 换行符被转为 <br>
```

---

## 6. 设计模式总结

| 模式 | 说明 |
|------|------|
| **映射驱动** | 使用字典将正则模式映射到颜色，易于扩展新的高亮规则 |
| **链式替换** | 按顺序逐个应用正则替换，后面的替换不会影响前面的结果 |
| **关注点分离** | `replace_newline_with_br` 独立处理换行，`highlight_text` 专注颜色高亮 |
