# 第三方组件与商标说明

本项目自身代码以 [MIT](LICENSE) 发布。以下是随附或依赖的第三方组件。

| 组件 | 许可 | 用途 | 说明 |
| --- | --- | --- | --- |
| [three.js](https://threejs.org/) | MIT | 3D 渲染（r1xx，内嵌于 `交通灯仿真.html`） | 文件内保留原始 `@license` 与 `SPDX-License-Identifier: MIT` 声明，未修改其代码 |
| [websockets](https://github.com/python-websockets/websockets) | BSD-3-Clause | 网关的 WebSocket 服务 | 通过 `pip install websockets` 安装 |
| [PyInstaller](https://pyinstaller.org/) | GPL-2.0-with-bootloader-exception | 仅构建时打包 EXE | bootloader 例外允许分发打包产物；源码不包含其代码 |
| Python | PSF License | 运行时 | |

## three.js

`交通灯仿真.html` 内嵌了 three.js 的压缩构建，原文保留：

```
/**
 * @license
 * Copyright 2010-2021 Three.js Authors
 * SPDX-License-Identifier: MIT
 */
```

three.js 的 MIT 许可允许自由使用与再分发，但要求保留版权与许可声明——因此本仓库不拆分或删除该注释块。

## 汇川 / Inovance

“汇川”“Easy”“AutoShop”“MVS”等名称与商标归深圳市汇川技术股份有限公司所有。
本项目是**第三方**的仿真与学习工具，与汇川官方无隶属、授权或背书关系；不包含任何汇川的闭源软件、
PLC 固件或 SDK。Modbus 寄存器映射依据公开的通信手册整理，实际项目请以官方手册与 AutoShop 工程为准。

## 免责声明

本项目仅供学习、演示与调试辅助。交通信号配时涉及安全，任何真实路口控制逻辑必须由具备资质的
工程人员依据当地规范设计、测试与验收，本项目不对由此产生的后果负责。
