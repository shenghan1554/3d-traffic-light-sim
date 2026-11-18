# -*- coding: utf-8 -*-
"""网关探针：连接 WebSocket，打印几帧状态，可选写一个 X/M 线圈。

用于在没有浏览器的情况下确认「PLC ←→ 网关 ←→ 页面」链路正常。

    python tools/ws_probe.py                       # 收 3 帧
    python tools/ws_probe.py --frames 5
    python tools/ws_probe.py --write X3=1          # 写 X3 并等待回执
    python tools/ws_probe.py --url ws://127.0.0.1:8765
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

import websockets


async def run(url: str, frames: int, write: str | None, timeout: float) -> int:
    async with websockets.connect(url, open_timeout=timeout) as ws:
        print(f"[ws] 已连接 {url}")
        for i in range(frames):
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=timeout))
            print(
                f"[帧{i}] ts={msg.get('ts')} hz={msg.get('hz')}\n"
                f"       Y={msg.get('coils')}\n"
                f"       D={msg.get('reg')}  X={msg.get('x')}  M={msg.get('m')}"
            )

        if write:
            area, _, value = write.partition("=")
            area = area.strip().upper()
            index = int(area[1:])
            payload = {"op": "write", "area": area[0], "addr": index, "val": int(value.strip() or "1")}
            await ws.send(json.dumps(payload))
            print(f"[ws] 已发送 {payload}")
            ack = None
            deadline = asyncio.get_running_loop().time() + timeout
            while asyncio.get_running_loop().time() < deadline:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=timeout))
                if msg.get("op") == "writeAck":
                    ack = msg
                    break
            if not ack:
                print("[ws] 未收到写回执")
                return 1
            print(f"[ws] 回执 {ack}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WebSocket 网关探针")
    parser.add_argument("--url", default="ws://127.0.0.1:8765", help="网关地址")
    parser.add_argument("--frames", type=int, default=3, help="接收帧数，默认 3")
    parser.add_argument("--write", default=None, help="写线圈，例如 X3=1 或 M0=1")
    parser.add_argument("--timeout", type=float, default=5.0, help="单次等待秒数，默认 5")
    args = parser.parse_args(argv)

    try:
        return asyncio.run(run(args.url, max(1, args.frames), args.write, args.timeout))
    except (OSError, asyncio.TimeoutError, websockets.exceptions.WebSocketException) as exc:
        print(f"[错误] {type(exc).__name__}: {exc}")
        print("       请确认：1) tools/mock_plc.py 或真实 PLC 已启动  2) plc_gateway.py 已启动")
        return 1


if __name__ == "__main__":
    sys.exit(main())
