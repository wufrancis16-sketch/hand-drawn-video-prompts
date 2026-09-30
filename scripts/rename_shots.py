# -*- coding: utf-8 -*-
"""把 ImageGen 生成的随机文件名按【生成顺序】批量重命名为 镜头NN.png。

为什么需要：ImageGen 落到 output_dir 的文件名是提示词开头截断 + 时间戳
（如 `Do_not_add_any_title__caption__2026-09-30T01-47-36.png`），
而流水线后续的 fix_bg / render_whiteboard2 都按 `镜头NN.png` 命名读取，必须先改名。
因为生图是**串行**的，mtime 顺序 == 镜头顺序。

用法:
    python rename_shots.py [raw目录] [--list]
    # 不传目录时读环境变量 WB_WORKDIR/outputs_land/raw
    python rename_shots.py --list          # 只看不改
    python rename_shots.py --start 6       # 从第 6 镜开始编号（补出某几镜时用）

注意：已存在 `镜头NN.png` 的一律跳过，不会覆盖；重跑安全。
"""
import os
import sys

EXTS = ('.png', '.jpg', '.jpeg', '.webp')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if args:
        raw = os.path.abspath(args[0])
    else:
        work = os.environ.get('WB_WORKDIR', os.getcwd())
        raw = os.path.join(work, 'outputs_land', 'raw')
    if not os.path.isdir(raw):
        raise SystemExit('目录不存在: ' + raw)

    start = 0
    if '--start' in sys.argv:
        start = int(sys.argv[sys.argv.index('--start') + 1]) - 1

    files = [f for f in os.listdir(raw)
             if f.lower().endswith(EXTS) and not f.startswith('镜头')]
    files.sort(key=lambda f: os.path.getmtime(os.path.join(raw, f)))
    already = [f for f in os.listdir(raw) if f.startswith('镜头')]
    print('目录:', raw)
    print('待重命名:', len(files), '| 已命名:', len(already))

    if '--list' in sys.argv:
        for f in files:
            print('  ', f)
        return

    n = max(start, len(already))
    for f in files:
        n += 1
        dst = '镜头%02d.png' % n
        dstp = os.path.join(raw, dst)
        if os.path.exists(dstp):
            print('skip (已存在)', dst)
            continue
        os.rename(os.path.join(raw, f), dstp)
        print('  ', f, '->', dst)

    total = len([f for f in os.listdir(raw) if f.startswith('镜头')])
    print('完成，raw 共', total, '张')


if __name__ == '__main__':
    main()
