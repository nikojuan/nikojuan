"""Render the TikTok Shop video for the bow-pattern bedding set.

Niko edit style v1: 9:16, Big Shoulders hook, Archivo captions with a Mint
active-word box, Instrument Serif emphasis in Butter, cards that pop in,
whip transitions between sections, SFX only (no music supplied).

The timeline follows the voice-over: scenes, captions, cards and punch-ins are
keyed to word indices from timing.json (output of voice_edit.py, re-transcribed).

Usage: python3 render.py <prep_dir> <fonts_dir> <timing.json> <out.mp4> [still times...]
"""
import math
import subprocess
import sys
import wave
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import json

PREP, FONTS, TIMING, OUT = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
TM = json.load(open(TIMING))
WS = [w["s"] for w in TM["words"]]   # word start times in the cut voice
WE = [w["e"] for w in TM["words"]]
W, H, FPS = 1080, 1920, 30
SAFE_RIGHT = int(W * 0.84)      # keep text left of the platform UI column
CX = 500                        # visual centre for text, shifted left of the UI

TANGERINE = (255, 106, 31)
MINT = (127, 224, 196)
BUTTER = (255, 224, 102)
SNOW = (255, 255, 255)
INK = (22, 22, 26)


def font(name, size):
    paths = {
        "hook": "fontsource-big-shoulders-display-5.3.0/files/big-shoulders-display-latin-900-normal.woff",
        "cap": "fontsource-archivo-5.3.0/files/archivo-latin-800-normal.woff",
        "emph": "fontsource-instrument-serif-5.3.0/files/instrument-serif-latin-400-italic.woff",
    }
    return ImageFont.truetype(f"{FONTS}/{paths[name]}", size)


F_HOOK = font("hook", 180)
F_CTA = font("hook", 210)
F_CAP = font("cap", 78)
F_EMPH = font("emph", 96)
F_CARD = font("cap", 56)
F_CHIP = font("hook", 64)

# ---------------------------------------------------------------- helpers

def ease_out_back(x, s=1.9):
    x = min(max(x, 0.0), 1.0) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def ease_in_out(x):
    x = min(max(x, 0.0), 1.0)
    return 0.5 - 0.5 * math.cos(math.pi * x)


def shadowed(layer, radius=14, offset=(0, 6), opacity=170):
    """Return layer with a soft dark drop shadow, padded so nothing clips."""
    pad = radius * 3
    out = Image.new("RGBA", (layer.width + 2 * pad, layer.height + 2 * pad), (0, 0, 0, 0))
    a = layer.split()[3].point(lambda v: v * opacity // 255)
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 255))
    sh.putalpha(a)
    out.alpha_composite(sh, (pad + offset[0], pad + offset[1]))
    out = out.filter(ImageFilter.GaussianBlur(radius))
    out.alpha_composite(layer, (pad, pad))
    return out


def place(frame, layer, center, scale=1.0, alpha=1.0):
    if alpha <= 0.01 or scale <= 0.01:
        return
    if abs(scale - 1) > 1e-3:
        layer = layer.resize((max(1, int(layer.width * scale)), max(1, int(layer.height * scale))), Image.BICUBIC)
    if alpha < 0.999:
        layer = layer.copy()
        layer.putalpha(layer.split()[3].point(lambda v: int(v * alpha)))
    x = int(center[0] - layer.width / 2)
    y = int(center[1] - layer.height / 2)
    frame.alpha_composite(layer, (x, y)) if x >= 0 and y >= 0 else frame.paste(layer, (x, y), layer)


def pop(t, start, end, dur=0.15, fade=0.10):
    """Card / caption entrance: 90% -> 100% with overshoot; fade-out exit."""
    if t < start or t > end:
        return 0.0, 0.0
    k = (t - start) / dur
    scale = 0.9 + 0.1 * ease_out_back(k) if k < 1 else 1.0
    alpha = min(1.0, k * 2.5)
    if t > end - fade:
        alpha *= max(0.0, (end - t) / fade)
    return scale, alpha

# ---------------------------------------------------------------- text layers

def word_size(word, f):
    b = f.getbbox(word)
    return b[2] - b[0], b


@lru_cache(maxsize=None)
def caption_layer(text, active, emph):
    """Sentence-case caption, 2-4 words, Mint box on the active word.
    `emph` is the single word (if any) set in Butter Instrument Serif Italic."""
    words = text.split(" ")
    space = 22
    asc = F_CAP.getmetrics()[0]
    line_h = 112
    items = []
    for i, w in enumerate(words):
        f = F_EMPH if w == emph else F_CAP
        ww, _ = word_size(w, f)
        items.append((w, f, ww))
    # wrap within the safe width
    max_w = (SAFE_RIGHT - 60) - 60
    lines, cur, cw = [], [], 0
    for i, it in enumerate(items):
        add = it[2] + (space if cur else 0)
        if cur and cw + add > max_w:
            lines.append(cur); cur, cw = [], 0; add = it[2]
        cur.append((i, it)); cw += add
    lines.append(cur)
    lw = max(sum(it[2] for _, it in ln) + space * (len(ln) - 1) for ln in lines)
    layer = Image.new("RGBA", (lw + 60, line_h * len(lines) + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    # Shadow pass for the white words only (box words carry their own contrast)
    for li, ln in enumerate(lines):
        x = 30 + (lw - (sum(it[2] for _, it in ln) + space * (len(ln) - 1))) // 2
        y = 20 + li * line_h
        for i, (w, f, ww) in ln:
            fy = y + (asc - f.getmetrics()[0]) + (10 if f is F_EMPH else 0)
            if i == active and f is F_CAP:
                d.rounded_rectangle((x - 14, y + 6, x + ww + 14, y + line_h - 10), 18, fill=MINT + (255,))
                d.text((x, fy), w, font=f, fill=INK)
            else:
                d.text((x, fy), w, font=f, fill=(BUTTER if f is F_EMPH else SNOW))
            x += ww + space
    # soft dark shadow under everything
    return shadowed(layer, radius=12, offset=(0, 5), opacity=200)


@lru_cache(maxsize=None)
def hook_layer(lines, key, f_size=180):
    f = F_HOOK if f_size == 180 else F_CTA
    lh = int(f_size * 0.9)
    widths = []
    for ln in lines:
        widths.append(sum(word_size(w, f)[0] for w in ln.split()) + 30 * (len(ln.split()) - 1))
    lw = max(widths)
    layer = Image.new("RGBA", (lw + 40, lh * len(lines) + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for li, ln in enumerate(lines):
        x = 20 + (lw - widths[li]) // 2
        for w in ln.split():
            d.text((x, 10 + li * lh), w, font=f, fill=TANGERINE if w == key else SNOW)
            x += word_size(w, f)[0] + 30
    return shadowed(layer, radius=16, offset=(0, 8), opacity=190)


@lru_cache(maxsize=None)
def card_layer(label, chip, chip_color):
    h = 128
    width = 130 + word_size(label, F_CARD)[0] + 40
    card = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle((0, 0, width - 1, h - 1), 20, fill=SNOW + (255,))
    d.ellipse((24, 24, 104, 104), fill=chip_color + (255,))
    fg = SNOW if chip_color != MINT else INK
    if chip == "✓":  # the display font has no check glyph, so draw one
        d.line([(44, 66), (58, 82), (86, 46)], fill=fg, width=10, joint="curve")
    else:
        cw = word_size(chip, F_CHIP)[0]
        d.text((64 - cw / 2, 26), chip, font=F_CHIP, fill=fg)
    d.text((130, 32), label, font=F_CARD, fill=INK)
    return shadowed(card, radius=24, offset=(0, 10), opacity=110)


@lru_cache(maxsize=None)
def detail_layer():
    src = Image.open(f"{PREP}/img1_detail.png").convert("RGB")
    D = 620
    img = src.resize((D, D), Image.LANCZOS)
    m = Image.new("L", (D, D), 0)
    ImageDraw.Draw(m).ellipse((int(D * 0.06), int(D * 0.06), int(D * 0.94), int(D * 0.94)), fill=255)
    ring = Image.new("RGBA", (D, D), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse((int(D * 0.06) - 10, int(D * 0.06) - 10, int(D * 0.94) + 10, int(D * 0.94) + 10), fill=SNOW + (255,))
    circ = img.convert("RGBA"); circ.putalpha(m)
    ring.alpha_composite(circ)
    return shadowed(ring, radius=24, offset=(0, 12), opacity=120)


@lru_cache(maxsize=None)
def thumb_layer():
    src = Image.open(f"{PREP}/img9.png").convert("RGB")
    t = src.resize((600, 600), Image.LANCZOS).convert("RGBA")
    m = Image.new("L", t.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, 599, 599), 24, fill=255)
    t.putalpha(m)
    return shadowed(t, radius=24, offset=(0, 12), opacity=160)

# ---------------------------------------------------------------- backgrounds

@lru_cache(maxsize=None)
def bg_source(name):
    return Image.open(f"{PREP}/{name}.png").convert("RGB")


@lru_cache(maxsize=None)
def overlay():
    """Top gradient behind the hook + soft band behind captions (legibility on a light bed)."""
    a = np.zeros((H, W), np.float32)
    y = np.arange(H)[:, None]
    a += 0.50 * np.clip(1 - y / 760, 0, 1) ** 1.4
    a += 0.30 * np.exp(-((y - 1160) / 260.0) ** 2)
    a = np.clip(a, 0, 0.6)
    ov = np.zeros((H, W, 4), np.uint8)
    ov[..., :3] = INK
    ov[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(ov, "RGBA")


def background(name, zoom, pan_x, pan_y=0.5):
    src = bg_source(name)
    s = max(W / src.width, H / src.height) * zoom
    cw, ch = W / s, H / s
    cx = cw / 2 + (src.width - cw) * pan_x
    cy = ch / 2 + (src.height - ch) * pan_y
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    fr = src.resize((W, H), Image.BICUBIC, box=box).convert("RGBA")
    fr.alpha_composite(overlay())
    return fr

# ---------------------------------------------------------------- timeline
# Everything is keyed to word indices of the voice-over (see timing.json):
#   0-6   ¿Tu cama nivel hotel? Mira este juego.
#   7-15  Los lazos van en relieve. Se sienten al tocarlos.
#   16-22 Suave, transpirable y para todo el año.
#   23-27 Va directo a la lavadora.
#   28-36 Calidad de hotel en ocho tamaños, blanco o beige.
#   37-45 Ojo, es la funda. El relleno no viene incluido.
#   46-51 El regalo perfecto para estrenar casa.
#   52-58 Toca el carrito y elige tu tamaño.
# caps: (text, emphasis word, first word idx, last word idx). Text is written by hand
# (sentence case, no full stops) and must have one token per spoken word.
# zoom: ("push",) slow 100->105, or ("punch", word idx) jump to 112% on the key word.
# Punches alternate with pushes so we never zoom on two cuts in a row.
SPEC = [
    dict(first=0, bg="img9", zoom=("push",), pan=(0.45, 0.55),
         hook=(("TU CAMA", "NIVEL HOTEL"), "HOTEL"),       # the hook *is* the caption for words 0-3
         caps=[("Mira este juego", None, 4, 6)]),
    dict(first=7, bg="img1_bed", zoom=("punch", 10), pan=(0.0, 0.35), detail=True,
         caps=[("Los lazos van", None, 7, 9), ("en relieve", "relieve", 10, 11),
               ("se sienten al tocarlos", None, 12, 15)]),
    dict(first=16, bg="img7", zoom=("push",), pan=(0.40, 0.70),
         cards=[("Suave al tacto", "1", 16), ("Transpirable", "2", 17), ("Para todo el año", "3", 19)],
         caps=[("Suave, transpirable", None, 16, 17), ("y para", None, 18, 19), ("todo el año", None, 20, 22)]),
    dict(first=23, bg="img6", zoom=("punch", 27), pan=(0.55, 0.45), chip=MINT,
         cards=[("Lavable a máquina", "✓", 23)],
         caps=[("Va directo", None, 23, 24), ("a la lavadora", None, 25, 27)]),
    dict(first=28, bg="img5", zoom=("push",), pan=(0.60, 0.55), chip=INK,
         cards=[("8 tamaños", "8", 32), ("Blanco o beige", "2", 34)],
         caps=[("Calidad de hotel", "hotel", 28, 30), ("en ocho tamaños", None, 31, 33),
               ("blanco o beige", None, 34, 36)]),
    dict(first=37, bg="img1_bed", zoom=("punch", 43), pan=(0.10, 0.60), chip=INK,
         cards=[("Funda + fundas", "+", 40), ("Relleno no incluido", "!", 42)],
         caps=[("Ojo: es la funda", None, 37, 40), ("el relleno", None, 41, 42),
               ("no viene incluido", None, 43, 45)]),
    dict(first=46, bg="img9", zoom=("push",), pan=(0.75, 0.40),
         caps=[("El regalo perfecto", "perfecto", 46, 48), ("para estrenar casa", None, 49, 51)]),
    dict(first=52, bg=None, cta=True, cta_word=52,
         caps=[("y elige tu tamaño", None, 55, 58)]),
]
LEAD = 0.08           # a cut lands just before the first word of its section
OUTRO_HOLD = 1.0      # CTA stays on screen after the last word
DURATION = round(WE[-1] + OUTRO_HOLD, 2)


def build_scenes():
    scenes = []
    for i, sp in enumerate(SPEC):
        start = 0.0 if i == 0 else WS[sp["first"]] - LEAD
        end = DURATION if i == len(SPEC) - 1 else WS[SPEC[i + 1]["first"]] - LEAD
        sc = dict(sp, start=start, end=end)
        caps = []
        for j, (text, emph, a, b) in enumerate(sp["caps"]):
            assert len(text.split(" ")) == b - a + 1, text
            t0 = WS[a] - start
            nxt = sp["caps"][j + 1][2] if j + 1 < len(sp["caps"]) else None
            t1 = (WS[nxt] - start) if nxt is not None else (end - start)
            caps.append((text, emph, t0, t1, tuple(WS[k] - start for k in range(a, b + 1))))
        sc["caps"] = caps
        if "cards" in sp:
            sc["cards"] = [(lbl, chip, WS[k] - start) for lbl, chip, k in sp["cards"]]
        if sp.get("zoom", ("",))[0] == "punch":
            sc["zoom"] = ("punch", WS[sp["zoom"][1]] - start)
        if sp.get("cta"):
            sc["cta_t"] = WS[sp["cta_word"]] - start
        scenes.append(sc)
    return scenes


SCENES = build_scenes()
WHIP = 7  # frames, motion-blur whip into each new section


def render_scene(sc, lt):
    dur = sc["end"] - sc["start"]
    if sc.get("cta"):
        fr = Image.new("RGBA", (W, H), INK + (255,))
        s, a = pop(lt, 0.10, dur)
        place(fr, thumb_layer(), (CX, 600), s, a)
        s, a = pop(lt, sc["cta_t"], dur)
        place(fr, hook_layer(("TOCA EL", "CARRITO"), "CARRITO", 210), (CX, 1100), s, a)
    else:
        z = sc["zoom"]
        if z[0] == "push":
            zoom = 1.0 + 0.05 * ease_in_out(lt / dur)
        else:
            zoom = 1.12 if lt >= z[1] else 1.0 + 0.01 * lt / max(z[1], 0.1)
        px = sc["pan"][0] + 0.06 * (lt / dur - 0.5)
        fr = background(sc["bg"], zoom, min(max(px, 0), 1), sc["pan"][1])

    if "hook" in sc:  # slam in at 0.1 s, 110% -> 100%
        lines, key = sc["hook"]
        if lt >= 0.1:
            k = min(1.0, (lt - 0.1) / 0.12)
            place(fr, hook_layer(lines, key), (CX, 420), 1.10 - 0.10 * ease_in_out(k), 1.0)
    if sc.get("detail"):
        s, a = pop(lt, 0.1, dur)
        place(fr, detail_layer(), (CX, 600), s, a)
    if "cards" in sc:
        n = len(sc["cards"])
        top = 330 if n == 3 else 420
        for i, (label, chip, t_in) in enumerate(sc["cards"]):
            s, a = pop(lt, t_in, dur)
            lay = card_layer(label, chip, sc.get("chip", TANGERINE))
            # left-aligned at x=60 (layer includes 72 px shadow padding)
            place(fr, lay, (60 - 72 + lay.width / 2, top + i * 170), s, a)
    for text, emph, t0, t1, starts in sc["caps"]:
        if t0 <= lt < t1:
            words = text.split(" ")
            active = max(i for i, st in enumerate(starts) if st <= lt)
            if words[active] == emph:
                active = -1  # the serif emphasis word is its own highlight
            s, a = pop(lt, t0, t1, dur=0.12, fade=0.0)
            place(fr, caption_layer(text, active, emph), (CX, 1160 if not sc.get("cta") else 1420), s, a)
    return fr


def scene_at(t):
    for i, sc in enumerate(SCENES):
        if sc["start"] <= t < sc["end"]:
            return i
    return len(SCENES) - 1


def hblur(arr, k):
    if k < 3:
        return arr
    c = np.cumsum(np.pad(arr.astype(np.float32), ((0, 0), (k, k), (0, 0)), mode="edge"), axis=1)
    out = (c[:, 2 * k:] - c[:, :-2 * k]) / (2 * k)
    return out[:, : arr.shape[1]]


def whip(out_fr, in_fr, k):
    """k in [0,1): slide left, blurred proportionally to speed."""
    strip = np.concatenate([np.asarray(out_fr.convert("RGB")), np.asarray(in_fr.convert("RGB"))], axis=1)
    off = int(ease_in_out(k) * W)
    speed = math.sin(math.pi * k)
    view = strip[:, off: off + W]
    return Image.fromarray(np.clip(hblur(view, int(90 * speed)), 0, 255).astype(np.uint8))


def main():
    n_frames = int(round(DURATION * FPS))
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", OUT],
        stdin=subprocess.PIPE)
    boundaries = [int(round(sc["start"] * FPS)) for sc in SCENES[1:]]
    for f in range(n_frames):
        t = f / FPS
        img = None
        for bi, b in enumerate(boundaries):
            if b - 3 <= f < b + WHIP - 3:
                prev, nxt = SCENES[bi], SCENES[bi + 1]
                out_fr = render_scene(prev, (prev["end"] - prev["start"]) - 0.001)
                in_fr = render_scene(nxt, 0.0)
                img = whip(out_fr, in_fr, (f - (b - 3)) / WHIP)
                break
        if img is None:
            sc = SCENES[scene_at(t)]
            img = render_scene(sc, t - sc["start"]).convert("RGB")
        ff.stdin.write(img.tobytes())
    ff.stdin.close()
    ff.wait()

# ---------------------------------------------------------------- sound

def make_sfx(path):
    sr = 48000
    total = np.zeros(int(DURATION * sr) + sr, np.float32)
    rng = np.random.default_rng(7)

    def whoosh():
        n = int(0.32 * sr)
        noise = rng.standard_normal(n).astype(np.float32)
        out = np.zeros(n, np.float32)
        y = 0.0
        for i in range(n):
            a = 0.02 + 0.25 * math.sin(math.pi * i / n)   # cutoff sweeps up then down
            y += a * (noise[i] - y)
            out[i] = y
        env = np.sin(np.linspace(0, math.pi, n)) ** 2
        return out * env * 1.6

    def popsnd():
        n = int(0.07 * sr)
        tt = np.arange(n) / sr
        freq = 900 - 500 * tt / 0.07
        return (np.sin(2 * math.pi * np.cumsum(freq) / sr) * np.exp(-tt * 55) * 0.35).astype(np.float32)

    # priority 0 = whoosh on every whip (always kept), 1 = pops (dropped if <1 s from another SFX)
    events = [(sc["start"] - 0.15, 0, "whoosh") for sc in SCENES[1:]]
    events.append((0.1, 1, "pop"))  # hook slam
    for sc in SCENES:
        if "cards" in sc:
            events.append((sc["start"] + sc["cards"][0][2], 1, "pop"))
        if sc.get("cta"):
            events.append((sc["start"] + sc["cta_t"], 1, "pop"))
    kept = [e for e in events if e[1] == 0]
    for e in sorted((e for e in events if e[1] == 1), key=lambda e: e[0]):
        if all(abs(e[0] - k[0]) >= 1.0 for k in kept):
            kept.append(e)
    for t0, _, kind in sorted(kept):
        snd = whoosh() if kind == "whoosh" else popsnd()
        i = int(max(t0, 0) * sr)
        total[i:i + len(snd)] += snd[: len(total) - i]
    total = total[: int(DURATION * sr)]
    total = total / max(1e-6, np.abs(total).max()) * 0.35
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((total * 32767).astype(np.int16).tobytes())
    return sorted(kept)


if __name__ == "__main__":
    kept = make_sfx(OUT + ".sfx.wav")
    print(f"duration {DURATION}s; scenes:", [(round(s["start"], 2), round(s["end"], 2)) for s in SCENES])
    print("sfx:", [(round(t, 2), k) for t, _, k in kept])
    if len(sys.argv) > 5:  # preview stills: python3 render.py ... out.mp4 3.0 7.5 ...
        for ts in sys.argv[5:]:
            t = float(ts); sc = SCENES[scene_at(t)]
            render_scene(sc, t - sc["start"]).convert("RGB").save(f"{OUT}.{ts}.png")
    else:
        main()
