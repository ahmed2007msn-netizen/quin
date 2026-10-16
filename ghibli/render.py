"""Procedural Ghibli-style animated scene -> MP4 (1080x1920, vertical)."""
import math, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1080, 1920
FPS, SECONDS = 30, 12
import os
N = int(os.environ.get('FRAMES', FPS * SECONDS))
TOTAL = FPS * SECONDS
PAN = 140          # foreground pan in px over the clip
MARGIN = 200
OUT = sys.argv[1] if len(sys.argv) > 1 else "ghibli.mp4"
rng = random.Random(7)
np.random.seed(7)

def lerp(a, b, t): return a + (b - a) * t
def hexc(h): h = h.lstrip('#'); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

# ---------- sky ----------
def make_sky():
    y = np.linspace(0, 1, H)[:, None]
    top, mid, hor = np.array(hexc('#3f8fd8')), np.array(hexc('#86c3ee')), np.array(hexc('#f6e7c8'))
    t1 = np.clip(y / 0.55, 0, 1)[..., None]
    t2 = np.clip((y - 0.55) / 0.2, 0, 1)[..., None]
    col = lerp(top, mid, t1) * (1 - (y > 0.55)[..., None]) + lerp(mid, hor, t2) * (y > 0.55)[..., None]
    sky = np.repeat(col, W, axis=1).astype(np.float32)
    # sun glow
    yy, xx = np.mgrid[0:H, 0:W]
    sx, sy = W * 0.70, H * 0.12
    d = np.sqrt((xx - sx) ** 2 + (yy - sy) ** 2)
    glow = np.exp(-(d / 420) ** 2)[..., None] * 0.55 + np.exp(-(d / 90) ** 2)[..., None] * 0.9
    sky = sky * (1 - glow) + np.array([255, 250, 230]) * glow
    return np.clip(sky, 0, 255)

# ---------- clouds ----------
def make_cloud(w, h, seed):
    r = random.Random(seed)
    S = 2
    img = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    blobs = []
    base_y = h * 0.86
    for i in range(7):   # flat-ish bottom row
        cx = w * (0.12 + 0.76 * i / 6) + r.uniform(-15, 15)
        rad = h * r.uniform(0.13, 0.18)
        blobs.append((cx, base_y - rad * 0.8, rad))
    for i in range(r.randint(5, 7)):   # billowing upper mass
        cx = r.uniform(w * 0.25, w * 0.75)
        spread = 1 - abs(cx - w / 2) / (w / 2)
        rad = h * r.uniform(0.18, 0.28) * (0.7 + 0.5 * spread)
        cy = base_y - h * 0.22 - spread * h * r.uniform(0.1, 0.3)
        rad = min(rad, cy - 8)
        blobs.append((cx, cy, rad))
    shadow, mid, light = (176, 196, 226, 255), (226, 234, 246, 255), (255, 255, 255, 255)
    for cx, cy, rad in blobs:   # shadow underside
        d.ellipse([(cx - rad) * S, (cy - rad + rad * 0.12) * S, (cx + rad) * S, (cy + rad + rad * 0.12) * S], fill=shadow)
    for cx, cy, rad in blobs:   # body
        d.ellipse([(cx - rad * .95) * S, (cy - rad * .98) * S, (cx + rad * .9) * S, (cy + rad * .8) * S], fill=mid)
    for cx, cy, rad in blobs:   # sunlit tops (light from upper right)
        rr = rad * 0.7
        d.ellipse([(cx - rr + rad * .2) * S, (cy - rad * .95) * S, (cx + rr + rad * .2) * S, (cy - rad * .95 + rr * 1.5) * S], fill=light)
    img = img.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.6))
    return img

# ---------- hills ----------
def ridge(width, base, amps, seed):
    r = np.random.RandomState(seed)
    x = np.arange(width)
    y = np.full(width, base, dtype=float)
    for a, f in amps:
        y += a * np.sin(x * f + r.uniform(0, 6.28))
    return y

def make_hill(width, ys, top_col, bot_col, rim=None, speckle=None, seed=0):
    img = np.zeros((H, width, 4), dtype=np.float32)
    yy = np.arange(H)[:, None]
    mask = yy >= ys[None, :]
    depth = np.clip((yy - ys[None, :]) / 500.0, 0, 1)[..., None]
    col = lerp(np.array(top_col, float), np.array(bot_col, float), depth)
    if rim is not None:
        rimw = np.exp(-((yy - ys[None, :]) / 10.0) ** 2)[..., None] * mask[..., None]
        col = col * (1 - rimw * .7) + np.array(rim, float) * rimw * .7
    img[..., :3] = col
    img[..., 3] = mask * 255
    pil = Image.fromarray(img.astype(np.uint8), 'RGBA')
    if speckle:
        r = random.Random(seed)
        d = ImageDraw.Draw(pil)
        for _ in range(speckle[0]):
            x = r.uniform(0, width)
            y0 = ys[int(min(x, width - 1))]
            y = r.uniform(y0 + 15, min(H, y0 + 700))
            c = speckle[1][r.randrange(len(speckle[1]))]
            rw, rh = r.uniform(6, 22), r.uniform(2, 6)
            d.ellipse([x - rw, y - rh, x + rw, y + rh], fill=c + (55,))
        a = np.array(pil); a[..., 3] = (mask * 255).astype(np.uint8); pil = Image.fromarray(a)
    return pil.filter(ImageFilter.GaussianBlur(0.8))

# ---------- tree ----------
def make_canopy(seed):
    r = random.Random(seed)
    w, h, S = 560, 520, 2
    img = Image.new('RGBA', (w * S, h * S))
    d = ImageDraw.Draw(img)
    clumps = [(r.uniform(110, 450), r.uniform(120, 400), r.uniform(70, 120)) for _ in range(16)]
    clumps.sort(key=lambda c: c[1])
    for cx, cy, rr in clumps:
        d.ellipse([(cx - rr) * S, (cy - rr) * S, (cx + rr) * S, (cy + rr) * S], fill=hexc('#2c5a2e') + (255,))
    for cx, cy, rr in clumps:
        k = rr * .78
        d.ellipse([(cx - k + 14) * S, (cy - k - 16) * S, (cx + k + 14) * S, (cy + k - 22) * S], fill=hexc('#4b8a3c') + (255,))
    for cx, cy, rr in clumps:
        k = rr * .45
        d.ellipse([(cx - k + 30) * S, (cy - k - 36) * S, (cx + k + 30) * S, (cy + k - 40) * S], fill=hexc('#8cc35a') + (255,))
    # leaf flecks
    for _ in range(140):
        cx, cy, rr = clumps[r.randrange(len(clumps))]
        a = r.uniform(0, 6.28); dist = r.uniform(0, rr * .9)
        x, y = cx + math.cos(a) * dist, cy + math.sin(a) * dist
        c = r.choice([hexc('#a9d86f'), hexc('#c8ea8a')])
        d.ellipse([(x - 6) * S, (y - 4) * S, (x + 6) * S, (y + 4) * S], fill=c + (120,))
    # keep flecks inside canopy
    base = Image.new('L', (w * S, h * S)); bd = ImageDraw.Draw(base)
    for cx, cy, rr in clumps:
        bd.ellipse([(cx - rr) * S, (cy - rr) * S, (cx + rr) * S, (cy + rr) * S], fill=255)
    img.putalpha(Image.fromarray(np.minimum(np.array(img)[..., 3], np.array(base))))
    return img.resize((w, h), Image.LANCZOS)

def draw_trunk(d, x, y):
    d.polygon([(x - 22, y), (x + 22, y), (x + 10, y - 230), (x - 8, y - 230)], fill=hexc('#5a3b28'))
    d.polygon([(x + 4, y), (x + 22, y), (x + 10, y - 230), (x + 2, y - 230)], fill=hexc('#7a5236'))
    d.line([(x, y - 150), (x - 70, y - 250)], fill=hexc('#5a3b28'), width=14)
    d.line([(x + 5, y - 170), (x + 80, y - 260)], fill=hexc('#5a3b28'), width=12)

def draw_house(d, x, y):
    d.rectangle([x - 70, y - 90, x + 70, y], fill=hexc('#f3ead8'))
    d.rectangle([x + 10, y - 90, x + 70, y], fill=hexc('#d9cdb4'))
    d.polygon([(x - 92, y - 86), (x + 92, y - 86), (x + 50, y - 160), (x - 50, y - 160)], fill=hexc('#c2463a'))
    d.polygon([(x + 20, y - 86), (x + 92, y - 86), (x + 50, y - 160), (x + 10, y - 160)], fill=hexc('#9c3329'))
    d.rectangle([x + 30, y - 190, x + 50, y - 135], fill=hexc('#8a5a44'))
    d.rectangle([x - 50, y - 62, x - 20, y - 32], fill=hexc('#ffd77a'))
    d.rectangle([x - 8, y - 55, x + 14, y], fill=hexc('#7a5236'))

# ---------- build static layers ----------
print('building layers...', flush=True)
sky = make_sky()
LW = W + MARGIN * 2
mount = make_hill(LW, ridge(LW, 1010, [(110, .004), (45, .011), (14, .03)], 1),
                  hexc('#8fb0d6'), hexc('#a9c4de'), rim=hexc('#c9dcef'))
far = make_hill(LW, ridge(LW, 1180, [(40, .005), (18, .013)], 2),
                hexc('#7fbf6a'), hexc('#5d9c55'), rim=hexc('#c7e59a'),
                speckle=(500, [hexc('#4f8d4a'), hexc('#9ad07a')]), seed=3)
mid_y = ridge(LW, 1360, [(70, .0035), (20, .012)], 4)
mid = make_hill(LW, mid_y, hexc('#8ccc5c'), hexc('#4f9a40'), rim=hexc('#e2f5a6'),
                speckle=(1200, [hexc('#5aa040'), hexc('#b6e27a'), hexc('#3f7d36'), hexc('#f5f0a0')]), seed=5)
md = ImageDraw.Draw(mid)
tree_x = 380 + MARGIN
tree_y = int(mid_y[tree_x]) + 30
house_x = 860 + MARGIN
house_y = int(mid_y[house_x]) + 40
draw_house(md, house_x, house_y)
draw_trunk(md, tree_x, tree_y)
# flowers on mid hill
fr = random.Random(11)
for _ in range(500):
    x = fr.uniform(0, LW); y0 = mid_y[int(min(x, LW - 1))]
    y = fr.uniform(y0 + 40, H)
    c = fr.choice([hexc('#ffffff'), hexc('#ffe36e'), hexc('#ffb3c7'), hexc('#ffffff')])
    s = 2 + (y - y0) / 160
    md.ellipse([x - s, y - s, x + s, y + s], fill=c)
canopy = make_canopy(9)
# tree shadow on the hill
sh = Image.new('RGBA', mid.size); sd = ImageDraw.Draw(sh)
sd.ellipse([tree_x - 260, tree_y - 30, tree_x + 120, tree_y + 40], fill=(30, 70, 30, 90))
sh = sh.filter(ImageFilter.GaussianBlur(14))
mid.alpha_composite(sh)

clouds = [(make_cloud(780, 460, 21), -260, 360, 9.0), (make_cloud(520, 300, 22), 900, 40, 7.0),
          (make_cloud(900, 520, 23), 640, 560, 11.0), (make_cloud(420, 240, 24), 80, 860, 5.0),
          (make_cloud(460, 260, 25), -620, 150, 8.0)]

# foreground grass blades
blades = []
gr = random.Random(17)
for i in range(900):
    x = gr.uniform(-40, LW + 40)
    base = gr.uniform(H - 380, H + 20)
    hgt = gr.uniform(90, 260) * (0.6 + (base - (H - 380)) / 500)
    shade = (base - (H - 380)) / 400
    col = gr.choice(['#3e8a34', '#57a83f', '#2f6e2b', '#6cbf4a', '#8bd35a'])
    c = np.array(hexc(col), float) * (1.05 - .35 * shade)
    blades.append((x, base, hgt, gr.uniform(10, 22), tuple(int(v) for v in np.clip(c, 0, 255)), gr.uniform(0, 6.28)))
blades.sort(key=lambda b: b[1])

particles = [dict(x=gr.uniform(0, W), y=gr.uniform(500, H), s=gr.uniform(3, 7), sp=gr.uniform(30, 70),
                  ph=gr.uniform(0, 6.28), kind=gr.choice(['seed', 'petal', 'petal'])) for _ in range(45)]
birds = [dict(x0=-80 - i * 70, y=380 + i * 35 + gr.uniform(-15, 15), ph=i * .9) for i in range(5)]

yy, xx = np.mgrid[0:H, 0:W]
vign = 1 - 0.28 * (((xx - W / 2) / (W * .75)) ** 2 + ((yy - H / 2) / (H * .75)) ** 2)
vign = np.clip(vign, 0.6, 1)[..., None].astype(np.float32)

def crop(layer, factor, p):
    off = int(MARGIN - PAN * factor * (p - .5) * 2 * .5)
    return layer.crop((off, 0, off + W, H))

ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                       '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
                       '-pix_fmt', 'yuv420p', '-movflags', '+faststart', OUT], stdin=subprocess.PIPE)
sky_img = Image.fromarray(sky.astype(np.uint8)).convert('RGBA')
for f in range(N):
    t = f / FPS; p = f / (TOTAL - 1)
    frame = sky_img.copy()
    # sun rays
    rays = Image.new('RGBA', (W, H)); rd = ImageDraw.Draw(rays)
    sx, sy = W * .70, H * .12
    for k in range(9):
        a = -2.0 + k * .32 + .03 * math.sin(t * .5 + k)
        rd.polygon([(sx, sy), (sx + math.cos(a) * 2400, sy + math.sin(a) * 2400),
                    (sx + math.cos(a + .07) * 2400, sy + math.sin(a + .07) * 2400)], fill=(255, 250, 220, 14))
    frame.alpha_composite(rays.filter(ImageFilter.GaussianBlur(12)))
    for img, x0, y0, spd in clouds:
        x = (x0 + spd * t - PAN * .15 * p + 900) % (W + 1400) - 900
        frame.alpha_composite(img, (int(x), int(y0 + 6 * math.sin(t * .3 + x0))))
    # birds
    bd = ImageDraw.Draw(frame)
    for b in birds:
        bx = b['x0'] + t * 95; by = b['y'] + 10 * math.sin(t * .8 + b['ph'])
        flap = 10 * math.sin(t * 9 + b['ph'])
        bd.line([(bx - 16, by - flap), (bx, by), (bx + 16, by - flap)], fill=(60, 70, 90, 255), width=3)
    frame.alpha_composite(crop(mount, .1, p))
    frame.alpha_composite(crop(far, .3, p))
    frame.alpha_composite(crop(mid, .55, p))
    off = int(MARGIN - PAN * .55 * (p - .5))
    # chimney smoke
    sm = Image.new('RGBA', (W, H)); smd = ImageDraw.Draw(sm)
    cx0, cy0 = house_x - off + 40, house_y - 195
    for k in range(7):
        a = ((t * .45 + k / 7) % 1)
        r = 10 + a * 38
        smd.ellipse([cx0 + a * 90 + 12 * math.sin(a * 6 + t) - r, cy0 - a * 300 - r,
                     cx0 + a * 90 + 12 * math.sin(a * 6 + t) + r, cy0 - a * 300 + r], fill=(250, 250, 255, int(150 * (1 - a))))
    frame.alpha_composite(sm.filter(ImageFilter.GaussianBlur(5)))
    # swaying canopy
    sway = 7 * math.sin(t * 1.3) + 3 * math.sin(t * 2.9)
    frame.alpha_composite(canopy.rotate(sway * .4, resample=Image.BICUBIC, center=(280, 500)),
                          (int(tree_x - off - 300 + sway), int(tree_y - 230 - 430)))
    # foreground grass (2x supersampled strip)
    GH = 520; S = 2
    g = Image.new('RGBA', (W * S, GH * S)); gd = ImageDraw.Draw(g)
    gd.rectangle([0, int(180 * S), W * S, GH * S], fill=(56, 120, 46, 255))
    goff = MARGIN - PAN * 1.0 * (p - .5)
    for x, base, hgt, wid, col, ph in blades:
        bx = x - goff
        if bx < -60 or bx > W + 60: continue
        gust = .5 + .5 * math.sin(t * 1.6 - bx * .006)
        bend = (18 + 55 * gust ** 2) + 8 * math.sin(t * 3 + ph)
        by = base - (H - GH)
        pts = []
        for s in range(7):
            u = s / 6
            px = bx + bend * u * u
            py = by - hgt * u
            w_ = wid * (1 - u) * .5
            pts.append((px - w_, py, px + w_))
        poly = [(a * S, py * S) for a, py, _ in pts] + [(b * S, py * S) for _, py, b in reversed(pts)]
        gd.polygon(poly, fill=col + (255,))
    g = g.resize((W, GH), Image.LANCZOS)
    frame.alpha_composite(g, (0, H - GH))
    # floating petals / seeds
    pd = ImageDraw.Draw(frame)
    for q in particles:
        px = (q['x'] + t * q['sp'] + 25 * math.sin(t * 1.1 + q['ph'])) % (W + 40) - 20
        py = q['y'] - t * 18 + 20 * math.sin(t * .9 + q['ph'] * 2)
        py = (py - 400) % (H - 400) + 400
        s = q['s']
        if q['kind'] == 'petal':
            pd.ellipse([px - s, py - s * .55, px + s, py + s * .55], fill=(255, 205, 220, 230))
        else:
            pd.ellipse([px - s * .6, py - s * .6, px + s * .6, py + s * .6], fill=(255, 255, 245, 220))
    arr = np.asarray(frame.convert('RGB'), dtype=np.float32)
    # warm grade + vignette + grain
    arr = arr * np.array([1.03, 1.0, .96], np.float32)
    arr *= vign
    arr += np.random.normal(0, 3.2, (H, W, 1)).astype(np.float32)
    ff.stdin.write(np.clip(arr, 0, 255).astype(np.uint8).tobytes())
    if f % 30 == 0: print(f'frame {f}/{N}', flush=True)
ff.stdin.close(); ff.wait()
print('done ->', OUT)
