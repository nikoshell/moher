"""Shared helpers for generated 1-bit projects (512x342, black = ink).

    from retro import Scene, console, write_project   # in projects/NAME/make_images.py
    write_project(HERE, [Scene("boot", frames, seconds=8)])
"""
import glob
import os
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import mac

W, H = 512, 342
CW, CH = 8, 16                      # Unifont cell
COLS, ROWS = W // CW, H // CH       # 64 x 21 text console
_FONT = None


def font():
    global _FONT
    if _FONT is None:
        path = os.environ.get("UNIFONT") or next(
            iter(sorted(glob.glob("/nix/store/*-unifont-*/share/fonts/unifont.bdf"))), None)
        if not path:
            raise SystemExit("unifont.bdf not found: set UNIFONT=/path/to/unifont.bdf")
        g, enc, rows = {}, None, None
        for line in open(path, encoding="latin-1"):
            if line.startswith("ENCODING"):
                enc = int(line.split()[1])
            elif line.startswith("BITMAP"):
                rows = []
            elif line.startswith("ENDCHAR"):
                w = len(rows[0]) * 4 if rows else 8
                if w == 8 and len(rows) == CH:       # half-width glyphs only
                    g[enc] = np.array([[int(r, 16) >> (7 - x) & 1 for x in range(8)] for r in rows], bool)
                rows = None
            elif rows is not None:
                rows.append(line.strip())
        _FONT = g
    return _FONT


def page(stipple=False):
    """Blank white frame, or the X11 50% grey root-window stipple."""
    a = np.zeros((H, W), bool)
    if stipple:
        a[(np.add.outer(np.arange(H), np.arange(W)) % 2) == 0] = True
    return Image.fromarray(~a).convert("1")


def text(im, x, y, s, invert=False, scale=1):
    """Draw s with Unifont at pixel (x, y); scale>1 for big text."""
    f, a = font(), np.asarray(im).copy()          # True = white
    for i, ch in enumerate(s):
        g = f.get(ord(ch), f[ord("?")])
        if scale > 1:
            g = g.repeat(scale, 0).repeat(scale, 1)
        x0, gh, gw = x + i * CW * scale, g.shape[0], g.shape[1]
        if x0 >= im.size[0] or y >= im.size[1] or x0 + gw <= 0:
            continue
        cell = a[y:y + gh, max(x0, 0):x0 + gw]
        gg = g[:cell.shape[0], max(0, -x0):max(0, -x0) + cell.shape[1]]
        cell[:] = gg if invert else ~gg
    im.paste(Image.fromarray(a).convert("1"))
    return im


def console(lines, cursor=None, invert_rows=(), size=(W, H)):
    """Text screen (64x21 at full size) from strings; cursor=(col, row) draws an underline."""
    im = Image.new("1", size, 1)                  # text is the ink (dots); bg is paper
    d = ImageDraw.Draw(im)
    cols, rows = size[0] // CW, size[1] // CH
    for r, s in enumerate(lines[-rows:]):
        if r in invert_rows:                      # highlighted row: black bar, text as gaps
            d.rectangle([0, r * CH, size[0] - 1, r * CH + CH - 1], fill=0)
        text(im, 0, r * CH, s[:cols], invert=r in invert_rows)
    if cursor:
        c, r = cursor
        ImageDraw.Draw(im).rectangle([c * CW, r * CH + 13, c * CW + 7, r * CH + 15], fill=0)
    return im


def window(im, x0, y0, x1, y1, title=""):
    """twm-style window: white body, black border, title bar. Returns content box."""
    d = ImageDraw.Draw(im)
    d.rectangle([x0, y0, x1, y1], fill=1, outline=0)
    d.rectangle([x0, y0, x1, y0 + 17], fill=0)
    for yy in range(y0 + 4, y0 + 14, 2):          # twm title stripes
        d.line([x1 - 40, yy, x1 - 6, yy], fill=1)
    d.rectangle([x0 + 3, y0 + 3, x0 + 14, y0 + 14], fill=1)       # iconify button
    d.rectangle([x0 + 6, y0 + 6, x0 + 11, y0 + 11], outline=0)
    text(im, x0 + 20, y0 + 1, title, invert=True)
    return x0 + 2, y0 + 19, x1 - 2, y1 - 2


def pattern(kind="grey", size=(W, H)):
    """Desktop fill: grey (50%), light (25%), dots (12%), diag stripes."""
    yy, xx = np.mgrid[0:size[1], 0:size[0]]
    ink = {"grey": (xx + yy) % 2 == 0, "light": (xx % 2 == 0) & (yy % 2 == 0),
           "dots": (xx % 4 == 0) & (yy % 4 == 0), "diag": (xx + yy) % 6 == 0}[kind]
    return Image.fromarray(~ink).convert("1")


def warp(src, quad, size=(W, H)):
    """Perspective-map src onto quad (4 dest corners, TL TR BR BL). Returns (image, mask)."""
    w, h = src.size
    A, b = [], []
    for (X, Y), (x, y) in zip(quad, [(0, 0), (w, 0), (w, h), (0, h)]):
        A += [[X, Y, 1, 0, 0, 0, -x * X, -x * Y], [0, 0, 0, X, Y, 1, -y * X, -y * Y]]
        b += [x, y]
    c = np.linalg.solve(np.array(A, float), np.array(b, float))
    img = src.convert("L").transform(size, Image.PERSPECTIVE, tuple(c), Image.NEAREST, fillcolor=255)
    mask = Image.new("1", size, 0)
    ImageDraw.Draw(mask).polygon([tuple(q) for q in quad], fill=1)
    return img.convert("1"), mask


def dither(gray):
    """Floyd-Steinberg float array 0..1 (1 = white) -> 1-bit image."""
    return Image.fromarray((np.clip(gray, 0, 1) * 255).astype(np.uint8)).convert("1")


# ------------------------------------------------------------------ project writer
@dataclass
class Scene:
    name: str
    frames: list
    seconds: float = 8.0           # time to play all frames
    scale: float = None            # camera zoom; None = auto-fit `box` to the viewport
    box: tuple = (0, 0, W, H)      # image px region that must fill the whole viewport
    centre: tuple = None           # image point looked at (u, v); None = centre of box
    pan: float = 0.06              # horizontal drift across the scene (fraction of width)
    cam_dir: list = field(default_factory=lambda: [-0.40, 1.26, 1.06])


def aim(u, v, scale, cam_dir, z=-1.3):
    """camera_pos whose screen centre looks at image point (u, v)."""
    def centre(px, py):
        p = {"camera_dir": np.array(cam_dir), "camera_pos": np.array([px, py, z]), "scale": scale}
        A, b = mac.plane_to_ndc(p, 1, 1)
        return (np.linalg.solve(A, -b) + 1) / 2
    c0 = centre(0, 0)
    J = np.column_stack([centre(1, 0) - c0, centre(0, 1) - c0])
    px, py = np.linalg.solve(J, np.array([u, v]) - c0)
    return [round(float(px), 4), round(float(py), 4), z]


ASPECT = 16 / 9                    # viewport the fit is computed for (1920x1080)


def view_corners(pos, scale, cam_dir, aspect=ASPECT):
    """Image-pixel corners of the visible viewport."""
    w, h = (aspect, 1.0)
    p = {"camera_dir": np.array(cam_dir), "camera_pos": np.array(pos), "scale": scale}
    A, b = mac.plane_to_ndc(p, w, h)
    out = []
    for nx, ny in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        q = np.linalg.solve(A, np.array([nx, ny]) - b)
        out.append(((q[0] + 1) / 2 * W, (q[1] + 1) / 2 * H))
    return out


def fit(sc):
    """Smallest zoom where the viewport, at both pan ends, stays inside sc.box."""
    x0, y0, x1, y1 = sc.box
    u, v = sc.centre
    lo, hi = 0.3, 40.0
    for _ in range(40):
        m = (lo + hi) / 2
        ok = all(x0 <= x <= x1 and y0 <= y <= y1
                 for du in (-sc.pan / 2, sc.pan / 2)
                 for x, y in view_corners(aim(u + du, v, m, sc.cam_dir), m, sc.cam_dir))
        lo, hi = (lo, m) if ok else (m, hi)
    return round(hi * 1.01, 3)


def write_project(here, scenes):
    """images/image-N.png strips + animation.toml: reveal, play, conceal per scene."""
    here = Path(here)
    (here / "images").mkdir(exist_ok=True)
    out = ['# Generated by make_images.py - edit that, not this file.\n',
           '[background]\ncolormap = "color.png"\nduration = 60.0\n',
           '[scenes]\ncamera_pos = [0.0, 0.0, -1.3]\ncamera_dir = [-0.40, 1.26, 1.06]\n'
           'scale = 2.5\nframe = 0\nprogress = 0.0\nprogress_angle = 0.0\n']
    reveal = 3.7
    for i, sc in enumerate(scenes, 1):
        strip = Image.new("1", (W, H * len(sc.frames)), 1)
        for k, f in enumerate(sc.frames):
            strip.paste(f.convert("1"), (0, k * H))
        strip.save(here / "images" / f"image-{i}.png")
        play0, play1 = reveal * 0.6, reveal * 0.6 + sc.seconds
        hide0, end = play1 + 0.5, play1 + 0.5 + reveal
        if sc.centre is None:
            sc.centre = ((sc.box[0] + sc.box[2]) / 2 / W, (sc.box[1] + sc.box[3]) / 2 / H)
        if sc.scale is None:
            sc.scale = fit(sc)
        u, v = sc.centre
        p0 = aim(u - sc.pan / 2, v, sc.scale, sc.cam_dir)
        p1 = aim(u + sc.pan / 2, v, sc.scale, sc.cam_dir)
        print(f"  {i:2d} {sc.name:18s} {len(sc.frames):3d} frames  scale {sc.scale}")
        out.append(f'''# {sc.name}
[[scenes.scene]]
image = "images/image-{i}.png"
frames = {len(sc.frames)}
duration = {end + 0.3:.2f}
scale = {sc.scale}
camera_dir = {sc.cam_dir}
keyframes = [
    {{ t = 0.0, frame = 0, camera_pos = {p0}, progress = -20.0, progress_angle = 0.0 }},
    {{ t = {reveal:.2f}, progress = 1.0 }},
    {{ t = {play0:.2f}, frame = 0 }},
    {{ t = {play1:.2f}, frame = {len(sc.frames) - 1} }},
    {{ t = {hide0:.2f}, progress = 1.0, progress_angle = 0.0 }},
    {{ t = {hide0:.2f}, progress = 21.0, progress_angle = 3.14159 }},
    {{ t = {end:.2f}, camera_pos = {p1}, progress = 0.0 }},
]
''')
    (here / "animation.toml").write_text("\n".join(out))
    total = sum(len(s.frames) for s in scenes)
    print(f"{here.name}: {len(scenes)} scenes, {total} frames -> images/, animation.toml")
