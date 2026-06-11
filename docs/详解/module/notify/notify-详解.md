# module/notify/notify.py 代码详解

## 1. 文件概述

`notify.py` 是通知推送模块，基于 `onepush` 库实现多渠道消息推送功能。支持多种通知服务商（如 Telegram、Discord、企业微信、ServerChan 等），并提供自定义 Webhook 推送能力。

**文件路径**: `module/notify/notify.py`
**代码行数**: 109 行
**主要功能**:
- 多渠道通知推送（Telegram、Discord、邮件等）
- 自定义 Webhook 推送
- YAML 配置解析
- 推送结果状态检查

---

## 2. 导入部分解释

```python
import onepush.core
import yaml
from onepush import get_notifier
from onepush.core import Provider
from onepush.exceptions import OnePushException
from onepush.providers.custom import Custom
from requests import Response
from smtplib import SMTPResponseException
from module.logger import logger

onepush.core.log = logger
```

| 导入项 | 来源模块 | 说明 |
|--------|----------|------|
| `onepush.core` | onepush | 核心模块，用于设置日志 |
| `yaml` | PyYAML | YAML 配置文件解析 |
| `get_notifier` | onepush | 获取通知器实例的工厂函数 |
| `Provider` | onepush.core | 通知提供商基类 |
| `OnePushException` | onepush.exceptions | onepush 异常类 |
| `Custom` | onepush.providers.custom | 自定义 Webhook 通知器 |
| `Response` | requests | HTTP 响应对象 |
| `SMTPResponseException` | smtplib | SMTP 邮件发送异常 |
| `logger` | module.logger | 项目日志记录器 |

**特殊配置**:
```python
onepush.core.log = logger
```
将 onepush 库的日志重定向到项目统一的 logger。

---

## 3. 类定义解释

### Notifier 类

```python
class Notifier:
    def __init__(self, _config: str, enable: bool=False) -> None:
```

**核心属性**:
- `config_name`: 配置名称（用于日志标识）
- `enable`: 是否启用通知
- `config`: 解析后的配置字典
- `provider_name`: 通知提供商名称
- `notifier`: 通知器实例
- `required`: 必填参数列表

**设计意图**: 封装 onepush 库，提供简化的通知推送接口。

---

## 4. 每个方法的逐行解释

### `__init__` 方法

```python
def __init__(self, _config: str, enable: bool=False) -> None:
    self.config_name: str = ""
    self.enable: bool = enable

    if not self.enable:
        return
    config = {}
    try:
        for item in yaml.safe_load_all(_config):
            config.update(item)
    except Exception as e:
        logger.error("Fail to load onepush config, skip sending")
        return
    self.config = config
    try:
        self.provider_name: str = self.config.pop("provider", None)
        if self.provider_name is None:
            logger.info("No provider specified, skip sending")
            return
        self.notifier: Provider = get_notifier(self.provider_name)
        self.required: list[str] = self.notifier.params["required"]
    except OnePushException:
        logger.exception("Init notifier failed")
        return
    except Exception as e:
        logger.exception(e)
        return
```

**逐行解释**:

| 行号 | 代码 | 说明 |
|------|------|------|
| 19 | `self.config_name: str = ""` | 初始化配置名称为空字符串 |
| 20 | `self.enable: bool = enable` | 存储启用状态 |
| 22-23 | `if not self.enable: return` | 未启用则直接返回 |
| 24 | `config = {}` | 初始化配置字典 |
| 26-28 | `for item in yaml.safe_load_all(_config):` | 解析 YAML 配置（支持多文档） |
| 29 | `except Exception` | 捕获解析异常 |
| 31 | `self.config = config` | 存储解析后的配置 |
| 34 | `self.provider_name = self.config.pop("provider", None)` | 提取并移除 provider 字段 |
| 36-37 | 检查 provider 是否存在 | 不存在则返回 |
| 39 | `self.notifier = get_notifier(self.provider_name)` | 获取通知器实例 |
| 40 | `self.required = self.notifier.params["required"]` | 获取必填参数列表 |
| 42-47 | 异常处理 | 捕获初始化异常 |

### `push` 方法

```python
def push(self, **kwargs) -> bool:
    if not self.enable:
        return False
    kwargs["title"] = f"{self.config_name} {kwargs['title']}"
    self.config.update(kwargs)
    for key in self.required:
        if key not in self.config:
            logger.warning(
                f"Notifier {self.notifier} require param '{key}' but not provided"
            )

    if isinstance(self.notifier, Custom):
        if "method" not in self.config or self.config["method"] == "post":
            self.config["datatype"] = "json"
        if not ("data" in self.config or isinstance(self.config["data"], dict)):
            self.config["data"] = {}
        if "title" in kwargs:
            self.config["data"]["title"] = kwargs["title"]
        if "content" in kwargs:
            self.config["data"]["content"] = kwargs["content"]

    if self.provider_name.lower() == "gocqhttp":
        access_token = self.config.get("access_token")
        if access_token:
            self.config["token"] = access_token

    try:
        resp = self.notifier.notify(**self.config)
        if isinstance(resp, Response):
            if resp.status_code != 200:
                logger.warning("Push notify failed!")
                logger.warning(f"HTTP Code:{resp.status_code}")
                return False
            else:
                if self.provider_name.lower() == "gocqhttp":
                    return_data: dict = resp.json()
                    if return_data["status"] == "failed":
                        logger.warning("Push notify failed!")
                        logger.warning(
                            f"Return message:{return_data['wording']}")
                        return False
    except SMTPResponseException:
        logger.warning("Appear SMTPResponseException")
        pass
    except OnePushException:
        logger.exception("Push notify failed")
        return False
    except Exception as e:
        logger.exception(e)
        return False

    logger.info("Push notify success")
    return True
```

**逐行解释**:

| 行号 | 代码 | 说明 |
|------|------|------|
| 51 | `if not self.enable: return False` | 未启用返回 False |
| 53 | `kwargs["title"] = f"{self.config_name} {kwargs['title']}"` | 在标题前添加配置名 |
| 54 | `self.config.update(kwargs)` | 合并参数到配置 |
| 56-61 | 必填参数检查 | 检查并警告缺失的必填参数 |
| 63-72 | Custom 通知器处理 | 设置 JSON 数据格式 |
| 74-77 | gocqhttp 特殊处理 | 转换 access_token 为 token |
| 80 | `resp = self.notifier.notify(**self.config)` | 发送通知 |
| 81-94 | 响应状态检查 | 检查 HTTP 状态码和返回数据 |
| 95-103 | 异常处理 | 捕获 SMTP、OnePush 等异常 |
| 105 | `logger.info("Push notify success")` | 记录成功日志 |
| 106 | `return True` | 返回成功状态 |

---

## 5. 核心算法流程图

```
┌─────────────────────────────────────────────────────┐
│                   Notifier 推送流程                  │
└───────────────────────────┬─────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────┐
│   检查 enable 状态                                   │
│   if not enable: return False                        │
└───────────────────────────┬─────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────┐
│   更新配置                                           │
│   title = config_name + title                        │
│   config.update(kwargs)                              │
└───────────────────────────┬─────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────┐
│   检查必填参数                                       │
│   for key in required:                               │
│     if key not in config: warning                    │
└───────────────────────────┬─────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────┐
│   通知器特殊处理                                     │
│   ├─ Custom: 设置 JSON 格式                          │
│   └─ gocqhttp: 转换 token                           │
└───────────────────────────┬─────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────┐
│   notifier.notify(**config)                          │
│   发送通知                                           │
└───────────────────────────┬─────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────┐
│   检查响应                                           │
│   ├─ Response: 检查 status_code                      │
│   │   ├─ 200: 成功                                  │
│   │   └─ 其他: 失败                                  │
│   └─ gocqhttp: 检查返回状态                          │
└───────────────────────────┬─────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────┐
│   异常处理                                           │
│   ├─ SMTPResponseException: 忽略                     │
│   ├─ OnePushException: 记录日志                       │
│   └─ Exception: 记录日志                             │
└───────────────────────────┬─────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────┐
│   return True / False                                │
└─────────────────────────────────────────────────────┘
```

### 初始化流程

```
┌─────────────────────────────────────┐
│        __init__ 初始化              │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   检查 enable                       │
│   not enable → return               │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   yaml.safe_load_all(_config)       │
│   解析 YAML 配置                     │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   config.pop("provider")            │
│   提取通知提供商名称                  │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   get_notifier(provider_name)       │
│   获取通知器实例                      │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   获取必填参数列表                    │
│   self.required = notifier.params   │
│               ["required"]          │
└─────────────────────────────────────┘
```

---

## 6. 使用示例

### 基本使用

```python
from module.notify.notify import Notifier

# YAML 配置
config = """
provider: telegram
token: YOUR_BOT_TOKEN
chat_id: YOUR_CHAT_ID
"""

# 创建通知器
notifier = Notifier(_config=config, enable=True)

# 发送通知
success = notifier.push(title="任务完成", content="所有任务已执行完毕")
print(f"推送结果: {success}")
```

### 自定义 Webhook

```python
config = """
provider: custom
url: https://your-webhook-url.com/notify
method: post
"""

notifier = Notifier(_config=config, enable=True)
notifier.push(title="告警", content="设备连接失败")
```

### ServerChan 推送

```python
config = """
provider: serverchan
token: YOUR_SENDKEY
"""

notifier = Notifier(_config=config, enable=True)
notifier.push(title="脚本状态", content="自动化脚本已启动")
```

### 企业微信推送

```python
config = """
provider: wecom
corpid: YOUR_CORPID
corpsecret: YOUR_CORPSECRET
agentid: YOUR_AGENTID
"""

notifier = Notifier(_config=config, enable=True)
notifier.push(title="任务通知", content="每日任务已完成")
```

### 禁用通知

```python
# 禁用状态下不会发送任何通知
notifier = Notifier(_config=config, enable=False)
result = notifier.push(title="测试", content="这条不会发送")
print(result)  # False
```

### 多文档 YAML 配置

```python
# 支持 YAML 多文档格式
config = """
provider: telegram
---
token: YOUR_BOT_TOKEN
---
chat_id: YOUR_CHAT_ID
"""

notifier = Notifier(_config=config, enable=True)
```

---

## 7. 设计模式总结

| 设计模式 | 应用说明 |
|----------|----------|
| **工厂模式** | 使用 `get_notifier()` 工厂函数创建通知器实例 |
| **策略模式** | 不同的通知提供商作为可互换的策略 |
| **门面模式** | `Notifier` 类封装了 onepush 库的复杂性 |
| **配置驱动** | 通过 YAML 配置驱动通知行为 |
| **防御性编程** | 多层异常处理确保程序稳定性 |

**设计优点**:
- 支持多种通知渠道，易于扩展
- YAML 配置灵活，支持多文档格式
- 完善的异常处理机制
- 自定义 Webhook 支持
- 日志重定向统一管理

**支持的通知渠道**（通过 onepush）:
- Telegram
- Discord
- 企业微信
- ServerChan
- PushPlus
- 钉钉
- 飞书
- Bark
- 自定义 Webhook

**注意事项**:
- 需要安装 `onepush` 和 `PyYAML` 依赖
- 不同通知渠道需要不同的配置参数
- gocqhttp 有特殊的 token 处理逻辑
- SMTP 异常会被静默忽略
