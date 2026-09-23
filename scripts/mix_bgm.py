# -*- coding: utf-8 -*-
"""把轻音乐 BGM 以低音量混进白板成片（口播保持清晰）。
用法: python mix_bgm.py <源视频.mp4> <bgm.wav> <输出.mp4> [bgm音量0.20]
依赖：ffmpeg（WB_FFMPEG 或系统 ffmpeg）。
"""
import os, sys, subprocess

FF = os.environ.get('WB_FFMPEG', r'E:\workbuddy\2026-08-10-16-44-11\ffmpeg\ffmpeg-9.0-full_build\bin\ffmpeg.exe')


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    src, bgm, out = sys.argv[1], sys.argv[2], sys.argv[3]
    bgm_vol = sys.argv[4] if len(sys.argv) > 4 else '0.20'
    voice_vol = sys.argv[5] if len(sys.argv) > 5 else '0.92'
    # 口播=0.92，BGM=0.20；normalize=0 防止双轨被自动归一化削波
    filt = ("[0:a]volume=%s[voice];[1:a]volume=%s[bgm];"
            "[voice][bgm]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]"
            % (voice_vol, bgm_vol))
    cmd = [FF, '-y', '-i', src, '-i', bgm, '-filter_complex', filt,
           '-map', '0:v', '-map', '[aout]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', out]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print('mixed', out, os.path.getsize(out) if os.path.exists(out) else 'MISSING')


if __name__ == '__main__':
    main()
