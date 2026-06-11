# module.device.handle 模块详解

## 1. 文件概述

`handle.py` 定义了 `Handle` 类及辅助工具，负责 **Windows 窗口句柄（HWND）管理**，包括：
- 通过窗口标题查找句柄
- 构建窗口句柄树（父子窗口层级）
- 自动识别模拟器类型（MuMu、雷电、夜神、蓝叠、逍遥）
- 获取截图目标句柄和窗口尺寸
- 获取系统缩放比例

**文件路径**: `module/device/handle.py`
**代码行数**: 439 行
**平台限制**: 仅支持 Windows（依赖 win32 API）

## 2. 导入部分解释

```python
import re                        # 正则表达式
from enum import Enum            # 枚举类
from time import sleep           # 线程休眠
from cached_property import cached_property  # 缓存属性（第三方库）
from anytree import NodeMixin, RenderTree, PreOrderIter  # 树结构库

# Win32 API 导入
from win32api import GetSystemMetrics, SendMessage, MAKELONG, PostMessage
from win32print import GetDeviceCaps
from win32process import GetWindowThreadProcessId
from win32gui import (GetWindowText, EnumWindows, FindWindow, FindWindowEx,
                      IsWindow, GetWindowRect, GetWindowDC, DeleteObject,
                      SetForegroundWindow, IsWindowVisible, GetDC, GetParent,
                      EnumChildWindows)
from win32con import (SRCCOPY, DESKTOPHORZRES, DESKTOPVERTRES, WM_LBUTTONUP,
                      WM_LBUTTONDOWN, WM_ACTIVATE, WA_ACTIVE, MK_LBUTTON,
                      WM_NCHITTEST, WM_SETCURSOR, HTCLIENT, WM_MOUSEMOVE)
from module.config.config import Config
from module.logger import logger
```

## 3. 辅助函数（第 24-73 行）

### 3.1 `handle_title2num(title)` — 标题转句柄

```python
def handle_title2num(title: str) -> int:
    return FindWindow(None, title)  # Win32 API，找不到返回 0
```

### 3.2 `handle_num2title(num)` — 句柄转标题

```python
def handle_num2title(num: int) -> str:
    return None if num is None or num == 0 or num == '' else GetWindowText(num)
```

### 3.3 `is_handle_valid(num)` — 句柄有效性检查

```python
def is_handle_valid(num: int) -> bool:
    return IsWindow(num)  # Win32 API
```

### 3.4 `handle_num2pid(num)` — 句柄转进程 ID

```python
def handle_num2pid(num: int) -> int:
    return 0 if num is None or num == 0 or num == '' else GetWindowThreadProcessId(num)[1]
```

### 3.5 `window_scale_rate()` — 系统缩放比例

```python
def window_scale_rate() -> float:
    hDC = GetDC(0)
    wReal = GetDeviceCaps(hDC, DESKTOPHORZRES)   # 物理分辨率
    hReal = GetDeviceCaps(hDC, DESKTOPVERTRES)
    wAfter = GetSystemMetrics(0)                  # 缩放后分辨率
    hAfter = GetSystemMetrics(1)
    return round(wReal / wAfter, 2)               # 如 1.25 表示 125% 缩放
```

## 4. WindowNode 类（第 76-87 行）

```python
class WindowNode(NodeMixin):
    def __init__(self, name, num, parent=None):
        super().__init__()
        self.name = name      # 窗口标题
        self.num = num        # 窗口句柄号
        self.parent = parent  # 父节点

    @classmethod
    def get_tree_depth(cls, root_node: 'WindowNode'):
        if not root_node.children:
            return 1 if root_node else 0
        return max(node.depth for node in root_node.descendants) + 1
```

使用 `anytree` 库的 `NodeMixin` 实现树结构，每个节点代表一个窗口。

## 5. EmulatorFamily 枚举（第 90-96 行）

```python
class EmulatorFamily(Enum):
    FAMILY_MUMU = 10          # MuMu 模拟器
    FAMILY_NOX = 20           # 夜神模拟器
    FAMILY_LD = 30            # 雷电模拟器
    FAMILY_MEMU = 40          # 逍遥模拟器
    FAMILY_BLUESTACKS = 50    # 蓝叠模拟器
    FAMILY_OTHER = 60         # 其他模拟器
```

## 6. Handle 类详解（第 130-438 行）

### 6.1 类变量

```python
emulator_list = ['MuMu12', 'MuMu', '雷电', '夜神', '蓝叠', '逍遥', '模拟器']
```

用于从窗口标题中识别模拟器的关键词列表。

```python
emulator_handle = {
    'nox_player': ['root_handle_title', 'Nox'],
    'ld_player': ['TheRender'],
    'mumu_player': ['root_handle_title', 'NemuPlayer'],
    'mumu_player_12': ['root_handle_title', 'MuMuPlayer'],
    'bluestacks_5': ['root_handle_title'],
    # ...
}
```

各模拟器的句柄树特征路径。

### 6.2 `__init__(self, config)` — 构造函数（第 161-223 行）

```python
def __init__(self, config) -> None:
    logger.hr('Handle')
    # 初始化配置
    if self.config is None:
        if isinstance(config, str):
            self.config = Config(config, task=None)
        else:
            self.config = config

    # 获取根句柄
    self.root_handle = self.config.script.device.handle
    if self.root_handle == "auto":
        # 自动检测：列举所有窗口 → 找到模拟器窗口
        window_list = Handle.all_windows()
        self.root_handle_title = self.auto_handle_title(window_list)
        self.root_handle_num = handle_title2num(self.root_handle_title)
    elif isinstance(self.root_handle, str):
        try:
            self.root_handle_num = int(self.root_handle)  # 数字句柄
        except ValueError:
            self.root_handle_num = handle_title2num(self.root_handle)  # 标题查找

    # 构建句柄树
    self.root_node = WindowNode(name=self.root_handle_title, num=self.root_handle_num)
    Handle.handle_tree(self.root_handle_num, self.root_node)

    # 如果没有子窗口，等待重试（模拟器可能还在初始化）
    if not self.root_node.children:
        for i in range(9):
            sleep(1)
            self.root_node = WindowNode(...)
            Handle.handle_tree(self.root_handle_num, self.root_node)
            if self.root_node.children:
                break

    # 打印句柄树结构
    for pre, fill, node in RenderTree(self.root_node):
        logger.info("%s%s" % (pre, node.name))
```

### 6.3 `all_windows()` — 获取所有窗口（第 226-240 行）

```python
@staticmethod
def all_windows() -> list:
    def enum_windows_callback(hwnd, windows):
        window_text = GetWindowText(hwnd)
        windows.append(window_text)
    windows = []
    EnumWindows(enum_windows_callback, windows)  # Win32 枚举所有顶层窗口
    return windows
```

### 6.4 `auto_handle_title(windows)` — 自动识别模拟器窗口（第 242-281 行）

```python
@classmethod
def auto_handle_title(cls, windows: list) -> str:
    emu_list = []
    for window_title in windows:
        for item in Handle.emulator_list:
            if window_title.find(item) != -1:
                emu_list.append(window_title)  # 包含模拟器关键词

    # 特殊处理 MuMu12
    if 'MuMu模拟器12' in emu_list and 'MuMuPlayer' in emu_list:
        emulator_title = 'MuMu模拟器12'

    # MuMu 5.0 特殊处理
    if emulator_title == '' and 'MuMu安卓设备' in emu_list:
        emulator_title = 'MuMu安卓设备'

    # 多个模拟器时使用第一个
    if len(emu_list) > 1 and emulator_title == '':
        emulator_title = emu_list[0]

    return emulator_title
```

### 6.5 `handle_tree(hwnd, node, level)` — 构建句柄树（第 283-303 行）

```python
@staticmethod
def handle_tree(hwnd, node: WindowNode, level: int = 0) -> None:
    child_windows = []
    EnumChildWindows(hwnd, lambda hwnd, param: param.append(hwnd), child_windows)

    if not child_windows:
        return
    for child_hwnd in child_windows:
        if GetParent(child_hwnd) == hwnd:  # 确认是直接子窗口
            child_text = GetWindowText(child_hwnd)
            child_node = WindowNode(name=child_text, num=child_hwnd, parent=node)
            Handle.handle_tree(child_hwnd, child_node, level + 1)  # 递归
```

### 6.6 `emulator_family` — 识别模拟器类型（第 305-342 行）

```python
@cached_property
def emulator_family(self) -> EmulatorFamily:
    children_num = len(self.root_node.children)
    if children_num == 1:
        name = self.root_node.children[0].name
        if name == 'MuMuPlayer':
            return EmulatorFamily.FAMILY_MUMU
        elif name == 'MuMuNxDevice':
            return EmulatorFamily.FAMILY_MUMU
        elif name == 'NemuPlayer':
            return EmulatorFamily.FAMILY_MUMU
        elif name == 'TheRender':
            return EmulatorFamily.FAMILY_LD
        elif name == 'HD-Player':
            return EmulatorFamily.FAMILY_BLUESTACKS
    elif children_num >= 3:
        name = self.root_node.children[0].name
        if name == 'Nox':
            return EmulatorFamily.FAMILY_NOX

    # 基于标题的回退判定
    for emu in Handle.emulator_list:
        if self.root_handle_title.find(emu) != -1:
            # 匹配到关键词，返回对应类型
    return EmulatorFamily.FAMILY_OTHER
```

**判定逻辑**: 先通过句柄树结构判定（更准确），再回退到标题关键词匹配。

### 6.7 `screenshot_handle_num` — 截图目标句柄（第 344-384 行）

```python
@cached_property
def screenshot_handle_num(self) -> int:
    if self.emulator_family == EmulatorFamily.FAMILY_MUMU:
        # MuMu12: 第一个子窗口 (MuMuPlayer)
        # MuMu: 第一个子窗口 (NemuPlayer)
        # MuMu 5.0: 第一个子窗口 (MuMuNxDevice)
        return self.root_node.children[0].num
    elif self.emulator_family == EmulatorFamily.FAMILY_NOX:
        # 夜神: children[1].children[1] 或 children[2].children[1]
        try:
            return self.root_node.children[1].children[1].num
        except:
            return self.root_node.children[2].children[1].num
    elif self.emulator_family == EmulatorFamily.FAMILY_LD:
        # 雷电: 遍历查找 'TheRender'
        for node in PreOrderIter(self.root_node):
            if node.name == 'TheRender':
                return node.num
    elif self.emulator_family == EmulatorFamily.FAMILY_BLUESTACKS:
        # 蓝叠: 遍历查找 'HD-Player'
        for node in PreOrderIter(self.root_node):
            if node.name == 'HD-Player':
                return node.num
    return self.root_node.num  # 回退到根句柄
```

### 6.8 `screenshot_size` — 截图尺寸（第 386-405 行）

```python
@cached_property
def screenshot_size(self) -> tuple or None:
    winRect = GetWindowRect(self.screenshot_handle_num)  # 获取窗口矩形
    scale_rate = window_scale_rate()                     # 系统缩放
    width_before = winRect[2] - winRect[0]   # 像素宽度
    height_before = winRect[3] - winRect[1]  # 像素高度
    width, height = width_before, height_before
    # 高缩放设备上校正为 1280x720
    if abs((width_before * scale_rate) - 1280) < 5:
        width = 1280
    if abs((height_before * scale_rate) - 720) < 5:
        height = 720
    return width, height
```

## 7. 核心算法流程图

```
Handle 初始化流程:
  │
  ├── 1. 获取根句柄
  │     ├── "auto" → all_windows() → auto_handle_title()
  │     ├── 数字   → 直接使用
  │     └── 字符串 → FindWindow(title)
  │
  ├── 2. 构建句柄树
  │     ├── handle_tree() 递归枚举子窗口
  │     └── 无子窗口时等待重试（最多 10 次，每次 1 秒）
  │
  ├── 3. 识别模拟器类型
  │     ├── 1 个子窗口
  │     │     ├── MuMuPlayer    → FAMILY_MUMU
  │     │     ├── MuMuNxDevice  → FAMILY_MUMU
  │     │     ├── NemuPlayer    → FAMILY_MUMU
  │     │     ├── TheRender     → FAMILY_LD
  │     │     └── HD-Player     → FAMILY_BLUESTACKS
  │     ├── ≥ 3 个子窗口
  │     │     └── Nox           → FAMILY_NOX
  │     └── 标题关键词回退
  │
  ├── 4. 获取截图句柄
  │     ├── MuMu     → children[0].num
  │     ├── 夜神     → children[1].children[1].num
  │     ├── 雷电     → 遍历查找 'TheRender'
  │     └── 蓝叠     → 遍历查找 'HD-Player'
  │
  └── 5. 获取截图尺寸
        └── GetWindowRect × 缩放比例 → 校正到 1280x720

各模拟器句柄树结构:
  MuMu12:
    MuMuPlayer (截图目标)
      └── nemudisplay

  雷电:
    TheRender (截图目标)
      └── sub

  夜神:
    Nox
      ├── Nox
      │   └── toolbar_nox
      └── Nox (截图目标)
          └── Nox
              └── sub

  蓝叠:
    HD-Player (截图目标)
      └── _ctl.W
```

## 8. 使用示例

```python
# 自动检测模拟器窗口
h = Handle(config='oas1')

# 查看句柄信息
print(f'根窗口: {h.root_handle_title}')
print(f'句柄号: {h.root_handle_num}')
print(f'模拟器类型: {h.emulator_family}')
print(f'截图句柄: {h.screenshot_handle_num}')
print(f'截图尺寸: {h.screenshot_size}')
print(f'系统缩放: {h.window_scale_rate}')

# 手动指定句柄
h2 = Handle(config='oas1')  # config 中设置 handle 为具体句柄号或标题
```

## 9. 设计模式总结

- **树结构模式**: 使用 `anytree` 库构建窗口层级树，支持递归遍历和深度计算
- **策略模式**: 根据 `EmulatorFamily` 选择不同的截图句柄获取策略
- **自动检测模式**: 通过遍历所有窗口 + 关键词匹配实现模拟器自动发现
- **缓存属性**: `@cached_property` 避免重复的 Win32 API 调用
- **重试等待**: 句柄树构建时支持重试，应对模拟器初始化延迟
- **Windows 专有**: 整个模块深度依赖 Win32 API，不支持跨平台
