# module/server/home_router.py 详解

## 1. 文件概述

`home_router.py` 是首页路由模块，负责：
- 提供首页相关的 API 接口
- 处理通知测试、服务器关闭、更新检查等功能
- 管理国际化翻译

## 2. 导入部分解释

```python
import json                              # JSON 处理
from fastapi import APIRouter, Body      # FastAPI 路由和请求体
from pathlib import Path                 # 文件路径操作
from module.config.utils import write_file  # 文件写入工具
from module.logger import logger         # 日志模块
from module.ocr.rpc import shutdown_ocr_server  # OCR 服务器关闭
from module.server.main_manager import MainManager  # 主管理器
from module.server.updater import Updater  # 更新器
from module.server.i18n import I18n       # 国际化
```

## 3. 类定义解释

此文件没有定义类，主要包含路由和处理函数。

### home_app 路由器（第15-18行）
```python
home_app = APIRouter(
    prefix="/home",  # 路由前缀
    tags=["home"],   # API 标签
)
```

## 4. 每个方法的逐行解释

### home_test 函数（第21-23行）
```python
@home_app.get('/test')
async def home_test():
    return {'message': 'test'}
```
测试接口，返回简单消息。

### home_menu 函数（第27-29行）
```python
@home_app.get('/home_menu')
async def home_menu():
    return {'Home': [], 'Updater': [], 'Tool': []}
```
返回首页菜单结构。

### notify_test 函数（第32-45行）
```python
@home_app.post('/notify_test')
async def notify_test(setting: str, title: str, content: str):
    from module.notify.notify import Notifier  # 延迟导入通知器
    try:
        notifier = Notifier(setting, True)  # 创建通知器实例
        if notifier.push(title=title, content=content):  # 发送通知
            del notifier  # 清理
            return True
        else:
            del notifier
            return False
    except Exception as e:
        logger.exception(e)  # 记录异常
        return str(e)        # 返回错误信息
```

### kill_server 函数（第48-52行）
```python
@home_app.get('/kill_server')
async def kill_server():
    shutdown_ocr_server()  # 关闭 OCR 服务器
    MainManager.signal_kill_server = True  # 设置关闭信号
    return 'success'
```

### update_info 函数（第55-68行）
```python
@home_app.get('/update_info')
async def update_info():
    try:
        updater = Updater()  # 创建更新器
        result = {
            'is_update': updater.check_update(),  # 检查是否有更新
            'branch': updater.current_branch(),   # 当前分支
            'current_commit': updater.current_commit(),  # 当前提交
            'latest_commit': updater.latest_commit(),    # 最新提交
            'commit': updater.get_commit(n=15),  # 最近15条提交
        }
        return result
    except Exception as e:
        logger.error(e)
        return None
```

### execute_update 函数（第71-79行）
```python
@home_app.get('/execute_update')
async def execute_update():
    # 下拉仓库 -> 关闭所有脚本进程 -> 最后重启oasx
    try:
        updater = Updater()
        updater.execute_pull()  # 执行 git pull
    except Exception as e:
        logger.error(e)
    return '手动更新将会立即结束运行中的脚本服务, 最后你还需重启oasx'
```

### chinese_translate 函数（第82-88行）
```python
@home_app.put('/chinese_translate')
async def chinese_translate(data: dict = Body(...)):
    try:
        I18n.save_zh_cn(data)  # 保存中文翻译
    except Exception as e:
        logger.error(e)
    return True
```

### additional_translate 函数（第91-98行）
```python
@home_app.get('/additional_translate')
async def additional_translate() -> dict:
    try:
        data = I18n.load_additions()  # 加载额外翻译
        return data
    except Exception as e:
        logger.error(e)
    return {}
```

## 5. 核心算法流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    首页 API 流程                              │
├─────────────────────────────────────────────────────────────┤
│  GET /home/test                                              │
│  └─ 返回测试消息                                              │
│                                                             │
│  GET /home/home_menu                                         │
│  └─ 返回菜单结构                                              │
│                                                             │
│  POST /home/notify_test                                      │
│  ├─ 创建通知器                                               │
│  ├─ 发送通知                                                 │
│  └─ 返回结果                                                 │
│                                                             │
│  GET /home/kill_server                                       │
│  ├─ 关闭 OCR 服务器                                          │
│  ├─ 设置关闭信号                                             │
│  └─ 返回成功                                                 │
│                                                             │
│  GET /home/update_info                                       │
│  ├─ 检查更新                                                 │
│  ├─ 获取分支信息                                             │
│  ├─ 获取提交信息                                             │
│  └─ 返回更新信息                                             │
│                                                             │
│  GET /home/execute_update                                    │
│  ├─ 执行 git pull                                           │
│  └─ 返回提示信息                                             │
│                                                             │
│  PUT /home/chinese_translate                                 │
│  └─ 保存中文翻译                                             │
│                                                             │
│  GET /home/additional_translate                              │
│  └─ 加载额外翻译                                             │
└─────────────────────────────────────────────────────────────┘
```

## 6. 使用示例

### 测试接口
```bash
curl http://localhost:8000/home/test
# 返回: {"message": "test"}
```

### 获取更新信息
```bash
curl http://localhost:8000/home/update_info
# 返回: {"is_update": true, "branch": "main", ...}
```

### 发送通知测试
```bash
curl -X POST "http://localhost:8000/home/notify_test?setting=telegram&title=Test&content=Hello"
# 返回: true
```

### 关闭服务器
```bash
curl http://localhost:8000/home/kill_server
# 返回: "success"
```

## 7. 设计模式总结

1. **路由模块化模式**: 使用 FastAPI 的 APIRouter 组织路由
2. **延迟导入模式**: 在函数内部导入模块，避免循环依赖
3. **异常处理模式**: 统一的 try-catch 处理
4. **配置驱动模式**: 通过配置文件控制行为
5. **服务管理模式**: 管理 OCR 服务器和脚本进程的生命周期