# 贡献指南

欢迎改进「3D 交通灯仿真」。项目很小：一个单文件网页、一个 Python 网关、一个 PLC 模拟器和一套安装器源码。

## 本地跑起来

```bat
python -m pip install -r requirements.txt
python tools\mock_plc.py        :: 终端 1：模拟 PLC
python plc_gateway.py           :: 终端 2：WebSocket 网关
:: 浏览器打开 交通灯仿真.html，点「连接网关」
```

没有 PLC 也能开发；模拟器会按固定 70 秒相位循环点亮 Y 线圈、填写 D 倒计时。

## 代码地图

```
交通灯仿真.html       页面：three.js 场景、车流、面板、WebSocket 客户端
plc_gateway.py        网关：Modbus TCP 主站（标准库手写）+ WebSocket 广播 + 写线圈
tools/mock_plc.py     本地 PLC 模拟器：Modbus TCP 从站 + 相位/倒计时 + --selftest
IO映射表.md           地址表（改映射时先改这里，再改网关与页面）
packaging/            安装器：PyInstaller onefile + PowerShell 图形向导 + 图标生成
```

约定：

1. **配时逻辑留在 PLC**：页面不实现相位状态机，只按 Y 线圈点灯、按 D 寄存器显示倒计时。
   任何“让网页自己跑配时”的改动都需要先讨论。
2. **网关只用标准库**：Modbus TCP 用 `socket`/`struct` 实现，避免为打包引入 pymodbus。
3. **保持页面单文件**：three.js 内嵌是刻意的（可离线、可塞进安装包），不要改成 CDN 引用；
   如需升级 three.js，替换 `script#three-lib` 内容并**保留 `@license` 注释**。
4. **地址映射三处一致**：`IO映射表.md`、`plc_gateway.py` 的 `ADDR`、页面里的 IO 表格。
5. **不要提交** `*.exe`、`dist/`、`build/` 等构建产物。

## 改动后自检

```bat
python tools\mock_plc.py --selftest     :: 相位 + Modbus 协议回环
python plc_gateway.py --check           :: 需要先启动模拟器
```

提交前确认：

- [ ] 上述自检通过
- [ ] 改了页面：浏览器里点过「连接网关」，看灯与倒计时正常
- [ ] 改了地址：`IO映射表.md` 与 README 同步更新
- [ ] 没有提交构建产物、个人路径或真实 PLC 的现场参数

## 提交规范

采用 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/)：

```
feat(page): 支持右转箭头灯
fix(gateway): 连接被 PLC 重置后立即重连
feat(mock): 增加 --offset 参数调整相位起点
docs: 补充 Easy 的 Modbus 地址说明
```

## 许可

本项目以 **MIT** 发布。提交贡献即表示你同意以同一许可授权你的代码，并确认没有引入
许可不兼容的第三方组件（尤其是内嵌到页面的库）。
