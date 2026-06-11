# module/server/annotator_rule_schema.py 详解

## 1. 文件概述

`annotator_rule_schema.py` 是标注器规则模式定义模块，负责：
- 定义各种规则类型的模式
- 提供规则字段的默认值和选项
- 生成规则模式数据
- 合并规则和默认值

## 2. 导入部分解释

```python
from __future__ import annotations  # 支持延迟注解
from collections import OrderedDict  # 有序字典
from copy import deepcopy            # 深拷贝
from typing import Any               # 类型提示
```

## 3. 类定义解释

此文件没有定义类，主要包含常量和函数。

### RULE_TYPE_SCHEMAS 常量（第7-160行）
```python
RULE_TYPE_SCHEMAS: OrderedDict[str, dict[str, Any]] = OrderedDict(
    {
        "image": {
            "type": "image",
            "label": "RuleImage",
            "capabilities": {
                "supports_test": True,
                "supports_crop": True,
                "supports_image_preview": True,
                "shared_roi_back": False,
            },
            "fields": [
                {"key": "itemName", "label": "itemName", "control": "text", "default": "new"},
                {
                    "key": "imageName",
                    "label": "imageName",
                    "control": "text",
                    "default": "",
                    "auto_from_item_name": True,
                },
                {
                    "key": "method",
                    "label": "method",
                    "control": "select",
                    "default": "Template matching",
                    "options": ["Template matching", "Sift Flann"],
                },
                {
                    "key": "threshold",
                    "label": "threshold",
                    "control": "number",
                    "default": 0.8,
                    "step": 0.01,
                    "min": 0,
                    "max": 1,
                    "integer": False,
                },
                {"key": "description", "label": "description", "control": "textarea", "default": "", "full": True},
            ],
        },
        "ocr": {
            "type": "ocr",
            "label": "RuleOcr",
            "capabilities": {
                "supports_test": True,
                "supports_crop": False,
                "supports_image_preview": False,
                "shared_roi_back": False,
            },
            "fields": [
                {"key": "itemName", "label": "itemName", "control": "text", "default": "new"},
                {
                    "key": "mode",
                    "label": "mode",
                    "control": "select",
                    "default": "Single",
                    "options": ["Single", "Full", "Digit", "DigitCounter", "Duration", "Quantity"],
                },
                {"key": "method", "label": "method", "control": "text", "default": "Default"},
                {"key": "keyword", "label": "keyword", "control": "text", "default": ""},
                {"key": "description", "label": "description", "control": "textarea", "default": "", "full": True},
            ],
        },
        "click": {
            "type": "click",
            "label": "RuleClick",
            "capabilities": {
                "supports_test": False,
                "supports_crop": False,
                "supports_image_preview": False,
                "shared_roi_back": False,
            },
            "fields": [
                {"key": "itemName", "label": "itemName", "control": "text", "default": "new"},
                {"key": "description", "label": "description", "control": "textarea", "default": "", "full": True},
            ],
        },
        "swipe": {
            "type": "swipe",
            "label": "RuleSwipe",
            "capabilities": {
                "supports_test": False,
                "supports_crop": False,
                "supports_image_preview": False,
                "shared_roi_back": False,
            },
            "fields": [
                {"key": "itemName", "label": "itemName", "control": "text", "default": "new"},
                {
                    "key": "mode",
                    "label": "mode",
                    "control": "select",
                    "default": "default",
                    "options": ["default", "vector"],
                },
                {"key": "description", "label": "description", "control": "textarea", "default": "", "full": True},
            ],
        },
        "long_click": {
            "type": "long_click",
            "label": "RuleLongClick",
            "capabilities": {
                "supports_test": False,
                "supports_crop": False,
                "supports_image_preview": False,
                "shared_roi_back": False,
            },
            "fields": [
                {"key": "itemName", "label": "itemName", "control": "text", "default": "new"},
                {
                    "key": "duration",
                    "label": "duration(ms)",
                    "control": "number",
                    "default": 1000,
                    "min": 1,
                    "step": 1,
                    "integer": True,
                },
                {"key": "description", "label": "description", "control": "textarea", "default": "", "full": True},
            ],
        },
        "list": {
            "type": "list",
            "label": "RuleList",
            "capabilities": {
                "supports_test": True,
                "supports_crop": True,
                "supports_image_preview": True,
                "shared_roi_back": True,
            },
            "fields": [
                {"key": "itemName", "label": "itemName", "control": "text", "default": "new"},
            ],
            "meta_fields": [
                {"key": "name", "label": "list.name", "control": "text", "default": "list_name"},
                {
                    "key": "direction",
                    "label": "list.direction",
                    "control": "select",
                    "default": "vertical",
                    "options": ["vertical", "horizontal"],
                },
                {
                    "key": "type",
                    "label": "list.type",
                    "control": "select",
                    "default": "image",
                    "options": ["image", "ocr"],
                },
                {"key": "description", "label": "list.description", "control": "text", "default": ""},
            ],
        },
    }
)
```

## 4. 每个方法的逐行解释

### ROI_DEFAULT 常量（第163行）
```python
ROI_DEFAULT = "0,0,100,100"  # 默认 ROI 值
```

### get_rule_types 函数（第166-167行）
```python
def get_rule_types() -> list[str]:
    return list(RULE_TYPE_SCHEMAS.keys())  # 返回所有规则类型
```

### get_rule_schema 函数（第170-174行）
```python
def get_rule_schema(rule_type: str) -> dict[str, Any]:
    schema = RULE_TYPE_SCHEMAS.get(str(rule_type or "").strip())  # 获取规则模式
    if not schema:
        schema = RULE_TYPE_SCHEMAS["image"]  # 默认使用 image 模式
    return deepcopy(schema)  # 返回深拷贝
```

### get_rule_schemas 函数（第177-178行）
```python
def get_rule_schemas() -> list[dict[str, Any]]:
    return [get_rule_schema(rule_type) for rule_type in get_rule_types()]  # 返回所有规则模式
```

### get_schema_payload 函数（第181-185行）
```python
def get_schema_payload() -> dict[str, Any]:
    return {
        "rule_types": get_rule_types(),  # 规则类型列表
        "schemas": {rule_type: get_rule_schema(rule_type) for rule_type in get_rule_types()},  # 规则模式字典
    }
```

### _field_defaults 函数（第188-189行）
```python
def _field_defaults(fields: list[dict[str, Any]]) -> dict[str, Any]:
    return {field["key"]: deepcopy(field.get("default")) for field in fields}  # 返回字段默认值字典
```

### default_rule 函数（第192-198行）
```python
def default_rule(rule_type: str) -> dict[str, Any]:
    schema = get_rule_schema(rule_type)  # 获取规则模式
    rule = _field_defaults(schema.get("fields", []))  # 获取字段默认值
    rule["roiFront"] = ROI_DEFAULT  # 设置默认 ROI
    if rule_type != "list":
        rule["roiBack"] = ROI_DEFAULT  # 非 list 类型设置 roiBack
    return rule
```

### default_list_meta 函数（第201-205行）
```python
def default_list_meta() -> dict[str, Any]:
    schema = get_rule_schema("list")  # 获取 list 规则模式
    meta = _field_defaults(schema.get("meta_fields", []))  # 获取元数据字段默认值
    meta["roiBack"] = ROI_DEFAULT  # 设置默认 ROI
    return meta
```

### merge_rule_with_defaults 函数（第208-214行）
```python
def merge_rule_with_defaults(rule_type: str, rule: dict[str, Any] | None) -> dict[str, Any]:
    merged = default_rule(rule_type)  # 获取默认规则
    if isinstance(rule, dict):
        merged.update(rule)  # 合并规则
    if rule_type == "list":
        merged.pop("description", None)  # list 类型移除 description
    return merged
```

### merge_list_meta_with_defaults 函数（第217-221行）
```python
def merge_list_meta_with_defaults(meta: dict[str, Any] | None) -> dict[str, Any]:
    merged = default_list_meta()  # 获取默认元数据
    if isinstance(meta, dict):
        merged.update(meta)  # 合并元数据
    return merged
```

### field_default 函数（第224-230行）
```python
def field_default(rule_type: str, key: str, fallback: Any = None) -> Any:
    schema = get_rule_schema(rule_type)  # 获取规则模式
    fields = list(schema.get("fields", [])) + list(schema.get("meta_fields", []))  # 合并字段
    for field in fields:
        if field.get("key") == key:  # 查找字段
            return deepcopy(field.get("default"))  # 返回默认值
    return fallback  # 返回回退值
```

### field_options 函数（第233-239行）
```python
def field_options(rule_type: str, key: str) -> list[str]:
    schema = get_rule_schema(rule_type)  # 获取规则模式
    fields = list(schema.get("fields", [])) + list(schema.get("meta_fields", []))  # 合并字段
    for field in fields:
        if field.get("key") == key:  # 查找字段
            return list(field.get("options", []))  # 返回选项
    return []  # 返回空列表
```

## 5. 核心算法流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    规则模式结构                               │
├─────────────────────────────────────────────────────────────┤
│  RULE_TYPE_SCHEMAS                                           │
│  ├─ image: 图片规则                                          │
│  │   ├─ type: "image"                                        │
│  │   ├─ label: "RuleImage"                                   │
│  │   ├─ capabilities: 能力配置                               │
│  │   └─ fields: 字段定义                                     │
│  ├─ ocr: OCR 规则                                            │
│  ├─ click: 点击规则                                          │
│  ├─ swipe: 滑动规则                                          │
│  ├─ long_click: 长按规则                                     │
│  └─ list: 列表规则                                           │
│      ├─ fields: 字段定义                                     │
│      └─ meta_fields: 元数据字段                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    规则合并流程                               │
├─────────────────────────────────────────────────────────────┤
│  1. 获取默认规则                                             │
│     ├─ 获取规则模式                                          │
│     ├─ 提取字段默认值                                        │
│     └─ 设置 ROI 默认值                                       │
│     ↓                                                        │
│  2. 合并用户规则                                             │
│     ├─ 更新默认值                                            │
│     └─ 保留用户设置                                          │
│     ↓                                                        │
│  3. 返回合并后的规则                                         │
└─────────────────────────────────────────────────────────────┘
```

## 6. 使用示例

### 获取规则类型
```python
from module.server.annotator_rule_schema import get_rule_types

types = get_rule_types()
print(types)  # ['image', 'ocr', 'click', 'swipe', 'long_click', 'list']
```

### 获取规则模式
```python
from module.server.annotator_rule_schema import get_rule_schema

schema = get_rule_schema('image')
print(schema)  # {'type': 'image', 'label': 'RuleImage', ...}
```

### 获取默认规则
```python
from module.server.annotator_rule_schema import default_rule

rule = default_rule('image')
print(rule)  # {'itemName': 'new', 'imageName': '', 'roiFront': '0,0,100,100', ...}
```

### 合并规则
```python
from module.server.annotator_rule_schema import merge_rule_with_defaults

user_rule = {'itemName': 'button', 'threshold': 0.9}
merged = merge_rule_with_defaults('image', user_rule)
print(merged)  # {'itemName': 'button', 'imageName': '', 'threshold': 0.9, ...}
```

### 获取字段默认值
```python
from module.server.annotator_rule_schema import field_default

default = field_default('image', 'threshold')
print(default)  # 0.8
```

### 获取字段选项
```python
from module.server.annotator_rule_schema import field_options

options = field_options('ocr', 'mode')
print(options)  # ['Single', 'Full', 'Digit', 'DigitCounter', 'Duration', 'Quantity']
```

## 7. 设计模式总结

1. **模式定义模式**: 使用字典定义规则模式结构
2. **工厂模式**: 通过函数创建规则和元数据
3. **合并模式**: 将用户规则与默认值合并
4. **查询模式**: 提供字段默认值和选项的查询功能
5. **配置驱动模式**: 使用配置定义规则类型和字段