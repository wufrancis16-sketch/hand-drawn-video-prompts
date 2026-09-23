"""把生成图的暖白底统一校正到精确色号 #F8F6EF，并抹掉平台水印。

单文件:
    python fix_bg.py <输入图> <输出图> [水印矩形 x0,y0,x1,y1]

批量(目录):
    python fix_bg.py <输入目录> <输出目录> [水印矩形 x0,y0,x1,y1]
    自动跳过: 含 '_检查_' / '_first_frame_' / '校正' / 'blank' / '分帧' 的文件名
    输出汇总报告到 <输出目录>/_batch_report.txt
"""
import os
import sys
import statistics
from PIL import Image

TARGET = (248, 246, 239)  # #F8F6EF
NEAR = 22.0     # 距离小于此值 -> 直接替换为目标色
FEATHER = 45.0  # 介于 NEAR 与 FEATHER 之间 -> 按比例向目标色过渡（保住抗锯齿边缘）

# 默认水印矩形（基于 1024x1536 生成图，右下角 "AI生成" 字样）
DEFAULT_WM = (790, 1440, 1024, 1536)

SKIP_KEYS = ("_检查_", "_first_frame_", "校正", "blank", "分帧")


def est_bg(im):
    w, h = im.size
    px = im.load()
    samples = []
    for x in range(0, w, 5):
        samples.append(px[x, 2])
        samples.append(px[x, h - 3])
    for y in range(0, h, 5):
        samples.append(px[2, y])
        samples.append(px[w - 3, y])
    return tuple(int(statistics.median([c[i] for c in samples])) for i in range(3))


def process(src, dst, wm_rect=None):
    im = Image.open(src).convert("RGB")
    w, h = im.size
    bg = est_bg(im)
    px = im.load()
    out = Image.new("RGB", (w, h))
    op = out.load()
    changed = near = 0
    for y in range(h):
        for x in range(w):
            p = px[x, y]
            d = ((p[0] - bg[0]) ** 2 + (p[1] - bg[1]) ** 2 + (p[2] - bg[2]) ** 2) ** 0.5
            if d <= NEAR:
                op[x, y] = TARGET
                near += 1
                changed += 1
            elif d <= FEATHER:
                t = (d - NEAR) / (FEATHER - NEAR)
                op[x, y] = tuple(int(TARGET[i] * (1 - t) + p[i] * t) for i in range(3))
                changed += 1
            else:
                op[x, y] = p
    if wm_rect:
        x0, y0, x1, y1 = wm_rect
        x1, y1 = min(x1, w), min(y1, h)
        for y in range(y0, y1):
            for x in range(x0, x1):
                op[x, y] = TARGET
    out.save(dst)

    chk = Image.open(dst).convert("RGB")
    corner = chk.getpixel((5, 5))
    return {
        "src": src, "dst": dst, "size": (w, h),
        "bg": bg, "near": near, "changed": changed,
        "corner": corner, "total": w * h,
    }


def print_report(r):
    w, h = r["size"]
    near_pct = 100 * r["near"] / r["total"]
    chg_pct = 100 * r["changed"] / r["total"]
    print("原图尺寸   : %d x %d  比例 %.4f (9:16=0.5625)" % (w, h, w / h))
    print("原背景色  : %s #%02X%02X%02X" % (r["bg"], *r["bg"]))
    print("偏移量    : dR=%+d dG=%+d dB=%+d" % (r["bg"][0] - 248, r["bg"][1] - 246, r["bg"][2] - 239))
    print("纯底色像素: %d (%.1f%%)" % (r["near"], near_pct))
    print("总改动像素: %d (%.1f%%)" % (r["changed"], chg_pct))
    print("修正后角点: %s #%02X%02X%02X" % (r["corner"], *r["corner"]))
    print("已保存    : %s" % r["dst"])


def batch(src_dir, dst_dir, wm_rect):
    os.makedirs(dst_dir, exist_ok=True)
    files = sorted(f for f in os.listdir(src_dir) if f.lower().endswith(".png"))
    todo = [f for f in files if not any(k in f for k in SKIP_KEYS)]
    rows = []
    for f in todo:
        src = os.path.join(src_dir, f)
        base, ext = os.path.splitext(f)
        dst = os.path.join(dst_dir, base + "_bgfix" + ext)
        r = process(src, dst, wm_rect)
        print_report(r)
        print("-" * 50)
        rows.append(r)
    with open(os.path.join(dst_dir, "_batch_report.txt"), "w", encoding="utf-8") as fh:
        fh.write("批量底色校正报告\n")
        fh.write("目标色: #F8F6EF (248,246,239)\n")
        fh.write("处理文件数: %d\n\n" % len(rows))
        fh.write("%-46s %-12s %-14s %-10s\n" % ("文件", "原背景", "偏移dB", "改动%"))
        for r in rows:
            bg = r["bg"]
            dB = bg[2] - 239
            fh.write("%-46s #%02X%02X%02X   %+4d       %.1f%%\n" % (
                os.path.basename(r["src"]), *bg, dB, 100 * r["changed"] / r["total"]))
        fh.write("\n全部已统一到 #F8F6EF。\n")
    print("\n批量完成，共 %d 张。报告: %s" % (len(rows), os.path.join(dst_dir, "_batch_report.txt")))


def main():
    args = sys.argv[1:]
    wm_rect = None
    if len(args) >= 3 and "," in args[-1]:
        wm_rect = tuple(int(v) for v in args[-1].split(","))
        args = args[:-1]
    if wm_rect is None:
        wm_rect = DEFAULT_WM

    if len(args) == 2 and os.path.isdir(args[0]):
        batch(args[0], args[1], wm_rect)
    elif len(args) == 2:
        r = process(args[0], args[1], wm_rect)
        print_report(r)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
