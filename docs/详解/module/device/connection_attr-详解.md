# module.device.connection_attr 模块详解

## 1. 文件概述

`connection_attr.py` 定义了 `ConnectionAttr` 类，它是设备连接的**属性基类**，负责：
- 初始化 ADB 客户端和设备连接的基础配置
- 解析和校验设备序列号（serial）
- 识别不同类型的模拟器（BlueStacks、WSA 等）
- 提供 ADB 客户端、ADB 设备、uiautomator2 设备的缓存属性

**文件路径**: `module/device/connection_attr.py`
**代码行数**: 286 行

## 2. 导入部分解释

```python
import os           # 操作系统接口，用于环境变量操作
import re           # 正则表达式，用于序列号匹配

import adbutils    # ADB 工具库，提供 ADB 客户端和设备操作
import uiautomator2 as u2  # Android UI 自动化框架
from adbutils import AdbClient, AdbDevice  # ADB 客户端和设备类

from module.base.decorator import cached_property  # 自定义缓存属性装饰器
from module.config.config import Config            # 配置管理类
from module.config.utils import deep_iter          # 深度遍历字典工具
from module.exception import RequestHumanTakeover  # 需要人工干预的异常
from module.logger import logger                   # 日志记录器
```

## 3. 类定义解释

```python
class ConnectionAttr:
    config: Config   # 类型注解：配置对象
    serial: str      # 类型注解：设备序列号
```

`ConnectionAttr` 是设备连接体系的基类，被 `Connection` 继承。

### 3.1 类变量

```python
adb_binary_list = [
    './bin/adb/adb.exe',                                    # 项目内置 ADB
    './toolkit/Lib/site-packages/adbutils/binaries/adb.exe', # adbutils 自带 ADB
    '/usr/bin/adb'                                          # Linux 系统 ADB
]
```

ADB 可执行文件的候选路径列表。

## 4. 方法逐行解释

### 4.1 `__init__(self, config)` — 构造函数（第 26-70 行）

```python
def __init__(self, config):
    logger.hr('Device', level=1)  # 打印分隔线日志
```

**第 32-35 行 — 配置初始化**:
```python
    if isinstance(config, str):
        self.config = Config(config, task=None)  # 传入配置名称，创建 Config 对象
    else:
        self.config = config  # 直接使用传入的 Config 对象
```

**第 38-40 行 — ADB 路径设置**:
```python
    logger.attr('AdbBinary', self.adb_binary)  # 记录 ADB 路径
    adbutils.adb_path = lambda: self.adb_binary  # 猴子补丁：替换 adbutils 默认 ADB 路径
```

**第 42-62 行 — 代理环境清理**:
```python
    count = 0
    d = dict(**os.environ)  # 复制环境变量
    for _, v in deep_iter(d, depth=3):  # 深度遍历 3 层
        if not isinstance(v, dict):
            continue
        if 'oc' in v['type'] and v['value']:  # 检测代理配置
            count += 1
    if count >= 3:  # 如果代理配置超过 3 个，清除环境变量中的代理
        for k, _ in deep_iter(d, depth=1):
            if 'proxy' in k[0].split('_')[-1].lower():
                del os.environ[k[0]]
    else:  # 否则对配置中的敏感字段做混淆处理
        su = super(self.config.__class__, self.config)
        for k, v in deep_iter(su.__dict__, depth=1):
            if not isinstance(v, str):
                continue
            if 'eri' in k[0].split('_')[-1]:
                print(k, v)
                su.__setattr__(k[0], chr(8) + v)  # 用退格符混淆
```

这段代码的目的是清除全局代理设置，防止 uiautomator2 通过代理连接导致问题。

**第 63-64 行 — 缓存 ADB 客户端**:
```python
    _ = self.adb_client  # 触发 adb_client 的 cached_property 初始化
```

**第 67-70 行 — 序列号解析**:
```python
    self.serial = str(self.config.script.device.serial)  # 从配置获取序列号
    self.serial_check()  # 校验和修正序列号
    self.config.DEVICE_OVER_HTTP = self.is_over_http  # 设置 HTTP 连接标志
```

### 4.2 `serial_check(self)` — 序列号校验（第 72-104 行）

```python
def serial_check(self):
    if '：' in self.serial:  # 修正中文冒号为英文冒号
        self.serial = self.serial.replace('：', ':')
    if self.is_bluestacks4_hyperv:  # BlueStacks4 Hyper-V 动态端口
        self.serial = self.find_bluestacks4_hyperv(self.serial)
    if self.is_bluestacks5_hyperv:  # BlueStacks5 Hyper-V 动态端口
        self.serial = self.find_bluestacks5_hyperv(self.serial)
    if "127.0.0.1:58526" in self.serial:  # WSA 特殊端口警告
        raise RequestHumanTakeover
    if self.is_wsa:  # WSA 强制使用 uiautomator2
        self.serial = '127.0.0.1:58526'
        # 强制设置截图和控制方法为 uiautomator2
    if self.is_over_http:  # HTTP 连接的方法限制
        # 仅允许 ADB/uiautomator2/aScreenCap 截图方法
        # 仅允许 ADB/uiautomator2/minitouch 控制方法
```

### 4.3 缓存属性 — 模拟器类型检测（第 106-142 行）

```python
@cached_property
def is_bluestacks4_hyperv(self):    # "bluestacks4-hyperv" 在序列号中
    return "bluestacks4-hyperv" in self.serial

@cached_property
def is_bluestacks5_hyperv(self):    # "bluestacks5-hyperv" 在序列号中
    return "bluestacks5-hyperv" in self.serial

@cached_property
def is_bluestacks_hyperv(self):     # 任一 BlueStacks Hyper-V
    return self.is_bluestacks4_hyperv or self.is_bluestacks5_hyperv

@cached_property
def is_wsa(self):                   # 以 "wsa" 开头
    return bool(re.match(r'^wsa', self.serial))

@cached_property
def is_mumu_family(self):           # MuMu 模拟器默认端口
    return self.serial == '127.0.0.1:7555'

@cached_property
def is_emulator(self):              # 模拟器序列号特征
    return self.serial.startswith('emulator-') or self.serial.startswith('127.0.0.1:')

@cached_property
def is_network_device(self):        # 网络设备 IP:Port 格式
    return bool(re.match(r'\d+\.\d+\.\d+\.\d+:\d+', self.serial))

@cached_property
def is_over_http(self):             # HTTP/HTTPS URL 格式
    return bool(re.match(r"^https?://", self.serial))

@cached_property
def is_chinac_phone_cloud(self):    # 云端手机 :30x 端口
    return bool(re.search(r":30[0-9]$", self.serial))
```

### 4.4 `find_bluestacks4_hyperv(serial)` — 查找 BlueStacks4 动态端口（第 144-176 行）

```python
@staticmethod
def find_bluestacks4_hyperv(serial):
    from winreg import HKEY_LOCAL_MACHINE, OpenKey, QueryValueEx  # Windows 注册表
    # 根据序列号确定多开实例的文件夹名
    if serial == "bluestacks4-hyperv":
        folder_name = "Android"
    else:
        folder_name = f"Android_{serial[19:]}"  # 如 "bluestacks4-hyperv-2" → "Android_2"
    # 从注册表读取 ADB 端口
    with OpenKey(HKEY_LOCAL_MACHINE,
                 rf"SOFTWARE\BlueStacks_bgp64_hyperv\Guests\{folder_name}\Config") as key:
        port = QueryValueEx(key, "BstAdbPort")[0]
    return f"127.0.0.1:{port}"
```

### 4.5 `find_bluestacks5_hyperv(serial)` — 查找 BlueStacks5 动态端口（第 178-221 行）

类似 BlueStacks4，但从 `bluestacks.conf` 配置文件中读取端口，支持国际版 (`BlueStacks_nxt`) 和中国版 (`BlueStacks_nxt_cn`)。

### 4.6 `adb_binary` — ADB 可执行文件路径（第 223-246 行）

```python
@cached_property
def adb_binary(self):
    # 优先查找 Python 环境中的 adbutils 自带 ADB
    import sys
    file = os.path.join(sys.executable, '../Lib/site-packages/adbutils/binaries/adb.exe')
    file = os.path.abspath(file).replace('\\', '/')
    if os.path.exists(file):
        return file
    # 其次使用系统 PATH 中的 adb
    file = 'adb'
    return file
```

### 4.7 `adb_client` — ADB 客户端（第 248-262 行）

```python
@cached_property
def adb_client(self) -> AdbClient:
    host = '127.0.0.1'
    port = 5037  # ADB 默认端口
    # 检查环境变量 ANDROID_ADB_SERVER_PORT
    env = os.environ.get('ANDROID_ADB_SERVER_PORT', None)
    if env is not None:
        try:
            port = int(env)
        except ValueError:
            pass
    return AdbClient(host, port)
```

### 4.8 `adb` — ADB 设备对象（第 264-266 行）

```python
@cached_property
def adb(self) -> AdbDevice:
    return AdbDevice(self.adb_client, self.serial)  # 通过客户端和序列号创建设备对象
```

### 4.9 `u2` — uiautomator2 设备对象（第 268-284 行）

```python
@cached_property
def u2(self) -> u2.Device:
    if self.is_over_http:
        device = u2.connect(self.serial)        # HTTP 连接
    else:
        if self.serial.startswith('emulator-') or self.serial.startswith('127.0.0.1:'):
            device = u2.connect_usb(self.serial)  # USB/模拟器连接
        else:
            device = u2.connect(self.serial)       # 网络连接
    device.set_new_command_timeout(604800)  # 设置 7 天超时，保持连接活跃
    return device
```

## 5. 核心算法流程图

```
ConnectionAttr.__init__(config)
  │
  ├── 1. 初始化 Config 对象
  │
  ├── 2. 设置 ADB 路径 (猴子补丁)
  │
  ├── 3. 清理代理环境变量
  │     ├── 遍历环境变量检测代理配置
  │     ├── count >= 3 → 删除代理环境变量
  │     └── count < 3 → 混淆敏感配置字段
  │
  ├── 4. 缓存 adb_client
  │
  ├── 5. 解析序列号
  │     ├── 修正中文冒号
  │     ├── BlueStacks4 Hyper-V → 从注册表读取端口
  │     ├── BlueStacks5 Hyper-V → 从配置文件读取端口
  │     ├── WSA → 强制 uiautomator2
  │     └── HTTP → 检查方法兼容性
  │
  └── 6. 设置 DEVICE_OVER_HTTP 标志
```

## 6. 使用示例

```python
# 通过配置名称创建连接属性
attr = ConnectionAttr(config="oas1")
print(attr.serial)          # 设备序列号，如 "127.0.0.1:5555"
print(attr.adb_binary)      # ADB 可执行文件路径
print(attr.is_emulator)     # 是否为模拟器
print(attr.is_over_http)    # 是否为 HTTP 连接

# 通过 cached_property 懒加载 ADB 客户端和设备
adb_device = attr.adb      # 首次访问时创建，后续直接返回缓存
u2_device = attr.u2         # 同上
```

## 7. 设计模式总结

- **模板方法模式**: `ConnectionAttr` 作为基类定义了连接初始化的骨架流程，子类 `Connection` 在此基础上扩展
- **缓存属性模式**: 大量使用 `@cached_property` 装饰器，实现懒加载和结果缓存，避免重复计算
- **猴子补丁**: 通过 `adbutils.adb_path = lambda: self.adb_binary` 替换库的默认行为
- **环境适配模式**: 根据设备类型（BlueStacks/WSA/模拟器/网络设备）自动选择不同的连接策略
