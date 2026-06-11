# module/server/script_websocket.py 详解

## 1. 文件概述

`script_websocket.py` 是 WebSocket 连接管理模块，负责：
- 管理 WebSocket 连接的生命周期
- 提供消息发送和广播功能
- 处理连接断开和错误情况
- 支持文本和 JSON 消息格式

## 2. 导入部分解释

```python
from typing import Iterable                              # 可迭代类型
from fastapi import WebSocket, WebSocketDisconnect       # FastAPI WebSocket
from starlette.websockets import WebSocketState          # WebSocket 状态
```

## 3. 类定义解释

### ScriptWSManager 类（第10-81行）
WebSocket 连接管理器，管理多个 WebSocket 连接。

## 4. 每个方法的逐行解释

### __init__ 方法（第12-13行）
```python
def __init__(self):
    self.active_connections: list[WebSocket] = []  # 活动连接列表
```

### connect 方法（第15-19行）
```python
async def connect(self, ws: WebSocket):
    # 等待连接
    await ws.accept()  # 接受 WebSocket 连接
    if ws not in self.active_connections:  # 如果连接不在列表中
        self.active_connections.append(ws)  # 添加到列表
```

### disconnect 方法（第21-33行）
```python
async def disconnect(self, ws: WebSocket):
    # 关闭时移除 ws 对象，重复调用也应安全
    if ws in self.active_connections:  # 如果连接在列表中
        self.active_connections.remove(ws)  # 从列表移除
    if ws.client_state == WebSocketState.DISCONNECTED:  # 如果已断开
        return
    try:
        # 给前端发送最后一次关闭信号
        await ws.close()  # 关闭连接
    except (RuntimeError, WebSocketDisconnect):
        return  # 忽略异常
    except Exception:
        return  # 忽略其他异常
```

### send_text 方法（第35-36行）
```python
async def send_text(self, ws: WebSocket, message: str) -> bool:
    return await self._send(ws, ws.send_text, message)  # 发送文本消息
```

### send_json 方法（第38-39行）
```python
async def send_json(self, ws: WebSocket, data: dict) -> bool:
    return await self._send(ws, ws.send_json, data)  # 发送 JSON 消息
```

### broadcast 方法（第41-43行）
```python
async def broadcast(self, message: str):
    # 广播消息
    await self._broadcast(self.active_connections, lambda connection: connection.send_text(message))
```

### broadcast_state 方法（第45-47行）
```python
async def broadcast_state(self, data: dict):
    # 广播自身的状态
    await self._broadcast(self.active_connections, lambda connection: connection.send_json(data))
```

### broadcast_log 方法（第49-51行）
```python
async def broadcast_log(self, log: str):
    # 广播日志
    await self._broadcast(self.active_connections, lambda connection: connection.send_text(log))
```

### _send 内部方法（第53-65行）
```python
async def _send(self, ws: WebSocket, sender, payload) -> bool:
    if ws.client_state == WebSocketState.DISCONNECTED:  # 如果已断开
        await self.disconnect(ws)  # 断开连接
        return False
    try:
        await sender(payload)  # 发送消息
        return True
    except (RuntimeError, WebSocketDisconnect):
        await self.disconnect(ws)  # 断开连接
        return False
    except Exception:
        await self.disconnect(ws)  # 断开连接
        return False
```

### _broadcast 内部方法（第67-80行）
```python
async def _broadcast(self, connections: Iterable[WebSocket], sender_factory) -> None:
    dead_connections: list[WebSocket] = []  # 死连接列表
    for connection in list(connections):  # 遍历所有连接
        if connection.client_state == WebSocketState.DISCONNECTED:  # 如果已断开
            dead_connections.append(connection)  # 添加到死连接列表
            continue
        try:
            await sender_factory(connection)  # 发送消息
        except (RuntimeError, WebSocketDisconnect):
            dead_connections.append(connection)  # 添加到死连接列表
        except Exception:
            dead_connections.append(connection)  # 添加到死连接列表
    for connection in dead_connections:  # 清理死连接
        await self.disconnect(connection)
```

## 5. 核心算法流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    WebSocket 连接管理流程                     │
├─────────────────────────────────────────────────────────────┤
│  连接建立                                                    │
│  ├─ accept(): 接受连接                                       │
│  └─ 添加到 active_connections                                │
│                                                             │
│  消息发送                                                    │
│  ├─ send_text(): 发送文本消息                                │
│  └─ send_json(): 发送 JSON 消息                              │
│                                                             │
│  消息广播                                                    │
│  ├─ broadcast(): 广播文本消息                                │
│  ├─ broadcast_state(): 广播状态                              │
│  └─ broadcast_log(): 广播日志                                │
│                                                             │
│  连接断开                                                    │
│  ├─ 从 active_connections 移除                               │
│  └─ 关闭 WebSocket 连接                                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    广播算法流程                               │
├─────────────────────────────────────────────────────────────┤
│  1. 创建死连接列表                                            │
│     ↓                                                        │
│  2. 遍历所有连接                                              │
│     ├─ 检查连接状态                                          │
│     ├─ 发送消息                                              │
│     └─ 记录失败连接                                          │
│     ↓                                                        │
│  3. 清理死连接                                                │
└─────────────────────────────────────────────────────────────┘
```

## 6. 使用示例

### 创建管理器
```python
from module.server.script_websocket import ScriptWSManager

manager = ScriptWSManager()
```

### 处理 WebSocket 连接
```python
from fastapi import WebSocket

async def websocket_handler(websocket: WebSocket):
    await manager.connect(websocket)  # 建立连接
    
    try:
        while True:
            data = await websocket.receive_text()  # 接收消息
            await manager.send_text(websocket, f"Echo: {data}")  # 发送回复
    except WebSocketDisconnect:
        await manager.disconnect(websocket)  # 断开连接
```

### 广播消息
```python
await manager.broadcast("Hello everyone!")  # 广播文本
await manager.broadcast_state({"status": "running"})  # 广播状态
await manager.broadcast_log("Log message")  # 广播日志
```

## 7. 设计模式总结

1. **连接管理模式**: 管理多个 WebSocket 连接的生命周期
2. **广播模式**: 支持向所有连接广播消息
3. **错误处理模式**: 统一处理连接错误和异常
4. **资源清理模式**: 自动清理断开的连接
5. **线程安全模式**: 使用列表管理连接，支持并发访问