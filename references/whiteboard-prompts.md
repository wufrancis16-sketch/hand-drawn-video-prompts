# 横版出图 Prompt 模板（双锁技术）

目标：生成 16:9 横版、暖白素描纸、Q 版手绘蜡笔风静帧，且**只出现指定关键词、不出现任何自加文字**。下面以 ERP 科普第 01 镜为例，所有镜通用此模板。

## 通用结构（必含）

- 画幅：`horizontal 16:9 landscape composition`
- 底色：`solid warm-white canvas background with exact base color #F8F6EF`
- 质感：`thick imperfect black hand-drawn marker and crayon outlines, bold flat wax-crayon color blocks`
- 比例：`natural restrained Q-version proportions`
- 三色：`black ink, sunflower yellow, cobalt blue, tomato red`
- 留白：`clean empty bottom 15 percent reserved for subtitles`
- 禁项：`No glossy rendering, no realistic lighting, no gradients, no vignette, no logos, no watermark, no photorealism, no 3D`

## 双锁 1：禁止多余文字（放 Prompt 最开头）

> Do not add any title, caption, subtitle, headline, watermark or any other extra text anywhere in the image, especially not along the bottom edge.

## 双锁 2：指定关键词只出现在某处、恰好一次（放结尾）

> Show the exact text "ERP" as small clean high-contrast hand-drawn black lettering written directly on the face of the standing sign board, not inside any card, label, sticker, note, rounded text box, title panel or isolated white panel; keep the lettering perfectly legible and undeformed. The letters "ERP" appear ONLY on the sign board surface and nowhere else. The text appears exactly once, in the correct order, not deformed, not mirrored, not scrambled, not duplicated. Do not write any other letters, Chinese characters, numerals or fake writing anywhere else in the image.

> 中文关键词同理：例如 `Show the exact Chinese keyword "合到一起" ... ONLY in the upper-left corner area and nowhere else.`

## 构图提示

横版要把主体铺满宽度（60–85%），上下留白。元素要**可拆分**——因为后续逐元素显绘（见 `whiteboard-workflow.md` 的 `ELEMS`）需要每个部件有独立区域：
- 人物 / 物件 / 箭头 / 关键词 各自成块，避免互相重叠到无法单独揭示。
- 关键词放左上角安全区，远离底部字幕区。

## 持笔手素材 Prompt

> A right hand holding a fat brown marker pen with a white barrel band, warm hand-drawn cartoon illustration style with crayon texture, skin-tone hand with a blue shirt sleeve cuff at the wrist. The marker pen tip points to the upper-left corner, held at a natural writing angle as if drawing on a whiteboard. Only the hand, sleeve and pen, nothing else. Pure transparent background, no paper, no shadow, no text, no watermark.

注意：实际生成的“透明底”常是棋盘格，需用洪泛填充抠掉四周棋盘格后再用（见流水线已知坑 #3）。
