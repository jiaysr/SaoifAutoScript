# module.device.emulator 模块详解

## 1. 文件概述

`emulator.py` 定义了模拟器实例管理和生命周期控制，包括：
- `EmulatorInstance` — 模拟器实例信息（路径、VirtualBox 配置等）
- `Bluestacks5Instance` — BlueStacks5 的特殊实现
- `EmulatorManager` — 模拟器管理器（检测、启动、停止、重启）

**文件路径**: `module/device/emulator.py`
**代码行数**: 328 行

## 2. 导入部分解释

```python
import os              # 文件路径和进程操作
import re              # 正则表达式（解析 vbox 文件）
import winreg          # Windows 注册表访问
import subprocess      # 子进程管理

from adbutils.errors import AdbError         # ADB 错误
from deploy.emulator import VirtualBoxEmulator  # VirtualBox 模拟器基类
from module.base.decorator import cached_property  # 缓存属性
from module.device.connection import Connection    # 连接基类
from module.device.method.utils import get_serial_pair  # 序列号配对工具
from module.exception import RequestHumanTakeover, EmulatorNotRunningError
from module.logger import logger
```

## 3. EmulatorInstance 类（第 16-64 行）

### 3.1 构造函数

```python
class EmulatorInstance(VirtualBoxEmulator):
    def __init__(self, name, root_path, emu_path,
                 vbox_path=None, vbox_name=None, kill_para=None, multi_para=None):
        super().__init__(
            name=name,            # 模拟器名称（用于卸载列表查找）
            root_path=root_path,  # 卸载程序到安装目录的相对路径
            adb_path=None,        # ADB 路径（未使用）
            vbox_path=vbox_path,  # VirtualBox 虚拟机文件夹相对路径
            vbox_name=vbox_name,  # .vbox 文件名正则表达式
        )
        self.emu_path = emu_path    # 模拟器可执行文件相对路径
        self.kill_para = kill_para  # 终止模拟器的命令行参数
        self.multi_para = multi_para  # 多开参数模板（#id 会被替换）
```

### 3.2 `id_and_serial` — 多开实例和序列号（第 42-64 行）

```python
@cached_property
def id_and_serial(self):
    # 1. 遍历 vbox 目录，找到所有匹配的 .vbox 文件
    vbox = []
    for path, folders, files in os.walk(os.path.join(self.root, self.vbox_path)):
        for file in files:
            if re.match(self.vbox_name, file):
                file = os.path.join(path, file)
                vbox.append(file)

    # 2. 从 .vbox 文件中解析 ADB 端口
    serial = []
    for file in vbox:
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f.readlines():
                # 匹配: <Forwarding name="port2" ... hostport="62026" guestport="5555"/>
                res = re.search('<*?hostport="(.*?)".*?guestport="5555"/>', line)
                if res:
                    serial.append([
                        os.path.basename(file).split(".")[0],  # 实例 ID
                        f'127.0.0.1:{res.group(1)}'            # ADB 序列号
                    ])
    return serial
```

**原理**: VirtualBox 的端口转发配置中，guestport="5555" 对应 Android ADB 端口，hostport 是宿主机映射端口。

## 4. Bluestacks5Instance 类（第 67-90 行）

```python
class Bluestacks5Instance(EmulatorInstance):
    @cached_property
    def root(self):
        try:
            return super().root
        except FileNotFoundError:
            self.name = 'BlueStacks_nxt_cn'  # 回退到中国版名称
            return super().root

    @cached_property
    def id_and_serial(self):
        # 从注册表读取配置目录
        try:
            reg = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\BlueStacks_nxt")
        except FileNotFoundError:
            reg = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\BlueStacks_nxt_cn")
        directory = winreg.QueryValueEx(reg, 'UserDefinedDir')[0]

        # 从 bluestacks.conf 解析端口
        with open(os.path.join(directory, 'bluestacks.conf'), encoding='utf-8') as f:
            content = f.read()
        emulators = re.findall(r'bst.instance.(\w+).status.adb_port="(\d+)"', content)
        serial = []
        for emulator in emulators:
            serial.append([emulator[0], f'127.0.0.1:{emulator[1]}'])
        return serial
```

**BlueStacks5 特殊性**: 不使用 VirtualBox，通过自己的配置文件管理多开实例。

## 5. EmulatorManager 类（第 93-327 行）

### 5.1 支持的模拟器列表

```python
class EmulatorManager(Connection):
    pid = None  # 当前模拟器进程 ID
    SUPPORTED_EMULATORS = {
        'nox_player': EmulatorInstance(
            name="Nox",
            root_path=".",
            emu_path="./Nox.exe",
            vbox_path="./BignoxVMS",
            vbox_name='.*.vbox$',
            kill_para='-quit',
            multi_para='-clone:#id',
        ),
        'mumu_player': EmulatorInstance(
            name="Nemu",
            root_path=".",
            emu_path="./EmulatorShell/NemuPlayer.exe",
            vbox_path="./vms",
            vbox_name='.*.nemu$',
        ),
        'bluestacks_5': Bluestacks5Instance(
            name='BlueStacks_nxt',
            root_path='.',
            emu_path='./HD-Player.exe',
            multi_para='--instance #id',
        ),
    }
```

### 5.2 `detect_emulator(self, serial, emulator)` — 检测模拟器（第 120-169 行）

```python
def detect_emulator(self, serial, emulator=None):
    if emulator is None:
        # 遍历所有支持的模拟器
        emulators = []
        for emulator in self.SUPPORTED_EMULATORS.values():
            try:
                serials = emulator.id_and_serial
                for cur_serial in serials:
                    if cur_serial[1] == serial:
                        emulators.append([emulator, cur_serial[0]])
            except FileNotFoundError:
                pass

        if len(emulators) == 1:
            return emulators[0]  # 唯一匹配
        elif len(emulators) == 0:
            logger.warning('Emulator not found')
        else:
            logger.warning('Multiple emulators found')
        raise RequestHumanTakeover
    else:
        # 指定模拟器类型中查找
        serials = emulator.id_and_serial
        for cur_serial in serials:
            if cur_serial[1] == serial:
                return emulator, cur_serial[0]
        raise RequestHumanTakeover
```

### 5.3 `execute(command)` — 执行命令（第 171-182 行）

```python
@staticmethod
def execute(command):
    command = command.replace(r"\\", "/").replace("\\", "/").replace('"', '"')
    logger.info(f'Execute: {command}')
    return subprocess.Popen(command, close_fds=True)  # 仅 Windows
```

### 5.4 `task_kill(pid, name)` — 终止进程（第 184-211 行）

```python
@staticmethod
def task_kill(pid=None, name=None):
    command = 'taskkill '
    if pid is not None:
        if isinstance(pid, list):
            for p in pid:
                command += f'/pid {p} '
        else:
            command += f'/pid {pid} '
    elif name is not None:
        if isinstance(name, list):
            for n in name:
                command += f'/im {n} '
        else:
            command += f'/im {name} '
    command += '/t /f'  # /t 终止子进程，/f 强制终止
    return EmulatorManager.execute(command)
```

### 5.5 `detect_emulator_status(serial)` — 检测模拟器状态（第 219-224 行）

```python
def detect_emulator_status(self, serial):
    devices = self.list_device()
    for device in devices:
        if device.serial == serial:
            return device.status  # 'device'/'offline'/'unauthorized'
    return 'offline'  # 未找到设备
```

### 5.6 `emulator_start(serial, emulator, multi_id, command)` — 启动模拟器（第 226-258 行）

```python
def emulator_start(self, serial, emulator=None, multi_id=None, command=None):
    if command is None:
        command = '"' + os.path.abspath(os.path.join(emulator.root, emulator.emu_path)) + '"'
        if emulator.multi_para is not None and multi_id is not None:
            command += " " + emulator.multi_para.replace("#id", multi_id)

    logger.info('Start emulator')
    pipe = self.execute(command)  # 启动进程
    self.pid = pipe.pid
    self.sleep(10)  # 等待 10 秒

    # 轮询等待模拟器就绪
    for _ in range(20):
        if pipe.poll() is not None:
            break  # 进程已退出
        try:
            if super().adb_connect(serial):
                self.sleep(10)  # 额外等待完全启动
                return True
        except EmulatorNotRunningError:
            pass
        self.sleep(5)  # 每 5 秒重试
    return False
```

### 5.7 `emulator_kill(serial, emulator, multi_id, command)` — 终止模拟器（第 260-300 行）

```python
def emulator_kill(self, serial, emulator=None, multi_id=None, command=None):
    if command is None and emulator.kill_para is not None:
        command = '"' + os.path.abspath(os.path.join(emulator.root, emulator.emu_path)) + '"'
        if emulator.multi_para is not None and multi_id is not None:
            command += " " + emulator.multi_para.replace("#id", multi_id)
        command += " " + emulator.kill_para

    logger.info('Kill emulator')

    # BlueStacks5 特殊处理：通过 ADB 重启
    if emulator == self.SUPPORTED_EMULATORS['bluestacks_5']:
        try:
            self.adb_command(['reboot', '-p'], timeout=20)
            if self.detect_emulator_status(serial) == 'offline':
                return True
        except AdbError:
            return False

    # MuMu 特殊处理：终止所有相关进程
    if emulator == self.SUPPORTED_EMULATORS['mumu_player']:
        self.task_kill(pid=None, name=['NemuHeadless.exe', 'NemuPlayer.exe', 'NemuSvc.exe'])
    elif command is not None:
        self.execute(command)  # 使用 kill 参数
    else:
        self.task_kill(pid=self.pid, name=os.path.basename(emulator.emu_path))

    self.sleep(5)
    # 轮询确认已关闭
    for _ in range(10):
        if self.detect_emulator_status(serial) == 'offline':
            self.pid = None
            return True
        self.sleep(2)
    return False
```

### 5.8 `emulator_restart()` — 重启模拟器（第 302-326 行）

```python
def emulator_restart(self):
    serial, _ = get_serial_pair(self.serial)
    if serial is None:
        serial = self.serial

    if os.name != 'nt':
        logger.warning('Restart simulator only works under Windows')
        return False

    logger.hr('Emulator restart')

    # 检测或指定模拟器类型
    if self.config.get_arg('Restart', '') == 'auto':
        emulator, multi_id = self.detect_emulator(serial)
    else:
        emulator = self.SUPPORTED_EMULATORS[self.config.RestartEmulator_EmulatorType]
        emulator, multi_id = self.detect_emulator(serial, emulator=emulator)

    # 最多重试 3 次
    for _ in range(3):
        if not self.emulator_kill(serial, emulator, multi_id):
            continue
        if self.emulator_start(serial, emulator, multi_id):
            return True

    logger.warning('Restart emulator failed for 3 times')
    raise RequestHumanTakeover
```

## 6. 核心算法流程图

```
模拟器检测流程:
  │
  ├── 遍历 SUPPORTED_EMULATORS
  │     ├── Nox   → 读取 .vbox 文件 → 解析 hostport
  │     ├── MuMu  → 读取 .nemu 文件 → 解析 hostport
  │     └── BS5   → 读取 bluestacks.conf → 解析 adb_port
  │
  ├── 匹配 serial
  │     ├── 唯一匹配 → 返回 (emulator, multi_id)
  │     ├── 无匹配   → 报错
  │     └── 多匹配   → 报错
  │
  └── 返回 (EmulatorInstance, multi_id)

模拟器启动流程:
  │
  ├── 1. 构建启动命令
  │     ├── 可执行文件路径
  │     └── 多开参数（#id → 实际 ID）
  │
  ├── 2. subprocess.Popen() 启动
  │
  └── 3. 轮询等待（最多 20 次，每次 5 秒）
        ├── adb_connect(serial) 成功 → 等 10 秒 → 返回 True
        └── 进程退出或超时 → 返回 False

模拟器终止流程:
  │
  ├── BlueStacks5 → adb reboot -p
  ├── MuMu        → taskkill NemuHeadless/NemuPlayer/NemuSvc
  ├── 有 kill_para → 执行 kill 命令
  └── 其他        → taskkill /pid /t /f
  │
  └── 轮询确认 offline（最多 10 次，每次 2 秒）

模拟器重启流程:
  │
  ├── 1. 检测模拟器类型
  ├── 2. 杀死模拟器（最多重试 3 次）
  └── 3. 启动模拟器（最多重试 3 次）
```

## 7. 使用示例

```python
# 通过 Connection 继承使用
manager = EmulatorManager(config="oas1")

# 检测当前 serial 对应的模拟器
emulator, multi_id = manager.detect_emulator(manager.serial)

# 启动模拟器
manager.emulator_start(serial, emulator, multi_id)

# 检查状态
status = manager.detect_emulator_status(serial)  # 'device' / 'offline'

# 重启模拟器
manager.emulator_restart()

# 终止模拟器
manager.emulator_kill(serial, emulator, multi_id)
```

## 8. 设计模式总结

- **继承体系**: `VirtualBoxEmulator` → `EmulatorInstance` → `Bluestacks5Instance`，逐层特化
- **注册表模式**: `SUPPORTED_EMULATORS` 字典注册所有支持的模拟器类型
- **模板方法**: `emulator_start`/`emulator_kill` 定义固定流程，通过参数适配不同模拟器
- **轮询等待**: 启动和终止都使用轮询 + sleep 等待异步操作完成
- **多开支持**: 通过 `multi_para` 参数模板和 `multi_id` 实现多开实例管理
- **平台限制**: `emulator_restart` 明确检查 `os.name != 'nt'`，仅支持 Windows
