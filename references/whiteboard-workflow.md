# 白板手绘显绘流水线（主推产出模式）

把中文口播稿变成 **16:9 白板手绘动画**：一只手握着马克笔，画面跟着口播**逐元素被画出来**，底部黄字字幕 + 中文配音 + 低音量轻音乐 BGM。全部本地生成，零视频生成额度消耗（仅生图 + TTS 联网）。

## 依赖

- Python 3.10+，安装：`pip install playwright edge_tts Pillow`
- 系统 Chrome（`WB_CHROME`，默认 `C:\Program Files\Google\Chrome\Application\chrome.exe`）
- ffmpeg（`WB_FFMPEG` / `WB_FFPROBE`）
- 生图工具 ImageGen（横版静帧）、可选图生图（擦除瑕疵）
- 中文字体 `Microsoft YaHei`（字幕用，Windows 自带 simhei/msyh 均可）

## 工程目录约定（用环境变量 `WB_WORKDIR` 指向，默认见脚本）

```
<WB_WORKDIR>/
  outputs_land/
    raw/        横版原图（ImageGen 输出，命名 镜头NN.png）
    final/      校正后成品图 镜头NN_bgfix.png   ← 渲染读取
    hand/       hand_final.png + tip.txt        ← 持笔手素材
  shots/aud/    shotNN.m4a                       ← 每镜配音
  shots_wb2/    shotNN_wb2.mp4 + concat.txt      ← 每镜动画 + 拼接清单
  frames_wb2/   中间帧（渲染后巨大，可删）
  最终成片.mp4
```

## 步骤

### ① 分镜
按口播语义切 4–6 秒一镜，每镜给一个视觉隐喻。把每镜口播文案填入 `scripts/render_whiteboard2.py` 的 `SUBS` 字典。

### ② 横版出图（双锁 Prompt）
用 ImageGen 出 **1536×1024（横版）** 图，套双锁 Prompt（见 `whiteboard-prompts.md`）：
- 开头锁「不允许出现任何标题/副标题/水印等多余文字」
- 结尾锁「指定关键词只出现在 XX 位置、恰好一次、不变形」
关键：模型会自作主张加底部大标题或把关键词写错位置，必须双锁 + 必要时图生图擦除。

### ③ 底色校正 + 去水印
```bash
python scripts/fix_bg.py <WB_WORKDIR>/outputs_land/raw <WB_WORKDIR>/outputs_land/final <水印矩形x0,y0,x1,y1>
```
横版 1536×1024 的水印矩形通常为 `1380,940,1536,1024`。脚本把暖白底统一到 `#F8F6EF` 并抹掉平台水印。

### ④ 生成配音
```bash
python scripts/gen_voice.py            # 全部 1..10 镜
python scripts/gen_voice.py 3 5        # 仅重出某镜
```
默认声线为**男声（云扬 `zh-CN-YunyangNeural`，沉稳适合科普）**。换女声改 `gen_voice.py` 顶部 `VOICE='zh-CN-XiaoxiaoNeural'`。
输出 `shots/aud/shotNN.m4a`，每镜时长由该段口播决定（后续动画时长据此对齐）。

### ⑤ 持笔手素材
已内置 `scripts/assets/hand_final.png` + `tip.txt`（笔尖坐标）。如需重做：用 ImageGen 生成「右手握马克笔、透明底」图 → 其透明底常被烙成棋盘格，用洪泛填充抠掉四周棋盘格色 → 记录笔尖归一化坐标到 `tip.txt`（格式 `hw hh tx ty`）。

### ⑥ 逐元素显绘渲染（核心）
编辑 `render_whiteboard2.py` 顶部的 `ELEMS` 字典：每镜按**口播叙述顺序**列出部件 `[nx,ny,nw,nh,权重]`，归一化坐标基于 1536×1024 原图；权重越大画得越慢。
```bash
python scripts/render_whiteboard2.py        # 全部 10 镜 + 自动拼接成片
python scripts/render_whiteboard2.py 1 3    # 只渲某几镜（调参验证用）
```
原理：每部件生成蛇形软边笔刷路径，按时间轴用 mask 逐步揭示原图；持笔手跟随当前笔尖位置 + 轻微抖动；底部黄字黑边字幕。逐帧用 Chrome 截图 1920×1080@25fps，ffmpeg 合成每镜 mp4，**前台**跑（本机后台任务约 2 分钟会被强制终止）。

### ⑦ BGM 合成 + 混音
BGM 为纯标准库合成的慢速钢琴琶音（无版权风险），内置 **6 首不同调性/情绪预设**，**默认每次随机选一首**，成片不单调：
```bash
python scripts/gen_bgm.py --dur 49.0 --out bgm_light.wav          # 默认随机一首
python scripts/gen_bgm.py --list                                  # 列出全部 6 首(暖阳C/微风G/月光F/清晨D/静夜Am/海岸E)
python scripts/gen_bgm.py --variant 3 --dur 49.0 --out bgm.wav    # 指定第 3 首(固定)
python scripts/gen_bgm.py --seed 1234 --dur 49.0 --out bgm.wav    # 指定随机种子(可复现)
python scripts/gen_bgm.py --random 0 --dur 49.0                   # 关闭随机，用默认首(暖阳C)
# 混音（第6参=倍速，默认 1.1，即每次成品自动加速 10%）
python scripts/mix_bgm.py 最终成片.mp4 bgm_light.wav 最终成片_带BGM.mp4 0.20 0.92 1.1
# 不变速写 1.0（视频走拷贝，零二次编码）
python scripts/mix_bgm.py 最终成片.mp4 bgm_light.wav 最终成片_带BGM.mp4 0.20 0.92 1.0
```
`0.20` 是 BGM 音量比，`0.92` 是口播音量比，`1.1` 是**整体倍速（默认）**——对视频与音频统一加速，口播与 BGM 仍同步。觉得偏大/偏小改前两个值重混即可，不必重新渲染；想去掉加速传 `1.0`。随机想复现某次就记下终端打印的 `seed=xxx` 再传 `--seed`。

## 已知坑（务必先看）

1. **ImageGen 并行 bug**：并行传不同 `output_dir` 时参数被吞、文件覆盖。必须**串行**逐张生成。
2. **后台任务被 2 分钟杀**：渲染全部 10 镜（约 1200+ 帧截图）在后台会失败，改**前台**跑（前台超时上限 10 分钟足够）。
3. **透明底变棋盘格**：ImageGen 的 `background:transparent` 经常把棋盘格烙进 RGB，需用洪泛填充从四边向内吃掉棋盘格色（深描边会挡住，不会误伤笔杆）。
4. **底色越禁越黄**：在 Prompt 里反复强调“暖白”反而让模型把底染黄（V1 #F3EDE1→V2 #F1E7D7）。放弃 Prompt 治色，统一走 `fix_bg.py` 后期校正。
5. **中文关键词错位**：模型可能把关键词写到额头/底部而非指定位置。靠双锁 Prompt 压制，必要时图生图局部擦除重出。
6. **中文字体**：字幕用系统 `Microsoft YaHei`（或 `simhei`），确保 ffmpeg/Chrome 能取到。
7. **配音联网**：edge_tts 需联网；首次跑确认能出 m4a 再批量。
8. **多项目必须显式设 `WB_WORKDIR`**：脚本内置默认工程目录是创建时的目录，不设环境变量时配音/成片会写进那个旧目录，甚至覆盖旧项目同名文件（实测发生过：gen_voice 覆盖了上一条片的音频）。每个新项目开工先设 `$env:WB_WORKDIR=<项目目录>` 再跑任何脚本。
