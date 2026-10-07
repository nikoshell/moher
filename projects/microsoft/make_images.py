#!/usr/bin/env python3
"""Microsoft showcase, 12 scenes from DOS to XP, 1-bit 512x342.

Each Scene has a `box`: the region that must fill the whole viewport (camera auto-fitted).
"""
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from retro import CH, CW, H, W, Scene, console, dither, page, pattern, text, write_project  # noqa: E402

rng = random.Random(1995)
ALT = [0.40, 1.26, 1.06]


def pointer(d, x, y):
    d.polygon([(x, y), (x, y + 16), (x + 4, y + 12), (x + 8, y + 19), (x + 10, y + 18),
               (x + 6, y + 11), (x + 11, y + 11)], fill=1, outline=0)


def bevel(d, x0, y0, x1, y1, down=False):
    """Win95 3D button: light top-left, dark bottom-right."""
    d.rectangle([x0, y0, x1, y1], fill=1, outline=0)
    a, b = (0, 1) if down else (1, 0)
    d.line([x0 + 1, y1 - 1, x1 - 1, y1 - 1], fill=b)
    d.line([x1 - 1, y0 + 1, x1 - 1, y1 - 1], fill=b)
    if not down:
        d.line([x0 + 2, y1 - 2, x1 - 2, y1 - 2], fill=0)
        d.line([x1 - 2, y0 + 2, x1 - 2, y1 - 2], fill=0)


def win31(im, x0, y0, x1, y1, title, menu=(), active=True):
    """Windows 3.x window. Returns client box."""
    d = ImageDraw.Draw(im)
    d.rectangle([x0, y0, x1, y1], fill=1, outline=0)
    d.rectangle([x0 + 3, y0 + 3, x1 - 3, y1 - 3], outline=0)
    d.rectangle([x0 + 3, y0 + 3, x1 - 3, y0 + 21], fill=0 if active else 1, outline=0)
    d.rectangle([x0 + 3, y0 + 3, x0 + 21, y0 + 21], fill=1, outline=0)
    d.rectangle([x0 + 7, y0 + 11, x0 + 17, y0 + 13], fill=0)
    for k, up in enumerate((False, True)):
        bx = x1 - 39 + k * 18
        d.rectangle([bx, y0 + 3, bx + 18, y0 + 21], fill=1, outline=0)
        cx, cy = bx + 9, y0 + 12
        d.polygon([(cx - 5, cy + 3), (cx + 5, cy + 3), (cx, cy - 3)] if up
                  else [(cx - 5, cy - 3), (cx + 5, cy - 3), (cx, cy + 3)], fill=0)
    text(im, (x0 + x1) // 2 - len(title) * CW // 2, y0 + 4, title, invert=active)
    top = y0 + 22
    if menu:
        x = x0 + 8
        for m in menu:
            text(im, x, top + 1, m)
            x += (len(m) + 2) * CW
        d.line([x0 + 3, top + 18, x1 - 3, top + 18], fill=0)
        top += 19
    return x0 + 4, top, x1 - 4, y1 - 4


def win95(im, x0, y0, x1, y1, title, menu=()):
    """Windows 95 window: bevelled frame, dark title bar, _ [] X. Returns client box."""
    d = ImageDraw.Draw(im)
    bevel(d, x0, y0, x1, y1)
    d.rectangle([x0 + 3, y0 + 3, x1 - 3, y0 + 20], fill=0)
    text(im, x0 + 8, y0 + 3, title, invert=True)
    for k, g in enumerate("_OX"):
        bx = x1 - 3 - (3 - k) * 18 + (2 if k == 2 else 0)
        bevel(d, bx, y0 + 5, bx + 15, y0 + 18)
        text(im, bx + 4, y0 + 3, g)
    top = y0 + 22
    if menu:
        x = x0 + 8
        for m in menu:
            text(im, x, top, m)
            x += (len(m) + 2) * CW
        top += 18
    return x0 + 4, top, x1 - 4, y1 - 4


def taskbar(im, start_down=False, clock="4:20 PM", buttons=()):
    d = ImageDraw.Draw(im)
    d.rectangle([0, H - 24, W - 1, H - 1], fill=1)
    d.line([0, H - 24, W - 1, H - 24], fill=0)
    bevel(d, 2, H - 21, 62, H - 3, down=start_down)
    flag(d, 8, H - 18, 12)
    text(im, 24, H - 20, "Start")
    for k, b in enumerate(buttons):
        bevel(d, 68 + k * 120, H - 21, 184 + k * 120, H - 3, down=k == 0)
        text(im, 74 + k * 120, H - 20, b[:13])
    bevel(d, W - 72, H - 21, W - 3, H - 3, down=True)
    text(im, W - 68, H - 20, clock)


def flag(d, x, y, s):
    """Simplified four-pane waving window flag (1-bit)."""
    for k, (dx, dy) in enumerate(((0, 0), (1, 0), (0, 1), (1, 1))):
        px, py = x + dx * (s // 2 + 1), y + dy * (s // 2 + 1)
        if k in (0, 3):
            d.rectangle([px, py, px + s // 2 - 1, py + s // 2 - 1], fill=0)
        else:
            d.rectangle([px, py, px + s // 2 - 1, py + s // 2 - 1], outline=0)


# ------------------------------------------------------------------ 1 MS-DOS
def dos():
    lines = ["Starting MS-DOS...", "", "HIMEM is testing extended memory...done.", "",
             "C:\\>ver", "", "MS-DOS Version 6.22", "", "C:\\>"]
    out = [console(lines[:k]) for k in range(1, len(lines) + 1)]
    listing = [" Volume in drive C is MS-DOS_6", " Directory of C:\\", "",
               "COMMAND  COM     54645 05-31-94   6:22a", "WINDOWS      <DIR>     01-01-95  12:00a",
               "DOS          <DIR>     01-01-95  12:00a", "GAMES        <DIR>     01-01-95  12:00a",
               "AUTOEXEC BAT       142 01-01-95  12:00a", "CONFIG   SYS        97 01-01-95  12:00a",
               "        6 file(s)      54884 bytes", "                 209715200 bytes free", "", "C:\\>"]
    for cmd, after in (("dir", listing), ("win", [])):
        for i in range(len(cmd) + 3):
            s = "C:\\>" + cmd[:i]
            out.append(console(lines[:-1] + [s], cursor=(len(s), len(lines) - 1)))
        lines = lines[:-1] + ["C:\\>" + cmd] + after
        for k in range(len(lines) - len(after), len(lines) + 1, 2):
            out.append(console(lines[:k]))
    return out


# ------------------------------------------------------------------ 2 Windows 3.1 splash
def splash31():
    out = []
    for i in range(30):
        im = page()
        d = ImageDraw.Draw(im)
        wave = i / 30 * 2 * math.pi
        for gx in range(4):                         # waving flag made of 4 panes
            for gy in range(2):
                pts = []
                for cx, cy in ((0, 0), (1, 0), (1, 1), (0, 1)):
                    u, v = (gx + cx) / 4, (gy + cy) / 2
                    pts.append((150 + u * 110 + 0 * v, 60 + v * 100 + 10 * math.sin(u * 6 + wave)))
                if gx % 2 == gy % 2:
                    d.polygon(pts, fill=0)
                else:
                    d.polygon(pts, outline=0)
                    for t in range(0, 10, 3):
                        a, b = pts[0], pts[2]
                        d.point((a[0] + (b[0] - a[0]) * t / 10, a[1] + (b[1] - a[1]) * t / 10), fill=0)
        for k in range(6):                          # trailing pixel squares
            d.rectangle([100 - k * 14, 80 + k * 9, 108 - k * 14, 88 + k * 9], fill=0)
        text(im, 280, 80, "Microsoft", scale=1)
        text(im, 280, 98, "Windows", scale=3)
        text(im, 440, 140, "3.1", scale=2)
        text(im, 120, 230, "Copyright (c) 1985-1992 Microsoft Corp.")
        out.append(im)
    return out


# ------------------------------------------------------------------ 3 Program Manager
ICONS = ["File Man", "Control", "Print Man", "Clipboard", "MS-DOS", "Notepad", "Write", "Paint",
         "Clock", "Calc"]


def icon31(d, im, x, y, label, k, sel=False):
    d.rectangle([x + 12, y, x + 44, y + 28], fill=1, outline=0)
    if k % 3 == 0:
        d.rectangle([x + 16, y + 4, x + 40, y + 12], fill=0)
    elif k % 3 == 1:
        d.ellipse([x + 18, y + 4, x + 38, y + 24], outline=0)
    else:
        for yy in range(y + 6, y + 26, 4):
            d.line([x + 16, yy, x + 40, yy], fill=0)
    if sel:
        d.rectangle([x - 2, y + 30, x + 58, y + 47], fill=0)
    text(im, x + 28 - len(label) * 4, y + 31, label, invert=sel)


def progman():
    out = []
    for i in range(40):
        im = pattern("light")
        d = ImageDraw.Draw(im)
        cx0, cy0, cx1, cy1 = win31(im, 8, 6, 504, 336, "Program Manager", ("File", "Options", "Window", "Help"))
        gx0, gy0, gx1, gy1 = win31(im, cx0 + 8, cy0 + 6, cx1 - 8, cy1 - 44, "Accessories", active=i > 8)
        for k, name in enumerate(ICONS):
            icon31(d, im, gx0 + 14 + (k % 5) * 92, gy0 + 10 + (k // 5) * 80, name, k, sel=i > 28 and k == 5)
        for k, g in enumerate(("Main", "Games", "StartUp")):
            gx = cx0 + 20 + k * 90
            d.rectangle([gx, cy1 - 38, gx + 30, cy1 - 18], fill=1, outline=0)
            text(im, gx - 2, cy1 - 17, g)
        t = min(i / 28, 1)
        pointer(d, 420 - (420 - (gx0 + 40)) * t, 300 - (300 - (gy0 + 110)) * t)
        out.append(im)
    return out


# ------------------------------------------------------------------ 4 Minesweeper
def minesweeper():
    n, size = 9, 24
    mines = set(rng.sample([(x, y) for x in range(n) for y in range(n) if (x, y) != (4, 4)], 10))
    count = {(x, y): sum((x + dx, y + dy) in mines for dx in (-1, 0, 1) for dy in (-1, 0, 1))
             for x in range(n) for y in range(n)}
    order, seen, queue = [], set(), [(4, 4)]
    while queue:
        c = queue.pop(0)
        if c in seen or c in mines:
            continue
        seen.add(c)
        order.append(c)
        if count[c] == 0:
            queue += [(c[0] + dx, c[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                      if 0 <= c[0] + dx < n and 0 <= c[1] + dy < n]
    rest = [c for c in count if c not in mines and c not in seen]
    rng.shuffle(rest)
    order += rest
    steps, out = 34, []
    for i in range(steps + 12):
        shown = set(order[:int(len(order) * min(i, steps) / steps)])
        won = i > steps
        im = pattern("light")
        d = ImageDraw.Draw(im)
        x0, y0, x1, y1 = win31(im, 130, 6, 382, 336, "Minesweeper", ("Game", "Help"))
        bx, by = x0 + (x1 - x0 - n * size) // 2, y0 + 44
        d.rectangle([x0 + 8, y0 + 6, x0 + 38, y0 + 26], fill=0)
        text(im, x0 + 11, y0 + 8, "000" if won else "010", invert=True)
        d.rectangle([x1 - 38, y0 + 6, x1 - 8, y0 + 26], fill=0)
        text(im, x1 - 35, y0 + 8, f"{min(i, 999):03d}", invert=True)
        fx = (x0 + x1) // 2
        bevel(d, fx - 12, y0 + 4, fx + 12, y0 + 28)
        d.ellipse([fx - 8, y0 + 8, fx + 8, y0 + 24], outline=0)
        if won:                                           # sunglasses
            d.rectangle([fx - 7, y0 + 12, fx + 7, y0 + 15], fill=0)
        else:
            d.point([(fx - 3, y0 + 13), (fx + 3, y0 + 13)], fill=0)
        d.arc([fx - 5, y0 + 13, fx + 5, y0 + 21], 20, 160, fill=0)
        for x in range(n):
            for y in range(n):
                cx, cy, c = bx + x * size, by + y * size, (x, y)
                if c in shown:
                    d.rectangle([cx, cy, cx + size - 1, cy + size - 1], outline=0)
                    if count[c]:
                        text(im, cx + 8, cy + 4, str(count[c]))
                else:
                    bevel(d, cx, cy, cx + size - 1, cy + size - 1)
                    if won and c in mines:
                        d.line([cx + 10, cy + 5, cx + 10, cy + 18], fill=0)
                        d.polygon([(cx + 11, cy + 5), (cx + 18, cy + 8), (cx + 11, cy + 11)], fill=0)
        out.append(im)
    return out


# ------------------------------------------------------------------ 5 Solitaire win cascade
def card(d, im, x, y, rank, suit):
    d.rounded_rectangle([x, y, x + 34, y + 48], 3, fill=1, outline=0)
    text(im, int(x) + 3, int(y) + 2, rank)
    sx, sy = x + 17, y + 30
    if suit == 0:   # spade/club-ish
        d.ellipse([sx - 6, sy - 8, sx + 6, sy + 4], fill=0)
        d.polygon([(sx, sy), (sx - 4, sy + 8), (sx + 4, sy + 8)], fill=0)
    else:           # heart/diamond-ish
        d.polygon([(sx, sy - 9), (sx + 8, sy), (sx, sy + 9), (sx - 8, sy)], fill=0 if suit == 2 else 1, outline=0)


def solitaire():
    out = []
    ranks = "KQJT98765432A"
    trails = Image.new("1", (W, H), 1)
    td = ImageDraw.Draw(trails)
    bouncers = []
    for i in range(60):
        if i % 4 == 0 and len(bouncers) < 14:
            k = len(bouncers)
            bouncers.append([300 + (k % 4) * 46, 30.0, rng.choice((-1, 1)) * rng.uniform(3, 6), 0.0,
                             ranks[k % 13], k % 3])
        for b in bouncers:
            b[3] += 1.6
            b[0] += b[2]
            b[1] += b[3]
            if b[1] > H - 70:
                b[1], b[3] = H - 70, -b[3] * 0.75
            if 0 < b[0] < W - 34:
                card(td, trails, b[0], b[1], b[4], b[5])     # cards leave trails, like 1990
        im = pattern("dots")
        im.paste(trails, (0, 0), Image.eval(trails, lambda p: 255 - p))
        d = ImageDraw.Draw(im)
        x0, y0, x1, y1 = win31(im, 0, 0, W - 1, 30, "Solitaire", ())
        for k in range(4):                                         # foundations, full
            card(d, im, 300 + k * 46, 34, "K", k % 3)
        out.append(im)
    return out


# ------------------------------------------------------------------ 6 Paint
def paint():
    strokes = []
    for t in np.linspace(0, 1, 30):          # house + sun drawn stroke by stroke
        strokes.append(t)
    out = []
    for i in range(44):
        im = pattern("light")
        d = ImageDraw.Draw(im)
        x0, y0, x1, y1 = win95(im, 4, 4, 508, 336, "untitled - Paint", ("File", "Edit", "View", "Image", "Help"))
        for k in range(16):                                         # tool box
            bevel(d, x0 + 2 + (k % 2) * 22, y0 + 4 + (k // 2) * 22, x0 + 22 + (k % 2) * 22, y0 + 24 + (k // 2) * 22,
                  down=k == 6)
        d.rectangle([x0 + 50, y0 + 2, x1 - 2, y1 - 30], fill=1, outline=0)   # canvas
        for k in range(14):                                         # palette
            px = x0 + 50 + k * 16
            d.rectangle([px, y1 - 26, px + 14, y1 - 12], fill=0 if k % 2 else 1, outline=0)
        cx, cy, prog = x0 + 140, y0 + 40, min(1, i / 34)
        segs = [((cx, cy + 120), (cx + 160, cy + 120)), ((cx + 160, cy + 120), (cx + 160, cy + 50)),
                ((cx + 160, cy + 50), (cx + 80, cy)), ((cx + 80, cy), (cx, cy + 50)),
                ((cx, cy + 50), (cx, cy + 120)), ((cx + 60, cy + 120), (cx + 60, cy + 80)),
                ((cx + 60, cy + 80), (cx + 95, cy + 80)), ((cx + 95, cy + 80), (cx + 95, cy + 120))]
        n = prog * len(segs)
        last = None
        for k, (a, b) in enumerate(segs):
            if k < int(n):
                d.line([a, b], fill=0, width=3)
            elif k == int(n) and k < len(segs):
                f = n - k
                last = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
                d.line([a, last], fill=0, width=3)
        if i > 30:                                                  # sun with rays
            sx, sy = x1 - 70, y0 + 40
            d.ellipse([sx - 18, sy - 18, sx + 18, sy + 18], fill=0)
            for r in range(8):
                a = r * math.pi / 4
                d.line([sx + 24 * math.cos(a), sy + 24 * math.sin(a), sx + 34 * math.cos(a), sy + 34 * math.sin(a)],
                       fill=0, width=2)
        pointer(d, *(last or (x1 - 60, y0 + 70)))
        out.append(im)
    return out


# ------------------------------------------------------------------ 7 Windows 95 desktop + Start menu
DESK = ["My Computer", "Network", "Recycle Bin", "Inbox", "Internet"]


def desk95(im, d):
    for k, name in enumerate(DESK):
        x, y = 14, 10 + k * 56
        d.rectangle([x + 10, y, x + 42, y + 26], fill=1, outline=0)
        d.rectangle([x + 14, y + 4, x + 38, y + 18], fill=0)
        text(im, x + 26 - len(name) * 4, y + 30, name[:8], invert=True)


def start95():
    items = ["Programs      >", "Documents     >", "Settings      >", "Find          >", "Help",
             "Run...", "-", "Shut Down..."]
    out = []
    for i in range(40):
        im = pattern("grey")
        d = ImageDraw.Draw(im)
        desk95(im, d)
        opened = i > 8
        taskbar(im, start_down=opened, buttons=() if i < 4 else ("My Computer",))
        if opened:
            n = min(len(items), (i - 8))
            mh = len(items) * 22 + 6
            mx0, my0 = 2, H - 24 - mh
            bevel(d, mx0, my0, mx0 + 190, H - 24)
            d.rectangle([mx0 + 3, my0 + 3, mx0 + 24, H - 27], fill=0)                 # side banner
            for k, ch in enumerate("Windows95"):
                text(im, mx0 + 10, H - 46 - k * 16, ch, invert=True)
            sel = min(n - 1, 0 + (i - 8) // 6) if i > 14 else -1
            for k, it in enumerate(items[:n]):
                y = my0 + 4 + k * 22
                if it == "-":
                    d.line([mx0 + 30, y + 10, mx0 + 184, y + 10], fill=0)
                    continue
                if k == sel:
                    d.rectangle([mx0 + 26, y, mx0 + 186, y + 20], fill=0)
                d.rectangle([mx0 + 32, y + 3, mx0 + 46, y + 17], fill=1 if k == sel else 0, outline=0)
                text(im, mx0 + 54, y + 2, it, invert=k == sel)
        pointer(d, 30 + (i > 8) * 40, H - 14 - min(i, 20) * 6 * (i > 8))
        out.append(im)
    return out


# ------------------------------------------------------------------ 8 3D Pipes screensaver
def pipes3d():
    canvas = Image.new("1", (W, H), 0)                   # black screen, pipes in white-with-shading
    d = ImageDraw.Draw(canvas)
    dirs = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    pipes = [[rng.randrange(2, 30) * 16, rng.randrange(2, 20) * 16, rng.randrange(4)] for _ in range(3)]
    out = []
    for i in range(50):
        for p in pipes:
            x, y, k = p
            if rng.random() < 0.25:
                k = (k + rng.choice((1, 3))) % 4
                d.ellipse([x - 10, y - 10, x + 10, y + 10], fill=1, outline=0)        # ball joint
                d.ellipse([x - 4, y - 7, x + 2, y - 2], fill=0)
            nx, ny = x + dirs[k][0] * 24, y + dirs[k][1] * 24
            if not (8 < nx < W - 8 and 8 < ny < H - 8):
                k = (k + 2) % 4
                nx, ny = x + dirs[k][0] * 24, y + dirs[k][1] * 24
            if dirs[k][0]:
                d.rectangle([min(x, nx), y - 7, max(x, nx), y + 7], fill=1, outline=0)
                d.line([min(x, nx), y - 3, max(x, nx), y - 3], fill=0)       # cylinder highlight line
                d.line([min(x, nx), y + 4, max(x, nx), y + 4], fill=0)
            else:
                d.rectangle([x - 7, min(y, ny), x + 7, max(y, ny)], fill=1, outline=0)
                d.line([x - 3, min(y, ny), x - 3, max(y, ny)], fill=0)
                d.line([x + 4, min(y, ny), x + 4, max(y, ny)], fill=0)
            p[:] = [nx, ny, k]
        out.append(canvas.copy())
    return out


# ------------------------------------------------------------------ 9 Clippy in Word
def clippy():
    letter = ["Dear Sir or Madam,", "", "I am writing to tell you about the", "new computer at the office.",
              "It is very fast and has a mouse."]
    flat = "\n".join(letter)
    out = []
    for i in range(52):
        im = pattern("light")
        d = ImageDraw.Draw(im)
        x0, y0, x1, y1 = win95(im, 2, 2, 510, 340, "Document1 - Microsoft Word",
                               ("File", "Edit", "View", "Insert", "Format", "Tools"))
        for k in range(14):                                          # toolbar
            bevel(d, x0 + 2 + k * 22, y0 + 2, x0 + 20 + k * 22, y0 + 20)
        d.rectangle([x0 + 20, y0 + 26, x1 - 20, y1 - 4], fill=1, outline=0)   # page
        k = min(len(flat), i * 3)
        for r, line in enumerate(flat[:k].split("\n")):
            text(im, x0 + 34, y0 + 36 + r * CH, line)
        if i > 20:                                                   # Clippy + balloon
            cx, cy = x1 - 70, y1 - 70
            d.arc([cx - 14, cy - 40, cx + 14, cy + 30], 180, 360, fill=0, width=3)
            d.arc([cx - 8, cy - 30, cx + 8, cy + 25], 0, 180, fill=0, width=3)
            d.line([cx - 14, cy - 5, cx - 14, cy + 20], fill=0, width=3)
            d.line([cx + 14, cy - 5, cx + 14, cy - 20], fill=0, width=3)
            for ex in (-8, 6):
                d.ellipse([cx + ex - 5, cy - 28, cx + ex + 5, cy - 16], fill=1, outline=0)
                d.ellipse([cx + ex - 2 + (i // 6 % 2), cy - 24, cx + ex + 2 + (i // 6 % 2), cy - 19], fill=0)
            bx0, by0, bx1, by1 = x1 - 300, y1 - 190, x1 - 30, y1 - 110
            d.rounded_rectangle([bx0, by0, bx1, by1], 8, fill=1, outline=0, width=2)
            d.polygon([(bx1 - 60, by1), (bx1 - 40, by1), (cx, cy - 42)], fill=1, outline=0)
            d.line([bx1 - 59, by1, bx1 - 41, by1], fill=1, width=2)
            for r, s in enumerate(["It looks like you're", "writing a letter.", "", "Would you like help?"]):
                text(im, bx0 + 10, by0 + 6 + r * 16, s)
        out.append(im)
    return out


# ------------------------------------------------------------------ 10 Windows XP Bliss + Start
def bliss():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    hill = H * 0.55 + 40 * np.sin(xx / W * math.pi * 1.2 + 0.3) - 30 * (xx / W)
    sky = 0.75 + 0.25 * (yy / H)
    g = np.where(yy > hill, 0.28 + 0.25 * np.clip((yy - hill) / 140, 0, 1), sky)
    for cx, cy, r in ((120, 70, 40), (170, 60, 30), (380, 90, 46), (430, 80, 34)):
        g = np.where(((xx - cx) / (r * 1.6)) ** 2 + ((yy - cy) / r) ** 2 < 1, 0.97, g)
    return g


def xp():
    base = bliss()
    items = ["Internet", "E-mail", "My Documents", "My Pictures", "My Music", "My Computer",
             "Control Panel", "Help and Support", "Search", "Run..."]
    out = []
    for i in range(44):
        im = dither(base)
        d = ImageDraw.Draw(im)
        for k, name in enumerate(("My Computer", "Recycle Bin")):
            x, y = 16, 14 + k * 60
            d.rectangle([x + 10, y, x + 42, y + 28], fill=1, outline=0)
            d.rectangle([x + 13, y + 3, x + 39, y + 18], fill=0)
            d.rectangle([x + 2, y + 31, x + 56, y + 47], fill=0)
            text(im, x + 28 - len(name[:7]) * 4, y + 31, name[:7], invert=True)
        d.rectangle([0, H - 26, W - 1, H - 1], fill=0)                               # taskbar
        d.rounded_rectangle([0, H - 26, 84, H - 1], 10, fill=1, outline=0)           # green start
        flag(d, 8, H - 20, 14)
        text(im, 28, H - 21, "start")
        text(im, W - 64, H - 21, "4:20 PM", invert=True)
        if i > 10:
            n = min(len(items), i - 10)
            mx0, my0, mx1 = 0, H - 26 - 240, 300
            d.rectangle([mx0, my0, mx1, H - 27], fill=1, outline=0)
            d.rectangle([mx0, my0, mx1, my0 + 36], fill=0)
            d.rectangle([mx0 + 8, my0 + 4, mx0 + 36, my0 + 32], fill=1)
            text(im, mx0 + 46, my0 + 10, "Administrator", invert=True)
            d.line([150, my0 + 36, 150, H - 50], fill=0)
            for k, it in enumerate(items[:n]):
                col, row = (0, k) if k < 5 else (1, k - 5)
                tx, ty = mx0 + 10 + col * 150, my0 + 46 + row * 30
                d.rectangle([tx, ty, tx + 16, ty + 16], fill=0 if col == 0 else 1, outline=0)
                text(im, tx + 22, ty, it[:15])
            d.rectangle([mx0, H - 50, mx1, H - 27], fill=0)
            text(im, mx1 - 200, H - 46, "Log Off   Turn Off", invert=True)
        out.append(im)
    return out


# ------------------------------------------------------------------ 11 Windows XP balloon + Solitaire? -> Notepad
def notepad():
    msg = ["Hello, world!", "", "Saved to C:\\WINDOWS\\HELLO.TXT"]
    flat, out = "\n".join(msg), []
    for k in range(len(flat) + 10):
        im = pattern("light")
        d = ImageDraw.Draw(im)
        x0, y0, x1, y1 = win31(im, 20, 20, 492, 320, "Notepad - HELLO.TXT", ("File", "Edit", "Search", "Help"))
        typed = flat[:k].split("\n")
        for r, line in enumerate(typed):
            text(im, x0 + 6, y0 + 6 + r * CH, line, scale=2 if r == 0 else 1)
        if k % 4 < 2 or k < len(flat):
            cx = x0 + 6 + len(typed[-1]) * CW * (2 if len(typed) == 1 else 1)
            cy = y0 + 6 + (len(typed) - 1) * CH
            d.line([cx, cy, cx, cy + (31 if len(typed) == 1 else 15)], fill=0, width=2)
        out.append(im)
    return out


# ------------------------------------------------------------------ 12 Blue screen
def bluescreen():
    body = ["", "", " " * 27 + " Windows ", "",
            "  A fatal exception 0E has occurred at 0028:C0011E36 in VXD",
            "  VMM(01) + 00010E36. The current application will be",
            "  terminated.", "",
            "  *  Press any key to terminate the current application.",
            "  *  Press CTRL+ALT+DEL again to restart your computer.",
            "     You will lose any unsaved information in all",
            "     applications.", "",
            " " * 19 + "Press any key to continue _"]
    out = []
    for i in range(30):
        im = page()
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W - 1, H - 1], fill=0)
        for r, s in enumerate(body[:min(len(body), 2 + i)]):
            if r == 2:
                d.rectangle([27 * CW, r * CH, 36 * CW - 1, r * CH + CH - 1], fill=1)
                text(im, 0, r * CH, s)
            else:
                text(im, 0, r * CH, s if not (r == len(body) - 1 and i % 4 >= 2) else s[:-1], invert=True)
        out.append(im)
    return out


if __name__ == "__main__":
    write_project(HERE, [
        Scene("MS-DOS 6.22", dos(), seconds=9, box=(0, 0, 330, 336), pan=0.03),
        Scene("Windows 3.1 splash", splash31(), seconds=6, box=(60, 40, 500, 260), pan=0.03, cam_dir=ALT),
        Scene("Program Manager", progman(), seconds=8, box=(0, 0, W, H), pan=0.03),
        Scene("Minesweeper", minesweeper(), seconds=9, box=(128, 6, 384, 336), pan=0.02, cam_dir=ALT),
        Scene("Solitaire win", solitaire(), seconds=9, box=(0, 0, W, H), pan=0.03),
        Scene("Paint", paint(), seconds=8, box=(0, 0, W, H), pan=0.03, cam_dir=ALT),
        Scene("Windows 95 Start", start95(), seconds=8, box=(0, 60, 330, H), pan=0.03),
        Scene("3D Pipes", pipes3d(), seconds=8, box=(0, 0, W, H), pan=0.03, cam_dir=ALT),
        Scene("Clippy", clippy(), seconds=9, box=(150, 120, 510, 340), pan=0.03),
        Scene("Windows XP", xp(), seconds=8, box=(0, 60, 330, H), pan=0.03, cam_dir=ALT),
        Scene("Notepad", notepad(), seconds=6, box=(20, 20, 330, 200), pan=0.03),
        Scene("Blue screen", bluescreen(), seconds=7, box=(0, 0, W, 240), pan=0.03, cam_dir=ALT),
    ])
