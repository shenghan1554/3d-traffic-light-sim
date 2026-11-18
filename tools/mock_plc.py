# -*- coding: utf-8 -*-
"""本地 Modbus TCP 从站（汇川 Easy 系列 PLC 模拟器）

用途：没有真实 PLC / AutoShop 仿真时，也能把 3D 网页完整跑起来看效果。
地址映射与 ``IO映射表.md`` 完全一致，网关与网页不需要任何改动。

    Y 0xFC00 起 16 点     4 方向 x 红/黄/绿/左（本模拟器自动按相位点亮）
    X 0xF800 起 8 点      网页按钮写入，模拟器原样保存并回读
    M 0x0000 起 8 点      网页按钮写入，模拟器原样保存并回读
    D 0x0000 起 8 个寄存器 4 方向 x 直行/左转 倒计时（本模拟器自动填写）

相位循环（共 70 秒）：

    南北直行绿 30s -> 南北黄 3s -> 全红 2s -> 东西直行绿 30s -> 东西黄 3s -> 全红 2s

用法：

    python tools/mock_plc.py                  # 监听 127.0.0.1:502（与网关默认一致）
    python tools/mock_plc.py --port 15020     # 端口被占用时换端口（网关需同步改 PLC_PORT）
    python tools/mock_plc.py --selftest       # 不需要端口，只验证相位与协议实现

然后：

    python plc_gateway.py --check             # 应打印 Y/D/X/M 实时值
    python plc_gateway.py                     # 启动网关，再打开 交通灯仿真.html 点「连接网关」

注意：这是**演示用的简化模拟器**，不是汇川官方软件，也不实现完整 Modbus 功能码；
生产逻辑请以 AutoShop 中的 PLC 程序为准。
"""

from __future__ import annotations

import argparse
import math
import socket
import socketserver
import struct
import sys
import threading
import time

# ==================== 与 IO映射表.md 一致的地址 ====================
ADDR_Y = 0xFC00          # Y0-Y15 输出线圈（灯）
ADDR_X = 0xF800          # X0-X7  输入线圈
ADDR_M = 0x0000          # M0-M7  辅助继电器
ADDR_D = 0x0000          # D0-D7  保持寄存器（倒计时）

COIL_SPACE = 0x10000     # 0x0000-0xFFFF 全地址空间
REG_SPACE = 0x10000

POLL_HZ_HINT = 5

# 相位表：(名称, 时长秒)
PHASES = [
    ("NS_GREEN", 30),
    ("NS_YELLOW", 3),
    ("ALL_RED", 2),
    ("EW_GREEN", 30),
    ("EW_YELLOW", 3),
    ("ALL_RED", 2),
]
CYCLE_TOTAL = sum(d for _, d in PHASES)
PHASE_START = []
_acc = 0
for _name, _dur in PHASES:
    PHASE_START.append(_acc)
    _acc += _dur

# 方向顺序与 Y 偏移：北 0、东 4、南 8、西 12；每方向 红/黄/绿/左
DIRS = ("north", "east", "south", "west")
OFFSET = {"north": 0, "east": 4, "south": 8, "west": 12}
LAMP = {"r": 0, "y": 1, "g": 2, "l": 3}


class PlcState:
    """一块 Easy PLC 的最小内存镜像 + 固定配时相位。"""

    def __init__(self, cycle_offset: float = 0.0) -> None:
        self.coils = bytearray(COIL_SPACE)
        self.regs = [0] * REG_SPACE
        self._t0 = time.monotonic() - cycle_offset
        self._last_phase = None

    # ---------- 时间 / 相位 ----------
    def elapsed(self) -> float:
        return (time.monotonic() - self._t0) % CYCLE_TOTAL

    def phase(self) -> tuple[str, float, float]:
        """返回 (相位名, 已持续秒, 剩余秒)。"""
        t = self.elapsed()
        for i, (name, dur) in enumerate(PHASES):
            start = PHASE_START[i]
            if start <= t < start + dur:
                return name, t - start, start + dur - t
        return PHASES[-1][0], 0.0, 0.0

    def _next_green(self, group: str) -> float:
        """该方向组下一次绿灯开始的时间点（周期内秒数）。"""
        return PHASE_START[0] if group == "NS" else PHASE_START[3]

    # ---------- 刷新输出 ----------
    def apply_phase(self) -> None:
        name, _, remain = self.phase()
        if name == self._last_phase:
            return
        self._last_phase = name

        ns_green = name == "NS_GREEN"
        ns_yellow = name == "NS_YELLOW"
        ew_green = name == "EW_GREEN"
        ew_yellow = name == "EW_YELLOW"

        def set_dir(direction: str, red: int, yellow: int, green: int, left: int = 0) -> None:
            base = ADDR_Y + OFFSET[direction]
            self.coils[base + LAMP["r"]] = 1 if red else 0
            self.coils[base + LAMP["y"]] = 1 if yellow else 0
            self.coils[base + LAMP["g"]] = 1 if green else 0
            self.coils[base + LAMP["l"]] = 1 if left else 0

        set_dir("north", red=not (ns_green or ns_yellow), yellow=ns_yellow, green=ns_green)
        set_dir("south", red=not (ns_green or ns_yellow), yellow=ns_yellow, green=ns_green)
        set_dir("east", red=not (ew_green or ew_yellow), yellow=ew_yellow, green=ew_green)
        set_dir("west", red=not (ew_green or ew_yellow), yellow=ew_yellow, green=ew_green)

    def refresh(self) -> None:
        """每次请求前调用：推进相位并更新倒计时寄存器。"""
        self.apply_phase()
        name, _, remain = self.phase()
        t = self.elapsed()

        def seconds_to_green(group: str) -> int:
            nxt = self._next_green(group)
            if group == "NS" and name in ("NS_GREEN", "NS_YELLOW"):
                return max(0, int(math.ceil(remain)))
            if group == "EW" and name in ("EW_GREEN", "EW_YELLOW"):
                return max(0, int(math.ceil(remain)))
            delta = (nxt - t) % CYCLE_TOTAL
            if delta <= 0.5:
                delta = CYCLE_TOTAL
            return int(math.ceil(delta))

        ns_cd = seconds_to_green("NS")
        ew_cd = seconds_to_green("EW")
        # D0/D1 北 直行/左转, D2/D3 东, D4/D5 南, D6/D7 西
        self.regs[ADDR_D + 0] = ns_cd   # 北直行
        self.regs[ADDR_D + 1] = 0       # 北左转（本模拟器不单独放行左转）
        self.regs[ADDR_D + 2] = ew_cd   # 东直行
        self.regs[ADDR_D + 3] = 0
        self.regs[ADDR_D + 4] = ns_cd   # 南直行
        self.regs[ADDR_D + 5] = 0
        self.regs[ADDR_D + 6] = ew_cd   # 西直行
        self.regs[ADDR_D + 7] = 0

    # ---------- Modbus 数据访问 ----------
    def read_coils(self, addr: int, count: int) -> list[int]:
        return [self.coils[(addr + i) % COIL_SPACE] & 1 for i in range(count)]

    def read_regs(self, addr: int, count: int) -> list[int]:
        return [self.regs[(addr + i) % REG_SPACE] for i in range(count)]

    def write_coil(self, addr: int, value: int) -> None:
        self.coils[addr % COIL_SPACE] = 1 if value else 0

    def write_reg(self, addr: int, value: int) -> None:
        self.regs[addr % REG_SPACE] = value & 0xFFFF


def pack_coils(bits: list[int]) -> bytes:
    out = bytearray((len(bits) + 7) // 8)
    for i, bit in enumerate(bits):
        if bit:
            out[i // 8] |= 1 << (i % 8)
    return bytes(out)


def build_response(state: PlcState, pdu: bytes) -> bytes:
    """处理一个 PDU，返回响应 PDU；异常返回 0x80|fc + 异常码。"""
    if not pdu:
        return b""
    fc = pdu[0]
    try:
        if fc == 0x01:  # 读线圈
            addr, count = struct.unpack(">HH", pdu[1:5])
            if count < 1 or count > 2000 or addr + count > COIL_SPACE:
                return bytes([fc | 0x80, 0x02])
            data = pack_coils(state.read_coils(addr, count))
            return bytes([fc, len(data)]) + data

        if fc == 0x03:  # 读保持寄存器
            addr, count = struct.unpack(">HH", pdu[1:5])
            if count < 1 or count > 125 or addr + count > REG_SPACE:
                return bytes([fc | 0x80, 0x02])
            values = state.read_regs(addr, count)
            return bytes([fc, len(values) * 2]) + struct.pack(">%dH" % len(values), *values)

        if fc == 0x05:  # 写单线圈
            addr, value = struct.unpack(">HH", pdu[1:5])
            if addr >= COIL_SPACE:
                return bytes([fc | 0x80, 0x02])
            state.write_coil(addr, 1 if value == 0xFF00 else 0)
            return pdu[:5]

        if fc == 0x06:  # 写单寄存器
            addr, value = struct.unpack(">HH", pdu[1:5])
            if addr >= REG_SPACE:
                return bytes([fc | 0x80, 0x02])
            state.write_reg(addr, value)
            return pdu[:5]

        if fc == 0x0F:  # 写多线圈
            addr, count, nbytes = struct.unpack(">HHB", pdu[1:6])
            if addr + count > COIL_SPACE or len(pdu) < 6 + nbytes:
                return bytes([fc | 0x80, 0x02])
            for i in range(count):
                bit = (pdu[6 + i // 8] >> (i % 8)) & 1
                state.write_coil(addr + i, bit)
            return struct.pack(">BHH", fc, addr, count)

        if fc == 0x10:  # 写多寄存器
            addr, count, nbytes = struct.unpack(">HHB", pdu[1:6])
            if addr + count > REG_SPACE or len(pdu) < 6 + nbytes:
                return bytes([fc | 0x80, 0x02])
            for i in range(count):
                (value,) = struct.unpack(">H", pdu[6 + i * 2: 8 + i * 2])
                state.write_reg(addr + i, value)
            return struct.pack(">BHH", fc, addr, count)

        return bytes([fc | 0x80, 0x01])  # 不支持的功能码
    except (struct.error, IndexError):
        return bytes([fc | 0x80, 0x03])  # 数据错误


class ModbusHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        state: PlcState = self.server.state  # type: ignore[attr-defined]
        sock = self.request
        try:
            sock.settimeout(10)
            while True:
                header = self._recv_exact(sock, 7)
                if header is None:
                    return
                txid, _proto, length, _unit = struct.unpack(">HHHB", header)
                body = self._recv_exact(sock, max(0, length - 1))
                if body is None:
                    return
                state.refresh()
                resp_pdu = build_response(state, body)
                if not resp_pdu:
                    return
                sock.sendall(struct.pack(">HHHB", txid, 0, len(resp_pdu) + 1, 1) + resp_pdu)
        except (ConnectionError, TimeoutError, OSError):
            return

    @staticmethod
    def _recv_exact(sock: socket.socket, n: int) -> bytes | None:
        buf = b""
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                return None
            buf += chunk
        return buf


class MockPlcServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, state: PlcState) -> None:
        self.state = state
        super().__init__(address, ModbusHandler)


# ==================== 自检 ====================
def _client_request(host: str, port: int, pdu: bytes) -> bytes:
    with socket.create_connection((host, port), timeout=3) as s:
        s.sendall(struct.pack(">HHHB", 1, 0, len(pdu) + 1, 1) + pdu)
        header = s.recv(7)
        if len(header) < 7:
            raise AssertionError("响应头不完整")
        _txid, _proto, length, _unit = struct.unpack(">HHHB", header)
        body = b""
        while len(body) < length - 1:
            chunk = s.recv(length - 1 - len(body))
            if not chunk:
                raise AssertionError("响应体不完整")
            body += chunk
        return body


def selftest() -> int:
    print("== 相位逻辑 ==")
    ok = True

    def at(offset: float) -> PlcState:
        st = PlcState(cycle_offset=offset)
        st.refresh()
        return st

    cases = [
        (1, "north", 2, 1, "南北绿"),
        (31, "north", 1, 1, "南北黄"),
        (34, "north", 0, 1, "全红"),
        (36, "east", 2, 1, "东西绿"),
        (66, "east", 1, 1, "东西黄"),
    ]
    for t, direction, lamp, expect, label in cases:
        st = at(t)
        base = ADDR_Y + OFFSET[direction]
        got = st.coils[base + lamp]
        status = "OK" if got == expect else "FAIL"
        if got != expect:
            ok = False
        print(f"  t={t:>2}s {label:<6} {direction} 灯位{lamp} 期望{expect} 实际{got} {status}")

    print("== 倒计时 ==")
    st = at(1)
    print(f"  t=1s  D0(北直行)={st.regs[0]}  D2(东直行)={st.regs[2]}")
    if st.regs[0] <= 0 or st.regs[2] <= 0:
        print("  FAIL 倒计时应为正值")
        ok = False

    print("== 协议 ==")
    state = PlcState(cycle_offset=1)
    server = MockPlcServer(("127.0.0.1", 0), state)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        body = _client_request("127.0.0.1", port, struct.pack(">BHH", 0x01, ADDR_Y, 16))
        if body[0] != 0x01 or body[1] != 2:
            raise AssertionError(f"FC01 响应异常: {body.hex()}")
        bits = [(body[2 + i // 8] >> (i % 8)) & 1 for i in range(16)]
        print("  FC01 读 Y0-Y15:", bits, "OK")

        body = _client_request("127.0.0.1", port, struct.pack(">BHH", 0x03, ADDR_D, 8))
        regs = list(struct.unpack(">8H", body[2:18]))
        print("  FC03 读 D0-D7 :", regs, "OK")

        body = _client_request("127.0.0.1", port, struct.pack(">BHH", 0x05, ADDR_X + 3, 0xFF00))
        if body[0] != 0x05:
            raise AssertionError("FC05 写线圈失败")
        print("  FC05 写 X3=1 : OK")

        body = _client_request("127.0.0.1", port, struct.pack(">BHH", 0x01, ADDR_X, 8))
        x = [(body[2 + i // 8] >> (i % 8)) & 1 for i in range(8)]
        if x[3] != 1:
            raise AssertionError(f"X3 未回读为 1: {x}")
        print("  FC01 回读 X :", x, "OK")
    except Exception as exc:  # noqa: BLE001
        print("  FAIL:", exc)
        ok = False
    finally:
        server.shutdown()
        server.server_close()

    print("\n自检" + ("通过" if ok else "失败"))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="汇川 Easy PLC 模拟器（Modbus TCP 从站）")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址，默认 127.0.0.1")
    parser.add_argument("--port", type=int, default=502, help="监听端口，默认 502（与网关一致）")
    parser.add_argument("--selftest", action="store_true", help="只做自检，不监听端口")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    state = PlcState()
    try:
        server = MockPlcServer((args.host, args.port), state)
    except OSError as exc:
        print(f"[错误] 无法监听 {args.host}:{args.port} —— {exc}")
        print("      端口可能被真实 PLC 仿真或网关占用；换端口：--port 15020（同时改 plc_gateway.py 的 PLC_PORT）")
        return 1

    print("=" * 58)
    print("汇川 Easy PLC 模拟器（演示用）")
    print("=" * 58)
    print(f"监听   : {args.host}:{args.port}   站号 1")
    print("映射   : Y=0xFC00  X=0xF800  M=0x0000  D=0x0000")
    print("相位   : 南北绿 30s → 黄 3s → 全红 2s → 东西绿 30s → 黄 3s → 全红 2s")
    print("下一步 : python plc_gateway.py   （或 --check 先自检）")
    print("按 Ctrl+C 停止。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
