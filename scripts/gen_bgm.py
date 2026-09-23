# -*- coding: utf-8 -*-
"""纯标准库合成一段柔和轻音乐 BGM（多首预设 + 默认随机，无版权风险）。
输出 16-bit PCM WAV，时长由 --dur 指定（秒）。

多首预设，每首不同调性/情绪；默认每次随机挑一首，保证成片不单调。
用法:
    python gen_bgm.py --dur 49.0 --out bgm_light.wav          # 随机一首
    python gen_bgm.py --list                                  # 列出全部可选 BGM
    python gen_bgm.py --variant 3 --dur 49.0 --out bgm.wav    # 指定第 3 首
    python gen_bgm.py --seed 1234 --dur 49.0 --out bgm.wav    # 指定随机种子(可复现)
    python gen_bgm.py --random 0 --dur 49.0                   # 关闭随机，用默认首(暖阳C)
"""
import math, wave, struct, argparse, os, sys, random

SR = 44100

# 十二平均律：MIDI 音号 -> 频率
def freq(midi):
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))

# 音色预设：泛音叠加比例（越亮高频越多）
TONE = {
    'warm':   ((1, 1.0), (2, 0.32), (3, 0.16), (4, 0.07)),
    'bright': ((1, 1.0), (2, 0.28), (3, 0.12), (5, 0.06)),
    'soft':   ((1, 1.0), (2, 0.36), (3, 0.20)),
}

# 用几个泛音叠加 + 软 ADSR 包络，模拟温暖钢琴感
def note_sample(t, f, dur, peak=0.16, tone='warm'):
    if t < 0 or t > dur:
        return 0.0
    a, d, s, r = 0.04, 0.18, 0.6, 0.35
    if t < a:
        env = t / a
    elif t < a + d:
        env = 1.0 - (1.0 - s) * ((t - a) / d)
    elif t < dur - r:
        env = s
    else:
        env = s * max(0.0, (dur - t) / r)
    env *= peak
    s_out = 0.0
    for k, amp in TONE[tone]:
        s_out += amp * math.sin(2 * math.pi * f * k * t)
    norm = sum(amp for _, amp in TONE[tone])
    s_out /= norm
    return s_out * env


def maj(root):  # 大三和弦 [根, 三, 五, 高八度根]
    return [root, root + 4, root + 7, root + 12]


def min_(root):  # 小三和弦
    return [root, root + 3, root + 7, root + 12]


# 多首预设：每首 = 名称 / 情绪描述 / 和弦进行(bass, arp) / 节奏 / 音色 / 主音量
VARIANTS = [
    {  # 1. 原版暖阳 C 大调 I–V–vi–IV，温暖明亮
        'name': '暖阳 (C 大调)',
        'desc': '温暖明亮，适合科普/正能量',
        'prog': [(48, maj(60)), (43, maj(55)), (45, min_(57)), (41, maj(53))],
        'beat': 0.92, 'tone': 'warm', 'peak': 0.14,
    },
    {  # 2. 微风 G 大调 vi–IV–I–V，轻快
        'name': '微风 (G 大调)',
        'desc': '轻快灵动，适合轻松话题',
        'prog': [(52, min_(64)), (48, maj(60)), (55, maj(67)), (50, maj(62))],
        'beat': 0.86, 'tone': 'bright', 'peak': 0.13,
    },
    {  # 3. 月光 F 大调 I–vi–IV–V，柔和抒情
        'name': '月光 (F 大调)',
        'desc': '柔和抒情，适合娓娓道来',
        'prog': [(53, maj(65)), (50, min_(62)), (46, maj(58)), (48, maj(60))],
        'beat': 1.00, 'tone': 'soft', 'peak': 0.13,
    },
    {  # 4. 清晨 D 大调 I–V–vi–IV，清亮
        'name': '清晨 (D 大调)',
        'desc': '清亮通透，适合开场/提神',
        'prog': [(50, maj(62)), (45, maj(57)), (47, min_(59)), (43, maj(55))],
        'beat': 0.84, 'tone': 'bright', 'peak': 0.14,
    },
    {  # 5. 静夜 A 小调 i–VI–III–VII，安静内敛
        'name': '静夜 (A 小调)',
        'desc': '安静内敛，适合走心/反思',
        'prog': [(45, min_(57)), (41, maj(53)), (48, maj(60)), (43, maj(55))],
        'beat': 1.04, 'tone': 'soft', 'peak': 0.12,
    },
    {  # 6. 海岸 E 大调 I–ii–IV–V，宽广
        'name': '海岸 (E 大调)',
        'desc': '宽广舒展，适合总结/展望',
        'prog': [(52, maj(64)), (54, min_(66)), (45, maj(57)), (47, maj(59))],
        'beat': 0.90, 'tone': 'warm', 'peak': 0.13,
    },
]


def build(dur, variant, rnd):
    beat = variant['beat'] * (1.0 + rnd.uniform(-0.03, 0.03))   # 节奏微抖
    tone = variant['tone']
    peak = variant['peak']
    lead = 0.95 * beat
    # 同一首内部的轻微变体：琶音方向 / 是否加八度尾音
    mode = rnd.choice(['normal', 'reverse', 'octave'])
    out = [0.0] * int(dur * SR)
    t0 = 0.0
    while t0 < dur:
        for bass_midi, arp in variant['prog']:
            bf = freq(bass_midi)
            for i in range(int(beat * SR)):
                t = i / SR
                if t0 + t < dur:
                    idx = int((t0 + t) * SR)
                    out[idx] += note_sample(t, bf, beat * 1.6, peak=0.10, tone=tone) * 0.9
            notes = list(arp)
            if mode == 'reverse':
                notes = list(reversed(notes))
            elif mode == 'octave':
                notes = notes + [notes[-1] + 12]
            for n, m in enumerate(notes):
                f = freq(m)
                nt = t0 + n * beat
                for i in range(int(lead * SR)):
                    t = i / SR
                    if nt + t < dur:
                        idx = int((nt + t) * SR)
                        out[idx] += note_sample(t, f, lead, peak=peak, tone=tone)
            t0 += 4 * beat
    n = len(out)
    for i in range(n):
        g = 1.0
        if i < 1.2 * SR:
            g = i / (1.2 * SR)
        elif i > n - 1.5 * SR:
            g = max(0.0, (n - i) / (1.5 * SR))
        out[i] *= g
        out[i] = max(-1.0, min(1.0, out[i]))
    return out


def write_wav(path, samples):
    with wave.open(path, 'w') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        frames = bytearray()
        for s in samples:
            v = int(s * 32767)
            v = max(-32768, min(32767, v))
            frames += struct.pack('<h', v)
        w.writeframes(bytes(frames))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dur', type=float, default=49.0, help='BGM 时长（秒），建议等于成片时长')
    ap.add_argument('--out', default='bgm_light.wav', help='输出 wav 路径')
    ap.add_argument('--random', type=int, default=1, help='1=随机选一首(默认), 0=用默认首(暖阳C)')
    ap.add_argument('--variant', type=int, default=0, help='指定第 N 首(1-based)，覆盖 --random')
    ap.add_argument('--seed', type=int, default=0, help='随机种子；0=本次随机(会打印)，便于复现')
    ap.add_argument('--list', action='store_true', help='仅列出可选 BGM 并退出')
    a = ap.parse_args()

    if a.list:
        print('可选 BGM（%d 首）：' % len(VARIANTS))
        for i, v in enumerate(VARIANTS, 1):
            print('  %d. %-14s — %s' % (i, v['name'], v['desc']))
        sys.exit(0)

    # 选定变体
    if a.variant:
        idx = a.variant - 1
        if idx < 0 or idx >= len(VARIANTS):
            print('ERROR: --variant 超出范围，可用 1..%d，或 --list 查看' % len(VARIANTS))
            sys.exit(1)
        chosen = VARIANTS[idx]
        info = 'variant=%d(固定)' % a.variant
        rnd = random.Random(a.seed) if a.seed else random
    elif a.random:
        if a.seed:
            rnd = random.Random(a.seed)
            info = 'seed=%d' % a.seed
        else:
            s = random.randint(1, 10 ** 9)
            rnd = random.Random(s)
            info = 'seed=%d(随机)' % s
        idx = rnd.randrange(len(VARIANTS))
        chosen = VARIANTS[idx]
    else:
        chosen = VARIANTS[0]
        info = '默认(暖阳C)'
        rnd = random.Random(a.seed) if a.seed else random

    print('BGM: %s | %s' % (chosen['name'], info))
    print('synth bgm %.1fs ...' % a.dur)
    s = build(a.dur, chosen, rnd)
    write_wav(a.out, s)
    print('wrote', a.out, os.path.getsize(a.out))


if __name__ == '__main__':
    main()
