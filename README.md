# 3D 交通灯仿真 · 汇川 Easy PLC 双向联机

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](#运行要求)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-lightgrey.svg)](#运行要求)
[![three.js](https://img.shields.io/badge/three.js-WebGL-black.svg)](THIRD_PARTY_NOTICES.md)

**一个单文件的 3D 路口仿真页面 + 一个 Modbus TCP 网关**：网页里的红绿灯与倒计时完全由 PLC 的
Y 线圈 / D 寄存器驱动，网页上的按钮又能反向写 PLC 的 X / M 线圈——**页面里没有相位状态机**，
配时逻辑始终留在 PLC 里。

自带一个**本地 PLC 模拟器**，没有 PLC、没有 AutoShop 也能立刻看到完整效果。

## 功能

| 能力 | 说明 |
| --- | --- |
| 3D 路口 | 4 进口 × 红/黄/绿/左转共 16 路灯、灯杆数码管倒计时、真实光照与阴影（three.js / WebGL） |
| 虚拟车流 | 直行/左转车辆、停止线排队、通行统计、平均等待、碰撞检测（可关「车距保护」看追尾） |
| 视角 | 默认 / 俯视 / 低角度 / 东西侧、自动环绕、鼠标拖拽缩放平移 |
| 双向通信 | WebSocket 5 Hz 接收 PLC 状态；按钮点击写 X0–X7 / M0–M7 并回读确认 |
| 完全离线 | 单文件 HTML，three.js 内嵌，无 CDN、无外链、不联网（除本机网关） |
| 安装包 | 附带 PyInstaller + PowerShell 图形向导的安装器源码，目标机无需 Python |

## 运行要求

| 项目 | 要求 |
| --- | --- |
| 系统 | Windows 10 / 11（网关与安装器只用标准库 + PowerShell；网页部分浏览器跨平台） |
| Python | 3.10+（仅网关与模拟器需要） |
| 依赖 | `websockets`（见 `requirements.txt`） |
| PLC | 可选。汇川 **Easy** 系列，默认 Modbus TCP 从站：端口 `502`、站号 `1` |

```bat
python -m pip install -r requirements.txt
```

## 快速开始（无 PLC 也能跑）

开两个终端，都在仓库根目录：

```bat
:: 终端 1：启动本地 PLC 模拟器（监听 127.0.0.1:502，相位自动循环）
python tools\mock_plc.py

:: 终端 2：启动 WebSocket 网关（ws://localhost:8765）
python plc_gateway.py
```

然后双击/用浏览器打开 `交通灯仿真.html`，点右侧「连接网关」。

- 约 70 秒一个完整循环：南北直行绿 30s → 黄 3s → 全红 2s → 东西直行绿 30s → 黄 3s → 全红 2s
- 页面右侧「报文监视」能看到网关每 200 ms 推送的 `coils / reg / x / m`
- 点 X0–X7 / M0–M7 按钮，会真实写入模拟器并回读（不是本地假状态）
- 先验证链路可用：`python plc_gateway.py --check` 打印当前 Y/D/X/M

## 连接真实汇川 Easy PLC

1. 用 AutoShop 把 PLC 程序下载好，PLC 保持 RUN；Easy 默认开启 Modbus TCP 从站（端口 502，站号 1），无需额外配置。
2. 电脑与 PLC 设为**同网段**（例如 PLC `192.168.1.88`，电脑 `192.168.1.100`）。
3. 启动网关时传入 IP：

```bat
python plc_gateway.py --ip 192.168.1.88
```

4. 浏览器打开 `交通灯仿真.html` → 连接网关。

> 也支持后台仿真：如果在电脑上跑汇川的 PLC 仿真（同样占用 127.0.0.1:502），直接 `python plc_gateway.py` 即可。
> 注意：`tools/mock_plc.py` 与真实 PLC 仿真不能同时占用 502 端口。

## IO 映射

完整地址表、X/Y/M/D 说明与汇川 Easy 全地址范围见 [`IO映射表.md`](IO映射表.md)。核心部分：

| 区域 | 元件 | Modbus | 功能码 | 方向 | 含义 |
| --- | --- | --- | --- | --- | --- |
| Y | Y0–Y15 | `0xFC00` 起 16 点 | 01 读线圈 | PLC → 网页 | 4 方向 × 红/黄/绿/左转 |
| D | D0–D7 | `0x0000` 起 8 字 | 03 读保持寄存器 | PLC → 网页 | 4 方向 × 直行/左转 倒计时 |
| X | X0–X7 | `0xF800` 起 8 点 | 05 写单线圈 | 网页 → PLC | 8 个输入按钮，回读确认 |
| M | M0–M7 | `0x0000` 起 8 点 | 05 写单线圈 | 网页 ⇄ PLC | 8 个辅助继电器按钮 |

> X/Y 是**八进制**软元件编号，但 Modbus 按十进制地址映射（Y0 → 64512 = 0xFC00）。
> M 区线圈与 D 区寄存器都在 `0x0000`，属于不同功能码空间，互不冲突——这是 Easy 的标准映射。

## 架构

```
┌──────────────────────────┐        WebSocket ws://localhost:8765        ┌───────────────────┐
│  交通灯仿真.html          │  ←── 5 Hz 状态帧 coils/reg/x/m ──────────  │  plc_gateway.py   │
│  three.js 3D 场景 + 面板  │  ──── 按钮写线圈 {op:"write"} ──────────→  │  Modbus TCP 主站  │
└──────────────────────────┘                                            └─────────┬─────────┘
                                                                                  │ Modbus TCP :502
                                                          ┌───────────────────────┴───────────────┐
                                                          │ 汇川 Easy PLC（真机 / 后台仿真）      │
                                                          │ 或 tools/mock_plc.py（本仓库模拟器）  │
                                                          └───────────────────────────────────────┘
```

设计取舍：

- **网页不做配时**：相位状态机在 PLC 里，页面只按 Y 线圈点亮灯、按 D 寄存器显示倒计时。
  这样同一套页面可以对接任何配时方案，也便于用 PLC 程序做教学与调试。
- **网关只用标准库**：Modbus TCP 用 `socket` + `struct` 手写，不依赖 pymodbus，便于打包成单文件 EXE。
- **每次事务独立连接**：实现简单、失败即重连；5 Hz × 4 次读取对 PLC 压力很小。

## 目录结构

```
3d-traffic-light-sim/
├─ 交通灯仿真.html          # 单文件 3D 页面（three.js 内嵌，MIT 声明保留）
├─ plc_gateway.py           # Modbus TCP <-> WebSocket 网关
├─ IO映射表.md              # 汇川 Easy 地址表与使用说明
├─ tools/
│  └─ mock_plc.py           # 本地 PLC 模拟器（演示/自测用，带 --selftest）
├─ packaging/               # 安装包构建源码
│  ├─ setup_installer.py    # 单文件安装器/启动器（PyInstaller onefile）
│  ├─ wizard.ps1            # PowerShell 图形安装/卸载向导
│  ├─ make_icon.py          # 纯标准库生成多尺寸 ICO
│  ├─ logo.png / traffic_light.ico
└─ requirements.txt
```

## 构建

### 1. 网关 EXE

```bat
python -m pip install pyinstaller
python -m PyInstaller --onefile --name plc_gateway --clean --noconfirm plc_gateway.py
```

输出 `dist\plc_gateway.exe`，目标机无需 Python。

### 2. 安装包（可选）

安装器把 HTML、网关 EXE、IO 映射表、图标与 PowerShell 向导打进一个单文件安装包。
在**仓库根目录**执行（注意 `packaging/` 下的资源路径）：

```bat
python -m PyInstaller --onefile --name "交通灯仿真_安装包" --clean --noconfirm ^
  --icon "packaging/traffic_light.ico" ^
  --add-data "交通灯仿真.html;." --add-data "plc_gateway.exe;." --add-data "IO映射表.md;." ^
  --add-data "packaging/traffic_light.ico;." --add-data "packaging/logo.png;." --add-data "packaging/wizard.ps1;." ^
  packaging/setup_installer.py
```

安装器行为：

- 默认装到 `%LOCALAPPDATA%\Programs\3D 交通灯仿真`（无需管理员权限）
- 创建桌面/开始菜单快捷方式、「修改PLC地址」「IO映射表」「卸载」入口
- 启动时若 8765 端口未监听则拉起网关，再用默认浏览器打开页面
- 卸载走 PowerShell 图形向导，可清理安装目录与注册表 `HKCU\Software\3D Traffic Light Sim`

资源自检：

```bat
交通灯仿真_安装包.exe --check
```

## 测试

```bat
:: 模拟器自检：相位逻辑 + Modbus 功能码 01/03/05 + 写读回环（不需要端口）
python tools\mock_plc.py --selftest

:: 端到端：先起 mock_plc，再自检网关
python tools\mock_plc.py
python plc_gateway.py --check

:: 不开浏览器验证推送与写线圈回执
python tools\ws_probe.py --frames 3 --write X3=1
```

`plc_gateway.py --check` 的退出码：读到数据返回 `0`，连不上返回 `1`——方便脚本和 CI 判断。

CI（[.github/workflows/ci.yml](.github/workflows/ci.yml)）会跑 Python 编译检查、模拟器自检、
页面自包含检查与仓库卫生检查。

## 常见问题

**端口 502 被占用？**
真实的汇川后台仿真或上一次的模拟器没关。换端口：`python tools\mock_plc.py --port 15020`，
同时把 `plc_gateway.py` 里的 `PLC_PORT` 改成 15020。

**页面显示「未连接」？**
先确认网关已启动（终端 1 打印 `网关已启动 ws://localhost:8765`），再点页面上的「连接网关」。
浏览器若开了代理/隐私插件，可能拦截本机 WebSocket，请放行 `localhost`。

**连接失败但 PLC 在线？**
用 `python plc_gateway.py --check` 区分是 TCP 不通（IP/网段/防火墙）还是 Modbus 读失败（PLC 未 RUN、地址不对）。

**按钮点了没反应？**
按钮状态以 PLC 回读为准。确认 `--check` 里 X/M 读数正常，且页面已连接。

**没有 PLC 能看效果吗？**
可以，见上文「快速开始」——`tools/mock_plc.py` 就是为此准备的。

## 许可与第三方

本项目以 **MIT** 发布（见 [LICENSE](LICENSE)）。内嵌的 three.js 为 MIT、网关依赖 websockets 为 BSD-3-Clause、
打包工具 PyInstaller 仅构建时使用；详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

“汇川 / Inovance / Easy / AutoShop” 是其权利人商标，本项目为第三方工具，无隶属或背书关系。
**仅供学习与调试；真实路口控制逻辑必须由具备资质的工程人员设计、测试与验收。**

## 参与贡献

欢迎 Issue 与 PR。改代码前请先看 [CONTRIBUTING.md](CONTRIBUTING.md)，
并确认 `python tools/mock_plc.py --selftest` 与 `python plc_gateway.py --check` 仍然通过。
