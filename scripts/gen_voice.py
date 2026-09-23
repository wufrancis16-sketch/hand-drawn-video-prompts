# -*- coding: utf-8 -*-
"""逐镜生成中文口播配音（edge_tts，微软晓晓），输出 shots/aud/shotNN.m4a。
依赖：edge_tts（pip install edge_tts），需联网。
用法: python gen_voice.py            # 生成全部 1..10 镜
      python gen_voice.py 1 3 5      # 仅生成指定镜
"""
import os, sys, asyncio
import edge_tts
from pathlib import Path

try:
    from render_whiteboard2 import SUBS, WORK
except Exception:
    # 独立运行时给出最小可用示例
    WORK = os.environ.get('WB_WORKDIR', r'E:\workbuddy\2026-09-22-15-27-07')
    SUBS = {1: '示例口播文案。'}

VOICE = 'zh-CN-XiaoxiaoNeural'
AUD = os.path.join(WORK, 'shots', 'aud')


async def tts_one(n, text):
    out = os.path.join(AUD, 'shot%02d.m4a' % n)
    comm = edge_tts.Communicate(text, VOICE)
    await comm.save(out)
    return out


def main():
    os.makedirs(AUD, exist_ok=True)
    shots = [int(a) for a in sys.argv[1:] if a.isdigit()] or sorted(SUBS.keys())
    for n in shots:
        text = SUBS.get(n)
        if not text:
            print('skip', n, 'no subtitle')
            continue
        asyncio.run(tts_one(n, text))
        print('voice', '%02d' % n, os.path.getsize(os.path.join(AUD, 'shot%02d.m4a' % n)))


if __name__ == '__main__':
    main()
