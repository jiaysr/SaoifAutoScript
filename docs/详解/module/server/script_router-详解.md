# module/server/script_router.py 详解

## 1. 文件概述

`script_router.py` 是脚本管理路由模块，负责：
- 管理脚本配置文件的 CRUD 操作
- 控制脚本实例的启动和停止
- 提供脚本任务参数的读取和修改
- 支持 SSE (Server-Sent Events) 和 WebSocket 实时通信

## 2. 导入部分解释

```python
import asyncio                                        # 异步编程
from fastapi import APIRouter, HTTPException          # FastAPI 路由和异常
from fastapi.responses import StreamingResponse       # 流式响应
from fastapi import WebSocket, WebSocketDisconnect    # WebSocket 支持
from datetime import datetime                         # 日期时间处理
from module.config.utils import convert_to_underscore # 配置工具
from module.logger import logger                      # 日志模块
from module.server.main_manager import mm             # 主管理器实例
from module.server.script_process import ScriptProcess, ScriptState  # 脚本进程
from tasks.Component.config_base import TimeDelta     # 时间差配置
```

## 3. 类定义解释

此文件没有定义类，主要包含路由和处理函数。

### script_app 路由器（第18行）
```python
script_app = APIRouter()  # 无前缀的路由器
```

## 4. 每个方法的逐行解释

### script_test 函数（第21-23行）
```python
@script_app.get('/test')
async def script_test():
    return 'success'
```
测试接口。

### script_menu 函数（第25-27行）
```python
@script_app.get('/script_menu')
async def script_menu():
    return mm.config_cache('template').gui_menu_list
```
返回脚本菜单列表。

### config_list 函数（第29-31行）
```python
@script_app.get('/config_list')
async def config_list():
    return mm.all_script_files()
```
获取所有配置文件列表。

### config_copy 函数（第33-36行）
```python
@script_app.post('/config_copy')
async def config_copy(file: str, template: str = 'template'):
    mm.copy(file, template)  # 复制配置文件
    return mm.all_script_files()  # 返回更新后的列表
```

### config_new_name 函数（第38-40行）
```python
@script_app.get('/config_new_name')
async def config_new_name():
    return mm.generate_script_name()  # 生成新的配置名
```

### config_all 函数（第42-44行）
```python
@script_app.get('/config_all')
async def config_all():
    return mm.all_json_file()  # 获取所有 JSON 文件
```

### config_rename 函数（第47-63行）
```python
@script_app.put('/config')
async def config_rename(old_name: str = '', new_name: str = ''):
    """
    update config name
    :param old_name: old config name
    :param new_name: new config name
    :return: True or False
    """
    if old_name == new_name or new_name == '':  # 检查参数有效性
        return False
    if old_name in mm.script_process:  # 如果脚本进程存在
        if mm.script_process[old_name].state != ScriptState.INACTIVE:  # 如果正在运行
            mm.script_process[old_name].stop()  # 先停止
        del mm.script_process[old_name]  # 删除进程引用
    if not mm.rename(old_name, new_name):  # 重命名文件
        raise HTTPException(status_code=400, detail='Rename failed')
    return True
```

### config_delete 函数（第66-81行）
```python
@script_app.delete('/config')
async def config_delete(name: str = ''):
    """
    delete config file
    :param name: config name
    :return: True or False
    """
    if name == '' or name == 'template':  # 检查参数有效性
        raise HTTPException(status_code=400, detail='Delete failed')
    if name in mm.script_process:  # 如果脚本进程存在
        if mm.script_process[name].state != ScriptState.INACTIVE:  # 如果正在运行
            mm.script_process[name].stop()  # 先停止
        del mm.script_process[name]  # 删除进程引用
    if not mm.delete(name):  # 删除文件
        raise HTTPException(status_code=400, detail='Delete failed')
    return True
```

### task_copy 函数（第84-91行）
```python
@script_app.put('/config/task/copy')
async def task_copy(task_name: str, dest_config_name: str, source_config_name: str):
    if dest_config_name not in mm.script_process or source_config_name not in mm.script_process:
        return False  # 检查配置是否存在
    source_task = getattr(mm.config_cache(source_config_name).model, convert_to_underscore(task_name), None)
    if source_task is None:
        return False  # 检查源任务是否存在
    return mm.config_cache(dest_config_name).model.copy_script_task(task_name, source_task)
```

### task_group_copy 函数（第94-101行）
```python
@script_app.put('/config/task/group/copy')
async def task_group_copy(task_name: str, group_name: str, dest_config_name: str, source_config_name: str):
    if dest_config_name not in mm.script_process or source_config_name not in mm.script_process:
        return False  # 检查配置是否存在
    source_task = getattr(mm.config_cache(source_config_name).model, convert_to_underscore(task_name), None)
    if source_task is None:
        return False  # 检查源任务是否存在
    return mm.config_cache(dest_config_name).model.copy_task_group(task_name, group_name, source_task)
```

### script_start 函数（第105-110行）
```python
@script_app.get('/{script_name}/start')
async def script_start(script_name: str):
    if script_name not in mm.script_process:  # 如果进程不存在
        mm.script_process[script_name] = ScriptProcess(script_name)  # 创建新进程
    mm.script_process[script_name].start()  # 启动进程
    return
```

### script_stop 函数（第112-118行）
```python
@script_app.get('/{script_name}/stop')
async def script_stop(script_name: str):
    if script_name not in mm.script_process:  # 如果进程不存在
        logger.warning(f'[{script_name}] script process does not exist')
        return
    mm.script_process[script_name].stop()  # 停止进程
    return
```

### script_task 函数（第120-122行）
```python
@script_app.get('/{script_name}/{task}/args')
async def script_task(script_name: str, task: str):
    return mm.config_cache(script_name).model.script_task(task)  # 获取任务参数
```

### script_task (PUT) 函数（第124-155行）
```python
@script_app.put('/{script_name}/{task}/{group}/{argument}/value')
async def script_task(script_name: str, task: str, group: str, argument: str, types: str, value):
    try:
        match types:  # 根据类型转换值
            case 'integer':
                value = int(value)
            case 'number':
                value = float(value)
            case 'boolean':
                if isinstance(value, str):
                    logger.warning(f'[{script_name}] script argument {argument} value is string, try to convert to bool')
                    if value.lower() in ['true', '1']:
                        value = True
                    elif value.lower() in ['false', '0']:
                        value = False
                value = bool(value)
            case 'string':
                pass
            case 'date_time':
                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            case 'time_delta':
                # strptime 是个好东西，但是不能解析00的天数
                day = int(value[1])
                date_time = datetime.strptime(value[3:], '%H:%M:%S')
                value = TimeDelta(days=day, hours=date_time.hour, minutes=date_time.minute, seconds=date_time.second)
            case 'time':
                value = datetime.strptime(value, '%H:%M:%S').time()
            case _: pass
    except Exception as e:
        # 类型不正确
        raise HTTPException(status_code=400, detail=f'Argument type error: {e}')
    return mm.config_cache(script_name).model.script_set_arg(task, group, argument, value)
```

### sync_next_run 函数（第158-168行）
```python
@script_app.put('/{script_name}/{task}/sync_next_run')
async def sync_next_run(script_name: str, task: str, target_dt: str):
    if script_name not in mm.script_process:  # 检查进程是否存在
        return False
    config = mm.config_cache(script_name)
    target = datetime.strptime(target_dt, '%Y-%m-%d %H:%M:%S') if target_dt else None
    config.task_delay(task=task, success=True, target=target)  # 设置任务延迟
    script_process = mm.script_process[script_name]
    config.get_next()  # 获取下一个任务
    await script_process.broadcast_state({"schedule": config.get_schedule_data()})  # 广播状态
    return True
```

### script_task_state 函数（第172-185行）
```python
@script_app.get('/{script_name}/state')
async def script_task_state(script_name: str):
    async def state_generate_events():
        while True:
            # 生成 SSE 事件数据
            event_data = "data: Hello, SSE!\n\n"
            yield event_data

            # 模拟异步操作，可以替换为您的实际处理逻辑
            await asyncio.sleep(1)

    response = StreamingResponse(state_generate_events(), media_type="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    return response
```

### script_task_log 函数（第187-200行）
```python
@script_app.get('/{script_name}/log')
async def script_task_log(script_name: str):
    async def log_generate_events():
        while True:
            # 生成 SSE 事件数据
            event_data = "data: log\n"
            yield event_data

            # 模拟异步操作，可以替换为您的实际处理逻辑
            await asyncio.sleep(1)

    response = StreamingResponse(log_generate_events(), media_type="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    return response
```

### websocket_endpoint 函数（第204-236行）
```python
@script_app.websocket("/ws/{script_name}")
async def websocket_endpoint(websocket: WebSocket, script_name: str):
    if script_name not in mm.script_process:  # 如果进程不存在
        mm.script_process[script_name] = ScriptProcess(script_name)  # 创建新进程
    script_process = mm.script_process[script_name]
    await script_process.connect(websocket)  # 连接 WebSocket

    try:
        await script_process.send_json(websocket, {"state": script_process.state})  # 发送状态
        config = mm.config_cache(script_name)
        config.get_next()  # 获取下一个任务
        await script_process.send_json(websocket, {"schedule": config.get_schedule_data()})  # 发送调度数据

        while True:
            # 初次进入，广播state schedule
            data = await websocket.receive_text()  # 接收消息
            if data == 'get_state':
                await script_process.broadcast_state({"state": script_process.state})  # 广播状态
            elif data == 'get_schedule':
                config = mm.config_cache(script_name)
                config.get_next()
                await script_process.broadcast_state({"schedule": config.get_schedule_data()})  # 广播调度
            elif data == 'start':
                await script_process.start()  # 启动脚本
            elif data == 'stop':
                await script_process.stop()  # 停止脚本

    except WebSocketDisconnect:
        logger.warning(f'[{script_name}] websocket disconnect')
        await script_process.disconnect(websocket)  # 断开连接
    except Exception as e:
        logger.exception(f'[{script_name}] websocket error: {e}')
        await script_process.disconnect(websocket)  # 断开连接
```

## 5. 核心算法流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    配置管理流程                               │
├─────────────────────────────────────────────────────────────┤
│  GET /config_list                                            │
│  └─ 返回所有配置文件列表                                      │
│                                                             │
│  POST /config_copy                                           │
│  └─ 复制配置文件                                             │
│                                                             │
│  PUT /config                                                 │
│  ├─ 检查参数有效性                                           │
│  ├─ 停止运行中的脚本                                         │
│  └─ 重命名配置文件                                           │
│                                                             │
│  DELETE /config                                              │
│  ├─ 检查参数有效性                                           │
│  ├─ 停止运行中的脚本                                         │
│  └─ 删除配置文件                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    脚本控制流程                               │
├─────────────────────────────────────────────────────────────┤
│  GET /{script_name}/start                                    │
│  ├─ 检查进程是否存在                                         │
│  ├─ 创建新进程（如果不存在）                                  │
│  └─ 启动进程                                                 │
│                                                             │
│  GET /{script_name}/stop                                     │
│  ├─ 检查进程是否存在                                         │
│  └─ 停止进程                                                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    WebSocket 通信流程                         │
├─────────────────────────────────────────────────────────────┤
│  1. 建立 WebSocket 连接                                      │
│     ↓                                                        │
│  2. 发送初始状态和调度数据                                    │
│     ↓                                                        │
│  3. 进入消息循环                                              │
│     ├─ get_state: 广播状态                                   │
│     ├─ get_schedule: 广播调度                                │
│     ├─ start: 启动脚本                                       │
│     └─ stop: 停止脚本                                        │
│     ↓                                                        │
│  4. 处理断开连接                                              │
└─────────────────────────────────────────────────────────────┘
```

## 6. 使用示例

### 获取配置列表
```bash
curl http://localhost:8000/config_list
# 返回: ["oas1", "oas2", ...]
```

### 启动脚本
```bash
curl http://localhost:8000/oas1/start
```

### 停止脚本
```bash
curl http://localhost:8000/oas1/stop
```

### WebSocket 连接
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/oas1');
ws.onmessage = function(event) {
    console.log(event.data);
};
ws.send('get_state');
```

## 7. 设计模式总结

1. **RESTful API 模式**: 使用标准的 HTTP 方法（GET、POST、PUT、DELETE）
2. **实时通信模式**: 支持 SSE 和 WebSocket 两种实时通信方式
3. **进程管理模式**: 管理脚本进程的生命周期
4. **类型转换模式**: 根据参数类型自动转换值
5. **广播模式**: 通过 WebSocket 广播状态和日志