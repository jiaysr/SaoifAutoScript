# module/server/tool_router.py 详解

## 1. 文件概述

`tool_router.py` 是工具路由模块，负责：
- 提供标注器（Annotator）相关的 API 接口
- 管理标注会话的生命周期
- 处理图片上传、裁剪、删除等操作
- 管理规则文件的加载、保存和测试
- 控制模拟器的启动、停止和截图

## 2. 导入部分解释

```python
import asyncio                                          # 异步编程
from typing import Any                                  # 类型提示
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect  # FastAPI 组件
from fastapi.responses import FileResponse              # 文件响应
from pydantic import BaseModel                          # 数据模型
from module.logger import logger                        # 日志模块
from module.server.tool import AnnotatorError, annotator_manager  # 标注器管理
```

## 3. 类定义解释

### 数据模型类（第20-86行）

#### EmulatorStartBody
```python
class EmulatorStartBody(BaseModel):
    session_id: str          # 会话 ID
    config_name: str         # 配置名称
    frame_rate: int = 2      # 帧率
```

#### SessionBody
```python
class SessionBody(BaseModel):
    session_id: str          # 会话 ID
```

#### RuleSaveBody
```python
class RuleSaveBody(BaseModel):
    session_id: str          # 会话 ID
    task_name: str           # 任务名称
    json_relpath: str        # JSON 相对路径
    rule_type: str           # 规则类型
    rules: list[dict[str, Any]]  # 规则列表
    list_meta: dict[str, Any] | None = None  # 列表元数据
```

#### UploadImageItem
```python
class UploadImageItem(BaseModel):
    name: str                # 图片名称
    content_base64: str      # Base64 编码的图片内容
```

#### UploadImagesBody
```python
class UploadImagesBody(BaseModel):
    session_id: str          # 会话 ID
    images: list[UploadImageItem]  # 图片列表
```

#### BatchDeleteImagesBody
```python
class BatchDeleteImagesBody(BaseModel):
    session_id: str          # 会话 ID
    image_ids: list[str]     # 图片 ID 列表
```

#### CropSaveBody
```python
class CropSaveBody(BaseModel):
    session_id: str          # 会话 ID
    image_id: str            # 图片 ID
    task_name: str           # 任务名称
    json_relpath: str        # JSON 相对路径
    image_name: str          # 图片名称
    roi: str                 # 感兴趣区域
```

#### RuleImageDeleteBody
```python
class RuleImageDeleteBody(BaseModel):
    task_name: str           # 任务名称
    json_relpath: str        # JSON 相对路径
    image_name: str          # 图片名称
```

#### RuleFileCreateBody
```python
class RuleFileCreateBody(BaseModel):
    dir_path: str            # 目录路径
    file_name: str           # 文件名
```

#### RuleFileDeleteBody
```python
class RuleFileDeleteBody(BaseModel):
    dir_path: str            # 目录路径
    file_name: str           # 文件名
```

#### RuleTestBody
```python
class RuleTestBody(BaseModel):
    session_id: str          # 会话 ID
    image_id: str            # 图片 ID
    task_name: str           # 任务名称
    json_relpath: str        # JSON 相对路径
    rule_type: str           # 规则类型
    rule: dict[str, Any]     # 规则数据
    list_meta: dict[str, Any] | None = None  # 列表元数据
```

## 4. 每个方法的逐行解释

### _raise_annotator_error 函数（第88-92行）
```python
def _raise_annotator_error(e: AnnotatorError) -> None:
    raise HTTPException(
        status_code=e.status_code,  # HTTP 状态码
        detail={"code": e.code, "message": e.message},  # 错误详情
    )
```

### _close_session_safely 函数（第95-96行）
```python
def _close_session_safely(session_id: str, reason: str) -> dict[str, Any]:
    return annotator_manager.close_session(session_id, reason=reason, raise_if_missing=False)
```

### tool_annotator_page 函数（第99-104行）
```python
@tool_app.get('/annotator')
async def tool_annotator_page():
    page = annotator_manager.index_file()  # 获取页面文件
    if not page.exists():  # 如果页面不存在
        raise HTTPException(status_code=404, detail={"code": "page_not_found", "message": "标注页面不存在"})
    return FileResponse(page)  # 返回文件响应
```

### annotator_create_session 函数（第107-110行）
```python
@tool_app.post('/annotator/api/session')
async def annotator_create_session():
    session = annotator_manager.create_session()  # 创建会话
    return {"code": "ok", "session": session}
```

### annotator_get_session 函数（第113-119行）
```python
@tool_app.get('/annotator/api/session/{session_id}')
async def annotator_get_session(session_id: str):
    try:
        session = annotator_manager.get_session_snapshot(session_id)  # 获取会话快照
        return {"code": "ok", "session": session}
    except AnnotatorError as e:
        _raise_annotator_error(e)  # 处理错误
```

### annotator_close_session 函数（第124-130行）
```python
@tool_app.delete('/annotator/api/session/{session_id}')
async def annotator_close_session(session_id: str, reason: str = "client_close"):
    try:
        result = _close_session_safely(session_id, f"api:{reason}")  # 关闭会话
        return {"code": "ok", **result}
    except AnnotatorError as e:
        _raise_annotator_error(e)
```

### annotator_close_session_beacon 函数（第133-139行）
```python
@tool_app.post('/annotator/api/session/{session_id}/close')
async def annotator_close_session_beacon(session_id: str, reason: str = "pagehide"):
    try:
        result = _close_session_safely(session_id, f"beacon:{reason}")  # 关闭会话（信标）
        return {"code": "ok", **result}
    except AnnotatorError as e:
        _raise_annotator_error(e)
```

### annotator_upload_images 函数（第141-150行）
```python
@tool_app.post('/annotator/api/images/upload')
async def annotator_upload_images(data: UploadImagesBody):
    try:
        images = annotator_manager.save_uploaded_images_base64(
            data.session_id,
            [item.dict() for item in data.images],  # 上传图片
        )
        return {"code": "ok", "images": images}
    except AnnotatorError as e:
        _raise_annotator_error(e)
```

### annotator_list_images 函数（第153-159行）
```python
@tool_app.get('/annotator/api/images')
async def annotator_list_images(session_id: str):
    try:
        images = annotator_manager.list_images(session_id)  # 列出图片
        return {"code": "ok", "images": images}
    except AnnotatorError as e:
        _raise_annotator_error(e)
```

### annotator_image_file 函数（第162-168行）
```python
@tool_app.get('/annotator/api/images/{session_id}/{image_id}')
async def annotator_image_file(session_id: str, image_id: str):
    try:
        image = annotator_manager.get_image_file(session_id, image_id)  # 获取图片文件
        return FileResponse(image)  # 返回文件响应
    except AnnotatorError as e:
        _raise_annotator_error(e)
```

### annotator_delete_image 函数（第171-177行）
```python
@tool_app.delete('/annotator/api/images/{session_id}/{image_id}')
async def annotator_delete_image(session_id: str, image_id: str):
    try:
        session = annotator_manager.delete_image(session_id, image_id)  # 删除图片
        return {"code": "ok", "session": session}
    except AnnotatorError as e:
        _raise_annotator_error(e)
```

### annotator_delete_batch_images 函数（第180-186行）
```python
@tool_app.post('/annotator/api/images/delete-batch')
async def annotator_delete_batch_images(data: BatchDeleteImagesBody):
    try:
        result = annotator_manager.delete_images(data.session_id, data.image_ids)  # 批量删除图片
        return {"code": "ok", **result}
    except AnnotatorError as e:
        _raise_annotator_error(e)
```

### annotator_clear_images 函数（第189-195行）
```python
@tool_app.post('/annotator/api/images/clear')
async def annotator_clear_images(data: SessionBody):
    try:
        result = annotator_manager.clear_images(data.session_id)  # 清空图片
        return {"code": "ok", **result}
    except AnnotatorError as e:
        _raise_annotator_error(e)
```

### annotator_configs 函数（第198-201行）
```python
@tool_app.get('/annotator/api/configs')
async def annotator_configs():
    configs = annotator_manager.list_configs()  # 列出配置
    return {"code": "ok", "configs": configs}
```

### annotator_tasks 函数（第204-207行）
```python
@tool_app.get('/annotator/api/tasks')
async def annotator_tasks():
    tasks = annotator_manager.list_task_names()  # 列出任务
    return {"code": "ok", "tasks": tasks}
```

### annotator_task_json_files 函数（第210-216行）
```python
@tool_app.get('/annotator/api/tasks/{task_name}/json')
async def annotator_task_json_files(task_name: str):
    try:
        files = annotator_manager.list_task_json_files(task_name)  # 列出任务 JSON 文件
        return {"code": "ok", "json_files": files}
    except AnnotatorError as e:
        _raise_annotator_error(e)
```

### annotator_rule_schema 函数（第219-225行）
```python
@tool_app.get('/annotator/api/rules/schema')
async def annotator_rule_schema():
    try:
        data = annotator_manager.rule_schema()  # 获取规则模式
        return {"code": "ok", **data}
    except AnnotatorError as e:
        _raise_annotator_error(e)
```

### annotator_load_rules 函数（第228-234行）
```python
@tool_app.get('/annotator/api/rules/load')
async def annotator_load_rules(task_name: str, json_relpath: str):
    try:
        data = annotator_manager.load_rule_file(task_name, json_relpath)  # 加载规则文件
        return {"code": "ok", **data}
    except AnnotatorError as e:
        _raise_annotator_error(e)
```

### annotator_rule_source 函数（第237-243行）
```python
@tool_app.get('/annotator/api/rules/source')
async def annotator_rule_source(dir_path: str = ""):
    try:
        data = annotator_manager.list_rule_source(dir_path)  # 列出规则源
        return {"code": "ok", **data}
    except AnnotatorError as e:
        _raise_annotator_error(e)
```

### annotator_rule_source_create 函数（第246-252行）
```python
@tool_app.post('/annotator/api/rules/source/create')
async def annotator_rule_source_create(data: RuleFileCreateBody):
    try:
        result = annotator_manager.create_rule_json(data.dir_path, data.file_name)  # 创建规则 JSON
        return {"code": "ok", **result}
    except AnnotatorError as e:
        _raise_annotator_error(e)
```

### annotator_rule_source_delete 函数（第255-261行）
```python
@tool_app.post('/annotator/api/rules/source/delete')
async def annotator_rule_source_delete(data: RuleFileDeleteBody):
    try:
        result = annotator_manager.delete_rule_json(data.dir_path, data.file_name)  # 删除规则 JSON
        return {"code": "ok", **result}
    except AnnotatorError as e:
        _raise_annotator_error(e)
```

### annotator_rule_image_preview 函数（第264-270行）
```python
@tool_app.get('/annotator/api/rules/image-preview')
async def annotator_rule_image_preview(task_name: str, json_relpath: str, image_name: str):
    try:
        image = annotator_manager.get_rule_image_file(task_name, json_relpath, image_name)  # 获取规则图片
        return FileResponse(image)  # 返回文件响应
    except AnnotatorError as e:
        _raise_annotator_error(e)
```

### annotator_rule_image_delete 函数（第273-279行）
```python
@tool_app.post('/annotator/api/rules/image/delete')
async def annotator_rule_image_delete(data: RuleImageDeleteBody):
    try:
        result = annotator_manager.delete_rule_image(data.task_name, data.json_relpath, data.image_name)  # 删除规则图片
        return {"code": "ok", **result}
    except AnnotatorError as e:
        _raise_annotator_error(e)
```

### annotator_start_emulator 函数（第282-288行）
```python
@tool_app.post('/annotator/api/emulator/start')
async def annotator_start_emulator(data: EmulatorStartBody):
    try:
        status = annotator_manager.start_emulator(data.session_id, data.config_name, data.frame_rate)  # 启动模拟器
        return {"code": "ok", "emulator": status}
    except AnnotatorError as e:
        _raise_annotator_error(e)
```

### annotator_stop_emulator 函数（第291-297行）
```python
@tool_app.post('/annotator/api/emulator/stop')
async def annotator_stop_emulator(data: SessionBody):
    try:
        status = annotator_manager.stop_emulator(data.session_id)  # 停止模拟器
        return {"code": "ok", "emulator": status}
    except AnnotatorError as e:
        _raise_annotator_error(e)
```

### annotator_emulator_status 函数（第300-306行）
```python
@tool_app.get('/annotator/api/emulator/status')
async def annotator_emulator_status(session_id: str):
    try:
        status = annotator_manager.emulator_status(session_id)  # 获取模拟器状态
        return {"code": "ok", "emulator": status}
    except AnnotatorError as e:
        _raise_annotator_error(e)
```

### annotator_capture_frame 函数（第309-315行）
```python
@tool_app.post('/annotator/api/emulator/capture')
async def annotator_capture_frame(data: SessionBody):
    try:
        image = annotator_manager.capture_from_emulator(data.session_id)  # 从模拟器截图
        return {"code": "ok", "image": image}
    except AnnotatorError as e:
        _raise_annotator_error(e)
```

### annotator_test_rule 函数（第318-332行）
```python
@tool_app.post('/annotator/api/rules/test')
async def annotator_test_rule(data: RuleTestBody):
    try:
        result = annotator_manager.test_rule(
            session_id=data.session_id,
            image_id=data.image_id,
            task_name=data.task_name,
            json_relpath=data.json_relpath,
            rule_type=data.rule_type,
            rule=data.rule,
            list_meta=data.list_meta,
        )  # 测试规则
        return {"code": "ok", "result": result}
    except AnnotatorError as e:
        _raise_annotator_error(e)
```

### annotator_save_rules 函数（第335-349行）
```python
@tool_app.post('/annotator/api/rules/save')
async def annotator_save_rules(data: RuleSaveBody):
    try:
        result = annotator_manager.save_rules_and_generate(
            session_id=data.session_id,
            task_name=data.task_name,
            json_relpath=data.json_relpath,
            rule_type=data.rule_type,
            rules=data.rules,
            list_meta=data.list_meta,
        )  # 保存规则并生成代码
        code = "ok" if result.get("generate_status") == "success" else "partial_success"
        return {"code": code, **result}
    except AnnotatorError as e:
        _raise_annotator_error(e)
```

### annotator_crop_save 函数（第352-365行）
```python
@tool_app.post('/annotator/api/images/crop-save')
async def annotator_crop_save(data: CropSaveBody):
    try:
        result = annotator_manager.save_cropped_image(
            session_id=data.session_id,
            image_id=data.image_id,
            task_name=data.task_name,
            json_relpath=data.json_relpath,
            image_name=data.image_name,
            roi=data.roi,
        )  # 保存裁剪图片
        return {"code": "ok", **result}
    except AnnotatorError as e:
        _raise_annotator_error(e)
```

### annotator_frame_ws 函数（第368-414行）
```python
@tool_app.websocket('/annotator/ws/{session_id}')
async def annotator_frame_ws(websocket: WebSocket, session_id: str):
    await websocket.accept()  # 接受 WebSocket 连接
    try:
        annotator_manager.get_session_snapshot(session_id)  # 验证会话存在
        while True:
            frame = annotator_manager.latest_emulator_frame(session_id)  # 获取最新帧
            if frame:
                await websocket.send_bytes(frame)  # 发送帧数据
                continue

            status = annotator_manager.emulator_status(session_id)  # 获取模拟器状态
            if status.get("state") == "error":  # 如果模拟器出错
                await websocket.send_json(
                    {
                        "event": "error",
                        "code": "emulator_error",
                        "message": status.get("error", "unknown"),
                    }
                )
                await websocket.close(code=1011)  # 关闭连接
                break

            await asyncio.sleep(0.1)  # 等待0.1秒
    except WebSocketDisconnect:
        logger.info(f"[annotator] ws disconnect, session={session_id}")
    except AnnotatorError as e:
        if e.code != "invalid_session":
            logger.warning(f"[annotator] ws annotator error, session={session_id}, code={e.code}")
        try:
            await websocket.send_json({"event": "error", "code": e.code, "message": e.message})
        except Exception:
            pass
        try:
            await websocket.close(code=1008)
        except Exception:
            pass
    except Exception as e:
        message = str(e).strip().lower()
        if e.__class__.__name__ == "ClientDisconnected" or "disconnected" in message:
            logger.info(f"[annotator] ws client disconnected during send, session={session_id}")
        else:
            logger.exception(f"[annotator] ws failed, session={session_id}")
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
```

## 5. 核心算法流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    标注会话管理流程                           │
├─────────────────────────────────────────────────────────────┤
│  创建会话                                                    │
│  ├─ POST /annotator/api/session                              │
│  └─ 返回会话信息                                             │
│                                                             │
│  获取会话                                                    │
│  ├─ GET /annotator/api/session/{session_id}                  │
│  └─ 返回会话快照                                             │
│                                                             │
│  关闭会话                                                    │
│  ├─ DELETE /annotator/api/session/{session_id}               │
│  └─ POST /annotator/api/session/{session_id}/close           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    图片管理流程                               │
├─────────────────────────────────────────────────────────────┤
│  上传图片                                                    │
│  ├─ POST /annotator/api/images/upload                        │
│  └─ 返回上传结果                                             │
│                                                             │
│  列出图片                                                    │
│  ├─ GET /annotator/api/images                                │
│  └─ 返回图片列表                                             │
│                                                             │
│  删除图片                                                    │
│  ├─ DELETE /annotator/api/images/{session_id}/{image_id}     │
│  └─ POST /annotator/api/images/delete-batch                  │
│                                                             │
│  裁剪图片                                                    │
│  └─ POST /annotator/api/images/crop-save                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    规则管理流程                               │
├─────────────────────────────────────────────────────────────┤
│  加载规则                                                    │
│  ├─ GET /annotator/api/rules/load                            │
│  └─ 返回规则数据                                             │
│                                                             │
│  保存规则                                                    │
│  ├─ POST /annotator/api/rules/save                           │
│  └─ 保存并生成代码                                           │
│                                                             │
│  测试规则                                                    │
│  ├─ POST /annotator/api/rules/test                           │
│  └─ 返回测试结果                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    模拟器控制流程                             │
├─────────────────────────────────────────────────────────────┤
│  启动模拟器                                                  │
│  ├─ POST /annotator/api/emulator/start                       │
│  └─ 返回模拟器状态                                           │
│                                                             │
│  停止模拟器                                                  │
│  ├─ POST /annotator/api/emulator/stop                        │
│  └─ 返回模拟器状态                                           │
│                                                             │
│  获取状态                                                    │
│  ├─ GET /annotator/api/emulator/status                       │
│  └─ 返回模拟器状态                                           │
│                                                             │
│  截图                                                        │
│  ├─ POST /annotator/api/emulator/capture                     │
│  └─ 返回截图信息                                             │
│                                                             │
│  WebSocket 流                                                │
│  └─ WS /annotator/ws/{session_id}                            │
└─────────────────────────────────────────────────────────────┘
```

## 6. 使用示例

### 创建标注会话
```bash
curl -X POST http://localhost:8000/tool/annotator/api/session
# 返回: {"code": "ok", "session": {...}}
```

### 上传图片
```bash
curl -X POST http://localhost:8000/tool/annotator/api/images/upload \
  -H "Content-Type: application/json" \
  -d '{"session_id": "xxx", "images": [{"name": "test.png", "content_base64": "..."}]}'
```

### 启动模拟器
```bash
curl -X POST http://localhost:8000/tool/annotator/api/emulator/start \
  -H "Content-Type: application/json" \
  -d '{"session_id": "xxx", "config_name": "oas1", "frame_rate": 2}'
```

### WebSocket 连接
```javascript
const ws = new WebSocket('ws://localhost:8000/tool/annotator/ws/xxx');
ws.onmessage = function(event) {
    if (event.data instanceof Blob) {
        // 处理帧数据
    } else {
        // 处理 JSON 消息
        const data = JSON.parse(event.data);
    }
};
```

## 7. 设计模式总结

1. **RESTful API 模式**: 使用标准的 HTTP 方法和路径设计
2. **数据验证模式**: 使用 Pydantic 模型验证请求数据
3. **错误处理模式**: 统一的异常处理和错误响应
4. **会话管理模式**: 管理标注会话的生命周期
5. **WebSocket 流模式**: 实时传输模拟器帧数据
6. **文件服务模式**: 提供图片和页面文件的访问