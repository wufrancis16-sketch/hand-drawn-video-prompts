# -*- coding: utf-8 -*-
"""纯标准库合成一段柔和轻音乐 BGM（慢速大调钢琴琶音，无版权风险）。
输出 16-bit PCM WAV，时长由 --dur 指定（秒）。
依赖：仅 Python 标准库（math/wave/struct/argparse）。

用法:
    python gen_bgm.py --dur 49.0 --out bgm_light.wav
"""
import math, wave, struct, argparse, os

SR = 44100

# 十二平均律：MIDI 音号 -> 频率
def freq(midi):
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))

# 用几个泛音叠加 + 软 ADSR 包络，模拟温暖钢琴感
def note_sample(t, f, dur, peak=0.16):
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
    for k, amp in ((1, 1.0), (2, 0.32), (3, 0.16), (4, 0.07)):
        s_out += amp * math.sin(2 * math.pi * f * k * t + 0.0)
    s_out /= (1.0 + 0.32 + 0.16 + 0.07)
    return s_out * env

# 和弦进行（I–V–vi–IV，C 大调，温暖明亮）
PROG = [
    (48, [60, 64, 67, 72]),   # C  major
    (43, [55, 59, 62, 67]),   # G  major
    (45, [57, 60, 64, 69]),   # A minor
    (41, [53, 57, 60, 65]),   # F  major
]

def build(dur):
    beat = 0.92          # 每音间隔（慢速）
    lead = 0.95 * beat   # 单音时长（留余韵）
    out = [0.0] * int(dur * SR)
    t0 = 0.0
    while t0 < dur:
        for bass_midi, arp in PROG:
            bf = freq(bass_midi)
            for i in range(int(beat * SR)):
                t = i / SR
                if t0 + t < dur:
                    idx = int((t0 + t) * SR)
                    out[idx] += note_sample(t, bf, beat * 1.6, peak=0.10) * 0.9
            for n, m in enumerate(arp):
                f = freq(m)
                nt = t0 + n * beat
                for i in range(int(lead * SR)):
                    t = i / SR
                    if nt + t < dur:
                        idx = int((nt + t) * SR)
                        out[idx] += note_sample(t, f, lead, peak=0.14)
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

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--dur', type=float, default=49.0, help='BGM 时长（秒），建议等于成片时长')
    ap.add_argument('--out', default='bgm_light.wav', help='输出 wav 路径')
    a = ap.parse_args()
    print('synth bgm %.1fs ...' % a.dur)
    s = build(a.dur)
    write_wav(a.out, s)
    print('wrote', a.out, os.path.getsize(a.out))
