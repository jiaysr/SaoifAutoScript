# config_modify.py 代码详解

## 1. 文件概述

`config_modify.py` 定义了 `ConfigModify` 类，继承自 `Config` 类，专门用于在脚本进程崩溃时允许用户修改配置。这个类解决了一个架构问题：当用户配置错误导致脚本进程崩溃时，用户无法修改配置来修复问题。

**主要职责：**
- 提供 GUI 配置修改接口
- 在脚本崩溃时仍可修改配置
- 获取任务列表和参数信息

## 2. 导入部分解释

```python
import json                                          # JSON 序列化

from module.config.config import Config              # 配置基类
from module.config.utils import convert_to_underscore  # 命名转换工具
from module.config.config_model import ConfigModel   # 配置模型

from module.logger import logger                     # 日志记录器
from pydantic import BaseModel, ValidationError      # Pydantic 数据验证
```

**导入说明：**
- `Config`: 基类，提供配置管理的核心功能
- `convert_to_underscore`: 将大驼峰命名转为下划线命名
- `ConfigModel`: 配置数据模型
- `ValidationError`: Pydantic 验证异常

## 3. 类定义解释

### 3.1 ConfigModify 类

```python
class ConfigModify(Config):
    """
    这个类的出现是为了修补一个架构问题：
    不同于Alas,我默认用户在GUI界面点击的时候就启动了脚本进程，
    初始化会直接同时初始化一个config和一个device
    
    如果用户配置不对这个进程直接挂掉了，用户甚至没有修改config的机会，
    即时重启了也会由于没有修改config而再次挂掉
    
    因此这个类的出现是为了在脚本进程挂掉的时候，
    用户可以修改config，然后再次启动脚本进程
    """
```

**设计动机：**
- 解决配置错误导致的启动失败问题
- 提供独立于脚本进程的配置修改能力
- 允许用户在脚本崩溃后修复配置

## 4. 每个方法的逐行解释

### 4.1 __init__ 方法

```python
def __init__(self, config: str) -> None:
    # 调用父类 Config 的初始化方法
    super().__init__(config)
```

**功能：** 初始化配置修改器。

### 4.2 gui_args 方法

```python
def gui_args(self, task: str) -> str:
    """
    获取给gui显示的参数
    :return:
    """
    # 调用父类的 gui_args 方法
    return super().gui_args(task=task)
```

**功能：** 获取指定任务的参数定义（JSON Schema）。

**参数说明：**
- `task`: 任务名称（大驼峰格式）

**返回值：** JSON 格式的参数定义字符串

### 4.3 gui_task 方法

```python
def gui_task(self, task: str) -> str:
    """
    获取给gui显示的任务 的参数的具体值
    :return:
    """
    # 委托给 model 的 gui_task 方法
    return self.model.gui_task(task=task)
```

**功能：** 获取指定任务的当前配置值。

**参数说明：**
- `task`: 任务名称

**返回值：** JSON 格式的任务配置字符串

### 4.4 gui_set_task 方法

```python
def gui_set_task(self, task: str, group: str, argument: str, value) -> bool:
    """
    设置给gui显示的任务 的参数的具体值
    :return:
    """
    # 参数名格式转换
    task = convert_to_underscore(task)
    group = convert_to_underscore(group)
    argument = convert_to_underscore(argument)

    # 构建配置路径
    path = f'{task}.{group}.{argument}'
    
    # 获取配置对象层级
    task_object = getattr(self.model, task, None)
    group_object = getattr(task_object, group, None)
    argument_object = getattr(group_object, argument, None)

    # 检查参数是否存在
    if argument_object is None:
        logger.error(f'gui_set_task {task}.{group}.{argument}.{value} failed')
        return False

    try:
        # 设置参数值
        setattr(group_object, argument, value)
        
        # 验证设置结果
        argument_object = getattr(group_object, argument, None)
        logger.info(f'gui_set_task {task}.{group}.{argument}.{argument_object}')
        
        # 保存配置
        super().save()
        return True
    except ValidationError as e:
        # Pydantic 验证失败
        logger.error(e)
        return False
```

**功能：** 设置任务配置参数。

**参数说明：**
- `task`: 任务名称
- `group`: 参数组名称
- `argument`: 参数名称
- `value`: 参数值

**返回值：** 设置成功返回 True，失败返回 False

**处理流程：**
1. 转换参数名为下划线格式
2. 获取配置对象层级
3. 检查参数是否存在
4. 设置参数值
5. 验证并保存

### 4.5 gui_task_list 方法

```python
def gui_task_list(self) -> str:
    """
    获取给gui显示的任务列表
    :return:
    """
    result = {}
    
    # 遍历所有配置项
    for key, value in self.model.dict().items():
        # 跳过字符串类型的配置
        if isinstance(value, str):
            continue
        # 跳过 restart 任务
        if key == "restart":
            continue
        # 跳过没有 scheduler 的配置
        if "scheduler" not in value:
            continue

        # 提取调度器信息
        scheduler = value["scheduler"]
        item = {
            "enable": scheduler["enable"],
            "next_run": str(scheduler["next_run"])
        }
        
        # 获取任务类型名
        key = self.config.model.type(key)
        result[key] = item
    
    return json.dumps(result)
```

**功能：** 获取所有任务的列表及其状态。

**返回值：** JSON 格式的任务列表字符串

**返回数据结构：**
```json
{
  "Orochi": {
    "enable": true,
    "next_run": "2024-01-01 12:00:00"
  },
  "AreaBoss": {
    "enable": false,
    "next_run": "2024-01-01 18:00:00"
  }
}
```

## 5. 核心算法流程图

### 5.1 配置修改流程

```
┌─────────────────────────────────────────────────────────────┐
│                   配置修改流程                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 获取任务参数定义（gui_args）                             │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │ 任务名称    │────→│ 获取 Schema │────→│ 返回 JSON   │   │
│  └─────────────┘     └─────────────┘     └─────────────┘   │
│                                                              │
│  2. 获取任务当前值（gui_task）                               │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │ 任务名称    │────→│ 获取实例    │────→│ 返回 JSON   │   │
│  └─────────────┘     └─────────────┘     └─────────────┘   │
│                                                              │
│  3. 设置任务参数（gui_set_task）                             │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │ 参数转换    │────→│ 获取对象    │────→│ 设置值      │   │
│  └─────────────┘     └─────────────┘     └─────────────┘   │
│        │                                      │              │
│        ▼                                      ▼              │
│  ┌─────────────┐                       ┌─────────────┐     │
│  │ 验证并保存  │                       │ 返回结果    │     │
│  └─────────────┘                       └─────────────┘     │
│                                                              │
│  4. 获取任务列表（gui_task_list）                            │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │ 遍历配置    │────→│ 提取调度器  │────→│ 返回 JSON   │   │
│  └─────────────┘     └─────────────┘     └─────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 脚本崩溃恢复流程

```
┌─────────────────────────────────────────────────────────────┐
│                   脚本崩溃恢复流程                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 脚本启动                                                 │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────┐                                            │
│  │ 加载配置    │                                            │
│  └─────────────┘                                            │
│     │                                                        │
│     ▼                                                        │
│  2. 配置错误？                                               │
│     ├─ 否 ──→ 正常运行                                      │
│     │                                                        │
│     └─ 是 ──→ 脚本崩溃                                      │
│              │                                               │
│              ▼                                               │
│        ┌─────────────┐                                      │
│        │ 启动修改器  │ ← ConfigModify                       │
│        └─────────────┘                                      │
│              │                                               │
│              ▼                                               │
│        ┌─────────────┐                                      │
│        │ 用户修改配置│                                      │
│        └─────────────┘                                      │
│              │                                               │
│              ▼                                               │
│        ┌─────────────┐                                      │
│        │ 重新启动    │                                      │
│        └─────────────┘                                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 6. 使用示例

```python
from module.config.config_modify import ConfigModify

# 创建配置修改器
modifier = ConfigModify(config='oas1')

# 获取任务列表
task_list_json = modifier.gui_task_list()
print(f"任务列表: {task_list_json}")

# 获取 Orochi 任务的参数定义
args_json = modifier.gui_args('Orochi')
print(f"Orochi 参数定义: {args_json}")

# 获取 Orochi 任务的当前配置
task_json = modifier.gui_task('Orochi')
print(f"Orochi 当前配置: {task_json}")

# 修改 Orochi 任务的配置
success = modifier.gui_set_task(
    task='Orochi',
    group='Scheduler',
    argument='Enable',
    value=True
)
print(f"设置结果: {success}")

# 修改成功后，可以重新启动脚本
if success:
    print("配置已更新，可以重新启动脚本")
```

**前端 JavaScript 示例：**
```javascript
// 获取任务列表
const taskList = JSON.parse(await api.getTaskList());

// 获取任务参数
const args = JSON.parse(await api.getArgs('Orochi'));

// 设置任务参数
const success = await api.setArg('Orochi', 'Scheduler', 'Enable', true);

if (success) {
    // 重新启动脚本
    await api.restartScript();
}
```

## 7. 设计模式总结

### 7.1 继承模式（Inheritance）
`ConfigModify` 继承自 `Config`，复用父类的功能并扩展 GUI 接口。

### 7.2 委托模式（Delegation）
将具体的配置操作委托给 `ConfigModel` 执行。

### 7.3 错误恢复模式
提供独立于脚本进程的配置修改能力，实现错误恢复。

### 7.4 接口隔离模式
提供专门的 GUI 接口（gui_args、gui_task、gui_set_task），与内部实现分离。

**设计优点：**
- 解耦：配置修改与脚本运行分离
- 容错：脚本崩溃后仍可修改配置
- 用户友好：提供清晰的 GUI 接口
- 安全：使用 Pydantic 验证确保数据有效性

**使用场景：**
- 脚本启动失败时的配置修复
- GUI 界面的配置编辑
- 远程配置管理

**注意事项：**
- `gui_task_list` 中 `self.config.model.type(key)` 可能存在笔误，应为 `self.model.type(key)`
- 参数设置会触发自动保存
- 验证失败时返回 False，不会保存无效数据
