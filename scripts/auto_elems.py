# -*- coding: utf-8 -*-
"""auto_elems.py —— 依据生成图的真实墨迹，自动把 ELEMS 的「近似锚框」收紧成「贴合框」。

为什么要这么做：`render_whiteboard2.py` 的 mask 只揭示 ELEMS 框内像素，框外笔画永远不显示。
锚框靠肉眼估必然偏，导致画面被切碎（历史事故：残留率最高 62%）。
本脚本把每个墨迹像素分配给最近/包含它的锚框，再用该组墨迹的包围盒替换锚框 → 残留率恒为 0。

用法:
    python auto_elems.py <WB_WORKDIR>            # 就地回写 render_whiteboard2.py
    python auto_elems.py <WB_WORKDIR> --dry      # 只报告不回写
"""
import ast
import io
import os
import re
import sys

import numpy as np
from PIL import Image

BG = np.array([248, 246, 239], dtype=np.int16)
TH = 26          # 与 fix_bg 的 NEAR 阈值一致
PAD = 12         # 贴合框外扩像素
MIN_NORM = 0.012  # 框最小归一化边长，避免过小导致笔刷路径塌缩


def load_ink(path):
    a = np.asarray(Image.open(path).convert('RGB'), dtype=np.int16)
    ink = np.abs(a - BG).max(axis=2) > TH
    # 去掉孤立噪点：8 邻域里至少 3 个是墨
    nb = np.zeros_like(ink, dtype=np.uint8)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nb += np.roll(np.roll(ink, dy, axis=0), dx, axis=1).astype(np.uint8)
    return ink & (nb >= 3)


def tighten(ink, anchors):
    """anchors: [[nx,ny,nw,nh,w], ...] -> 收紧后的同结构列表"""
    H, W = ink.shape
    ys, xs = np.nonzero(ink)
    if len(xs) == 0:
        return anchors
    nx = xs / W
    ny = ys / H
    best = np.full(len(xs), -1, dtype=np.int16)
    bestd = np.full(len(xs), 1e9, dtype=np.float64)
    for i, (ax, ay, aw, ah, _w) in enumerate(anchors):
        cx, cy = ax + aw / 2.0, ay + ah / 2.0
        d = (nx - cx) ** 2 + (ny - cy) ** 2
        inside = (nx >= ax) & (nx < ax + aw) & (ny >= ay) & (ny < ay + ah)
        d = np.where(inside, d * 1e-4, d)          # 包含优先
        upd = d < bestd
        bestd[upd] = d[upd]
        best[upd] = i
    out = []
    for i, (ax, ay, aw, ah, w) in enumerate(anchors):
        m = best == i
        if not m.any():
            continue
        x0 = max(0.0, (xs[m].min() - PAD) / W)
        x1 = min(1.0, (xs[m].max() + PAD + 1) / W)
        y0 = max(0.0, (ys[m].min() - PAD) / H)
        y1 = min(1.0, (ys[m].max() + PAD + 1) / H)
        if x1 - x0 < MIN_NORM:
            c = (x0 + x1) / 2.0
            x0, x1 = max(0.0, c - MIN_NORM / 2), min(1.0, c + MIN_NORM / 2)
        if y1 - y0 < MIN_NORM:
            c = (y0 + y1) / 2.0
            y0, y1 = max(0.0, c - MIN_NORM / 2), min(1.0, c + MIN_NORM / 2)
        out.append([round(x0, 4), round(y0, 4), round(x1 - x0, 4), round(y1 - y0, 4), w])
    return out


def main():
    work = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') \
        else os.environ.get('WB_WORKDIR', os.getcwd())
    dry = '--dry' in sys.argv
    rp = os.path.join(work, 'render_whiteboard2.py')
    src = io.open(rp, encoding='utf-8', newline='').read()
    crlf = '\r\n' in src
    s = src.replace('\r\n', '\n')
    m = re.search(r'ELEMS\s*=\s*\{.*?\n\}', s, re.S)
    E = ast.literal_eval(m.group(0).split('=', 1)[1].strip())
    sys.stdout.reconfigure(errors='replace')

    new = {}
    for k in sorted(E):
        img = os.path.join(work, 'outputs_land', 'final', '镜头%02d_bgfix.png' % k)
        if not os.path.isfile(img):
            print('[SKIP] 镜%02d 无图' % k)
            new[k] = E[k]
            continue
        ink = load_ink(img)
        t = tighten(ink, E[k])
        new[k] = t
        print('镜%02d: %d 框 -> %d 框' % (k, len(E[k]), len(t)))

    lines = ['ELEMS = {']
    for k in sorted(new):
        lines.append('    %d: [' % k)
        row = []
        for b in new[k]:
            row.append('[%.4f, %.4f, %.4f, %.4f, %.1f]' % tuple(b))
        for i in range(0, len(row), 2):
            lines.append('        ' + ', '.join(row[i:i + 2]) + ',')
        lines.append('    ],')
    lines.append('}')
    block = '\n'.join(lines)

    out = s[:m.start()] + block + s[m.end():]
    if dry:
        print('\n--- dry run，未回写 ---\n' + block)
        return
    io.open(rp, 'wb').write(
        (out.replace('\n', '\r\n') if crlf else out).encode('utf-8'))
    print('\n已回写:', rp)


if __name__ == '__main__':
    main()
