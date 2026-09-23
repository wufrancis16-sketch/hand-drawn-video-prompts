---
name: hand-drawn-video-prompts
description: 手绘白板动画视频生成技能。把中文口播稿变成 16:9 / 9:16 的逐元素手绘显绘视频（持笔手跟随、口播配音、字幕、轻音乐 BGM）。当用户要制作手绘科普/讲解视频、白板动画、手绘风格营销视频，或需要中文口播稿转视频时使用。Hand-drawn whiteboard animation: Chinese voiceover script -> 16:9 reveal-drawing video with marker-hand, TTS, subtitles, light BGM.
---

# 手绘白板动画视频（Hand-Drawn Whiteboard Animation）

把中文口播稿变成**真正的手绘描绘视频**：一只手握着马克笔，画面跟着口播**逐元素被画出来**（不是图片+推近的幻灯片），底部黄字字幕 + 中文配音 + 低音量轻音乐。视觉语言是现代 Q 版手绘蜡笔插画，固定暖白纸底 `#F8F6EF`。

## 两种产出模式

- **A. 白板显绘动画（主推，已验证）**：16:9，逐元素揭示 + 持笔手 + 配音 + 字幕 + BGM。见 [`references/whiteboard-workflow.md`](references/whiteboard-workflow.md) 与 [`scripts/`](scripts/)。**用户要“手绘视频/白板动画/跟脚本画出来”时走这条。**
- **B. 9:16 静帧分镜包（原始能力）**：竖版 Q 版分镜 Prompt 包，对接 Flow/Nano Banana 做图生视频。见 [`references/automation-workflow.md`](references/automation-workflow.md)、[`references/style-guide.md`](references/style-guide.md)、[`references/output-example.md`](references/output-example.md)。

若用户给完整文稿且未指定模式，默认走 **A**。

## 非妥协的视觉规范

- 固定暖白纸底，精确色号 `#F8F6EF`；只允许极淡低对比纸纹。禁用米黄/渐变/暗角/漂移底色。
- 粗黑不规则手绘墨线 + 向日葵黄 / 钴蓝 / 番茄红三色块。
- Q 版人物比例自然克制：禁大头娃娃、鼓眼、写实脸、3D、赛博 HUD、复古报纸风。
- 每镜 2–4 个可读视觉组，上下留白充足；字幕不进生成画面（做确定性文字层）。

## 模式 A：白板显绘流水线（速查）

依赖：`pip install playwright edge_tts Pillow`；系统 Chrome；ffmpeg；ImageGen（生图）。

```bash
# 1) 横版出图 1536x1024（双锁 Prompt，见 references/whiteboard-prompts.md）→ outputs_land/raw/镜头NN.png
# 2) 底色校正 + 去水印
python scripts/fix_bg.py <WB_WORKDIR>/outputs_land/raw <WB_WORKDIR>/outputs_land/final 1380,940,1536,1024
# 3) 逐镜配音（edge_tts，联网）
python scripts/gen_voice.py
# 4) 逐元素显绘渲染（前台跑！后台会被 2 分钟杀）
python scripts/render_whiteboard2.py          # 全部 10 镜 + 拼接成片
# 5) 轻音乐 BGM + 混音
python scripts/gen_bgm.py --dur 49.0 --out bgm_light.wav
python scripts/mix_bgm.py 成片.mp4 bgm_light.wav 成片_带BGM.mp4 0.20
```

配置：`SUBS`（每镜口播文案）与 `ELEMS`（每镜部件序列 `[nx,ny,nw,nh,权重]`，按口播顺序）在 `scripts/render_whiteboard2.py` 顶部按项目填写；`WB_WORKDIR` / `WB_FFMPEG` / `WB_CHROME` 用环境变量覆盖机器路径。

**为什么生动**：`ELEMS` 决定画面“先画哪个部件、后画哪个部件”，手跟着笔尖移动——画面跟着脚本逻辑长出来，而不是整图左→右硬扫。

完整细节、双锁 Prompt 模板、持笔手素材生成、已知坑（ImageGen 并行覆盖、后台 2 分钟杀、透明底棋盘格、底色越禁越黄、关键词错位）见 [`references/whiteboard-workflow.md`](references/whiteboard-workflow.md) 与 [`references/whiteboard-prompts.md`](references/whiteboard-prompts.md)。

## 模式 B：9:16 静帧分镜（速查）

1. 每 4–6 秒一镜，给视觉隐喻；不把金额/日期/公司名交给图像模型。
2. 每镜输出自包含英文生图 Prompt（竖版 9:16、`#F8F6EF`、粗黑线、三色、主体占宽 60–70%）+ 图生视频 Prompt。
3. 中文关键词默认直接写在纸上（左上/侧安全区，禁贴底部），用双锁 Prompt 控位置。
4. 交付 Prompt 包 + 可选成片；详细见 `references/`。

## 实体准确性

国旗/公司/Logo/公众人物/数字日期：用明确实体锚点 + 确定性文字层，不靠模型凭记忆画 Logo；公众人物用非写实 Q 版 caricature（发型/眼镜/服饰/道具），不绕过安全限制。输出中附实体准确性说明。

## 质量检查（交付前必做）

- 每镜一个核心含义、合理时长、字段齐全；Prompt 自包含且画幅/底色/线稿/色板一致。
- 精确数字、日期、Logo、国旗、长文本标记走确定性处理。
- 公众人物为非写实 Q 版、无安全绕过。
- 模式 A：逐镜核对 `ELEMS` 部件出场顺序与口播一致；确认无自加标题、关键词位置正确。
- 不含任何 API 配置复杂化或不必要的确认闸。

中文参考：[SKILL.zh-CN.md](SKILL.zh-CN.md)
