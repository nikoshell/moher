#!/usr/bin/env python3
"""Linux showcase, 12 scenes (r/unixporn-flavoured), 1-bit 512x342.

Each Scene has a `box`: the region that must fill the whole viewport. The camera
zoom is fitted to it automatically, so the screen is never half empty.
"""
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from retro import CH, COLS, CW, H, ROWS, W, Scene, console, pattern, text, warp, write_project  # noqa: E402

rng = random.Random(1991)
ALT = [0.40, 1.26, 1.06]
TUX = ["        #####", "       #######", "       ##O#O##", "       #VVVVV#", "     ##  VVV  ##",
       "    #          ##", "   #            ##", "   #            ###", "  QQ#           ##Q",
       "QQQQQQ#       #QQQQQQ", "QQQQQQQ#     #QQQQQQQ", "  QQQQQ#######QQQQQ"]


def typing(pre, prompt, cmd, hold=4, size=(W, H)):
    out = []
    for i in range(len(cmd) + hold):
        s = prompt + cmd[:i]
        rows = size[1] // CH
        out.append(console(pre + [s], cursor=(len(s), min(len(pre), rows - 1)), size=size))
    return out


def penguin(scale=1):
    """Small 1-bit framebuffer Tux (24x28), like the kernel boot logo."""
    a = np.ones((28, 24), bool)
    yy, xx = np.mgrid[0:28, 0:24]
    body = ((xx - 12) / 10) ** 2 + ((yy - 17) / 10) ** 2 <= 1
    head = ((xx - 12) / 7) ** 2 + ((yy - 7) / 7) ** 2 <= 1
    belly = ((xx - 12) / 6) ** 2 + ((yy - 18) / 7.5) ** 2 <= 1
    a[body | head] = False
    a[belly] = True
    a[(np.abs(xx - 9) <= 1) & (np.abs(yy - 6) <= 1)] = True
    a[(np.abs(xx - 15) <= 1) & (np.abs(yy - 6) <= 1)] = True
    a[(yy == 10) & (np.abs(xx - 12) <= 2)] = True
    a[(yy >= 26) & ((np.abs(xx - 7) <= 3) | (np.abs(xx - 17) <= 3))] = False
    return Image.fromarray(a.repeat(scale, 0).repeat(scale, 1)).convert("1")


# ------------------------------------------------------------------ 1 GRUB
def grub():
    entries = ["Arch Linux", "Advanced options for Arch Linux", "Ubuntu 8.04 LTS",
               "Windows XP Professional (on /dev/sda1)", "Memory test (memtest86+)"]
    out = []
    for i in range(30):
        sel = min(i // 5, 3) if i < 20 else 0
        lines = ["", "               GNU GRUB  version 2.06", "",
                 " +" + "-" * 60 + "+"]
        lines += [" | " + ("*" if k == sel else " ") + e.ljust(57) + "|" for k, e in enumerate(entries)]
        lines += [" |" + " " * 60 + "|"] * 7 + [" +" + "-" * 60 + "+", "",
                  "      Use the ^ and v keys to select which entry is",
                  f"      highlighted. Booting in {max(0, 5 - i // 6)}s."]
        out.append(console(lines, invert_rows=(4 + sel,)))
    return out


# ------------------------------------------------------------------ 2 kernel boot with Tux logos
def boot():
    log = ["Linux version 2.6.24 (gcc 4.2.3) #1 SMP", "CPU: Intel(R) Core(TM)2 Duo CPU",
           "Memory: 2063748k/2096128k available", "Console: colour dummy device 80x25",
           "fb0: VESA VGA frame buffer device", "ACPI: Core revision 20070126",
           "NET: Registered protocol family 2", "Freeing initrd memory: 6848k freed",
           "PCI: Using MMCONFIG for extended config space", "ata1: SATA link up 3.0 Gbps",
           "sd 0:0:0:0: [sda] 312581808 512-byte hardware sectors", " sda: sda1 sda2 sda3 < sda5 >",
           "EXT3-fs: mounted filesystem with ordered data mode.", "input: AT Translated Set 2 keyboard",
           "usb 1-1: new high speed USB device using ehci_hcd", "eth0: link up, 100Mbps, full-duplex",
           "Adding 2096472k swap on /dev/sda5.", "Freeing unused kernel memory: 304k freed"]
    tux = penguin(1)
    out = []
    for k in range(len(log) + 6):
        im = console([""] * 2 + log[:k][-(ROWS - 2):])
        for n in range(2):                                 # one penguin per CPU, top-left
            im.paste(tux, (4 + n * 28, 2))
        out.append(im)
    return out


# ------------------------------------------------------------------ 3 systemd + login
def systemd():
    units = ["Mounted /boot.", "Started Load Kernel Modules.", "Reached target Local File Systems.",
             "Started udev Kernel Device Manager.", "Reached target Swap.", "Started Network Manager.",
             "Reached target Network.", "Started OpenSSH Daemon.", "Started Login Service.",
             "Started Getty on tty1.", "Reached target Multi-User System.",
             "Reached target Graphical Interface."]
    lines, out = [], []
    for u in units:
        lines.append("[  OK  ] " + u)
        out.append(console(lines, invert_rows=()))
        out.append(out[-1])
    tty = lines + ["", "Arch Linux 6.9.1-arch1-1 (tty1)", ""]
    out += typing(tty, "archbox login: ", "neo", hold=1)
    out += typing(tty + ["archbox login: neo"], "Password: ", "", hold=6)
    return out


# ------------------------------------------------------------------ 4 neofetch
def neofetch():
    info = ["neo@archbox", "-----------", "OS: Arch Linux x86_64", "Host: ThinkPad X220",
            "Kernel: 6.9.1-arch1-1", "Uptime: 42 days, 3 hours", "Packages: 1337 (pacman)",
            "Shell: zsh 5.9", "WM: i3", "Theme: Gruvbox [GTK3]", "Terminal: urxvt",
            "CPU: Intel i5-2520M (4) @ 3.2GHz", "Memory: 1984MiB / 7861MiB"]
    art = [a.replace("Q", "#").replace("V", "#").replace("O", " ") for a in TUX]
    out = typing([], "[neo@archbox ~]$ ", "neofetch", hold=3)
    full = ["[neo@archbox ~]$ neofetch"]
    for r in range(max(len(art), len(info)) + 1):
        left = (art[r] if r < len(art) else "").ljust(24)
        right = info[r] if r < len(info) else ("\u2588\u2588" * 8 if r == len(info) else "")
        full.append(" " + left + right)
    for k in range(2, len(full) + 1):
        out.append(console(full[:k]))
    return out + [console(full + ["[neo@archbox ~]$ "], cursor=(17, len(full)))] * 10


# ------------------------------------------------------------------ 5 i3 rice with gaps
def bars(n, t):
    return [abs(math.sin(t * 0.7 + k * 0.6) * math.cos(t * 0.31 + k * 0.23)) for k in range(n)]


def i3():
    out = []
    code = ["local function rice()", "  gaps = 12", "  border = 2", "  font = 'Terminus 9'",
            "  bar = 'polybar'", "  return 'unixporn'", "end", "", ":wq"]
    for i in range(48):
        im = pattern("diag")
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W - 1, 17], fill=1)                                  # bar
        for k, ws in enumerate(["1:term", "2:web", "3:code", "4:music"]):
            x = 2 + k * 64
            if k == 0:
                d.rectangle([x, 1, x + 60, 16], fill=0)
            text(im, x + 2, 1, ws, invert=k == 0)
        text(im, W - 15 * CW, 1, f"vol 70%  21:{30 + i // 12:02d}")
        g = 10
        panes = [(g, 18 + g, 300, H - g), (300 + g, 18 + g, W - g, 180), (300 + g, 180 + g, W - g, H - g)]
        for k, (x0, y0, x1, y1) in enumerate(panes):
            d.rectangle([x0 - 2, y0 - 2, x1 + 2, y1 + 2], fill=0 if k == 0 else 1, outline=0)
            pw, ph = x1 - x0, y1 - y0
            if k == 0:
                shown = code[:min(len(code), i // 3 + 1)]
                body = console(["~/.config/i3 $ vim rice.lua", ""] + shown, size=(pw, ph))
            elif k == 1:
                t = i / 8
                cpu = [int(18 * (0.3 + 0.7 * abs(math.sin(t + c)))) for c in range(4)]
                body = console([f"{c + 1}[" + "|" * v + " " * (18 - v) + "]" for c, v in enumerate(cpu)]
                               + [f"Mem[{'|' * 9}{' ' * 9}]", "", "  PID CPU% Command", " 1337 23.1 firefox",
                                  "  420  8.4 polybar", "   69  2.0 picom"], size=(pw, ph))
            else:
                body = Image.new("1", (pw, ph), 1)
                bd = ImageDraw.Draw(body)
                vals = bars(14, i / 3)
                bw = pw // 14
                for c, v in enumerate(vals):
                    top = int(ph - 8 - v * (ph - 30))
                    bd.rectangle([c * bw + 2, top, c * bw + bw - 3, ph - 8], fill=0)
                text(body, 4, 2, "cava - now playing")
            im.paste(body, (x0, y0))
        out.append(im)
    return out


# ------------------------------------------------------------------ 6 htop
def htop():
    procs = ["/usr/bin/firefox", "Xorg :0", "i3", "polybar main", "picom --experimental-backends",
             "urxvt", "zsh", "vim rice.lua", "pulseaudio --daemonize", "mpd", "cava", "htop",
             "dunst", "sshd", "systemd --user", "NetworkManager"]
    out = []
    for i in range(36):
        t = i / 5
        lines = []
        for c in range(4):
            v = 0.15 + 0.8 * abs(math.sin(t * (1 + c * .3) + c))
            n = int(v * 25)
            lines.append(f"  {c + 1}[{'|' * n}{' ' * (25 - n)}{v * 100:5.1f}%]   "
                         + ["Tasks: 142, 612 thr; 2 running", f"Load average: {0.4 + v:.2f} 0.88 0.71",
                            "Uptime: 42 days, 03:14:07", ""][c])
        lines += [f"  Mem[{'|' * 17}{' ' * 8}1.94G/7.67G]", f"  Swp[{' ' * 25}  0K/2.00G]", "",
                  "  PID USER      PRI  NI  VIRT   RES S CPU% MEM%   TIME+  Command"]
        rows = sorted(((rng.randint(100, 9999), p, rng.random() * (40 if k < 3 else 6))
                       for k, p in enumerate(procs)), key=lambda r: -r[2])
        lines += [f"{pid:5d} neo        20   0 {rng.randint(100, 3000):4d}M {rng.randint(10, 900):4d}M "
                  f"{'R' if cpu > 20 else 'S'} {cpu:4.1f}  {rng.random() * 9:3.1f}  0:{rng.randint(0, 59):02d}.{rng.randint(0, 99):02d} {p}"
                  for pid, p, cpu in rows[:ROWS - len(lines) - 1]]
        lines.append("F1Help  F2Setup F3Search F4Filter F5Tree  F6SortBy F9Kill F10Quit")
        out.append(console(lines, invert_rows=(7, ROWS - 1)))
    return out


# ------------------------------------------------------------------ 7 vim
def vim():
    code = ["#include <stdio.h>", "", "/* the obligatory first program */", "int main(void)", "{",
            '    printf("Hello, world!\\n");', "    return 0;", "}"]
    flat, out = "\n".join(code), []
    for k in range(0, len(flat) + 1, 3):
        buf = flat[:k].split("\n")
        nums = [f"{n + 1:3d} {l}" for n, l in enumerate(buf)]
        lines = nums + ["~"] * (ROWS - 2 - len(buf)) + [" NORMAL  hello.c  utf-8  unix  c   %d:%d"
                                                          % (len(buf), len(buf[-1]) + 1), "-- INSERT --"]
        out.append(console(lines, cursor=(len(buf[-1]) + 4, len(buf) - 1), invert_rows=(ROWS - 2,)))
    done = [f"{n + 1:3d} {l}" for n, l in enumerate(code)] + ["~"] * (ROWS - 2 - len(code))
    for s in (":", ":w", ":wq", '"hello.c" 8L, 115B written'):
        out += [console(done + [" NORMAL  hello.c  utf-8  unix  c", s], invert_rows=(ROWS - 2,))] * 3
    return out


# ------------------------------------------------------------------ 8 pipes.sh
def pipes():
    grid = [[" "] * COLS for _ in range(ROWS)]
    turn = {(0, 1): "\u2513", (1, 0): "\u2517", (0, 3): "\u251b", (3, 0): "\u250f",
            (2, 1): "\u251b", (1, 2): "\u250f", (2, 3): "\u2513", (3, 2): "\u2517"}
    dirs = [(1, 0), (0, 1), (-1, 0), (0, -1)]          # right, down, left, up
    walkers = [[rng.randrange(COLS), rng.randrange(ROWS), rng.randrange(4)] for _ in range(4)]
    out = []
    for _ in range(50):
        for _ in range(6):
            for w in walkers:
                x, y, d = w
                nd = d if rng.random() > 0.15 else (d + rng.choice((1, 3))) % 4
                ch = ("\u2501" if nd % 2 == 0 else "\u2503") if nd == d else turn.get((d, nd), "+")
                grid[y][x] = ch
                w[2] = nd
                w[0] = (x + dirs[nd][0]) % COLS
                w[1] = (y + dirs[nd][1]) % ROWS
        out.append(console(["".join(r) for r in grid]))
    return out


# ------------------------------------------------------------------ 9 cmatrix
def cmatrix():
    drops = [rng.randint(-ROWS, ROWS) for _ in range(COLS)]
    speed = [rng.choice((1, 1, 2)) for _ in range(COLS)]
    chars = "abcdefghijklmnopqrstuvwxyz0123456789@#$%&*+=<>"
    out = []
    for _ in range(40):
        grid = [[" "] * COLS for _ in range(ROWS)]
        for c in range(0, COLS, 2):
            drops[c] += speed[c]
            for r in range(ROWS):
                if 0 <= drops[c] - r < 9:
                    grid[r][c] = rng.choice(chars)
            if drops[c] - 9 > ROWS:
                drops[c] = rng.randint(-10, 0)
        out.append(console(["".join(r) for r in grid]))
    return out


# ------------------------------------------------------------------ 10 sl
SL = [r"      ====        ________                ___________ ",
      r"  _D _|  |_______/        \__I_I_____===__|_________| ",
      r"   |(_)---  |   H\________/ |   |        =|___ ___|   ",
      r"   /     |  |   H  |  |     |   |         ||_| |_||   ",
      r"  |      |  |   H  |__--------------------| [___] |   ",
      r"  | ________|___H__/__|_____/[][]~\_______|       |   ",
      r"  |/ |   |-----------I_____I [][] []  D   |=======|__ ",
      r"__/ =| o |=-~~\  /~~\  /~~\  /~~\ ____Y___________|__ ",
      r" |/-=|___|=    ||    ||    ||    |_____/~\___/        ",
      r"  \_/      \O=====O=====O=====O_/      \_/            "]


def sl():
    out = []
    for i in range(44):
        x = COLS - i * 3
        smoke = ["   (@@) (  ) (@)  ( )  @@    ()    @", "  (   )   (@@@)", "      @@  ()"]
        lines = ["$ sl", ""]
        for k in range(3):
            s = " " * max(0, x + 4 + k * 2) + smoke[(k + i) % 3]
            lines.append(s[:COLS])
        for s in SL:
            lines.append(((" " * x + s) if x >= 0 else s[-x:])[:COLS])
        lines += ["", "\u2550" * COLS]
        out.append(console(lines))
    return out


# ------------------------------------------------------------------ 11 fortune | cowsay
def cowsay():
    msg = "There are only two hard things in Computer Science: cache invalidation and naming things."
    words, lines, cur = msg.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > 34:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    lines.append(cur)
    wd = max(map(len, lines))
    bubble = [" " + "_" * (wd + 2)]
    for k, l in enumerate(lines):
        a, b = ("/", "\\") if k == 0 else ("\\", "/") if k == len(lines) - 1 else ("|", "|")
        bubble.append(f"{a} {l.ljust(wd)} {b}")
    bubble.append(" " + "-" * (wd + 2))
    cow = [r"        \   ^__^", r"         \  (oo)\_______", r"            (__)\       )\/\\",
           r"                ||----w |", r"                ||     ||"]
    out = typing([], "$ ", "fortune | cowsay", hold=2)
    full = ["$ fortune | cowsay"] + bubble + cow
    for k in range(2, len(full) + 1):
        out.append(console(full[:k]))
    return out + [console(full + ["$ "], cursor=(2, len(full)))] * 10


# ------------------------------------------------------------------ 12 Compiz desktop cube
def cube():
    faces = [neofetch()[-1], htop()[10], i3()[30], cmatrix()[20]]
    small = [f.resize((256, 171), Image.NEAREST) for f in faces]
    out = []
    for i in range(48):
        a = i / 48 * math.pi * 1.5 + 0.35
        im = pattern("light")
        d = ImageDraw.Draw(im)
        d.ellipse([96, 286, 416, 330], fill=0)                                    # shadow
        drawn = []
        for k in range(4):
            th = a + k * math.pi / 2
            n = math.sin(th + math.pi / 4)
            corners = []
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                ang = th + (math.pi / 4 if sx > 0 else -math.pi / 4)
                x3, z3 = math.sin(ang) * 1.41, math.cos(ang) * 1.41
                y3 = sy * 0.95 - 0.12
                f = 5.5 / (5.5 - z3)
                corners.append((256 + x3 * 105 * f, 171 + y3 * 105 * f - 20 * (1 - f)))
            drawn.append((n, k, corners))
        for depth, k, corners in sorted(drawn):
            if depth < -0.05:
                continue
            img, mask = warp(small[k], corners)
            im.paste(img, (0, 0), mask)
            d.polygon(corners, outline=0)
        out.append(im)
    return out


if __name__ == "__main__":
    write_project(HERE, [
        Scene("GRUB", grub(), seconds=6, box=(8, 16, 504, 230), pan=0.04),
        Scene("kernel boot", boot(), seconds=6, box=(0, 0, 340, 336), pan=0.04, cam_dir=ALT),
        Scene("systemd + login", systemd(), seconds=8, box=(0, 0, 300, 336), pan=0.03),
        Scene("neofetch", neofetch(), seconds=8, box=(0, 0, 450, 240), pan=0.04, cam_dir=ALT),
        Scene("i3 rice", i3(), seconds=10, box=(0, 0, W, H), pan=0.03),
        Scene("htop", htop(), seconds=8, box=(0, 0, 500, 300), pan=0.04, cam_dir=ALT),
        Scene("vim", vim(), seconds=8, box=(0, 0, 290, 150), pan=0.03),
        Scene("pipes.sh", pipes(), seconds=7, box=(0, 0, W, H), pan=0.04, cam_dir=ALT),
        Scene("cmatrix", cmatrix(), seconds=6, box=(0, 0, W, H), pan=0.04),
        Scene("sl", sl(), seconds=6, box=(0, 16, W, 290), pan=0.02, cam_dir=ALT),
        Scene("fortune | cowsay", cowsay(), seconds=6, box=(0, 0, 330, 220), pan=0.03),
        Scene("compiz cube", cube(), seconds=10, box=(56, 30, 456, 336), pan=0.02, cam_dir=ALT),
    ])
