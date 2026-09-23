# hand-drawn-video-prompts

把中文口播稿变成 **16:9 白板手绘动画** 的 WorkBuddy 技能：一只手握着马克笔，画面跟着口播**逐元素被画出来**，底部黄字字幕 + 中文配音 + 低音量轻音乐 BGM。视觉语言为现代 Q 版手绘蜡笔插画，固定暖白纸底 `#F8F6EF`。

> 也保留原始能力：9:16 竖版 Q 版分镜 Prompt 包（对接 Flow / Nano Banana 图生视频）。

## 它能做什么

- 中文口播稿 → 分镜 → 横版手绘静帧（ImageGen，双锁 Prompt 控文字）
- 逐元素手绘揭示动画（SVG mask + Chrome 逐帧渲染 + ffmpeg）
- 中文配音（edge_tts）、字幕、纯合成轻音乐 BGM 混音
- 全程本地生成，零视频生成额度消耗（仅生图 + TTS 联网）

## 目录结构

```
hand-drawn-video-prompts/
├── SKILL.md / SKILL.zh-CN.md        # 技能说明（主推 16:9 白板动画）
├── README.md
├── LICENSE
├── references/
│   ├── whiteboard-workflow.md       # 16:9 白板动画完整流水线 + 已知坑
│   ├── whiteboard-prompts.md        # 横版出图双锁 Prompt 模板 + 持笔手素材
│   ├── automation-workflow.md       # 原始 9:16 自动成片路线
│   ├── style-guide.md               # 视觉规范
│   └── output-example.md            # 输出示例
└── scripts/
    ├── render_whiteboard2.py        # 逐元素显绘渲染（核心）
    ├── gen_voice.py                 # 逐镜配音（edge_tts）
    ├── gen_bgm.py                   # 轻音乐 BGM 合成（纯标准库）
    ├── mix_bgm.py                   # BGM 低音量混音
    ├── fix_bg.py                    # 暖白底校正 + 去水印
    └── assets/
        ├── hand_final.png           # 持笔手素材（透明背景）
        └── tip.txt                 # 笔尖坐标 hw hh tx ty
```

## 快速开始

```bash
pip install playwright edge_tts Pillow
# 设置工程目录与工具路径（也可直接改脚本顶部默认值）
export WB_WORKDIR="你的工程目录"
export WB_FFMPEG="ffmpeg路径"   WB_FFPROBE="ffprobe路径"   WB_CHROME="Chrome路径"

# 1. 横版出图 1536x1024 → outputs_land/raw/镜头NN.png（双锁 Prompt 见 references）
# 2. 底色校正 + 去水印
python scripts/fix_bg.py $WB_WORKDIR/outputs_land/raw $WB_WORKDIR/outputs_land/final 1380,940,1536,1024
# 3. 配音
python scripts/gen_voice.py
# 4. 逐元素显绘（前台运行！后台会被 2 分钟杀）
python scripts/render_whiteboard2.py
# 5. BGM + 混音
python scripts/gen_bgm.py --dur 49.0 --out bgm_light.wav
python scripts/mix_bgm.py 成片.mp4 bgm_light.wav 成片_带BGM.mp4 0.20
```

## 关键踩坑（详见 references/whiteboard-workflow.md）

- ImageGen 并行传不同 output_dir 会参数被吞、文件覆盖 → **串行**生成
- 渲染全部 10 镜（~1200 帧）在后台会被 2 分钟强制终止 → **前台**跑
- ImageGen 透明底常烙成棋盘格 → 洪泛填充抠边
- 反复强调“暖白”反而把底色染黄 → 统一走 `fix_bg.py` 后期校正
- 模型会自加底部标题 / 关键词写错位置 → 双锁 Prompt + 必要时图生图擦除

## 许可

MIT（见 LICENSE）。
