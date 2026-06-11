# filter.py 逐行代码详解

> 源文件路径：`module/base/filter.py`
> 参考来源：[AzurLaneAutoScript](https://github.com/LmeSzinc/AzurLaneAutoScript/blob/master/module/base/filter.py)

---

## 1. 文件概述

`filter.py` 实现了一个通用的字符串过滤器解析框架。它能够：
- 解析用 `>` 分隔的过滤器字符串
- 通过正则表达式提取过滤条件
- 将过滤条件应用到对象列表上，返回匹配的对象
- 支持预设（preset）关键字

主要用于自动化脚本中对任务、装备、角色等对象的选择和排序。

---

## 2. 导入部分解释

```python
import re                                    # 正则表达式模块，用于解析过滤器字符串
from module.logger import logger             # 项目日志模块，用于输出警告信息
```

---

## 3. Filter 类逐行解释

### 3.1 `__init__(self, regex, attr, preset=())` — 构造函数

```python
class Filter:
    def __init__(self, regex, attr, preset=()):
```

**第 7-8 行**：定义 Filter 类。参数说明：
- `regex`：正则表达式，用于解析每条过滤条件
- `attr`：属性名列表，与正则捕获组一一对应
- `preset`：预设关键字列表（如 `'reset'`、`'default'`）

```python
        if isinstance(regex, str):
            regex = re.compile(regex)
```

**第 15-16 行**：如果 `regex` 是字符串，则编译为正则表达式对象。

```python
        self.regex = regex
        self.attr = attr
        self.preset = tuple(list(p.lower() for p in preset))
        self.filter_raw = []
        self.filter = []
```

**第 17 行**：保存正则对象。
**第 18 行**：保存属性名列表。
**第 19 行**：将预设关键字统一转小写并存储为元组。
**第 20 行**：`filter_raw` 存储原始过滤器字符串列表。
**第 21 行**：`filter` 存储解析后的过滤条件列表。

---

### 3.2 `load(self, string)` — 加载过滤器字符串

```python
    def load(self, string):
```

**第 23 行**：加载一个过滤器字符串。

```python
        string = str(string)
        string = re.sub(r'[ \t\r\n]', '', string)
        string = re.sub(r'[＞﹥›˃ᐳ❯]', '>', string)
```

**第 36 行**：确保输入为字符串。
**第 37 行**：去除所有空白字符（空格、制表符、换行符）。
**第 38 行**：将各种 Unicode 类 `>` 字符统一替换为标准 `>`（`＞`、`﹥`、`›`、`˃`、`ᐳ`、`❯`）。

```python
        self.filter_raw = string.split('>')
        self.filter = [self.parse_filter(f) for f in self.filter_raw]
```

**第 39 行**：以 `>` 分割得到原始过滤条件列表。
**第 40 行**：对每条原始条件调用 `parse_filter` 进行解析。

---

### 3.3 `is_preset(self, filter)` — 判断是否为预设

```python
    def is_preset(self, filter):
        return len(filter) and filter.lower() in self.preset
```

**第 42-43 行**：检查字符串是否非空且在预设列表中（不区分大小写）。

---

### 3.4 `apply(self, objs, func=None)` — 应用过滤器

```python
    def apply(self, objs, func=None):
```

**第 45 行**：将过滤器应用到对象列表上。

```python
        out = []
        for raw, filter in zip(self.filter_raw, self.filter):
```

**第 56-57 行**：遍历原始字符串和解析后的过滤条件。

```python
            if self.is_preset(raw):
                raw = raw.lower()
                if raw not in out:
                    out.append(raw)
```

**第 58-61 行**：如果是预设关键字，转小写后去重添加到输出。

```python
            else:
                for index, obj in enumerate(objs):
                    if self.apply_filter_to_obj(obj=obj, filter=filter) and obj not in out:
                        out.append(obj)
```

**第 62-65 行**：否则遍历所有对象，将满足条件且未重复的对象添加到输出。

```python
        if func is not None:
            objs, out = out, []
            for obj in objs:
                if isinstance(obj, str):
                    out.append(obj)
                elif func(obj):
                    out.append(obj)
                else:
                    pass
```

**第 67-76 行**：如果提供了额外的过滤函数 `func`，对结果进行二次过滤。字符串（预设）直接保留，对象需要通过 `func` 检查。

```python
        return out
```

**第 78 行**：返回过滤后的列表。

---

### 3.5 `applys(self, objs, funcs)` — 多重过滤

```python
    def applys(self, objs, funcs):
        return self.apply(objs, func=lambda x: all(func(x) for func in funcs))
```

**第 80-91 行**：接收多个过滤函数，使用 `all()` 组合——对象必须通过所有过滤函数才算匹配。

---

### 3.6 `apply_filter_to_obj(self, obj, filter)` — 单对象匹配

```python
    def apply_filter_to_obj(self, obj, filter):
```

**第 93 行**：检查单个对象是否满足过滤条件。

```python
        for attr, value in zip(self.attr, filter):
            if not value:
                continue
            if str(obj.__getattribute__(attr)).lower() != str(value):
                return False
        return True
```

**第 103-109 行**：
- 遍历属性名和对应的过滤值
- 如果过滤值为空（`None` 或空字符串），跳过该条件
- 将对象属性和过滤值都转为小写字符串进行比较
- 任何一个条件不满足就返回 `False`
- 全部满足返回 `True`

---

### 3.7 `parse_filter(self, string)` — 解析单条过滤条件

```python
    def parse_filter(self, string):
```

**第 111 行**：解析单条过滤条件字符串。

```python
        string = string.replace(' ', '').lower()
        result = re.search(self.regex, string)
```

**第 119 行**：去除空格并转小写。
**第 120 行**：用正则表达式搜索匹配。

```python
        if self.is_preset(string):
            return [string]
```

**第 122-123 行**：如果是预设关键字，直接返回。

```python
        if result and len(string) and result.span()[1]:
            return [result.group(index + 1) for index, attr in enumerate(self.attr)]
```

**第 125-126 行**：如果正则匹配成功，提取各捕获组的值作为过滤条件。

```python
        else:
            logger.warning(f'Invalid filter: "{string}". ...')
            return ['1nVa1d'] + [None] * (len(self.attr) - 1)
```

**第 128-131 行**：匹配失败时记录警告，并返回一个不可能匹配任何对象的条件（`'1nVa1d'`），确保无效过滤器不会误匹配。

---

## 4. 类属性和数据结构

```
filter_raw: ["gold", "purple > 10", "reset"]
filter:     [["gold"], ["purple", "10"], ["reset"]]

apply() 输出示例:
  [obj_gold_1, obj_purple_2, "reset"]
```

---

## 5. 核心算法流程图

### 过滤器解析流程

```
输入字符串: "gold > purple > 10 > reset"
 │
 ▼
去除空白 + Unicode标准化
 │
 ▼
以 ">" 分割: ["gold", "purple", "10", "reset"]
 │
 ▼
逐条解析:
  "gold"   → 正则匹配 → 过滤条件
  "purple" → 正则匹配 → 过滤条件
  "10"     → 正则匹配 → 过滤条件
  "reset"  → 预设匹配 → 直接保留
 │
 ▼
输出: [条件1, 条件2, 条件3, "reset"]
```

### apply() 匹配流程

```
输入: objs=[装备A, 装备B, 装备C], filter条件列表
 │
 ▼
遍历每条 filter:
  ├─ 是预设? → 加入输出
  └─ 不是? → 遍历所有 obj:
              ├─ 属性匹配? → 加入输出(去重)
              └─ 不匹配? → 跳过
 │
 ▼
有 func 二次过滤?
  ├─ 有 → 逐个检查
  └─ 无 → 直接返回
 │
 ▼
返回结果列表
```

---

## 6. 使用示例

```python
import re

# 定义过滤器：正则表达式提取颜色和数量
filter_obj = Filter(
    regex=r'(\w+)(\d+)?',       # 匹配 "gold10" 或 "purple"
    attr=['color', 'amount'],    # 对应属性名
    preset=['reset', 'default']  # 预设关键字
)

# 加载过滤器字符串
filter_obj.load('gold > purple > 10 > reset')

# 应用过滤器
result = filter_obj.apply(equipments)
# 返回: [gold装备, purple装备, "reset"]
```

---

## 7. 设计模式总结

| 模式 | 说明 |
|------|------|
| **策略模式** | 通过正则表达式和属性名配置，实现不同过滤策略 |
| **管道模式** | `>` 分隔的过滤条件形成处理管道，按优先级排列 |
| **防御性编程** | 无效过滤器返回不可能匹配的值 `'1nVa1d'`，而非抛异常 |
| **Unicode 标准化** | 自动处理多种类 `>` 字符，提升用户体验 |
| **二次过滤** | `apply()` 支持 `func` 参数实现额外的业务逻辑过滤 |
