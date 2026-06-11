# decorator.py 逐行代码详解

> 源文件路径：`module/base/decorator.py`

---

## 1. 文件概述

`decorator.py` 提供了多种实用的装饰器工具，主要用于：
- **Config 装饰器**：根据配置选项动态选择执行不同的同名函数
- **cached_property**：带类型支持的缓存属性装饰器
- **function_drop**：随机丢弃函数调用（用于模拟卡顿测试）
- **run_once**：确保函数只执行一次

---

## 2. 导入部分解释

```python
from functools import wraps                        # 保留被装饰函数的元数据
from typing import Callable, Generic, TypeVar       # 类型注解支持
```

**第 2-3 行**：`wraps` 是装饰器的标准工具；`Callable`、`Generic`、`TypeVar` 用于泛型类型注解。

```python
T = TypeVar("T")
```

**第 5 行**：定义泛型类型变量 `T`，用于 `cached_property` 的类型推断。

---

## 3. Config 类 — 配置驱动的函数选择器

### 3.1 类定义与文档

```python
class Config:
    func_list = {}
```

**第 8-20 行**：`Config` 类包含一个类变量 `func_list`，结构为：
```python
{
    '函数名': [
        {'options': {'配置键': 配置值}, 'func': 函数对象},
        ...
    ]
}
```

### 3.2 `when(cls, **kwargs)` — 装饰器工厂

```python
    @classmethod
    def when(cls, **kwargs):
```

**第 30-31 行**：类方法，返回一个装饰器。`**kwargs` 是配置选项（如 `USE_ONE_CLICK_RETIREMENT=True`）。

```python
        from module.logger import logger
        options = kwargs
```

**第 45-46 行**：延迟导入 logger；保存配置选项。

```python
        def decorate(func):
            name = func.__name__
            data = {'options': options, 'func': func}
```

**第 48-50 行**：`decorate` 是实际的装饰器。获取函数名，构建数据字典。

```python
            if name not in cls.func_list:
                cls.func_list[name] = [data]
            else:
                override = False
                for record in cls.func_list[name]:
                    if record['options'] == data['options']:
                        record['func'] = data['func']
                        override = True
                if not override:
                    cls.func_list[name].append(data)
```

**第 51-60 行**：
- 如果函数名不在 `func_list` 中，创建新列表
- 如果已存在，检查是否有相同配置的记录，有则覆盖，无则追加

```python
            @wraps(func)
            def wrapper(self, *args, **kwargs):
```

**第 62-63 行**：定义包装函数，`self` 是实例（如 ModuleBase）。

```python
                for record in cls.func_list[name]:
                    flag = [value is None or self.config.__getattribute__(key) == value
                            for key, value in record['options'].items()]
                    if not all(flag):
                        continue
                    return record['func'](self, *args, **kwargs)
```

**第 70-77 行**：
- 遍历该函数名下的所有记录
- 检查每个配置选项：值为 `None` 表示通配，否则要求精确匹配
- 所有条件都满足时，调用对应的函数并返回

```python
                logger.warning(f'No option fits for {name}, using the last define func.')
                return func(self, *args, **kwargs)
```

**第 79-80 行**：如果没有匹配的配置，使用最后定义的函数作为默认，并输出警告。

```python
            return wrapper
        return decorate
```

**第 82-84 行**：返回包装函数 → 返回装饰器 → 返回装饰器工厂。

---

## 4. cached_property 类 — 缓存属性

### 4.1 类定义

```python
class cached_property(Generic[T]):
```

**第 86 行**：泛型描述符类，实现了只计算一次的属性缓存。

```python
    def __init__(self, func: Callable[..., T]):
        self.func = func
```

**第 96-97 行**：接收被装饰的函数。

```python
    def __get__(self, obj, cls) -> T:
        if obj is None:
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value
```

**第 99-104 行**：
- `__get__` 是描述符协议方法
- 如果从类访问（`obj is None`），返回描述符自身
- 否则调用函数计算值，**直接存入实例的 `__dict__`**
- 后续访问会直接从 `__dict__` 获取，不再调用函数（属性遮蔽描述符）

---

## 5. 辅助函数

### 5.1 `del_cached_property(obj, name)` — 删除缓存属性

```python
def del_cached_property(obj, name):
    try:
        del obj.__dict__[name]
    except KeyError:
        pass
```

**第 106-117 行**：安全删除缓存的属性值。`KeyError` 时静默处理。

### 5.2 `has_cached_property(obj, name)` — 检查是否已缓存

```python
def has_cached_property(obj, name):
    return name in obj.__dict__
```

**第 119-127 行**：检查属性是否已被缓存。

---

## 6. function_drop 装饰器 — 随机丢弃调用

```python
def function_drop(rate=0.5, default=None):
```

**第 131 行**：装饰器工厂，`rate` 为丢弃概率（0~1），`default` 为丢弃时的返回值。

```python
    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if random.uniform(0, 1) > rate:
                return func(*args, **kwargs)
            else:
```

**第 151-154 行**：生成 0~1 随机数，大于 `rate` 则正常执行，否则丢弃。

```python
                cls = ''
                arguments = [str(arg) for arg in args]
                if len(arguments):
                    matched = re.search('<(.*?) object at', arguments[0])
                    if matched:
                        cls = matched.group(1) + '.'
                        arguments.pop(0)
                arguments += [f'{k}={v}' for k, v in kwargs.items()]
                arguments = ', '.join(arguments)
                logger.info(f'Dropped: {cls}{func.__name__}({arguments})')
                return default
```

**第 157-167 行**：
- 从第一个参数的字符串表示中提取类名（如 `<Device object at 0x...>` → `Device`）
- 拼接所有参数的日志格式
- 记录丢弃信息并返回默认值

```python
    return decorate
```

**第 171 行**：返回装饰器。

> **注意**：此函数引用了 `random` 和 `re` 模块，但未在文件顶部导入，实际使用时需要确保已导入。

---

## 7. run_once 装饰器 — 只执行一次

```python
def run_once(f):
```

**第 174 行**：装饰器，确保函数只在首次调用时执行。

```python
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not wrapper.has_run:
            wrapper.has_run = True
            return f(*args, **kwargs)

    wrapper.has_run = False
    return wrapper
```

**第 195-202 行**：
- 在 `wrapper` 函数对象上附加 `has_run` 属性（初始为 `False`）
- 首次调用时设为 `True` 并执行原函数
- 后续调用直接返回 `None`

---

## 8. 核心算法流程图

### Config.when() 选择流程

```
调用 func(self, *args, **kwargs)
 │
 ▼
遍历 func_list[name] 中的每条记录
 │
 ▼
记录的每个 option 是否匹配?
 ├─ option.value is None → 通配，匹配
 └─ self.config.key == option.value → 精确匹配
 │
 ▼
所有 option 都匹配? ──是──▶ 调用该记录的函数
 │
 否
 │
 ▼
继续下一条记录
 │
 ▼
全部不匹配 → 警告 + 使用最后定义的函数
```

### cached_property 缓存机制

```
首次访问 obj.prop
 │
 ▼
触发 __get__ 描述符
 │
 ▼
调用 self.func(obj) 计算值
 │
 ▼
存入 obj.__dict__['prop'] = value
 │
 ▼
返回 value

后续访问 obj.prop
 │
 ▼
Python 直接从 obj.__dict__['prop'] 获取
（描述符被实例属性遮蔽，不再触发 __get__）
```

---

## 9. 使用示例

```python
# Config 装饰器
class MyModule:
    @Config.when(ENABLE_FAST_MODE=True)
    def process(self):
        return "fast"

    @Config.when(ENABLE_FAST_MODE=False)
    def process(self):
        return "slow"

# cached_property
class MyClass:
    @cached_property
    def expensive_data(self):
        print("Computing...")
        return sum(range(1000000))

obj = MyClass()
print(obj.expensive_data)  # 输出 "Computing..." + 结果
print(obj.expensive_data)  # 直接返回缓存值，不再计算

# run_once
@run_once
def init_database():
    print("Database initialized")

init_database()  # 执行
init_database()  # 跳过，返回 None
```

---

## 10. 设计模式总结

| 模式 | 说明 |
|------|------|
| **策略模式** | `Config.when()` 根据配置动态选择不同的函数实现 |
| **描述符模式** | `cached_property` 使用 Python 描述符协议实现惰性计算 |
| **装饰器工厂** | `function_drop(rate)` 返回装饰器，支持参数化配置 |
| **状态标志** | `run_once` 在函数对象上附加 `has_run` 属性控制执行次数 |
| **延迟导入** | `Config.when` 和 `function_drop` 内部延迟导入 `logger`/`random` |
