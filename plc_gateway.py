# -*- coding: utf-8 -*-
"""
汇川 Easy 系列 PLC <-> WebSocket 双向网关（单参数极简版）
==========================================================
1) 读 PLC 线圈 Y0-Y15（4 方向 x 红/黄/绿/左转）-> 网页灯与车流
2) 读 PLC 保持寄存器 D0-D7 -> 4 方向倒计时（每方向 直行/左转 各 1 字）
3) 网页 16 个按钮 -> 写 PLC 线圈 X0-X7、M0-M7，并回读确认

【只需改一个东西】PLC_IP  ——  默认 127.0.0.1（本机后台仿真），真机改成 PLC 的 IP

线圈映射（Y 区，4 方向 x 4 灯 = 16 位）：
    北 Y0=红 Y1=黄 Y2=绿 Y3=左转      东 Y4..Y7
    南 Y8..Y11                        西 Y12..Y15

倒计时（保持寄存器 D0-D7，每方向 2 字）：
    D0=北直行 D1=北左转   D2=东直行 D3=东左转
    D4=南直行 D5=南左转   D6=西直行 D7=西左转

网页按钮（写线圈）：
    X0-X7 -> 0xF800 起 8 位（离散输入区，按线圈读写）
    M0-M7 -> 0x0000 起 8 位（辅助继电器区）

汇川 Easy 官方默认值（写死，无需配置）：从站/Server，端口 502，站号 1；
Y 区 0xFC00、X 区 0xF800、M 区 0x0000、D 区 0x0000；单元 ID 通常 1。

运行：
    plc_gateway.exe                     # 连 127.0.0.1
    plc_gateway.exe --ip 192.168.1.88   # 连真机
    plc_gateway.exe --check             # 自检：打印 Y/X/M/D 当前值
"""
import asyncio
import json
import time
import socket
import struct
import argparse
import sys
import websockets

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    import os
    os.system("chcp 65001 >nul 2>&1")
except Exception:
    pass

# ==================== 只需修改这一行 ====================
PLC_IP = "127.0.0.1"        # 本机后台仿真；真机改成 PLC 的 IP
# =====================================================

PLC_PORT = 502
UNIT_ID  = 1
ADDR = {"Y": 0xFC00, "X": 0xF800, "M": 0x0000, "D": 0x0000}
WS_HOST = "0.0.0.0"
WS_PORT = 8765
POLL_HZ = 5

clients = set()
tx_lock = None  # 运行时绑定 asyncio.Lock，保证同一时刻只有一次 Modbus 事务


# ---------- 底层 Modbus TCP（标准库手写，不依赖 pymodbus）----------
class ModbusError(Exception):
    pass


def _transaction(pdu, timeout=2.0):
    """发送一个 Modbus PDU，返回响应 PDU（不含 MBAP 头）。"""
    txid = 1
    mbap = struct.pack(">HHHB", txid, 0, len(pdu) + 1, UNIT_ID)
    with socket.create_connection((PLC_IP, PLC_PORT), timeout=timeout) as s:
        s.sendall(mbap + pdu)
        hdr = b""
        while len(hdr) < 7:
            c = s.recv(7 - len(hdr))
            if not c:
                raise ModbusError("响应头不完整")
            hdr += c
        _, _, length, _ = struct.unpack(">HHHB", hdr)
        body = b""
        while len(body) < length - 1:
            c = s.recv(length - 1 - len(body))
            if not c:
                break
            body += c
    if len(body) < 2:
        raise ModbusError("响应体不完整")
    if body[0] & 0x80:
        raise ModbusError("异常码 0x%02X（地址越界/功能码不支持）" % body[1])
    return body


def read_coils(addr, count):
    body = _transaction(struct.pack(">BHH", 0x01, addr, count))
    bits = []
    for byte in body[2:2 + body[1]]:
        for i in range(8):
            bits.append(1 if (byte >> i) & 1 else 0)
    return bits[:count]


def read_regs(addr, count):
    body = _transaction(struct.pack(">BHH", 0x03, addr, count))
    return [struct.unpack(">H", body[2 + i * 2:4 + i * 2])[0] for i in range(body[1] // 2)]


def write_coil(addr, value):
    _transaction(struct.pack(">BHH", 0x05, addr, 0xFF00 if value else 0x0000))


def snapshot():
    """一次性读回 Y/X/M/D，组装网页需要的完整状态。"""
    y = read_coils(ADDR["Y"], 16)
    x = read_coils(ADDR["X"], 8)
    m = read_coils(ADDR["M"], 8)
    d = read_regs(ADDR["D"], 8)
    return y, x, m, d


def tcp_probe(ip, port, timeout=1.5):
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True, "TCP 端口可连接"
    except socket.timeout:
        return False, "连接超时（IP 不对 / 不同网段 / 防火墙拦截）"
    except ConnectionRefusedError:
        return False, "连接被拒绝（端口未开放）"
    except OSError as e:
        return False, "网络不可达: %s" % e


def self_check(ip):
    global PLC_IP
    PLC_IP = ip
    print("=" * 60)
    print("汇川 Easy PLC 连接自检")
    print("=" * 60)
    print("[1] 目标   : %s:%d  站号 %d" % (ip, PLC_PORT, UNIT_ID))
    print("[2] 读取   : Y0-Y15(灯) / D0-D7(倒计时) / X0-X7 / M0-M7")
    print("[3] 说明   : Easy 默认做 Modbus TCP 从站，端口 502，无需配置")
    ok, msg = tcp_probe(ip, PLC_PORT)
    print("\n[TCP] %s" % msg)
    if not ok:
        print("  → 电脑 IPv4 设为同网段(如 192.168.1.100)；后台仿真请用 127.0.0.1")
        return False
    try:
        y, x, m, d = snapshot()
        print("[Y 灯]   %s" % " ".join(map(str, y)))
        print("         北=%s 东=%s 南=%s 西=%s" %
              ("".join(map(str, y[0:4])), "".join(map(str, y[4:8])),
               "".join(map(str, y[8:12])), "".join(map(str, y[12:16]))))
        print("[D 倒计时] %s" % d)
        print("[X 输入] %s   [M 继电器] %s" %
              ("".join(map(str, x)), "".join(map(str, m))))
        print("\n  ✓ 连接正常，直接运行即可启动网关。")
        return True
    except Exception as e:
        print("[Modbus] 读取失败: %s" % e)
        print("  → 确认仿真已启动 / PLC 在 RUN")
        return False


async def broadcaster():
    """轮询 PLC 全量状态并广播给所有网页。"""
    interval = 1.0 / POLL_HZ
    frames = 0
    err_shown = False
    while True:
        try:
            y, x, m, d = await asyncio.to_thread(snapshot)
            payload = {
                "ts": int(time.time() * 1000),
                "coils": y,      # Y0-Y15 灯
                "reg": d,        # D0-D7 倒计时
                "x": x,          # X0-X7
                "m": m,          # M0-M7
                "map": "Y0",
                "hz": POLL_HZ,
            }
            msg = json.dumps(payload)
            dead = []
            for ws in list(clients):
                try:
                    await ws.send(msg)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                clients.discard(ws)
            frames += 1
            if frames == 1 or frames % (POLL_HZ * 10) == 0:
                print("[PLC] Y=%s D=%s X=%s M=%s (%d 帧)" %
                      ("".join(map(str, y)), d, "".join(map(str, x)),
                       "".join(map(str, m)), frames))
            err_shown = False
        except Exception as e:
            if not err_shown:
                print("[PLC] 读失败: %s （持续重连）" % e)
                err_shown = True
        await asyncio.sleep(interval)


async def handle_write(msg):
    """处理网页按钮：写 X/M 线圈，返回确认。"""
    area = str(msg.get("area", "")).upper()
    addr = int(msg.get("addr", -1))
    value = 1 if msg.get("val") else 0
    if area not in ("X", "M") or addr < 0 or addr > 7:
        return {"op": "writeAck", "ok": False, "err": "参数错误"}
    try:
        async with tx_lock:
            await asyncio.to_thread(write_coil, ADDR[area] + addr, value)
        return {"op": "writeAck", "ok": True, "area": area, "addr": addr, "val": value}
    except Exception as e:
        return {"op": "writeAck", "ok": False, "err": str(e)}


async def ws_handler(websocket):
    clients.add(websocket)
    print("[WS] 页面连接（当前 %d 个）" % len(clients))
    try:
        async for raw in websocket:
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            if isinstance(msg, dict) and msg.get("op") == "write":
                ack = await handle_write(msg)
                try:
                    await websocket.send(json.dumps(ack))
                except Exception:
                    pass
                print("[WS] 写线圈 %s%d = %d -> %s" %
                      (msg.get("area"), msg.get("addr"),
                       1 if msg.get("val") else 0, "OK" if ack.get("ok") else ack.get("err")))
    except Exception:
        pass
    finally:
        clients.discard(websocket)
        print("[WS] 页面断开（剩余 %d 个）" % len(clients))


async def main(ip):
    global PLC_IP, tx_lock
    PLC_IP = ip
    tx_lock = asyncio.Lock()
    ok, msg = tcp_probe(ip, PLC_PORT)
    print("[预检] %s" % msg)
    if not ok:
        print("[预检] PLC 暂不可达，网关仍会启动并持续重连。\n")
    async with websockets.serve(ws_handler, WS_HOST, WS_PORT):
        print("[WS] 网关已启动 ws://localhost:%d" % WS_PORT)
        print("[提示] 打开 交通灯仿真.html，点「连接网关」\n")
        await broadcaster()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="汇川 Easy PLC <-> WebSocket 双向网关")
    p.add_argument("--ip", default=PLC_IP, help="PLC IP，默认 127.0.0.1（本机仿真）")
    p.add_argument("--check", action="store_true", help="只自检并打印 Y/X/M/D")
    args = p.parse_args()
    if args.check:
        self_check(args.ip)
    else:
        try:
            asyncio.run(main(args.ip))
        except KeyboardInterrupt:
            print("\n已退出")
