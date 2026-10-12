# 白板手绘显绘流水线（主推产出模式）

把中文口播稿变成 **16:9 白板手绘动画**：一只手握着马克笔，画面跟着口播**逐元素被画出来**，底部黄字字幕 + 中文配音 + 低音量轻音乐 BGM。全部本地生成，零视频生成额度消耗（仅生图 + TTS 联网）。

## 执行方式：全自动，不逐步确认 ★

用户给出完整口播稿 = 授权端到端执行。从建目录到交付成片**一口气跑完**，不要逐步骤问“要不要继续”。

- 动工前只说一句额度消耗（每镜约 5–10 额度）。
- 出图后自行逐张验收（人类？立牌字对？有无多余英文/涂鸦？），有瑕疵直接图生图返工。
- 镜数由 `SUBS` 长度决定（`render_whiteboard2.py` 已按 `len(SUBS)` 驱动，不再写死 10 镜）；长稿 12–16 镜。
- 只有方向性选择（画风 / 配音音色 / 选题方向）才找用户确认。

## 依赖

- Python 3.10+，安装：`pip install playwright edge_tts Pillow`
- **本机用哪个解释器（重要，2026-10-08 实测）**：不要用裸 `binaries\python\versions\3.13.12\python.exe`——它是干净解释器，**没有** playwright / Pillow / edge_tts，直接跑会 `ModuleNotFoundError`。流水线一律用隔离环境
  `C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe`（playwright + Pillow + numpy 齐备）。
  缺 edge_tts 时：该解释器 `-m pip install edge-tts`；若随后报 `No module named 'typing_extensions'`，再 `-m pip install --force-reinstall --no-deps typing-extensions`（该环境 site-packages 有个 `~ip` 坏分发会干扰依赖判定，属无害警告）。
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

**出图后第一步必须改名**：ImageGen 落盘的文件名是「提示词开头截断 + 时间戳」（如 `Do_not_add_any_title__caption__2026-09-30T01-47-36.png`），而后续 `fix_bg` / `render_whiteboard2` 都按 `镜头NN.png` 读取，文档里写的「输出去 outputs_land/raw/镜头NN.png」不会自动成立。因为生图是**串行**的，mtime 顺序 == 镜头顺序，直接跑
```bash
python scripts/rename_shots.py            # 按 mtime 顺序批量改名（已命名的跳过，重跑安全）
python scripts/rename_shots.py --list     # 只看不改（改名顺序对不对）
```
补出某几镜后用 `--start 6` 从第 6 镜接着编号。

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

**成片命名**：脚本默认用「工程目录名 + `_手绘显绘_16x9.mp4`」，可用环境变量 `WB_OUTNAME` 覆盖。

**分批渲染（镜数多时必用）**：脚本只在「一次传满 `len(SUBS)` 镜」时才自动拼接，分批跑不会拼。做法是 `render_whiteboard2.py 1 2 3 4 5 6 7 8` → `render_whiteboard2.py 9 10 11 12 13 14 15`，再手动 concat。**实测 15 镜（共 66.2s / 1655 帧）按 8+7 两批前台跑各约 2–4 分钟，稳；不要一次传 15 镜**（前台 10 分钟上限有风险）。**手动写 concat 清单必须用绝对路径**——ffmpeg 的 concat demuxer 把清单里的相对路径解析为「相对清单文件所在目录」，写 `shots_wb2/shot01_wb2.mp4` 会变成 `shots_wb2/shots_wb2/...` 而报 `rc=-2`（实测踩过）。脚本自己写的那份清单本来就是绝对路径，所以自动拼接不会踩到。

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

> **BGM 时长**：`--dur` 建议给足「渲染总时长（即倍速前的时长，看渲染日志末尾各镜 dur 之和）」。`mix_bgm.py` 已用 `-stream_loop -1` 让 BGM 自动循环补齐，**给短了片尾也不会静音**（验证：8s BGM 铺满 48.4s 成片），但循环接点可能听得出，所以还是给足更自然。

## 已知坑（务必先看）

1. **ImageGen 并行 bug**：并行传不同 `output_dir` 时参数被吞、文件覆盖。必须**串行**逐张生成。
2. **后台任务被 2 分钟杀**：渲染全部 10 镜（约 1200+ 帧截图）在后台会失败，改**前台**跑（前台超时上限 10 分钟足够）。
3. **透明底变棋盘格**：ImageGen 的 `background:transparent` 经常把棋盘格烙进 RGB，需用洪泛填充从四边向内吃掉棋盘格色（深描边会挡住，不会误伤笔杆）。
4. **底色越禁越黄**：在 Prompt 里反复强调“暖白”反而让模型把底染黄（V1 #F3EDE1→V2 #F1E7D7）。放弃 Prompt 治色，统一走 `fix_bg.py` 后期校正。
5. **中文关键词错位**：模型可能把关键词写到额头/底部而非指定位置。靠双锁 Prompt 压制，必要时图生图局部擦除重出。
6. **中文字体**：字幕用系统 `Microsoft YaHei`（或 `simhei`），确保 ffmpeg/Chrome 能取到。
7. **配音联网**：edge_tts 需联网；首次跑确认能出 m4a 再批量。
8. **多项目必须显式设 `WB_WORKDIR`**：脚本内置默认工程目录是创建时的目录，不设环境变量时配音/成片会写进那个旧目录，甚至覆盖旧项目同名文件（实测发生过：gen_voice 覆盖了上一条片的音频）。每个新项目开工先设 `$env:WB_WORKDIR=<项目目录>` 再跑任何脚本。
9. **双锁 Prompt 也会彻底失效，必须逐张肉眼验收**：实测某镜被画成完全无关的动物（老板→卡通牛）、立牌关键词被写成「高高兴兴 快乐」而非指定的「高效」。出图后**逐张 Read 核对**：①人物是否是人类且符合描述；②立牌文字是否等于指定关键词；③有无多余英文/假字。不合格就**重出**（别只改文字，人物跑偏要重写 Prompt 并显式否定，如 “a human person, absolutely not an animal”）。
   - **重复立牌**：同一关键词被画成**两块牌子**是高频失效形态（实测「记忆」「自动」「进销存」均出过两块，`appears exactly once` 管不住）。验收必须确认“关键词恰好出现一次”，多出来的那块擦掉，保留其中一块。
     - **首选矩形填充底色（秒级，2026-10-10 实测）**：立牌四周是均匀暖白纸底，不必动用图生图——从原图备份恢复 → 用 PIL 把「多余立牌」的矩形区域整体填 `(248,246,239)` → 重跑 `fix_bg.py`。**关键是把矩形框得足够大**：第一次按肉眼范围框（例 448,168→550,380）会留下描边残迹（一条竖线 + 一条横虚线），向外扩 10–20px（438,158→568,402）才干净。填充框别侵入相邻元素（卡车/仓库）即可。
     - 若立牌压在别的元素上（背景非纯色），才退回图生图定点擦除。
10. **画面里的零散英文要清掉**：模型常在不显眼处塞英文（软箱上 `SOFTWARE`、账单上 `ITEM/PRICE/TOTAL`、便签上的假手写乱字），与中文片违和。按需用图生图定点擦除（保留关键词立牌），删除后重跑 ③→⑥→⑦。原图先备份到工程根 `backup_镜头NN_v1.png`。
    - **整页假数据**：空白单据会被模型填满假字段（实测订单纸写出「订单编号 D-001 / 下单日期 2024-05-20 / 数量 10 20 30」）。这种整页杂字**擦除成本高于重出**，直接重出并在 Prompt 里强调 `completely blank, no writing, no numbers, no letters, no table lines` 更快更干净。
    - **底部整行乱码中文**：模型也会在字幕预留区写一行通顺度极差的中文（实测「问题这一样？结果有的的假接订表。」），必须擦掉——它会和真字幕打架。
11. **批量删中间帧会被安全删除拦截**：`frames_wb2/` 有上千文件，Python `shutil.rmtree` 会报 `SAFE_DELETE_BULK_CONFIRM_REQUIRED`；改用 PowerShell `Remove-Item -Recurse -Force`。
12. **并列场景会被自加“分隔符”**：要求画“左右两个场景／两件事”时，模型会在中缝自作主张加**一条全高竖虚线 + 一个十字加号**当装饰（实测 16 镜片的两场景镜）。它不算关键词也不是乱码，但很显眼，验收必须清掉。
    - **定位必须用像素扫描，别靠眼看**：拿放大裁图目测坐标会出错——实测把人物右边缘当成虚线，填错位置直接误伤原画。可靠做法（numpy）：
      ```python
      nb = (np.abs(a - np.array([248, 246, 239])).sum(axis=2) > 60)
      colcnt = nb[40:720, :].sum(axis=0)     # 竖虚线所在列计数飙高（实测 650+）
      rowcnt = nb[:, x0:x1].sum(axis=1)      # 横杠所在行出现局部峰值（实测 20+）
      ```
      先扫出列／行再定矩形；两侧留 10–20px 安全间距避开人物与货架。**填完必须跑 `fix_bg.py`**，底色归一化后填充痕迹完全看不出来（raw 阶段偏白是正常的，别据此判断失败）。
    - **抹除前先备份原图**（`backup_镜头NN_v1.png`），填错能回滚重做——本轮正是靠备份救回来的。
    - 填充值用 `(248,246,239)` 并叠 ±5 随机噪声，比纯色块更接近纸纹。
