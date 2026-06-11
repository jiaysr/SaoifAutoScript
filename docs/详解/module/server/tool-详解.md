# module/server/tool.py 详解

## 1. 文件概述

`tool.py` 是标注器核心模块，负责：
- 管理标注会话和图片
- 处理模拟器截图和帧捕获
- 实现规则的加载、保存、测试和生成功能
- 提供图片裁剪和 ROI 处理
- 管理会话生命周期和清理

## 2. 导入部分解释

```python
import json                              # JSON 处理
import re                                # 正则表达式
import shutil                            # 文件操作
import threading                         # 线程支持
import time                              # 时间处理
import uuid                              # UUID 生成
import base64                            # Base64 编解码
from dataclasses import dataclass        # 数据类
from pathlib import Path                 # 文件路径
from typing import Any                   # 类型提示
import cv2                               # OpenCV 图像处理
import numpy as np                       # NumPy 数组
from filelock import FileLock            # 文件锁
from dev_tools.assets_extract import AssetsExtractor  # 资源提取器
from dev_tools.assets_test import detect_image_detail, detect_ocr_detail  # 资源测试
from module.config.atomicwrites import atomic_write  # 原子写入
from module.config.config import Config  # 配置类
from module.device.device import Device  # 设备类
from module.logger import logger         # 日志模块
from module.server.config_manager import ConfigManager  # 配置管理器
from module.server.annotator_rule_schema import (  # 规则模式
    default_list_meta,
    field_default,
    field_options,
    get_rule_types,
    get_schema_payload,
    merge_list_meta_with_defaults,
    merge_rule_with_defaults,
)
```

## 3. 类定义解释

### 常量定义（第36-50行）
```python
PROJECT_ROOT = Path.cwd().resolve()  # 项目根目录
TASKS_ROOT = (PROJECT_ROOT / "tasks").resolve()  # 任务根目录
ANNOTATOR_ROOT = (PROJECT_ROOT / "log" / "annotator").resolve()  # 标注器根目录

ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}  # 允许的图片扩展名
ALLOWED_RULE_TYPE = set(get_rule_types())  # 允许的规则类型
ALLOWED_OCR_MODE = set(field_options("ocr", "mode"))  # 允许的 OCR 模式
ALLOWED_LIST_DIRECTION = set(field_options("list", "direction"))  # 允许的列表方向
ALLOWED_LIST_MODE = set(field_options("list", "type"))  # 允许的列表模式
ALLOWED_SWIPE_MODE = set(field_options("swipe", "mode"))  # 允许的滑动模式

SESSION_IDLE_TIMEOUT_SECONDS = 10 * 60  # 会话空闲超时（10分钟）
SESSION_SWEEP_INTERVAL_SECONDS = 30     # 会话清理间隔（30秒）
EMULATOR_CAPTURE_MAX_RETRIES = 3        # 模拟器截图最大重试次数
EMULATOR_CAPTURE_RETRY_BACKOFF_SECONDS = 1.0  # 重试退避时间
```

### AnnotatorError 类（第53-58行）
```python
class AnnotatorError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code          # 错误代码
        self.message = message    # 错误消息
        self.status_code = status_code  # HTTP 状态码
```

### SessionImage 数据类（第61-78行）
```python
@dataclass
class SessionImage:
    image_id: str          # 图片 ID
    path: Path             # 图片路径
    source: str            # 图片来源
    original_name: str     # 原始文件名
    created_at: float      # 创建时间

    def to_dict(self, session_id: str) -> dict[str, Any]:
        url = f"/tool/annotator/api/images/{session_id}/{self.image_id}"
        return {
            "id": self.image_id,
            "name": self.original_name,
            "source": self.source,
            "created_at": self.created_at,
            "url": url,
            "thumb_url": url,
        }
```

### EmulatorCaptureSession 类（第81-271行）
模拟器截图会话管理。

### AnnotatorSession 类（第273-356行）
标注会话管理。

### AnnotatorManager 类（第358-1441行）
标注器管理器，核心类。

## 4. 每个方法的逐行解释

### EmulatorCaptureSession.__init__ 方法（第82-96行）
```python
def __init__(self, session_id: str) -> None:
    self.session_id = session_id  # 会话 ID
    self.state = "stopped"        # 状态
    self.config_name = ""         # 配置名
    self.frame_rate = 2           # 帧率
    self.error = ""               # 错误信息
    self._thread: threading.Thread | None = None  # 线程
    self._stop_event = threading.Event()  # 停止事件
    self._frame_lock = threading.Lock()   # 帧锁
    self._latest_frame = None      # 最新帧
    self._latest_jpeg: bytes | None = None  # 最新 JPEG
    self._updated_at = 0.0         # 更新时间
    self._retry_count = 0          # 重试计数
    self._max_retries = EMULATOR_CAPTURE_MAX_RETRIES  # 最大重试次数
    self._last_error_at = 0.0      # 最后错误时间
```

### EmulatorCaptureSession.status 方法（第98-110行）
```python
def status(self) -> dict[str, Any]:
    with self._frame_lock:  # 加锁
        return {
            "state": self.state,
            "config_name": self.config_name,
            "frame_rate": self.frame_rate,
            "error": self.error,
            "updated_at": self._updated_at,
            "last_frame_at": self._updated_at,
            "retry_count": self._retry_count,
            "max_retries": self._max_retries,
            "last_error_at": self._last_error_at,
        }
```

### EmulatorCaptureSession.start 方法（第112-127行）
```python
def start(self, config_name: str, frame_rate: int) -> int:
    self.stop(clear_error=True)  # 先停止
    with self._frame_lock:
        self.config_name = config_name
        self.frame_rate = max(1, min(int(frame_rate), 10))  # 限制帧率范围
        self.state = "starting"
        self.error = ""
        self._updated_at = 0.0
        self._retry_count = 0
        self._last_error_at = 0.0
        self._latest_frame = None
        self._latest_jpeg = None
    self._stop_event.clear()  # 清除停止事件
    self._thread = threading.Thread(target=self._run, daemon=True, name=f"annotator_capture_{self.session_id}")
    self._thread.start()  # 启动线程
    return self.frame_rate
```

### EmulatorCaptureSession.stop 方法（第129-140行）
```python
def stop(self, clear_error: bool = False) -> None:
    self._stop_event.set()  # 设置停止事件
    thread = self._thread
    if thread and thread.is_alive():
        thread.join(timeout=2.5)  # 等待线程结束
    self._thread = None
    with self._frame_lock:
        self.state = "stopped"
        self._retry_count = 0
        if clear_error:
            self.error = ""
            self._last_error_at = 0.0
```

### EmulatorCaptureSession._run 方法（第189-244行）
```python
def _run(self) -> None:
    device: Device | None = None
    interval = max(0.1, 1.0 / float(self.frame_rate))  # 计算间隔
    try:
        config = Config(config_name=self.config_name)  # 创建配置
        while not self._stop_event.is_set():  # 循环直到停止
            if device is None:
                try:
                    device = self._build_device(config, interval)  # 构建设备
                    with self._frame_lock:
                        self.state = "running"
                except Exception as e:
                    should_retry, attempt, _ = self._mark_capture_failure("connect", e)
                    if not should_retry:
                        break
                    if self._stop_event.wait(EMULATOR_CAPTURE_RETRY_BACKOFF_SECONDS * attempt):
                        break
                    continue

            try:
                frame = device.screenshot()  # 截图
            except Exception as e:
                self._release_device(device)
                device = None
                should_retry, attempt, _ = self._mark_capture_failure("capture", e)
                if not should_retry:
                    break
                if self._stop_event.wait(EMULATOR_CAPTURE_RETRY_BACKOFF_SECONDS * attempt):
                    break
                continue

            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)  # 转换颜色空间
            ok, buf = cv2.imencode(".jpg", frame_bgr)  # 编码为 JPEG
            if ok:
                with self._frame_lock:
                    self._latest_frame = frame_bgr.copy()  # 保存帧
                    self._latest_jpeg = buf.tobytes()  # 保存 JPEG
                    self._updated_at = time.time()  # 更新时间
                    self._retry_count = 0
                    self.error = ""
                    self.state = "running"

            if self._stop_event.wait(interval):  # 等待间隔
                break
    except Exception:
        with self._frame_lock:
            self.state = "error"
            self._last_error_at = time.time()
            if not self.error:
                self.error = "模拟器采集线程异常退出"
        logger.error(f"[annotator] emulator capture loop crashed, session={self.session_id}, config={self.config_name}")
    finally:
        self._release_device(device)  # 释放设备
        if self.state != "error":
            with self._frame_lock:
                self.state = "stopped"
```

### AnnotatorManager.create_session 方法（第506-521行）
```python
def create_session(self) -> dict[str, Any]:
    self._cleanup_expired_sessions()  # 清理过期会话
    with self._cleanup_lock:
        session_id = uuid.uuid4().hex  # 生成会话 ID
        session = AnnotatorSession(session_id)  # 创建会话
        replace_reason = f"replaced_by:{session_id}"
        replaced_count = self._replace_active_sessions(session, replace_reason)  # 替换活动会话
        orphan_removed = self._cleanup_foreign_session_dirs(
            keep_session_id=session_id,
            reason=f"create_session:{session_id}",
        )  # 清理孤立目录
    logger.info(
        f"[annotator] session created, session={session_id}, "
        f"replaced_sessions={replaced_count}, removed_other_dirs={orphan_removed}"
    )
    return session.snapshot()  # 返回会话快照
```

### AnnotatorManager.save_uploaded_images_base64 方法（第541-570行）
```python
def save_uploaded_images_base64(self, session_id: str, images_payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    session = self._get_session(session_id)  # 获取会话
    results: list[dict[str, Any]] = []
    for payload in images_payload:
        filename = str(payload.get("name", "")).strip()
        content_base64 = str(payload.get("content_base64", "")).strip()
        if not filename:
            continue
        if not content_base64:
            continue
        suffix = Path(filename).suffix.lower()
        if not suffix:
            suffix = ".png"
        if suffix not in ALLOWED_IMAGE_EXT:
            raise AnnotatorError("invalid_image_ext", f"不支持的图片类型: {suffix}", 400)
        image_name = f"{uuid.uuid4().hex}_{self._safe_stem(filename)}{suffix}"
        target = session.upload_dir / image_name
        if "," in content_base64:
            content_base64 = content_base64.split(",", 1)[1]  # 移除 Base64 头
        try:
            content = base64.b64decode(content_base64)  # 解码 Base64
        except Exception as e:
            raise AnnotatorError("invalid_image_data", f"图片编码解析失败: {filename}", 400) from e
        target.write_bytes(content)  # 写入文件
        image = session.add_image(target, "upload", filename)  # 添加到会话
        results.append(image.to_dict(session_id))
    if not results:
        raise AnnotatorError("empty_upload", "未上传有效图片", 400)
    logger.info(f"[annotator] upload images, session={session_id}, count={len(results)}")
    return results
```

### AnnotatorManager.test_rule 方法（第1166-1307行）
```python
def test_rule(
    self,
    session_id: str,
    image_id: str,
    task_name: str,
    json_relpath: str,
    rule_type: str,
    rule: dict[str, Any],
    list_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    session = self._get_session(session_id)  # 获取会话
    _, source_path = self._load_session_bgr_image(session, image_id)  # 加载图片

    if rule_type == "image":
        # 处理图片规则
        item_name = str(rule.get("itemName", "")).strip() or "unnamed"
        image_name = str(rule.get("imageName", "")).strip()
        if not image_name:
            raise AnnotatorError("invalid_rule", "image 规则缺少 imageName", 400)
        method = str(rule.get("method", field_default("image", "method", "Template matching"))).strip() or field_default("image", "method", "Template matching")
        try:
            threshold = float(rule.get("threshold", 0.8))
        except (TypeError, ValueError) as e:
            raise AnnotatorError("invalid_rule", "threshold 非法", 400) from e
        roi_back = self._parse_roi_tuple(str(rule.get("roiBack", "")))
        task_root, target_json = self._resolve_json_path(task_name, json_relpath)
        template = self.get_rule_image_file(task_name, json_relpath, image_name)
        from module.atom.image import RuleImage
        target = RuleImage(
            roi_front=self._parse_roi_tuple(str(rule.get("roiFront", "0,0,100,100"))),
            roi_back=roi_back,
            method=method,
            threshold=threshold,
            file=str(template),
        )
        detail = detect_image_detail(str(source_path), target)  # 检测图片
        return {
            "rule_type": "image",
            "item_name": item_name,
            "image_name": image_name,
            "matched": bool(detail.get("matched", False)),
            "similarity": float(detail.get("similarity", 0.0)),
            "roiFront": self._parse_roi(str(detail.get("roiFront", rule.get("roiFront", "0,0,100,100")))),
            "roiBack": self._parse_roi(str(detail.get("roiBack", rule.get("roiBack", "0,0,100,100")))),
            "threshold": threshold,
            "message": str(detail.get("message", "not_match")),
            "target_json": str(target_json.relative_to(task_root).as_posix()),
        }

    if rule_type == "ocr":
        # 处理 OCR 规则
        item_name = str(rule.get("itemName", "")).strip() or "unnamed"
        mode = str(rule.get("mode", field_default("ocr", "mode", "Single"))).strip() or field_default("ocr", "mode", "Single")
        method = str(rule.get("method", "Default")).strip() or "Default"
        keyword = str(rule.get("keyword", "")).strip()
        roi_front = self._parse_roi_tuple(str(rule.get("roiFront", "")))
        roi_back = self._parse_roi_tuple(str(rule.get("roiBack", "")))
        from module.atom.ocr import RuleOcr
        target = RuleOcr(
            name=item_name,
            mode=mode,
            method=method,
            roi=roi_front,
            area=roi_back,
            keyword=keyword,
        )
        detail = detect_ocr_detail(str(source_path), target)  # 检测 OCR
        return {
            "rule_type": "ocr",
            "item_name": item_name,
            "matched": bool(detail.get("matched", False)),
            "similarity": float(detail.get("similarity", 0.0)),
            "text": str(detail.get("text", "")),
            "keyword": keyword,
            "roiFront": self._parse_roi(str(detail.get("roiFront", rule.get("roiFront", "0,0,100,100")))),
            "roiBack": self._parse_roi(str(detail.get("roiBack", rule.get("roiBack", "0,0,100,100")))),
            "message": str(detail.get("message", "not_match")),
        }

    if rule_type == "list":
        # 处理列表规则
        if not list_meta:
            raise AnnotatorError("invalid_rule", "list 测试缺少 list_meta", 400)
        item_name = str(rule.get("itemName", "")).strip()
        if not item_name:
            raise AnnotatorError("invalid_rule", "list 项缺少 itemName", 400)
        list_type = str(list_meta.get("type", field_default("list", "type", "image"))).strip() or field_default("list", "type", "image")
        if list_type not in ALLOWED_LIST_MODE:
            raise AnnotatorError("invalid_rule", f"list_meta.type 不支持: {list_type}", 400)
        list_roi_back = self._parse_roi_tuple(str(list_meta.get("roiBack", "")))
        if list_type == "image":
            template = self.get_list_item_image_file(task_name, json_relpath, item_name)
            from module.atom.image import RuleImage
            target = RuleImage(
                roi_front=list_roi_back,
                roi_back=list_roi_back,
                method="Template matching",
                threshold=0.8,
                file=str(template),
            )
            detail = detect_image_detail(str(source_path), target)
            return {
                "rule_type": "list",
                "list_type": "image",
                "item_name": item_name,
                "image_name": self._list_item_image_name(item_name),
                "matched": bool(detail.get("matched", False)),
                "similarity": float(detail.get("similarity", 0.0)),
                "roiFront": self._parse_roi(str(detail.get("roiFront", self._parse_roi(str(list_meta.get("roiBack", "0,0,100,100")))))),
                "roiBack": self._parse_roi(str(detail.get("roiBack", self._parse_roi(str(list_meta.get("roiBack", "0,0,100,100")))))),
                "threshold": 0.8,
                "message": str(detail.get("message", "not_match")),
            }
        from module.atom.ocr import RuleOcr
        target = RuleOcr(
            name=item_name,
            mode="Full",
            method="Default",
            roi=list_roi_back,
            area=(0, 0, 10, 10),
            keyword=item_name,
        )
        detail = detect_ocr_detail(str(source_path), target)
        return {
            "rule_type": "list",
            "list_type": "ocr",
            "item_name": item_name,
            "matched": bool(detail.get("matched", False)),
            "similarity": float(detail.get("similarity", 0.0)),
            "text": str(detail.get("text", "")),
            "keyword": item_name,
            "roiFront": self._parse_roi(str(detail.get("roiFront", self._parse_roi(str(list_meta.get("roiBack", "0,0,100,100")))))),
            "roiBack": self._parse_roi(str(detail.get("roiBack", self._parse_roi(str(list_meta.get("roiBack", "0,0,100,100")))))),
            "message": str(detail.get("message", "not_match")),
        }

    raise AnnotatorError("invalid_rule_type", f"不支持测试的 rule_type: {rule_type}", 400)
```

### AnnotatorManager.save_rules_and_generate 方法（第1309-1378行）
```python
def save_rules_and_generate(
    self,
    session_id: str,
    task_name: str,
    json_relpath: str,
    rule_type: str,
    rules: list[dict[str, Any]],
    list_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ = self._get_session(session_id)  # 验证会话
    if not isinstance(rules, list):
        raise AnnotatorError("invalid_rule", "rules 必须是数组", 400)

    task_root, target_json = self._resolve_json_path(task_name, json_relpath)  # 解析路径

    # 根据规则类型规范化规则
    if rule_type == "image":
        payload = self._normalize_image_rules(rules) if rules else []
    elif rule_type == "ocr":
        payload = self._normalize_ocr_rules(rules) if rules else []
    elif rule_type == "click":
        payload = self._normalize_click_rules(rules) if rules else []
    elif rule_type == "swipe":
        payload = self._normalize_swipe_rules(rules) if rules else []
    elif rule_type == "long_click":
        payload = self._normalize_long_click_rules(rules) if rules else []
    elif rule_type == "list":
        payload = self._normalize_list_rules(rules, list_meta)
    else:
        raise AnnotatorError("invalid_rule_type", f"不支持的 rule_type: {rule_type}", 400)

    target_json.parent.mkdir(parents=True, exist_ok=True)  # 创建目录

    lock = FileLock(f"{target_json}.lock")  # 获取文件锁
    with lock:
        with atomic_write(target_json, overwrite=True, encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)  # 写入 JSON

    save_status = "success"
    generate_status = "success"
    generate_error = ""
    assets_file = ""
    extract_root = None
    try:
        extract_root, assets_path = self._resolve_assets_extract_target(task_root, target_json)
        assets_file = str(assets_path.relative_to(PROJECT_ROOT).as_posix())
        AssetsExtractor(str(extract_root)).extract()  # 提取资源
    except Exception as e:
        generate_status = "failed"
        generate_error = str(e)
        logger.exception(
            f"[annotator] assets generate failed, session={session_id}, task={task_name}, "
            f"target={target_json}, extract_root={extract_root}"
        )

    logger.info(
        f"[annotator] save rules, session={session_id}, task={task_name}, target={target_json}, "
        f"rule_type={rule_type}, save_status={save_status}, generate_status={generate_status}, "
        f"assets_file={assets_file or 'n/a'}"
    )

    rule_count = len(payload.get("list", [])) if isinstance(payload, dict) and "list" in payload else len(payload)

    return {
        "save_status": save_status,
        "generate_status": generate_status,
        "error": generate_error,
        "target_json": str(target_json.relative_to(PROJECT_ROOT).as_posix()),
        "assets_file": assets_file,
        "rule_count": rule_count,
    }
```

### AnnotatorManager.save_cropped_image 方法（第1380-1438行）
```python
def save_cropped_image(
    self,
    session_id: str,
    image_id: str,
    task_name: str,
    json_relpath: str,
    image_name: str,
    roi: str,
) -> dict[str, Any]:
    session = self._get_session(session_id)  # 获取会话
    image = session.images.get(image_id)  # 获取图片
    if image is None:
        raise AnnotatorError("image_not_found", f"图片不存在: {image_id}", 404)

    if not image.path.exists():
        raise AnnotatorError("image_not_found", "源图片文件不存在", 404)

    task_root, target_json = self._resolve_json_path(task_name, json_relpath)  # 解析路径
    image_rel = Path(image_name)
    if image_rel.is_absolute():
        raise AnnotatorError("invalid_path", "image_name 必须是相对路径", 400)

    target_image = (target_json.parent / image_rel).resolve()  # 目标图片路径
    self._ensure_within_root(target_image, task_root)  # 确保路径安全
    if target_image.suffix.lower() not in ALLOWED_IMAGE_EXT:
        raise AnnotatorError("invalid_image_ext", "目标图片后缀不受支持", 400)

    raw = cv2.imread(str(image.path), cv2.IMREAD_COLOR)  # 读取图片
    if raw is None:
        raise AnnotatorError("invalid_image_data", "源图片读取失败", 400)

    roi_text = self._parse_roi(roi)  # 解析 ROI
    x_f, y_f, w_f, h_f = [float(v) for v in roi_text.split(",")]
    x = int(round(x_f))
    y = int(round(y_f))
    w = int(round(w_f))
    h = int(round(h_f))

    ih, iw = raw.shape[:2]  # 获取图片尺寸
    x = max(0, min(x, iw - 1))  # 限制 x 范围
    y = max(0, min(y, ih - 1))  # 限制 y 范围
    w = max(1, min(w, iw - x))  # 限制宽度
    h = max(1, min(h, ih - y))  # 限制高度
    crop = raw[y:y + h, x:x + w]  # 裁剪图片

    target_image.parent.mkdir(parents=True, exist_ok=True)  # 创建目录
    ok = cv2.imwrite(str(target_image), crop)  # 保存图片
    if not ok:
        raise AnnotatorError("save_image_failed", "保存裁剪图片失败", 500)

    logger.info(
        f"[annotator] save crop image, session={session_id}, image={image_id}, target={target_image}, roi={roi_text}"
    )

    return {
        "save_status": "success",
        "target_image": str(target_image.relative_to(PROJECT_ROOT).as_posix()),
        "roi": roi_text,
    }
```

## 5. 核心算法流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    标注会话管理流程                           │
├─────────────────────────────────────────────────────────────┤
│  创建会话                                                    │
│  ├─ 生成 UUID                                               │
│  ├─ 创建 AnnotatorSession                                   │
│  ├─ 替换现有会话                                             │
│  └─ 清理孤立目录                                             │
│                                                             │
│  获取会话                                                    │
│  ├─ 清理过期会话                                             │
│  ├─ 查找会话                                                 │
│  └─ 更新最后活动时间                                         │
│                                                             │
│  关闭会话                                                    │
│  ├─ 停止模拟器捕获                                           │
│  ├─ 清理会话目录                                             │
│  └─ 从管理器移除                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    模拟器截图流程                             │
├─────────────────────────────────────────────────────────────┤
│  1. 创建设备连接                                             │
│     ↓                                                        │
│  2. 循环截图                                                  │
│     ├─ 截图                                                  │
│     ├─ 转换颜色空间                                          │
│     ├─ 编码为 JPEG                                           │
│     └─ 保存帧数据                                            │
│     ↓                                                        │
│  3. 处理错误和重试                                           │
│     ├─ 连接失败                                              │
│     ├─ 截图失败                                              │
│     └─ 达到最大重试次数                                      │
│     ↓                                                        │
│  4. 释放设备                                                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    规则测试流程                               │
├─────────────────────────────────────────────────────────────┤
│  1. 加载源图片                                               │
│     ↓                                                        │
│  2. 根据规则类型处理                                         │
│     ├─ image: 模板匹配                                       │
│     ├─ ocr: 文字识别                                         │
│     └─ list: 列表匹配                                        │
│     ↓                                                        │
│  3. 返回测试结果                                             │
│     ├─ matched: 是否匹配                                     │
│     ├─ similarity: 相似度                                    │
│     └─ message: 结果消息                                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    规则保存流程                               │
├─────────────────────────────────────────────────────────────┤
│  1. 验证会话                                                 │
│     ↓                                                        │
│  2. 规范化规则数据                                           │
│     ├─ 验证字段                                              │
│     ├─ 设置默认值                                            │
│     └─ 格式化 ROI                                           │
│     ↓                                                        │
│  3. 写入 JSON 文件                                           │
│     ├─ 获取文件锁                                            │
│     └─ 原子写入                                              │
│     ↓                                                        │
│  4. 生成资源文件                                             │
│     ├─ 提取资源                                              │
│     └─ 生成 assets.py                                        │
│     ↓                                                        │
│  5. 返回结果                                                 │
└─────────────────────────────────────────────────────────────┘
```

## 6. 使用示例

### 创建标注会话
```python
from module.server.tool import annotator_manager

session_data = annotator_manager.create_session()
session_id = session_data["session_id"]
```

### 上传图片
```python
import base64

with open("test.png", "rb") as f:
    content = base64.b64encode(f.read()).decode()

images = annotator_manager.save_uploaded_images_base64(
    session_id,
    [{"name": "test.png", "content_base64": content}]
)
```

### 测试规则
```python
result = annotator_manager.test_rule(
    session_id=session_id,
    image_id="xxx",
    task_name="TaskName",
    json_relpath="rules.json",
    rule_type="image",
    rule={
        "itemName": "button",
        "imageName": "button.png",
        "roiFront": "100,100,200,200",
        "roiBack": "0,0,1280,720",
        "method": "Template matching",
        "threshold": 0.8
    }
)
print(result["matched"])  # True 或 False
```

### 保存规则
```python
result = annotator_manager.save_rules_and_generate(
    session_id=session_id,
    task_name="TaskName",
    json_relpath="rules.json",
    rule_type="image",
    rules=[...]
)
print(result["save_status"])  # "success"
```

## 7. 设计模式总结

1. **会话管理模式**: 使用 UUID 管理多个标注会话
2. **生产者-消费者模式**: 模拟器捕获线程生产帧数据，WebSocket 消费帧数据
3. **线程安全模式**: 使用锁保护共享资源
4. **资源管理模式**: 自动清理过期会话和临时文件
5. **原子操作模式**: 使用原子写入确保文件完整性
6. **策略模式**: 根据规则类型使用不同的测试策略
7. **模板方法模式**: 规范化和验证规则数据