# -*- coding: utf-8 -*-
"""用标准库生成红绿灯图标 traffic_light.ico（无 Pillow 依赖）。
生成多尺寸 PNG 内嵌于 ICO，Win10/Win11 原生支持。"""
import struct, zlib, math, os

def clamp(v): return max(0, min(255, int(v)))

def draw(size):
    s = size
    px = [[(0, 0, 0, 0)] * s for _ in range(s)]
    # 圆角矩形背景边界
    x0, y0, x1, y1 = 0.10*s, 0.04*s, 0.90*s, 0.96*s
    rad = 0.14*s
    lights = [(0.27*s, (255, 82, 82)), (0.50*s, (255, 201, 60)), (0.73*s, (58, 214, 126))]
    lamp_r = 0.115*s
    ring_r = 0.135*s
    cx = 0.5*s
    for y in range(s):
        for x in range(s):
            # 圆角矩形判定
            dx = max(x0+rad-x, 0, x-(x1-rad))
            dy = max(y0+rad-y, 0, y-(y1-rad))
            inside = (x0 <= x <= x1 and y0 <= y <= y1 and dx*dx+dy*dy <= rad*rad)
            if not inside:
                continue
            # 背景渐变 + 竖向高光
            t = (y-y0)/(y1-y0)
            bg = (clamp(38+18*(1-t)), clamp(52+18*(1-t)), clamp(70+22*(1-t)), 255)
            # 顶部细微反光
            if y < y0 + 0.12*s:
                bg = (bg[0]+12, bg[1]+14, bg[2]+16, 255)
            px[y][x] = bg
    # 画灯（从外向内：外壳环 -> 灯面 -> 高光）
    for cy, col in lights:
        for y in range(s):
            for x in range(s):
                d = math.hypot(x-cx, y-cy)
                if d <= ring_r:
                    px[y][x] = (16, 22, 30, 255)
                if d <= lamp_r:
                    # 边缘略暗，中心亮
                    k = 0.55 + 0.45*(1-(d/lamp_r)**2)
                    px[y][x] = (clamp(col[0]*k), clamp(col[1]*k), clamp(col[2]*k), 255)
                # 左上高光点
                if d <= lamp_r*0.95:
                    hx, hy = cx-lamp_r*0.32, cy-lamp_r*0.32
                    hd = math.hypot(x-hx, y-hy)
                    if hd <= lamp_r*0.22:
                        a = 0.55*(1-hd/(lamp_r*0.22))
                        r,g,b,_ = px[y][x]
                        px[y][x] = (clamp(r+(255-r)*a), clamp(g+(255-g)*a), clamp(b+(255-b)*a), 255)
    return px

def png_bytes(px):
    s = len(px)
    raw = bytearray()
    for y in range(s):
        raw.append(0)
        for x in range(s):
            raw.extend(px[y][x])
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        c += struct.pack(">I", zlib.crc32(tag+data) & 0xffffffff)
        return c
    ihdr = struct.pack(">IIBBBBB", s, s, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
            chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))

def make_ico(sizes, out):
    pngs = [(sz, png_bytes(draw(sz))) for sz in sizes]
    n = len(pngs)
    header = struct.pack("<HHH", 0, 1, n)
    offset = 6 + 16*n
    entries, blobs = bytearray(), bytearray()
    for sz, data in pngs:
        w = 0 if sz >= 256 else sz
        h = 0 if sz >= 256 else sz
        entries += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
        blobs += data
    with open(out, "wb") as f:
        f.write(header + bytes(entries) + bytes(blobs))
    print("ICO", out, os.path.getsize(out), "bytes", "sizes", sizes)

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    make_ico([256, 64, 48, 32, 16], os.path.join(here, "traffic_light.ico"))
