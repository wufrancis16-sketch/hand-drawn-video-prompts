# -*- coding: utf-8 -*-
"""16:9 白板显绘 v2：逐元素手绘揭示——按口播顺序逐部件画出（蛇形软边笔刷 + 持笔手跟随 + 抖动）
用法: python render_whiteboard2.py [镜号...]   不带参数=全部10镜+拼接

依赖：playwright（pip install playwright，使用系统 Chrome）、ffmpeg、Pillow
环境变量（可选，不设置则使用下方默认工程目录）:
    WB_WORKDIR  工程根目录（含 outputs_land/final、shots/aud、outputs_land/hand）
    WB_FFMPEG   ffmpeg 可执行路径
    WB_FFPROBE  ffprobe 可执行路径
    WB_CHROME   Chrome 可执行路径
"""
import os, json, subprocess, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

# ===== 工程配置（按项目修改 / 或用环境变量覆盖）=====
WORK = os.environ.get('WB_WORKDIR', r'E:\workbuddy\2026-09-22-15-27-07')
FF = os.environ.get('WB_FFMPEG', r'E:\workbuddy\2026-08-10-16-44-11\ffmpeg\ffmpeg-9.0-full_build\bin\ffmpeg.exe')
FFP = os.environ.get('WB_FFPROBE', r'E:\workbuddy\2026-08-10-16-44-11\ffmpeg\ffmpeg-9.0-full_build\bin\ffprobe.exe')
CHROME = os.environ.get('WB_CHROME', r'C:\Program Files\Google\Chrome\Application\chrome.exe')

OUT = os.path.join(WORK, 'shots_wb2')
FRAMES = os.path.join(WORK, 'frames_wb2')
IMG_DIR = os.path.join(WORK, 'outputs_land', 'final')
HAND = Path(WORK, 'outputs_land', 'hand', 'hand_final.png').as_uri()
TIP = os.path.join(WORK, 'outputs_land', 'hand', 'tip.txt')
FPS = 25
CW, CH = 1920, 1080

# 每镜口播文案（按项目替换）
SUBS = {
    1: '很多老板听过ERP，但不知道它到底是什么。',
    2: '简单来说，ERP就是企业资源管理系统。',
    3: '它可以把企业里的采购、销售、库存、生产、财务等业务流程整合到一个系统里。',
    4: '以前采购、仓库、销售、财务各管各的，',
    5: '数据靠Excel传来传去，',
    6: '容易出现库存不准、账目对不上、',
    7: '订单跟进混乱的问题。',
    8: '用了ERP之后，业务数据可以实时同步，',
    9: '老板能看到经营情况，员工也能更高效地协同工作。',
    10: '简单理解，ERP就是帮企业把人、货、财、业务流程管理起来的一套数字化工具。',
}

# 每镜元素序列: [nx, ny, nw, nh, 权重]（归一化坐标，基于1536x1024原图），按口播叙述顺序
# 即“先画哪个部件、后画哪个部件”，权重越大画得越慢（占时长越多）
ELEMS = {
    1: [  # 老板 -> ERP立牌 -> 红问号 -> 黄射线
        [0.25, 0.32, 0.25, 0.44, 1.2], [0.50, 0.375, 0.195, 0.25, 1.0],
        [0.378, 0.11, 0.145, 0.285, 0.9], [0.66, 0.285, 0.085, 0.23, 0.6]],
    2: [  # 老板 -> 大蓝箱 -> 手上投递物 -> 番茄 -> 关键词
        [0.095, 0.18, 0.135, 0.37, 1.1], [0.25, 0.09, 0.34, 0.49, 1.5],
        [0.29, 0.17, 0.09, 0.10, 0.6], [0.29, 0.68, 0.065, 0.09, 0.5],
        [0.055, 0.095, 0.175, 0.10, 0.9]],
    3: [  # 五人(采购/销售/库存/生产/财务) -> 三箭头 -> 蓝圆环 -> 关键词
        [0.037, 0.185, 0.145, 0.35, 1.0], [0.185, 0.19, 0.145, 0.345, 1.0],
        [0.32, 0.083, 0.115, 0.26, 1.0], [0.46, 0.185, 0.10, 0.35, 1.0],
        [0.587, 0.20, 0.085, 0.34, 1.0], [0.135, 0.30, 0.075, 0.10, 0.4],
        [0.26, 0.375, 0.085, 0.10, 0.4], [0.405, 0.265, 0.055, 0.10, 0.4],
        [0.298, 0.32, 0.105, 0.16, 0.9], [0.02, 0.03, 0.145, 0.06, 0.7]],
    4: [  # 四人 -> 隔墙 -> 关键词
        [0.12, 0.16, 0.115, 0.39, 1.0], [0.235, 0.16, 0.11, 0.39, 1.0],
        [0.35, 0.16, 0.11, 0.39, 1.0], [0.465, 0.16, 0.115, 0.39, 1.0],
        [0.218, 0.12, 0.255, 0.425, 1.1], [0.04, 0.06, 0.175, 0.10, 0.7]],
    5: [  # 左上 -> 右上 -> 右下 -> 左下 -> 中间乱飞区 -> 关键词
        [0.045, 0.03, 0.175, 0.275, 1.0], [0.52, 0.03, 0.145, 0.25, 1.0],
        [0.505, 0.30, 0.15, 0.27, 1.0], [0.06, 0.30, 0.145, 0.26, 1.0],
        [0.195, 0.05, 0.31, 0.36, 1.6], [0.01, 0.02, 0.09, 0.04, 0.5]],
    6: [  # 天平主体 -> 左盘货箱 -> 右盘账本 -> 放大镜 -> 红叉 -> 关键词
        [0.25, 0.04, 0.245, 0.545, 1.3], [0.062, 0.28, 0.245, 0.265, 1.1],
        [0.395, 0.225, 0.185, 0.19, 0.9], [0.485, 0.10, 0.165, 0.195, 0.9],
        [0.38, 0.165, 0.045, 0.07, 0.4], [0.02, 0.035, 0.10, 0.05, 0.6]],
    7: [  # 红绳大结 -> 小人 -> 缠脚绳圈 -> 关键词
        [0.23, 0.05, 0.42, 0.41, 1.6], [0.055, 0.12, 0.23, 0.37, 1.1],
        [0.205, 0.33, 0.08, 0.09, 0.4], [0.015, 0.025, 0.07, 0.04, 0.5]],
    8: [  # 五组齿轮+人 从左到右 -> 关键词
        [0.023, 0.155, 0.18, 0.36, 1.0], [0.205, 0.21, 0.09, 0.30, 0.8],
        [0.29, 0.18, 0.115, 0.33, 0.9], [0.41, 0.21, 0.085, 0.30, 0.8],
        [0.495, 0.15, 0.17, 0.36, 1.0], [0.035, 0.05, 0.175, 0.10, 0.7]],
    9: [  # 老板+凳 -> 表盘 -> 黄轮 -> 推人群 -> 关键词
        [0.055, 0.18, 0.13, 0.37, 1.1], [0.172, 0.055, 0.15, 0.245, 0.9],
        [0.45, 0.135, 0.17, 0.33, 1.1], [0.38, 0.075, 0.30, 0.475, 1.4],
        [0.03, 0.055, 0.11, 0.08, 0.7]],
    10: [  # 工具箱 -> 箱内人货财 -> 老板 -> 关键词
        [0.127, 0.11, 0.37, 0.46, 1.3], [0.17, 0.22, 0.30, 0.17, 1.1],
        [0.425, 0.07, 0.195, 0.50, 1.1], [0.02, 0.035, 0.10, 0.06, 0.6]],
}

HTML_TPL = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body{margin:0;background:#F8F6EF}#cv{display:block}
</style></head><body>
<canvas id="cv" width="1920" height="1080"></canvas>
<script>
const IMG = new Image(); IMG.src = '__IMG__';
const HAND = new Image(); HAND.src = '__HAND__';
const SUBS = __SUBS__;
const DUR = __DUR__;
const ELEMS = __ELEMS__;
const HW = 430, HH = 430 * __HRATIO__;
const TXF = __TXF__, TYF = __TYF__;
const IMGX = 150, IMGW = 1620, IMGH = 1080;
window.__ready = false;
let ok = 0;
IMG.onload = () => { ok++; if (ok === 2) window.__ready = true; };
HAND.onload = () => { ok++; if (ok === 2) window.__ready = true; };

// 笔刷 sprite（软边圆）
const SPR = document.createElement('canvas'); SPR.width = SPR.height = 256;
(() => { const c = SPR.getContext('2d');
  const g = c.createRadialGradient(128,128,70,128,128,128);
  g.addColorStop(0,'rgba(255,255,255,1)'); g.addColorStop(1,'rgba(255,255,255,0)');
  c.fillStyle = g; c.fillRect(0,0,256,256); })();

const mask = document.createElement('canvas'); mask.width = 1920; mask.height = 1080;
const mctx = mask.getContext('2d');
const comp = document.createElement('canvas'); comp.width = 1920; comp.height = 1080;
const cctx = comp.getContext('2d');

// 每元素生成蛇形抖动路径
function jit(i, amp){ return [Math.sin(i*12.9898)*amp, Math.sin(i*78.233)*amp]; }
const ITEMS = ELEMS.map((e) => {
  const [nx,ny,nw,nh,w] = e;
  const x0 = IMGX + nx*IMGW, y0 = ny*IMGH, bw = nw*IMGW, bh = nh*IMGH;
  const r = Math.max(26, Math.min(95, Math.min(bw,bh)*0.55));
  const rows = Math.max(2, Math.round(bh/(r*1.15)));
  const raw = [];
  for (let i=0;i<rows;i++){
    const y = y0 + bh*(i+0.5)/rows;
    if (i%2===0){ raw.push([x0,y],[x0+bw,y]); } else { raw.push([x0+bw,y],[x0,y]); }
  }
  const sp = r*0.45, pts = [];
  for (let s=0;s<raw.length-1;s++){
    const ax=raw[s][0], ay=raw[s][1], bx=raw[s+1][0], by=raw[s+1][1];
    const L = Math.hypot(bx-ax, by-ay), n = Math.max(1, Math.round(L/sp));
    for (let k=0;k<n;k++){ const u=k/n; pts.push([ax+(bx-ax)*u, ay+(by-ay)*u]); }
  }
  pts.push(raw[raw.length-1].slice());
  const pts2 = pts.map((p,i)=>{ const j=jit(i, r*0.14); return [p[0]+j[0], p[1]+j[1]]; });
  return { pts: pts2, r, w, start: pts2[0], end: pts2[pts2.length-1] };
});

// 时间轴
const ENTER = Math.min(0.4, DUR*0.08), MOVE = Math.min(0.14, DUR*0.03), EXIT = Math.max(0.35, DUR*0.07);
const HOME = [2250, 1350];
let total = ENTER + EXIT + MOVE*(ITEMS.length-1);
let wsum = 0; for (const it of ITEMS) wsum += it.w;
const drawT = DUR - total;
let acc = ENTER;
const SEG = [];
let prev = ITEMS[0].start;
for (let i=0;i<ITEMS.length;i++){
  const it = ITEMS[i];
  if (i>0){ SEG.push({type:'move', t0:acc, t1:acc+MOVE, from:prev, to:it.start}); acc += MOVE; }
  const d = drawT * it.w / wsum;
  SEG.push({type:'draw', t0:acc, t1:acc+d, item:i}); acc += d; prev = it.end;
}
SEG.push({type:'exit', t0:acc, t1:acc+EXIT, from:prev, to:HOME});
const T_END = acc + EXIT;

function ease(u){ return u*u*(3-2*u); }
function handPosAt(t){
  if (t >= T_END) return null;
  for (const s of SEG){
    if (t >= s.t0 && t < s.t1){
      const u = (t-s.t0)/(s.t1-s.t0);
      if (s.type === 'draw'){
        const it = ITEMS[s.item];
        const k = u*(it.pts.length-1);
        const i0 = Math.floor(k), fr = k-i0;
        const a = it.pts[i0], b = it.pts[Math.min(i0+1, it.pts.length-1)];
        return [a[0]+(b[0]-a[0])*fr, a[1]+(b[1]-a[1])*fr + Math.sin(t*9)*3];
      }
      const e = ease(u);
      return [s.from[0]+(s.to[0]-s.from[0])*e, s.from[1]+(s.to[1]-s.from[1])*e];
    }
  }
  return null;
}
function reveal(t){
  mctx.clearRect(0,0,1920,1080);
  for (const s of SEG){
    if (s.type !== 'draw') continue;
    const it = ITEMS[s.item];
    let k;
    if (t >= s.t1) k = it.pts.length;
    else if (t <= s.t0) continue;
    else k = Math.floor(((t-s.t0)/(s.t1-s.t0)) * it.pts.length);
    for (let i=0;i<k;i++) mctx.drawImage(SPR, it.pts[i][0]-it.r, it.pts[i][1]-it.r, it.r*2, it.r*2);
  }
}
function wrap(text, n){
  if (text.length <= n) return [text];
  const mid = Math.ceil(text.length / 2);
  const P = '，。；、？！：,;.?!:';
  let cut = -1;
  for (let d = 0; d <= Math.floor(n/2); d++){
    if (mid + d < text.length && P.indexOf(text[mid+d]) >= 0){ cut = mid + d + 1; break; }
    if (mid - d - 1 >= 0 && P.indexOf(text[mid-d-1]) >= 0){ cut = mid - d; break; }
  }
  if (cut < 0) cut = mid;
  return [text.slice(0, cut), text.slice(cut)];
}
function renderAt(t){
  const ctx = document.getElementById('cv').getContext('2d');
  ctx.fillStyle = '#F8F6EF'; ctx.fillRect(0,0,1920,1080);
  reveal(t);
  cctx.globalCompositeOperation = 'source-over';
  cctx.clearRect(0,0,1920,1080);
  cctx.drawImage(IMG, 0,0,IMG.width,IMG.height, IMGX,0,IMGW,IMGH);
  cctx.globalCompositeOperation = 'destination-in';
  cctx.drawImage(mask, 0,0);
  ctx.drawImage(comp, 0,0);
  const hp = handPosAt(t);
  if (hp) ctx.drawImage(HAND, hp[0]-TXF*HW, hp[1]-TYF*HH, HW, HH);
  const lines = wrap(SUBS, 24);
  ctx.font = 'bold 46px "Microsoft YaHei", sans-serif';
  ctx.textAlign = 'center'; ctx.lineWidth = 8; ctx.lineJoin = 'round';
  ctx.strokeStyle = '#1a1a1a'; ctx.fillStyle = '#F6DE3A';
  const baseY = 1080 - 60 - (lines.length-1)*58;
  lines.forEach((ln,i)=>{ const y = baseY + i*58; ctx.strokeText(ln,960,y); ctx.fillText(ln,960,y); });
}
</script></body></html>"""


def audio_dur(f):
    r = subprocess.run([FFP, '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'json', f], capture_output=True, text=True)
    return float(json.loads(r.stdout)['format']['duration'])


def render_shot(i, browser):
    n = '%02d' % i
    img = Path(IMG_DIR, '镜头%s_bgfix.png' % n).as_uri()
    audio = os.path.join(WORK, 'shots', 'aud', 'shot%s.m4a' % n)
    dur = audio_dur(audio)
    tip = open(TIP).read().split()
    hw, hh, tx, ty = map(int, tip)
    html = (HTML_TPL.replace('__IMG__', img).replace('__HAND__', HAND)
            .replace('__SUBS__', json.dumps(SUBS[i], ensure_ascii=False))
            .replace('__DUR__', repr(dur))
            .replace('__ELEMS__', json.dumps(ELEMS[i]))
            .replace('__HRATIO__', repr(hh / hw))
            .replace('__TXF__', repr(tx / hw)).replace('__TYF__', repr(ty / hh)))
    hp = Path(OUT, 'shot%s.html' % n)
    hp.parent.mkdir(exist_ok=True)
    hp.write_text(html, encoding='utf-8')
    fdir = os.path.join(FRAMES, n)
    os.makedirs(fdir, exist_ok=True)
    nf = int(round(dur * FPS))
    ctx = browser.new_context(viewport={'width': CW, 'height': CH}, device_scale_factor=1)
    pg = ctx.new_page()
    pg.goto(hp.as_uri())
    pg.wait_for_function('window.__ready===true', timeout=30000)
    for k in range(nf + 1):
        t = k / FPS
        pg.evaluate('renderAt(%f)' % t)
        pg.screenshot(path=os.path.join(fdir, 'f%04d.png' % k))
    ctx.close()
    mp4 = os.path.join(OUT, 'shot%s_wb2.mp4' % n)
    subprocess.run([FF, '-framerate', str(FPS), '-i', os.path.join(fdir, 'f%04d.png'),
                    '-i', audio, '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
                    '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-shortest', '-y', mp4],
                   cwd=WORK, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print('SHOT', n, 'dur=%.2f frames=%d size=%d' % (dur, nf + 1, os.path.getsize(mp4)), flush=True)
    return mp4


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    shots = [int(a) for a in sys.argv[1:] if a.isdigit()] or list(range(1, 11))
    parts = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME,
                                    args=['--no-sandbox', '--disable-gpu', '--force-device-scale-factor=1'])
        for i in shots:
            parts.append(render_shot(i, browser))
        browser.close()
    if len(shots) == 10:
        lst = os.path.join(OUT, 'concat.txt')
        with open(lst, 'w', encoding='utf-8') as f:
            for m in sorted(parts):
                f.write("file '%s'\n" % m.replace('\\', '/'))
        final = os.path.join(WORK, 'ERP科普_手绘显绘v2_16x9.mp4')
        subprocess.run([FF, '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', '-y', final],
                       cwd=WORK, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print('FINAL', final, os.path.getsize(final), flush=True)
