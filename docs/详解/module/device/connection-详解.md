# module.device.connection 模块详解

## 1. 文件概述

`connection.py` 定义了 `Connection` 类和辅助的 `retry` 装饰器、`AdbDeviceWithStatus` 类。它是设备连接的**核心实现层**，负责：
- ADB 命令执行和 Shell 操作
- 设备发现和连接管理（connect/disconnect/reconnect）
- 端口转发（forward）和反向代理（reverse）
- 包管理和检测
- uiautomator2 安装

**文件路径**: `module/device/connection.py`
**代码行数**: 892 行

## 2. 导入部分解释

```python
import ipaddress      # IP 地址处理，用于判断设备是否在同一子网
import logging        # 日志级别常量
import platform       # 平台检测（Linux 特殊处理）
import re             # 正则表达式
import socket         # 网络套接字
import subprocess     # 子进程管理
import time           # 时间操作
from functools import wraps  # 装饰器工具

import uiautomator2 as u2           # Android UI 自动化
from adbutils import AdbClient, AdbDevice, AdbTimeout, ForwardItem, ReverseItem
from adbutils.errors import AdbError  # ADB 错误类

from module.base.decorator import Config, cached_property, del_cached_property
from module.base.utils import ensure_time
from module.device.connection_attr import ConnectionAttr  # 基类
from module.device.method.utils import (
    RETRY_TRIES, remove_shell_warning, retry_sleep,
    handle_adb_error, PackageNotInstalled,
    recv_all, possible_reasons,
    random_port, get_serial_pair)
from module.config.server import set_server
from module.exception import RequestHumanTakeover, EmulatorNotRunningError
from module.logger import logger
from module.map.map_grids import SelectedGrids  # 带筛选功能的列表容器
```

## 3. retry 装饰器（第 28-74 行）

```python
def retry(func):
    @wraps(func)
    def retry_wrapper(self, *args, **kwargs):
        init = None
        for _ in range(RETRY_TRIES):  # 默认重试次数
            try:
                if callable(init):
                    retry_sleep(_)    # 按指数退避等待
                    init()            # 执行恢复操作
                return func(self, *args, **kwargs)
            except RequestHumanTakeover:
                break                 # 需要人工干预，不再重试
            except ConnectionResetError as e:
                logger.error(e)
                def init():
                    self.adb_reconnect()  # ADB 连接重置 → 重新连接
            except AdbError as e:
                if handle_adb_error(e):
                    def init():
                        self.adb_reconnect()  # 可恢复的 ADB 错误
                else:
                    break                     # 不可恢复的 ADB 错误
            except PackageNotInstalled as e:
                logger.error(e)
                def init():
                    self.detect_package()     # 包未安装 → 重新检测
            except Exception as e:
                logger.exception(e)
                def init():
                    pass                      # 其他异常 → 仅重试
        logger.critical(f'Retry {func.__name__}() failed')
        raise RequestHumanTakeover
    return retry_wrapper
```

**设计要点**:
- 采用延迟初始化模式（`init` 函数在下次循环开头执行）
- 不同异常类型对应不同的恢复策略
- 指数退避等待避免频繁重试

## 4. AdbDeviceWithStatus 类（第 77-88 行）

```python
class AdbDeviceWithStatus(AdbDevice):
    def __init__(self, client: AdbClient, serial: str, status: str):
        self.status = status  # 设备状态：'device'/'offline'/'unauthorized'
        super().__init__(client, serial)

    def __str__(self):
        return f'AdbDevice({self.serial}, {self.status})'

    __repr__ = __str__  # repr 和 str 输出相同

    def __bool__(self):
        return True  # 始终为 True，避免被当作 None
```

扩展 `AdbDevice`，增加设备状态信息，用于 `list_device()` 返回结果。

## 5. Connection 类（第 91-892 行）

### 5.1 `__init__(self, config)` — 构造函数（第 92-115 行）

```python
class Connection(ConnectionAttr):
    def __init__(self, config):
        super().__init__(config)        # 调用 ConnectionAttr.__init__
        if not self.is_over_http:       # 非 HTTP 连接才检测设备
            self.detect_device()
        self.adb_connect(self.serial)   # 连接设备
        logger.attr('AdbDevice', self.adb)
        self.package = self.config.script.device.package_name.value  # 获取包名
        if self.package == 'auto':
            self.detect_package()       # 自动检测包名
        logger.attr('PackageName', self.package)
```

### 5.2 `adb_command(self, cmd, timeout=10)` — 执行 ADB 命令（第 117-153 行）

有两个版本，通过 `@Config.when(DEVICE_OVER_HTTP=...)` 装饰器条件选择：

**非 HTTP 版本**:
```python
@Config.when(DEVICE_OVER_HTTP=False)
def adb_command(self, cmd, timeout=10):
    cmd = list(map(str, cmd))
    cmd = [self.adb_binary, '-s', self.serial] + cmd  # 构建完整命令
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=False)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()                    # 超时则强制终止
        stdout, stderr = process.communicate()
    return stdout
```

**HTTP 版本**: 直接抛出异常，因为 HTTP 连接不支持子进程命令。

### 5.3 `adb_shell(self, cmd, ...)` — 执行 Shell 命令（第 155-220 行）

**非 HTTP 版本**:
```python
@Config.when(DEVICE_OVER_HTTP=False)
def adb_shell(self, cmd, stream=False, recvall=True, timeout=10, rstrip=True):
    if not isinstance(cmd, str):
        cmd = list(map(str, cmd))
    if stream:
        result = self.adb.shell(cmd, stream=True, timeout=timeout, rstrip=rstrip)
        if recvall:
            return recv_all(result)   # 接收全部数据 → bytes
        else:
            return result             # 返回 socket 对象
    else:
        result = self.adb.shell(cmd, stream=False, timeout=timeout, rstrip=rstrip)
        result = remove_shell_warning(result)  # 移除 shell 警告信息
        return result                          # str
```

**HTTP 版本**: 通过 uiautomator2 的 HTTP 接口执行 shell 命令。

### 5.4 设备属性查询（第 222-281 行）

```python
def adb_getprop(self, name):          # 获取 Android 系统属性
    return self.adb_shell(['getprop', name]).strip()

@cached_property
def cpu_abi(self) -> str:              # CPU 架构 (arm64-v8a, x86_64 等)
    ...

@cached_property
def sdk_ver(self) -> int:              # Android SDK 版本
    ...

@cached_property
def is_avd(self):                      # 是否为 Android Virtual Device
    ...

@cached_property
def nemud_app_keep_alive(self) -> str: # MuMu 保活属性
    ...

@cached_property
def is_mumu_over_version_356(self) -> bool:  # MuMu12 版本 >= 3.5.6
    ...
```

### 5.5 `_nc_server_host_port` — 网络通信服务器配置（第 283-328 行）

```python
@cached_property
def _nc_server_host_port(self):
    # BlueStacks Hyper-V → ADB reverse
    if self.is_bluestacks_hyperv:
        host = '127.0.0.1'
        port = self.adb_reverse(f'tcp:{self.config.REVERSE_SERVER_PORT}')
        return host, port, host, self.config.REVERSE_SERVER_PORT
    # 模拟器 → 本地主机
    if self.is_emulator or self.is_over_http:
        host = socket.gethostbyname(socket.gethostname())
        port = random_port(self.config.FORWARD_PORT_RANGE)
        if self.is_avd:  # AVD 使用 10.0.2.2
            return host, port, "10.0.2.2", port
        return host, port, host, port
    # 网络设备 → 同子网主机
    if self.is_network_device:
        hosts = socket.gethostbyname_ex(socket.gethostname())[2]
        ip = ipaddress.ip_address(self.serial.split(':')[0])
        for host in hosts:
            if ip in ipaddress.ip_interface(f'{host}/24').network:
                port = random_port(self.config.FORWARD_PORT_RANGE)
                return host, port, host, port
    # 其他 → ADB reverse
    host = '127.0.0.1'
    port = self.adb_reverse(f'tcp:{self.config.REVERSE_SERVER_PORT}')
    return host, port, host, self.config.REVERSE_SERVER_PORT
```

**返回值**: `(server_listen_host, server_listen_port, client_connect_host, client_connect_port)`

### 5.6 `reverse_server` — 反向服务器（第 330-344 行）

```python
@cached_property
def reverse_server(self):
    del_cached_property(self, '_nc_server_host_port')  # 刷新端口配置
    host_port = self._nc_server_host_port
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(host_port[:2])    # 绑定地址和端口
    server.settimeout(5)          # 5 秒超时
    server.listen(5)              # 最大 5 个排队连接
    return server
```

### 5.7 `nc_command` — netcat 命令检测（第 346-380 行）

```python
@cached_property
def nc_command(self):
    sdk = self.sdk_ver
    if sdk >= 28:  # Android 9+ 优先使用 busybox nc
        trial = [['busybox', 'nc'], ['nc']]
    else:
        trial = [['nc'], ['busybox', 'nc']]
    for command in trial:
        result = self.adb_shell(command)
        if 'not found' in result or 'inaccessible' in result:
            continue
        return command
    raise RequestHumanTakeover  # 无可用 nc 命令
```

### 5.8 `adb_shell_nc` — 通过 netcat 传输数据（第 382-412 行）

```python
def adb_shell_nc(self, cmd, timeout=5, chunk_size=262144):
    server = self.reverse_server     # 启动服务器
    server.settimeout(timeout)
    cmd += ["|", *self.nc_command, *self._nc_server_host_port[2:]]  # 管道到 nc
    stream = self.adb_shell(cmd, stream=True, recvall=False)
    try:
        conn, conn_port = server.accept()  # 等待客户端连接
    except socket.timeout:
        output = recv_all(stream, chunk_size=chunk_size)
        raise AdbTimeout('reverse server accept timeout')
    data = recv_all(conn, chunk_size=chunk_size, recv_interval=0.001)  # 接收数据
    conn.close()
    return data
```

**用途**: 高效传输截图等大数据，绕过 ADB shell 的编码开销。

### 5.9 `adb_forward` / `adb_reverse` — 端口转发（第 418-475 行）

```python
def adb_forward(self, remote):
    # 查找已有的 forward，复用端口
    for forward in self.adb.forward_list():
        if forward.serial == self.serial and forward.remote == remote:
            if not port:
                port = int(forward.local[4:])  # 复用
            else:
                self.adb_forward_remove(forward.local)  # 删除冗余
    if port:
        return port
    else:
        port = random_port(self.config.FORWARD_PORT_RANGE)  # 创建新的
        self.adb.forward(f'tcp:{port}', remote)
        return port
```

`adb_reverse` 逻辑类似，但使用 `self.adb.reverse()`。

### 5.10 `adb_connect(self, serial)` — 连接设备（第 517-578 行）

```python
@Config.when(DEVICE_OVER_HTTP=False)
def adb_connect(self, serial):
    # 1. 处理离线和未授权设备
    for device in self.list_device():
        if device.status == 'offline':
            self.adb_disconnect(serial)
        elif device.status == 'unauthorized':
            logger.error('please accept ADB debugging')
    # 2. 跳过 emulator-* 和纯字母序列号
    if 'emulator-' in serial:
        return True
    if re.match(r'^[a-zA-Z0-9]+$', serial):
        return True
    # 3. 尝试连接 3 次
    for _ in range(3):
        msg = self.adb_client.connect(serial)
        if 'connected' in msg:
            return True
        elif 'bad port' in msg:
            raise RequestHumanTakeover
        elif '(10061)' in msg:
            raise EmulatorNotRunningError
    return False
```

### 5.11 `adb_reconnect` — 重连（第 601-623 行）

```python
@Config.when(DEVICE_OVER_HTTP=False)
def adb_reconnect(self):
    if self.config.script.device.adb_restart and len(self.list_device()) == 0:
        self.adb_restart()           # 重启 ADB 服务器
        self.adb_connect(self.serial)
        self.detect_device()
    else:
        self.adb_disconnect(self.serial)  # 断开后重连
        self.adb_connect(self.serial)
        self.detect_device()
```

### 5.12 `install_uiautomator2` — 安装 u2（第 625-640 行）

```python
def install_uiautomator2(self):
    init = u2.init.Initer(self.adb, loglevel=logging.DEBUG)
    if init.abi not in ['x86_64', 'x86', 'arm64-v8a', 'armeabi-v7a', 'armeabi']:
        init.abi = init.abis[0]  # MuMu X 兼容处理
    init.set_atx_agent_addr('127.0.0.1:7912')
    try:
        init.install()
    except ConnectionError:
        u2.init.GITHUB_BASEURL = 'http://tool.appetizer.io/openatx'  # 国内镜像
        init.install()
    self.uninstall_minicap()  # minicap 在某些模拟器上不工作
```

### 5.13 `get_orientation` — 获取屏幕方向（第 682-714 行）

```python
@retry
def get_orientation(self):
    _DISPLAY_RE = re.compile(
        r'.*DisplayViewport{.*orientation=(?P<orientation>\d+),.*deviceWidth=(?P<width>\d+),.*'
    )
    output = self.adb_shell(['dumpsys', 'display'])
    res = _DISPLAY_RE.search(output)
    if res:
        o = int(res.group('orientation'))  # 0-3
    else:
        o = 0  # 默认正常方向
    self.orientation = o
    return o
```

### 5.14 `list_device` — 列出设备（第 716-742 行）

```python
@retry
def list_device(self):
    devices = []
    with self.adb_client._connect() as c:
        c.send_command("host:devices")  # ADB 协议命令
        c.check_okay()
        output = c.read_string_block()
        for line in output.splitlines():
            parts = line.strip().split("\t")
            if len(parts) != 2:
                continue
            device = AdbDeviceWithStatus(self.adb_client, parts[0], parts[1])
            devices.append(device)
    return SelectedGrids(devices)  # 返回可筛选的列表
```

### 5.15 `detect_device` — 自动检测设备（第 744-810 行）

```python
def detect_device(self):
    devices = self.list_device()
    available = devices.select(status='device')    # 可用设备
    unavailable = devices.delete(available)        # 不可用设备
    # 自动模式：只有一个设备时自动选择
    if self.config.script.device.serial == 'auto':
        if available.count == 1:
            self.serial = devices[0].serial
    # 处理雷电模拟器序列号跳变
    port_serial, emu_serial = get_serial_pair(self.serial)
    if port_device and emu_device:
        # 根据状态选择正确的序列号
```

### 5.16 `list_package` / `detect_package` — 包管理（第 812-892 行）

```python
@retry
def list_package(self, show_log=True):
    # 快速方式：dumpsys package（约 80ms）
    output = self.adb_shell(r'dumpsys package | grep "Package \["')
    packages = re.findall(r'Package \[([^\s]+)\]', output)
    if len(packages):
        return packages
    # 备选方式：pm list packages（约 200ms）
    output = self.adb_shell(['pm', 'list', 'packages'])
    packages = re.findall(r'package:([^\s]+)', output)
    return packages

def detect_package(self, keywords=('onmyoji', 'yys'), set_config=True):
    packages = self.list_app_packages(keywords=keywords)
    if len(packages) == 1:
        self.package = packages[0]  # 自动选择唯一匹配
```

## 6. 核心算法流程图

```
Connection.__init__(config)
  │
  ├── ConnectionAttr.__init__()  ← 基类初始化
  │
  ├── detect_device()  ← 设备发现
  │     ├── list_device()  ← 获取设备列表
  │     ├── 处理 offline/unauthorized 设备
  │     └── auto 模式自动选择
  │
  ├── adb_connect(serial)  ← 建立连接
  │     ├── 跳过 emulator-* 序列号
  │     └── 最多重试 3 次
  │
  └── detect_package()  ← 包检测
        ├── list_package()  ← 获取包列表
        └── 按关键词过滤

adb_shell 执行流程:
  │
  ├── DEVICE_OVER_HTTP=False
  │     ├── stream=False → adb.shell() → remove_shell_warning → str
  │     └── stream=True  → adb.shell(stream=True)
  │           ├── recvall=True  → recv_all() → bytes
  │           └── recvall=False → socket 对象
  │
  └── DEVICE_OVER_HTTP=True
        ├── stream=False → u2.shell().output → str
        └── stream=True  → u2.shell(stream=True).content → bytes

重试机制 (retry 装饰器):
  │
  ├── RequestHumanTakeover → 立即终止
  ├── ConnectionResetError → adb_reconnect()
  ├── AdbError             → handle_adb_error() → adb_reconnect()
  ├── PackageNotInstalled  → detect_package()
  └── Exception            → 仅重试
```

## 7. 使用示例

```python
# 创建连接（自动检测设备和包名）
conn = Connection(config="oas1")

# 执行 shell 命令
result = conn.adb_shell(['dumpsys', 'battery'])
print(result)  # "Current Battery Service state: ..."

# 列出所有包
packages = conn.list_package()

# 获取屏幕方向
orientation = conn.get_orientation()  # 0=正常, 1=右旋, 2=倒置, 3=左旋

# 端口转发
port = conn.adb_forward('tcp:7912')  # 转发到本地端口
```

## 8. 设计模式总结

- **装饰器模式**: `@retry` 装饰器为 ADB 操作提供自动重试和错误恢复
- **策略模式**: `@Config.when()` 根据配置选择不同的方法实现（HTTP vs 非 HTTP）
- **缓存属性模式**: `@cached_property` 用于懒加载昂贵的计算结果（如 `nc_command`、`cpu_abi`）
- **模板方法模式**: `Connection` 继承 `ConnectionAttr`，在其基础上扩展连接管理逻辑
- **资源管理**: 端口转发的复用和冗余清理，避免资源泄漏
