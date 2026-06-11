# module/server/app.py 详解

## 1. 文件概述

`app.py` 是 OAS (Open Auto Script) Web 服务的主入口文件。它负责：
- 创建和配置 FastAPI 应用实例
- 设置 CORS 中间件
- 注册路由（home、script、tool）
- 定义应用生命周期管理（启动和关闭）
- 全局异常处理
- 解析命令行参数

## 2. 导入部分解释

```python
from pathlib import Path                    # 文件路径操作
from contextlib import asynccontextmanager  # 异步上下文管理器装饰器
import argparse                             # 命令行参数解析
from starlette import status                # HTTP 状态码常量
from starlette.responses import JSONResponse  # JSON 响应类
from fastapi import FastAPI, Request        # FastAPI 框架核心
from fastapi.middleware.cors import CORSMiddleware  # CORS 中间件
from module.logger import logger            # 项目日志模块
from module.server.home_router import home_app  # 首页路由
from module.server.script_router import script_app  # 脚本管理路由
from module.server.tool_router import tool_app  # 工具路由
from module.server.setting import State     # 全局状态管理
from module.server.main_manager import mm   # 主管理器实例
from starlette.staticfiles import StaticFiles  # 静态文件服务
```

## 3. 类定义解释

此文件没有定义类，主要包含函数和模块级配置。

## 4. 每个方法的逐行解释

### lifespan 函数（第23-27行）
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await on_startup()  # 应用启动时执行
    yield               # 应用运行期间
    await on_shutdown() # 应用关闭时执行
```
这是一个异步上下文管理器，用于管理 FastAPI 应用的生命周期。

### FastAPI 应用创建（第29-34行）
```python
app = FastAPI(
    title='OAS',                    # 应用标题
    description='OAS web service',  # 应用描述
    version='0.0.0',                # 版本号
    lifespan=lifespan,              # 生命周期管理器
)
```

### CORS 中间件配置（第36-42行）
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # 允许所有来源
    allow_credentials=True,   # 允许携带凭证
    allow_methods=["*"],      # 允许所有 HTTP 方法
    allow_headers=["*"]       # 允许所有请求头
)
```

### 路由注册（第44-46行）
```python
app.include_router(home_app)    # 注册首页路由
app.include_router(script_app)  # 注册脚本管理路由
app.include_router(tool_app)    # 注册工具路由
```

### 静态文件挂载（第48-50行）
```python
annotator_static_dir = Path(__file__).resolve().parent / "web" / "annotator" / "static"
if annotator_static_dir.exists():
    app.mount("/tool/annotator/static", StaticFiles(directory=str(annotator_static_dir)), name="annotator_static")
```
检查标注器静态文件目录是否存在，如果存在则挂载到 `/tool/annotator/static` 路径。

### on_startup 函数（第53-60行）
```python
async def on_startup():
    logger.info('OAS web service startup done')
    if app.state.script_instances:  # 如果有需要启动的脚本实例
        await mm.restart_processes(app.state.script_instances)  # 重启这些进程
```

### on_shutdown 函数（第63-64行）
```python
async def on_shutdown():
    logger.info('OAS web service shutdown done')
```

### 全局异常处理器（第67-78行）
```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Internal Server Error: ", exc_info=True)  # 记录错误日志
    message = ', '.join(str(arg) for arg in exc.args) if exc.args else str(exc)  # 构建错误消息
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,  # 500 状态码
        content={'message': message},  # 返回错误消息
    )
```

### fastapi_app 函数（第81-110行）
```python
def fastapi_app():
    # 创建参数解析器
    parser = argparse.ArgumentParser(description="OAS web service")
    
    # 添加 -k/--key 参数（密码）
    parser.add_argument(
        "-k", "--key", type=str, help="Password of OAS. No password by default"
    )
    
    # 添加 --cdn 参数（是否使用 CDN）
    parser.add_argument(
        "--cdn",
        action="store_true",
        help="Use jsdelivr cdn for pywebio static files (css, js). Self host cdn by default.",
    )
    
    # 添加 --run 参数（启动时运行的配置名）
    parser.add_argument(
        "--run",
        nargs="+",
        type=str,
        help="Run OAS by config names on startup",
    )
    
    args, _ = parser.parse_known_args()  # 解析参数
    
    # 处理运行配置
    runs = None
    if args.run:  # 如果命令行指定了 --run 参数
        runs = args.run
    elif State.deploy_config.Run:  # 如果部署配置中有 Run 配置
        tmp = State.deploy_config.Run.split(",")
        runs = [l.strip(" ['\"]") for l in tmp if len(l)]
    
    app.state.script_instances = runs  # 将运行配置存储到应用状态
    
    return app
```

## 5. 核心算法流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI 应用启动流程                       │
├─────────────────────────────────────────────────────────────┤
│  1. 创建 FastAPI 应用实例                                     │
│     ↓                                                        │
│  2. 添加 CORS 中间件                                         │
│     ↓                                                        │
│  3. 注册路由 (home, script, tool)                            │
│     ↓                                                        │
│  4. 挂载静态文件目录                                          │
│     ↓                                                        │
│  5. 执行 lifespan 管理器                                     │
│     ├─ on_startup()                                          │
│     │   ├─ 记录启动日志                                      │
│     │   └─ 重启指定的脚本进程                                  │
│     ├─ 应用运行中...                                         │
│     └─ on_shutdown()                                         │
│         └─ 记录关闭日志                                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    命令行参数处理流程                         │
├─────────────────────────────────────────────────────────────┤
│  1. 解析命令行参数                                            │
│     ├─ -k/--key: 密码                                        │
│     ├─ --cdn: 是否使用 CDN                                   │
│     └─ --run: 启动时运行的配置名                              │
│     ↓                                                        │
│  2. 确定运行配置                                              │
│     ├─ 优先使用命令行参数                                     │
│     └─ 否则使用部署配置文件                                   │
│     ↓                                                        │
│  3. 存储到 app.state.script_instances                        │
└─────────────────────────────────────────────────────────────┘
```

## 6. 使用示例

### 启动应用
```python
# 直接启动
uvicorn module.server.app:app --host 0.0.0.0 --port 8000

# 使用命令行参数
python -m module.server.app --run oas1 oas2 --key mypassword
```

### 访问 API
```bash
# 测试接口
curl http://localhost:8000/home/test

# 获取首页菜单
curl http://localhost:8000/home/home_menu
```

## 7. 设计模式总结

1. **生命周期管理模式**: 使用 FastAPI 的 lifespan 上下文管理器管理应用启动和关闭
2. **中间件模式**: 通过 CORS 中间件处理跨域请求
3. **路由分离模式**: 将不同功能的路由分离到不同模块（home、script、tool）
4. **全局异常处理模式**: 使用异常处理器统一处理未捕获异常
5. **配置管理模式**: 支持命令行参数和配置文件两种配置方式
6. **静态文件服务模式**: 将前端静态文件挂载到特定路径