# server.py 代码详解

## 1. 文件概述

`server.py` 定义了服务器相关的配置和工具函数，用于管理不同服务器（cn、en、jp、tw）的配置。它提供了服务器识别、包名转换、服务器列表等功能。

**主要职责：**
- 定义有效服务器列表
- 管理包名与服务器的映射关系
- 提供服务器设置和转换函数
- 存储各服务器的区服列表

## 2. 导入部分解释

```python
# 本文件没有导入任何外部模块
# 使用全局变量管理服务器状态
```

## 3. 类定义解释

```python
# 本文件没有定义类
# 使用模块级变量和函数实现功能
```

## 4. 每个方法的逐行解释

### 4.1 模块级变量

```python
server = 'cn'  # 默认服务器为中国服务器

VALID_SERVER = ['cn', 'en', 'jp', 'tw']  # 有效服务器列表

VALID_PACKAGE = {
    'com.netease.onmyoji.wyzymnqsd_cps': 'cn'  # 包名到服务器的映射
}

VALID_CHANNEL_PACKAGE = {
    # 应用商店包名映射
    'com.bilibili.blhx.huawei': ('cn', '华为'),
    'com.bilibili.blhx.mi': ('cn', '小米'),
    'com.tencent.tmgp.bilibili.blhx': ('cn', '腾讯应用宝'),
    'com.bilibili.blhx.baidu': ('cn', '百度'),
    'com.bilibili.blhx.qihoo': ('cn', '360'),
    'com.bilibili.blhx.nearme.gamecenter': ('cn', 'oppo'),
    'com.bilibili.blhx.vivo': ('cn', 'vivo'),
    'com.bilibili.blhx.mz': ('cn', '魅族'),
    
    # 第三方游戏平台
    'com.bilibili.blhx.uc': ('cn', 'UC九游'),
    'com.bilibili.blhx.mzw': ('cn', '拇指玩'),
    'com.yiwu.blhx.yx15': ('cn', '一五游戏'),
    'com.bilibili.blhx.m4399': ('cn', '4399')
}

VALID_SERVER_LIST = {
    'cn_android': [
        '莱茵演习', '巴巴罗萨', '霸王行动', '冰山行动', '彩虹计划',
        '发电机计划', '瞭望台行动', '十字路口行动', '朱诺行动',
        '杜立特空袭', '地狱犬行动', '开罗宣言', '奥林匹克行动',
        '小王冠行动', '波茨坦公告', '白色方案', '瓦尔基里行动',
        '曼哈顿计划', '八月风暴', '秋季旅行', '水星行动', '莱茵河卫兵',
        '北极光计划', '长戟计划'
    ],
    'cn_ios': [
        '夏威夷', '珊瑚海', '中途岛', '铁底湾', '所罗门', '马里亚纳',
        '莱特湾', '硫磺岛', '冲绳岛', '阿留申群岛', '马耳他'
    ],
    'cn_channel': [
        '皇家巡游', '大西洋宪章', '十字军行动', '龙骑兵行动', '冥王星行动'
    ],
    'en': [
        'Avrora', 'Lexington', 'Sandy', 'Washington', 'Amagi',
        'Little Enterprise'
    ],
    'jp': [
        'ブレスト', '横須賀', '佐世保', '呉', '舞鶴',
        'ルルイエ', 'サモア', '大湊', 'トラック', 'ラバウル',
        '鹿児島', 'マドラス', 'サンディエゴ', '竹敷', 'キール',
        '若松', 'オデッサ', 'スイートバン'
    ]
}
```

**变量说明：**
- `server`: 当前服务器标识
- `VALID_SERVER`: 支持的服务器列表
- `VALID_PACKAGE`: 标准包名到服务器的映射
- `VALID_CHANNEL_PACKAGE`: 渠道包名到服务器的映射
- `VALID_SERVER_LIST`: 各服务器的区服列表

### 4.2 set_server 函数

```python
def set_server(package_or_server: str):
    """
    Change server and this will effect globally,
    including assets and server specific methods.

    Args:
        package_or_server: package name or server.
    """
    global server
    server = to_server(package_or_server)
```

**功能：** 设置全局服务器。

**参数说明：**
- `package_or_server`: 包名或服务器标识

**注意：** 使用 `global` 关键字修改模块级变量。

### 4.3 to_server 函数

```python
def to_server(package_or_server: str) -> str:
    """
    Convert package/server to server.
    To unknown packages, consider they are a CN channel servers.
    """
    # 如果是有效的服务器标识，直接返回
    if package_or_server in VALID_SERVER:
        return package_or_server
    
    # 如果是标准包名，返回对应的服务器
    elif package_or_server in VALID_PACKAGE:
        return VALID_PACKAGE[package_or_server]
    
    # 如果是渠道包名，返回对应的服务器
    elif package_or_server in VALID_CHANNEL_PACKAGE:
        return VALID_CHANNEL_PACKAGE[package_or_server][0]
    
    # 未知包名，默认返回中国服务器
    else:
        return 'cn'
```

**功能：** 将包名或服务器标识转换为服务器标识。

**转换逻辑：**
1. 检查是否为有效服务器标识
2. 检查是否为标准包名
3. 检查是否为渠道包名
4. 默认返回 'cn'

### 4.4 to_package 函数

```python
def to_package(package_or_server: str) -> str:
    """
    Convert package/server to package.
    """
    package_or_server = package_or_server.lower()
    
    # 如果已经是包名，直接返回
    if package_or_server in VALID_PACKAGE:
        return package_or_server

    # 查找服务器对应的包名
    for key, value in VALID_PACKAGE.items():
        if value == package_or_server:
            return key

    # 找不到对应的包名
    raise ValueError(f'Server invalid: {package_or_server}')
```

**功能：** 将服务器标识转换为包名。

**转换逻辑：**
1. 转换为小写
2. 检查是否已经是包名
3. 查找服务器对应的包名
4. 找不到则抛出异常

## 5. 核心算法流程图

### 5.1 服务器转换流程

```
┌─────────────────────────────────────────────────────────────┐
│                   to_server() 转换流程                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  输入: package_or_server                                     │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 在 VALID_SERVER 中？                                 │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                        │
│     ├─ 是 ──→ 返回服务器标识                                │
│     │                                                        │
│     └─ 否 ──→ 继续检查                                      │
│              │                                               │
│              ▼                                               │
│        ┌─────────────────────────────────────────────┐     │
│        │ 在 VALID_PACKAGE 中？                        │     │
│        └─────────────────────────────────────────────┘     │
│              │                                               │
│              ├─ 是 ──→ 返回对应的服务器                      │
│              │                                               │
│              └─ 否 ──→ 继续检查                              │
│                       │                                      │
│                       ▼                                      │
│                 ┌─────────────────────────────────────┐    │
│                 │ 在 VALID_CHANNEL_PACKAGE 中？        │    │
│                 └─────────────────────────────────────┘    │
│                       │                                      │
│                       ├─ 是 ──→ 返回对应的服务器            │
│                       │                                      │
│                       └─ 否 ──→ 返回 'cn'（默认）          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 包名转换流程

```
┌─────────────────────────────────────────────────────────────┐
│                   to_package() 转换流程                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  输入: package_or_server                                     │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 转换为小写                                           │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 在 VALID_PACKAGE 中？                                │   │
│  └─────────────────────────────────────────────────────┘   │
│     │                                                        │
│     ├─ 是 ──→ 返回包名                                      │
│     │                                                        │
│     └─ 否 ──→ 查找服务器对应的包名                          │
│              │                                               │
│              ├─ 找到 ──→ 返回包名                            │
│              │                                               │
│              └─ 未找到 ──→ 抛出 ValueError                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 服务器架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      服务器架构                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    服务器类型                         │   │
│  │  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐               │   │
│  │  │ cn  │  │ en  │  │ jp  │  │ tw  │               │   │
│  │  └─────┘  └─────┘  └─────┘  └─────┘               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    包名映射                           │   │
│  │  ┌─────────────────────────────┐                    │   │
│  │  │ com.netease.onmyoji...     │ ──→ cn             │   │
│  │  └─────────────────────────────┘                    │   │
│  │  ┌─────────────────────────────┐                    │   │
│  │  │ com.bilibili.blhx.huawei   │ ──→ cn (华为)      │   │
│  │  └─────────────────────────────┘                    │   │
│  │  ...                                                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    区服列表                           │   │
│  │  cn_android: [莱茵演习, 巴巴罗萨, ...]               │   │
│  │  cn_ios: [夏威夷, 珊瑚海, ...]                       │   │
│  │  en: [Avrora, Lexington, ...]                        │   │
│  │  jp: [ブレスト, 横須賀, ...]                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 6. 使用示例

```python
import module.config.server as server_module
from module.config.server import set_server, to_server, to_package, VALID_SERVER_LIST

# 设置当前服务器
set_server('cn')
print(f"当前服务器: {server_module.server}")

# 包名转服务器
server = to_server('com.netease.onmyoji.wyzymnqsd_cps')
print(f"包名对应的服务器: {server}")  # 输出: cn

# 渠道包名转服务器
server = to_server('com.bilibili.blhx.huawei')
print(f"渠道包名对应的服务器: {server}")  # 输出: cn

# 服务器转包名
package = to_package('cn')
print(f"服务器对应的包名: {package}")  # 输出: com.netease.onmyoji.wyzymnqsd_cps

# 获取区服列表
cn_android_servers = VALID_SERVER_LIST['cn_android']
print(f"安卓区服列表: {cn_android_servers}")

en_servers = VALID_SERVER_LIST['en']
print(f"英语区服列表: {en_servers}")

# 未知包名处理
server = to_server('unknown.package.name')
print(f"未知包名对应的服务器: {server}")  # 输出: cn（默认）

# 错误处理
try:
    package = to_package('invalid_server')
except ValueError as e:
    print(f"错误: {e}")
```

## 7. 设计模式总结

### 7.1 模块模式（Module）
使用 Python 模块组织相关功能，通过模块级变量管理状态。

### 7.2 映射模式（Mapping）
使用字典实现包名到服务器的映射关系。

### 7.3 默认值模式
对于未知输入，返回默认值 'cn' 而不是抛出异常。

### 7.4 全局状态模式
使用 `global` 关键字管理服务器状态。

**设计优点：**
- 简单清晰：使用字典实现映射
- 容错性强：未知输入返回默认值
- 易于扩展：添加新服务器只需修改字典
- 分类明确：标准包名和渠道包名分开管理

**使用场景：**
- 多服务器游戏脚本
- 包名识别和服务器选择
- 区服列表展示

**注意事项：**
- 使用 `import module.config.server as server_module` 而不是 `from xxx import xxx`
- 全局变量 `server` 的修改会影响整个应用
- 区服名称使用中文，可能需要编码处理
- 渠道包名映射值是元组 `(server, channel_name)`
