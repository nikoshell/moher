#!/usr/bin/env python3
"""Render 1-bit pixel-art scenes to video with an animated rounded-pixel reveal.

Each project directory holds an animation.toml (scenes, keyframed camera and reveal),
images/ (1-bit frame strips) and an optional color.png palette.

    uv run mac.py projects/linux                      # -> projects/linux/out/linux.mp4
    uv run mac.py projects/linux --gpu                # render on the GPU (wgpu/Vulkan)
    uv run mac.py projects/linux --still f.png --at 8 # single frame
    uv run mac.py --selfcheck
"""
import argparse
import subprocess
import sys
import tomllib
from pathlib import Path

import numpy as np
from PIL import Image

# Stand-in palette (t, top, bottom, foreground) until the real color.png is present.
STAND_IN = [
    # Default palette, cycled over [background].duration seconds:
    # saturated background (top, bottom), ink = darker shade of the same hue.
    (0.00, (0x8F, 0xC7, 0x36), (0x6E, 0xA8, 0x1E), (0x2E, 0x4A, 0x0A)),  # green
    (0.25, (0x2E, 0xB8, 0xFE), (0x1A, 0x84, 0xE0), (0x0A, 0x2E, 0x5A)),  # blue
    (0.50, (0xB0, 0x5E, 0xFE), (0x86, 0x3A, 0xE0), (0x34, 0x10, 0x5A)),  # purple
    (0.75, (0xFE, 0x54, 0x2E), (0xE0, 0x38, 0x1A), (0x5A, 0x14, 0x08)),  # orange
]


def load_palette(path):
    """color.png columns 0/1/2 = bg top, bg bottom, foreground; rows = time."""
    if not path.exists():
        return np.array([s[1:] for s in STAND_IN], np.float32)
    a = np.asarray(Image.open(path).convert("RGB"), np.float32)
    return a[:, :3]                     # (rows, 3 colours, rgb)


def palette_at(pal, t):
    """Palette colours at cycle position t: lerp between rows, wrapping."""
    x = len(pal) * (t % 1.0)
    lo = int(x) % len(pal)
    c = pal[lo] + (pal[(lo + 1) % len(pal)] - pal[lo]) * (x - int(x))
    return c[0], c[1], c[2]

KEYS = ("camera_pos", "camera_dir", "scale", "frame", "progress", "progress_angle")


# ------------------------------------------------------------------ timeline
def track_get(kfs, t):
    """Keyframe track value at t; two keys with the same t make a step."""
    for i, (kt, v) in enumerate(kfs):
        if t < kt:
            if i == 0:
                return v
            lt, lv = kfs[i - 1]
            f = (t - lt) / (kt - lt) if kt != lt else 1.0
            return lv + (v - lv) * f
    return kfs[-1][1] if kfs else None


class Scene:
    def __init__(self, cfg, base, defaults):
        img = np.asarray(Image.open(base / cfg["image"]).convert("RGB"))
        n = cfg.get("frames", 1)
        h = img.shape[0] // n
        # black pixels are ink
        ink = ~((img[..., 0] != 0) & (img[..., 1] != 0) & (img[..., 2] != 0))
        self.frames = [ink[i * h:(i + 1) * h] for i in range(n)]
        self.duration = cfg["duration"]
        self.static = {k: np.array(cfg[k], float) for k in KEYS if k in cfg}
        self.defaults = defaults
        kfs = cfg.get("keyframes", [])
        # stable sort by t, like OrderedFloat sort_by_key
        self.tracks = {k: sorted(((kf["t"], np.array(kf[k], float)) for kf in kfs if k in kf),
                                 key=lambda x: x[0]) for k in KEYS}

    def props(self, t):
        p = {}
        for k in KEYS:
            v = track_get(self.tracks[k], t)
            p[k] = v if v is not None else self.static.get(k, self.defaults[k])
        p["frame"] = int(round(float(p["frame"]))) % len(self.frames)
        return p


def load(path):
    path = Path(path)
    cfg = tomllib.loads(path.read_text())
    sc = cfg["scenes"]
    defaults = {k: np.array(sc[k], float) for k in KEYS}
    scenes = [Scene(s, path.parent, defaults) for s in sc["scene"]]
    cmap = path.parent / cfg["background"]["colormap"]
    return scenes, load_palette(cmap), cfg["background"]["duration"], cmap.exists()


def at(scenes, time):
    """Animation::scene: scenes play back to back in order, looping."""
    total = sum(s.duration for s in scenes)
    t = time % total
    for s in scenes:
        if t <= s.duration:
            return s, s.props(t)
        t -= s.duration
    return scenes[-1], scenes[-1].props(scenes[-1].duration)


# ------------------------------------------------------------------ camera
def plane_to_ndc(p, W, H):
    """2x2 A, b with ndc = A @ quad_xy + b  (ortho * look_at_rh * scale, z=0 plane)."""
    f = p["camera_dir"] / np.linalg.norm(p["camera_dir"])
    s = np.cross(f, [0, 0, 1.0]); s /= np.linalg.norm(s)
    u = np.cross(s, f)
    eye = p["camera_pos"]
    A = np.array([[s[0], s[1]], [u[0], u[1]]]) * p["scale"]
    b = -np.array([s @ eye, u @ eye])
    a = W / H
    sx, sy = (1.0, a) if a >= 1 else (1.0 / a, 1.0)   # new_orthographic bounds
    S = np.diag([sx, sy])
    return S @ A, S @ b


# ------------------------------------------------------------------ shader
class Renderer:
    def __init__(self, W, H, opacity=1.0, soft=0.0, saturation=1.0):
        self.W, self.H = W, H
        # Look controls. soft = edge blur in source pixels.
        self.opacity, self.soft, self.sat = opacity, soft, saturation
        x = (np.arange(W, dtype=np.float32) + 0.5) / W * 2 - 1
        y = 1 - (np.arange(H, dtype=np.float32) + 0.5) / H * 2
        self.nx, self.ny = np.meshgrid(x, y)
        self.grad = (1 - (np.arange(H, dtype=np.float32) + 0.5) / H)[:, None, None]  # uv.y, row 0 = top

    def frame(self, scene, p, top, bottom, fg):
        top, bottom, fg = (saturate(c, self.sat) for c in (top, bottom, fg))
        W, H = self.W, self.H
        ink = scene.frames[p["frame"]]
        ih, iw = ink.shape
        A, b = plane_to_ndc(p, W, H)
        Ai = np.linalg.inv(A).astype(np.float32)
        dx, dy = self.nx - np.float32(b[0]), self.ny - np.float32(b[1])
        u = (Ai[0, 0] * dx + Ai[0, 1] * dy + 1) * 0.5
        v = (Ai[1, 0] * dx + Ai[1, 1] * dy + 1) * 0.5

        px, py = u * iw - 0.5, v * ih - 0.5
        rx, ry = np.round(px), np.round(py)
        dist = np.maximum(np.abs(px - rx), np.abs(py - ry))
        ang = float(p["progress_angle"])
        prog = (u * np.float32(np.cos(ang)) + v * np.float32(np.sin(ang))) * 20 + np.float32(p["progress"])
        edge = dist - 0.45 * np.clip(prog, 0, 1)

        # fwidth(dist): screen-space derivative of pixel coords (constant, affine map)
        J = np.abs(Ai) * np.array([[iw], [ih]]) * np.array([2 / W, 2 / H]) * 0.5
        cw = np.float32(max(J[0].sum(), J[1].sum()) + self.soft)
        e = np.clip((edge + cw) / (2 * cw), 0, 1)
        smooth = e * e * (3 - 2 * e)
        # fade each dot with its radius so a fully shrunk pixel leaves no speck
        smooth = 1 - (1 - smooth) * np.clip(0.45 * np.clip(prog, 0, 1) / cw, 0, 1)

        inside = (u >= 0) & (u <= 1) & (v >= 0) & (v <= 1)
        ix = np.clip(rx, 0, iw - 1).astype(np.int32)
        iy = np.clip(ry, 0, ih - 1).astype(np.int32)
        hit = ink[iy, ix] & inside
        alpha = np.clip(1 - smooth, 0, 1) * hit * np.float32(self.opacity)

        bg = np.asarray(top, np.float32) * self.grad + np.asarray(bottom, np.float32) * (1 - self.grad)
        out = bg + (np.asarray(fg, np.float32) - bg) * alpha[..., None]
        return np.clip(out + 0.5, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ GPU (Vulkan via wgpu)
WGSL = """
struct U { m: vec4f, b: vec4f, s: vec4f, size: vec4f, top: vec4f, bottom: vec4f, fg: vec4f };
@group(0) @binding(0) var<uniform> u: U;
@group(0) @binding(1) var<storage, read> ink: array<u32>;

@vertex
fn vs(@builtin(vertex_index) i: u32) -> @builtin(position) vec4f {
    var p = array(vec2f(-1.0, -1.0), vec2f(3.0, -1.0), vec2f(-1.0, 3.0));
    return vec4f(p[i], 0.0, 1.0);
}

@fragment
fn fs(@builtin(position) pos: vec4f) -> @location(0) vec4f {
    // Same maths as Renderer.frame, one fragment per output pixel.
    let dx = pos.x / u.size.x * 2.0 - 1.0 - u.b.x;
    let dy = 1.0 - pos.y / u.size.y * 2.0 - u.b.y;
    let uu = (u.m.x * dx + u.m.y * dy + 1.0) * 0.5;
    let vv = (u.m.z * dx + u.m.w * dy + 1.0) * 0.5;
    let iw = u.s.x; let ih = u.s.y; let cw = u.s.z;
    let px = vec2f(uu * iw - 0.5, vv * ih - 0.5);
    let r = round(px);
    let dist = max(abs(px.x - r.x), abs(px.y - r.y));
    let prog = (uu * cos(u.b.w) + vv * sin(u.b.w)) * 20.0 + u.b.z;
    let radius = 0.45 * clamp(prog, 0.0, 1.0);
    let e = clamp((dist - radius + cw) / (2.0 * cw), 0.0, 1.0);
    var sm = e * e * (3.0 - 2.0 * e);
    sm = 1.0 - (1.0 - sm) * clamp(radius / cw, 0.0, 1.0);
    let inside = uu >= 0.0 && uu <= 1.0 && vv >= 0.0 && vv <= 1.0;
    let ix = u32(clamp(r.x, 0.0, iw - 1.0));
    let iy = u32(clamp(r.y, 0.0, ih - 1.0));
    let hit = select(0.0, f32(ink[iy * u32(iw) + ix]), inside);
    let alpha = clamp(1.0 - sm, 0.0, 1.0) * hit * u.s.w;
    let g = 1.0 - pos.y / u.size.y;
    let bg = u.top.rgb * g + u.bottom.rgb * (1.0 - g);
    return vec4f(mix(bg, u.fg.rgb, alpha), 1.0);
}
"""


class GpuRenderer(Renderer):
    """Same output as Renderer, computed by a fragment shader (Vulkan on Linux)."""

    def __init__(self, W, H, opacity=1.0, soft=0.0, saturation=1.0):
        import wgpu
        self.wgpu = wgpu
        self.W, self.H = W, H
        self.opacity, self.soft, self.sat = opacity, soft, saturation
        self.row = (W * 4 + 255) // 256 * 256      # readback rows must be 256-byte aligned
        adapter = wgpu.gpu.request_adapter_sync(power_preference="high-performance")
        print(f"gpu: {adapter.info.get('device', '?')} ({adapter.info.get('backend_type', '?')})",
              file=sys.stderr)
        self.dev = d = adapter.request_device_sync()
        self.tex = d.create_texture(size=(W, H, 1), format="rgba8unorm",
                                    usage=wgpu.TextureUsage.RENDER_ATTACHMENT | wgpu.TextureUsage.COPY_SRC)
        self.ubuf = d.create_buffer(size=7 * 16, usage=wgpu.BufferUsage.UNIFORM | wgpu.BufferUsage.COPY_DST)
        self.ibuf = self.bind = None
        self.ink_key = None
        mod = d.create_shader_module(code=WGSL)
        self.pipe = d.create_render_pipeline(
            layout="auto",
            vertex={"module": mod, "entry_point": "vs"},
            fragment={"module": mod, "entry_point": "fs", "targets": [{"format": "rgba8unorm"}]},
            primitive={"topology": "triangle-list"})

    def ensure(self, buf, size):
        """Storage buffer at least `size` bytes; a new one invalidates the bind group."""
        if buf is not None and buf.size >= size:
            return buf
        self.bind = None
        return self.dev.create_buffer(size=max(size, 16),
                                      usage=self.wgpu.BufferUsage.STORAGE | self.wgpu.BufferUsage.COPY_DST)

    def frame(self, scene, p, top, bottom, fg):
        wgpu, d, W, H = self.wgpu, self.dev, self.W, self.H
        top, bottom, fg = (saturate(c, self.sat) / 255 for c in (top, bottom, fg))
        ink = scene.frames[p["frame"]]
        ih, iw = ink.shape
        if self.ink_key is not ink:             # upload only when the art frame changes
            data = ink.astype(np.uint32).tobytes()
            self.ibuf = self.ensure(self.ibuf, len(data))
            d.queue.write_buffer(self.ibuf, 0, data)
            self.ink_key = ink
        if self.bind is None:
            self.bind = d.create_bind_group(layout=self.pipe.get_bind_group_layout(0), entries=[
                {"binding": 0, "resource": {"buffer": self.ubuf}},
                {"binding": 1, "resource": {"buffer": self.ibuf}}])
        A, b = plane_to_ndc(p, W, H)
        Ai = np.linalg.inv(A)
        J = np.abs(Ai) * np.array([[iw], [ih]]) * np.array([2 / W, 2 / H]) * 0.5
        cw = max(J[0].sum(), J[1].sum()) + self.soft
        u = np.array([*Ai.ravel(), b[0], b[1], float(p["progress"]), float(p["progress_angle"]),
                      iw, ih, cw, self.opacity, W, H, 0, 0,
                      *top, 0, *bottom, 0, *fg, 0], np.float32)
        d.queue.write_buffer(self.ubuf, 0, u.tobytes())

        enc = d.create_command_encoder()
        rp = enc.begin_render_pass(color_attachments=[{
            "view": self.tex.create_view(), "load_op": "clear", "store_op": "store",
            "clear_value": (0, 0, 0, 1)}])
        rp.set_pipeline(self.pipe)
        rp.set_bind_group(0, self.bind)
        rp.draw(3)
        rp.end()
        d.queue.submit([enc.finish()])
        buf = d.queue.read_texture({"texture": self.tex}, {"bytes_per_row": self.row, "rows_per_image": H},
                                   (W, H, 1))
        return np.frombuffer(buf, np.uint8).reshape(H, self.row // 4, 4)[:, :W, :3]


def gpucheck(a):
    """GPU and CPU renders of the same frame must agree."""
    scenes, stops, period, _ = load(a.config)
    W, H = 640, 400
    cpu = Renderer(W, H, a.opacity, a.soft, a.saturation)
    gpu = GpuRenderer(W, H, a.opacity, a.soft, a.saturation)
    for t in (0.5, 7.0, 14.0, 40.0, 100.0):
        x = render_at(cpu, scenes, stops, period, a.offset, t).astype(int)
        y = render_at(gpu, scenes, stops, period, a.offset, t).astype(int)
        diff = np.abs(x - y)
        print(f"t={t:6.1f}  mean|diff| {diff.mean():.3f}  >8: {(diff.max(2) > 8).mean() * 100:.3f}%")
        assert diff.mean() < 1.0 and (diff.max(2) > 8).mean() < 0.002, "GPU disagrees with CPU"
    print("gpucheck: ok")


def saturate(c, k):
    """Scale chroma around luma by k (1 = unchanged)."""
    c = np.asarray(c, np.float32)
    y = c @ np.array([0.299, 0.587, 0.114], np.float32)
    return np.clip(y + (c - y) * k, 0, 255)


def render_at(r, scenes, stops, period, offset, t):
    s, p = at(scenes, t)
    p["scale"] = p["scale"] * getattr(r, "zoom", 1.0)
    top, bottom, fg = palette_at(stops, t / period + offset)
    return r.frame(s, p, top, bottom, fg)


# ------------------------------------------------------------------ check
def selfcheck():
    # duplicate-t keyframes step, linear between
    kf = [(0.0, 0.0), (5.0, 30.0), (10.0, 30.0), (10.0, 12.5), (15.0, -15.0)]
    assert track_get(kf, 2.5) == 15.0
    assert track_get(kf, 9.99) == 30.0 and track_get(kf, 10.0) == 12.5
    assert track_get(kf, 99) == -15.0 and track_get(kf, -1) == 0.0
    p = {"camera_dir": np.array([0.0, 1.0, 0.0]), "camera_pos": np.zeros(3), "scale": 2.0}
    A, b = plane_to_ndc(p, 200, 100)
    assert np.allclose(np.abs(A), [[2, 0], [0, 0]])  # looking along +y: plane is edge-on
    # full render: hidden at progress<=0, ink drawn in fg when fully revealed
    scenes, stops, period, _ = load(Path(__file__).parent / "projects/macintosh/animation.toml")
    r = Renderer(320, 200)
    s = scenes[0]
    p = s.props(7.0)
    img = r.frame(s, p, (255, 255, 255), (255, 255, 255), (0, 0, 0))
    assert (img < 128).any() and (img > 128).any(), "revealed scene draws ink"
    p["progress"] = -100.0
    img = r.frame(s, p, (255, 255, 255), (255, 255, 255), (0, 0, 0))
    assert img.min() == 255, "unrevealed scene is fully blank (no specks)"
    assert abs(sum(x.duration for x in scenes) - 189.53) < 1e-6
    print("selfcheck: ok")


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project", nargs="?", default="projects/macintosh",
                    help="project dir with animation.toml (+ images/, color.png)")
    ap.add_argument("--out", help="default: <project>/out/<project-name>.mp4")
    ap.add_argument("--width", type=int, default=2560)
    ap.add_argument("--height", type=int, default=1600)
    ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--seconds", type=float, help="default: one full loop of all scenes")
    ap.add_argument("--offset", type=float, default=0.0, help="palette phase 0..1")
    ap.add_argument("--opacity", type=float, default=0.85, help="ink opacity")
    ap.add_argument("--soft", type=float, default=0.0, help="edge blur in source pixels")
    ap.add_argument("--saturation", type=float, default=1.0, help="colour saturation multiplier")
    ap.add_argument("--zoom", type=float, default=1.0, help="multiply every scene's scale (<1 = further out)")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--still")
    ap.add_argument("--at", type=float, default=0.0)
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--gpu", action="store_true", help="render with the GPU (wgpu/Vulkan)")
    ap.add_argument("--gpucheck", action="store_true", help="compare GPU vs CPU frames")
    ap.add_argument("--encoder", default="libx264", help="e.g. h264_nvenc, h264_vaapi")
    a = ap.parse_args()
    proj = Path(a.project)
    a.config = str(proj / "animation.toml")
    a.out = a.out or str(proj / "out" / f"{proj.resolve().name}.mp4")
    if a.selfcheck:
        return selfcheck()
    if a.gpucheck:
        return gpucheck(a)

    scenes, stops, period, real = load(a.config)
    if not real:
        print("note: color.png not found, using stand-in palette", file=sys.stderr)
    r = (GpuRenderer if a.gpu else Renderer)(a.width, a.height, a.opacity, a.soft, a.saturation)
    r.zoom = a.zoom
    if a.still:
        Image.fromarray(render_at(r, scenes, stops, period, a.offset, a.at)).save(a.still)
        return

    total = sum(s.duration for s in scenes)
    n = int(round((a.seconds or total) * a.fps))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{a.width}x{a.height}", "-r", str(a.fps), "-i", "-",
        *(["-c:v", "libx264", "-preset", "slow", "-tune", "animation", "-crf", str(a.crf)]
          if a.encoder == "libx264" else ["-c:v", a.encoder, "-b:v", "25M"]),
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    for i in range(n):
        ff.stdin.write(render_at(r, scenes, stops, period, a.offset, a.start + i / a.fps).tobytes())
        if i % a.fps == 0:
            print(f"\r{i / a.fps:6.1f}/{n / a.fps:.1f}s", end="", file=sys.stderr, flush=True)
    ff.stdin.close()
    sys.exit(ff.wait())


if __name__ == "__main__":
    main()
