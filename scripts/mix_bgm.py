# -*- coding: utf-8 -*-
"""把轻音乐 BGM 以低音量混进白板成片，并可选整体倍速（口播保持清晰）。
用法: python mix_bgm.py <源视频.mp4> <bgm.wav> <输出.mp4> [bgm音量0.20] [口播音量0.92] [倍速1.1]
依赖：ffmpeg（WB_FFMPEG 或系统 ffmpeg）。
倍速说明：speed>1 表示加速（如 1.1=快 10%）。对视频与音频统一变速，保持口播/BGM 同步。
          默认 1.1（每次成品自动加速）；传入 1.0 即不变速（视频走拷贝，零二次编码）。
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
    speed = float(sys.argv[6]) if len(sys.argv) > 6 else 1.1
    # 口播=0.92，BGM=0.20；normalize=0 防止双轨被自动归一化削波
    audio_filt = ("[0:a]volume=%s[voice];[1:a]volume=%s[bgm];"
                  "[voice][bgm]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[mixed]"
                  % (voice_vol, bgm_vol))
    if abs(speed - 1.0) < 1e-6:
        # 不变速：视频直接拷贝，仅混音（无二次编码）
        filt = audio_filt
        cmd = [FF, '-y', '-i', src, '-i', bgm, '-filter_complex', filt,
               '-map', '0:v', '-map', '[mixed]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', out]
    else:
        # 变速：视频 setpts + 音频 atempo，统一加速，口播与 BGM 仍同步
        filt = (audio_filt +
                ";[0:v]setpts=%s*PTS[v];[mixed]atempo=%s[aout]" % (1.0 / speed, speed))
        cmd = [FF, '-y', '-i', src, '-i', bgm, '-filter_complex', filt,
               '-map', '[v]', '-map', '[aout]', '-c:v', 'libx264', '-preset', 'medium',
               '-crf', '18', '-c:a', 'aac', '-b:a', '160k', out]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print('mixed speed=%.2f' % speed, out, os.path.getsize(out) if os.path.exists(out) else 'MISSING')


if __name__ == '__main__':
    main()
