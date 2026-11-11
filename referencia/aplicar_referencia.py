"""Edita un vídeo copiando el ritmo, los cortes, los subtítulos y los colores de una referencia.

Necesita el perfil que crea analizar_referencia.py (revisado a mano en la parte de subtítulos).

Qué hace, en este orden:
  1. Cortes de pausas: quita los silencios más largos que los que deja la referencia.
  2. Ritmo: pone un cambio visual (corte de encuadre / punch-in) con la misma secuencia de
     duraciones de plano que la referencia, ajustado al inicio de la palabra más cercana.
  3. Color: iguala la curva de cada canal R/G/B y la saturación a la referencia.
  4. Subtítulos: misma posición, fuente, tamaño, mayúsculas, palabras por subtítulo,
     colores y efecto de palabra activa.
  5. Audio: voz normalizada a -14 LUFS.

Transcripción: pasa --palabras palabras.json ([{"w","s","e"}, ...] en tiempos del vídeo
original). Si no se pasa, intenta faster-whisper; si no está disponible, sale sin subtítulos.

Uso:
  python3 aplicar_referencia.py perfil.json entrada.mp4 salida.mp4 [--palabras p.json]
         [--fuentes carpeta] [--sin-cortes-de-pausa] [--prueba 1.5 6.0]   (solo fotogramas)
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("perfil"); ap.add_argument("entrada"); ap.add_argument("salida")
ap.add_argument("--palabras")
ap.add_argument("--fuentes", default=os.path.join(HERE, "fuentes"))
ap.add_argument("--sin-cortes-de-pausa", action="store_true")
ap.add_argument("--zoom", type=float, default=1.12, help="nivel del punch-in en cada cambio")
ap.add_argument("--ancla-y", type=float, default=0.38, help="altura de la cara (0 arriba, 1 abajo) para el zoom")
ap.add_argument("--prueba", type=float, nargs="*", help="solo guarda fotogramas en estos segundos")
a = ap.parse_args()

P = json.load(open(a.perfil))
W, H = P["formato"]["ancho"], P["formato"]["alto"]
FPS = P["formato"]["fps"] or 30
SUB = P["subtitulos"]


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,width,height:format=duration", "-of", "json", path],
                       capture_output=True, text=True, check=True)
    j = json.loads(r.stdout)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    return int(v["width"]), int(v["height"]), float(j["format"]["duration"]), \
        any(s["codec_type"] == "audio" for s in j["streams"])


IW, IH, IDUR, HAS_AUDIO = probe(a.entrada)
tmp = a.salida + ".tmp"
os.makedirs(tmp, exist_ok=True)

# ------------------------------------------------------------- 1. palabras
words = []
if a.palabras:
    words = json.load(open(a.palabras))
elif HAS_AUDIO:
    try:
        from faster_whisper import WhisperModel
        run(["ffmpeg", "-v", "error", "-y", "-i", a.entrada, "-ac", "1", "-ar", "16000", f"{tmp}/voz16.wav"])
        m = WhisperModel(os.environ.get("WHISPER_MODEL", "small"), device="cpu", compute_type="int8")
        segs, _ = m.transcribe(f"{tmp}/voz16.wav", language=os.environ.get("IDIOMA", "es"), word_timestamps=True)
        words = [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)} for s in segs for w in s.words]
        json.dump(words, open(f"{tmp}/palabras.json", "w"), ensure_ascii=False)
    except Exception as e:  # sin modelo / sin red
        print(f"AVISO: no se pudo transcribir ({type(e).__name__}: {str(e)[:120]}). Sin subtítulos.", file=sys.stderr)

# ------------------------------------------------------------- 2. cortes de pausa
max_gap = max(0.06, min(0.3, P["pausas"].get("hueco_max_tipico", 0.1)))
keep = [(0.0, IDUR)]
if HAS_AUDIO and not a.sin_cortes_de_pausa:
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", a.entrada, "-af",
                        f"silencedetect=n=-38dB:d={max_gap:.3f}", "-f", "null", "-"],
                       capture_output=True, text=True)
    sil, st = [], None
    for line in r.stderr.splitlines():
        if "silence_start" in line:
            st = max(0.0, float(line.split("silence_start:")[1].split()[0]))
        elif "silence_end" in line and st is not None:
            sil.append((st, float(line.split("silence_end:")[1].split()[0]))); st = None
    if st is not None:
        sil.append((st, IDUR))
    pad = 0.04  # aire que se deja a cada lado de la voz
    keep, pos = [], 0.0
    for s, e in sil:
        # el hueco que queda tras cortar = 2*pad (≈ el hueco típico de la referencia)
        cs, ce = s + pad, e - pad
        if s <= 0.01:
            cs = 0.0; ce = max(0.0, e - 0.12)  # deja 0.12 s de entrada
        if e >= IDUR - 0.01:
            ce = IDUR
        if ce - cs > 0.02:
            if cs > pos:
                keep.append((pos, cs))
            pos = ce
    if pos < IDUR:
        keep.append((pos, IDUR))
    keep = [(s, e) for s, e in keep if e - s > 0.05]


def to_new(t):
    """tiempo original -> tiempo editado (None si cae en un trozo cortado)."""
    acc = 0.0
    for s, e in keep:
        if t < s:
            return acc
        if t <= e:
            return acc + t - s
        acc += e - s
    return acc


NDUR = sum(e - s for s, e in keep)
nwords = []
for w in words:
    s, e = to_new(w["s"]), to_new(w["e"])
    if e - s > 0.01:
        nwords.append({"w": w["w"], "s": round(s, 3), "e": round(e, 3)})
# saltos de corte en el tiempo nuevo (jump cuts de pausa)
jumps, acc = [], 0.0
for s, e in keep[:-1]:
    acc += e - s
    jumps.append(acc)

# ------------------------------------------------------------- 3. ritmo (cambios visuales)
pattern = [d for d in P["ritmo"]["planos"] if d >= 0.2] or [2.5]
starts = [w["s"] for w in nwords]
changes, t, k = [], 0.0, 0
while True:
    t += pattern[k % len(pattern)]; k += 1
    if t >= NDUR - 0.4:
        break
    cands = [x for x in starts + jumps if abs(x - t) <= 0.35]
    if cands:
        t = min(cands, key=lambda x: abs(x - t))
    if not changes or t - changes[-1] > 0.2:
        changes.append(round(t, 3))
# encuadre por plano: alterna abierto / punch-in (nunca dos zooms seguidos)
shots = [0.0] + changes + [NDUR]
zooms = [1.0 if i % 2 == 0 else a.zoom for i in range(len(shots) - 1)]


def zoom_at(t):
    for i in range(len(shots) - 1):
        if shots[i] <= t < shots[i + 1]:
            z = zooms[i]
            # plano largo (> 4 s) sin zoom: empuje lento 100 -> 105 %
            d = shots[i + 1] - shots[i]
            if z == 1.0 and d > 4:
                z = 1.0 + 0.05 * (t - shots[i]) / d
            return z
    return 1.0


# ------------------------------------------------------------- 4. color
def sample_frames(path, n=24):
    out = []
    for t in np.linspace(0.2, max(0.3, IDUR - 0.2), n):
        r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1",
                            "-vf", "scale=180:-2", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           capture_output=True)
        if r.stdout:
            out.append(np.frombuffer(r.stdout, np.uint8).reshape(-1, 3))
    return np.concatenate(out).astype(np.float32)


C = P["color"]
pct = C["percentiles"]
px = sample_frames(a.entrada)
luts = []
for i, c in enumerate("rgb"):
    src = np.percentile(px[:, i], pct)
    dst = np.array(C["curvas_rgb"][c])
    xs = np.concatenate([[0], np.maximum.accumulate(src), [255]])
    ys = np.concatenate([[0], np.maximum.accumulate(dst), [255]])
    xs = xs + np.arange(len(xs)) * 1e-3  # estrictamente creciente
    luts.append(np.clip(np.interp(np.arange(256), xs, ys), 0, 255).astype(np.uint8))
mapped = np.stack([luts[i][px[:, i].astype(np.uint8)] for i in range(3)], 1).astype(np.float32)
mx, mn = mapped.max(1), mapped.min(1)
sat_now = float(np.where(mx > 0, (mx - mn) / (mx + 1e-6), 0).mean())
SAT = float(np.clip(C["saturacion_media"] / (sat_now + 1e-6), 0.6, 1.6))


def grade(f):
    g = np.stack([luts[i][f[..., i]] for i in range(3)], -1)
    if abs(SAT - 1) > 0.03:
        gf = g.astype(np.float32)
        y = gf @ np.array([0.299, 0.587, 0.114], np.float32)
        gf = y[..., None] + (gf - y[..., None]) * SAT
        g = np.clip(gf, 0, 255).astype(np.uint8)
    return g


# ------------------------------------------------------------- 5. subtítulos
def hex2rgb(h):
    h = (h or "#FFFFFF").lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def load_font(name, size):
    n = name.lower().replace(" ", "-")
    alias = {"extrabold": "800", "black": "900", "bold": "700", "regular": "400"}
    for k, v in alias.items():
        n = n.replace(k, v)
    for cand in (n, n + "-800", n.rsplit("-", 1)[0] + "-800"):
        p = os.path.join(a.fuentes, cand + ".woff")
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    print(f"AVISO: fuente '{name}' no encontrada en {a.fuentes}; uso DejaVu Sans Bold.", file=sys.stderr)
    return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)


FONT = load_font(SUB.get("fuente", "archivo-800"), int(SUB.get("tamano", 78)))
TXT = hex2rgb(SUB.get("color_texto"))
HL = hex2rgb(SUB.get("color_resalte") or "#7FE0C4")
INK = hex2rgb(SUB.get("color_texto_en_caja", "#16161A"))
MODE = SUB.get("palabra_activa", "caja")
NPER = int(SUB.get("palabras_por_subtitulo", 3))
UP = SUB.get("mayusculas", False)
CY = int(SUB.get("posicion_y", 0.6) * H)
MAXW = int(W * 0.78)

# grupos de N palabras, cortando también en fin de frase
groups, cur = [], []
for i, w in enumerate(nwords):
    cur.append(i)
    if len(cur) >= NPER or w["w"][-1:] in ".?!,;:":
        groups.append(cur); cur = []
if cur:
    groups.append(cur)


def clean(s):
    s = s.strip(" ,;:")
    return s.upper() if UP else s


_cache = {}


def caption_layer(gi, active):
    key = (gi, active)
    if key in _cache:
        return _cache[key]
    ids = groups[gi]
    toks = [clean(nwords[i]["w"]) for i in ids]
    sp = FONT.getlength(" ")
    # partir en líneas que quepan
    lines, line = [], []
    for j, tk in enumerate(toks):
        test = " ".join(toks[x] for x in line + [j])
        if line and FONT.getlength(test) > MAXW:
            lines.append(line); line = []
        line.append(j)
    lines.append(line)
    asc, desc = FONT.getmetrics()
    lh = int((asc + desc) * 1.05)
    padx, pady = int(FONT.size * 0.18), int(FONT.size * 0.08)
    lay = Image.new("RGBA", (W, lh * len(lines) + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    boxes = []
    for li, ln in enumerate(lines):
        total = sum(FONT.getlength(toks[j]) for j in ln) + sp * (len(ln) - 1)
        x = (W - total) / 2
        y = 20 + li * lh
        for j in ln:
            wl = FONT.getlength(toks[j])
            if ids[j] == active and MODE == "caja":
                boxes.append((x - padx, y + pady, x + wl + padx, y + asc + desc - pady))
            x += wl + sp
    txt = Image.new("RGBA", lay.size, (0, 0, 0, 0))
    dt = ImageDraw.Draw(txt)
    for li, ln in enumerate(lines):
        total = sum(FONT.getlength(toks[j]) for j in ln) + sp * (len(ln) - 1)
        x = (W - total) / 2
        y = 20 + li * lh
        for j in ln:
            act = ids[j] == active
            col = INK if (act and MODE == "caja") else HL if (act and MODE == "color") else TXT
            sw = int(SUB.get("contorno", 0))
            dt.text((x, y), toks[j], font=FONT, fill=col + (255,),
                    stroke_width=sw, stroke_fill=(0, 0, 0, 255) if sw else None)
            x += FONT.getlength(toks[j]) + sp
    # sombra suave
    shadow_r = int(SUB.get("sombra", 6))
    if shadow_r:
        a_ = txt.split()[3].point(lambda v: v * 150 // 255)
        sh = Image.new("RGBA", txt.size, (0, 0, 0, 255)); sh.putalpha(a_)
        sh = sh.filter(ImageFilter.GaussianBlur(shadow_r))
        lay.alpha_composite(sh, (0, 4))
    for b in boxes:
        d.rounded_rectangle(b, radius=int(FONT.size * 0.18), fill=HL + (255,))
    lay.alpha_composite(txt)
    _cache[key] = (lay, CY - lay.height // 2)
    return _cache[key]


def caption_at(t):
    for gi, ids in enumerate(groups):
        s = nwords[ids[0]]["s"]
        e = nwords[groups[gi + 1][0]]["s"] if gi + 1 < len(groups) else min(nwords[ids[-1]]["e"] + 0.3, NDUR - 0.05)
        if s <= t < e:
            act = ids[0]
            for i in ids:
                if nwords[i]["s"] <= t:
                    act = i
            return caption_layer(gi, act)
    return None


# ------------------------------------------------------------- render
sel = "+".join(f"between(t,{s:.3f},{e:.3f})" for s, e in keep)
# rellena 9:16 desde cualquier formato (recorte centrado)
fit = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
vf = f"select='{sel}',setpts=N/FRAME_RATE/TB,fps={FPS},{fit}" if len(keep) > 1 or keep[0] != (0.0, IDUR) \
    else f"fps={FPS},{fit}"


def process(f, t):
    img = Image.fromarray(grade(f))
    z = zoom_at(t)
    if z > 1.001:
        cw, ch = W / z, H / z
        cx = W / 2
        cy = min(max(H * a.ancla_y, ch / 2), H - ch / 2)
        img = img.resize((W, H), Image.BICUBIC, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))
    cap = caption_at(t) if nwords else None
    if cap:
        img = img.convert("RGBA")
        img.alpha_composite(cap[0], (0, max(0, cap[1])))
        img = img.convert("RGB")
    return img


dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", a.entrada, "-vf", vf, "-an",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
size = W * H * 3

if a.prueba:
    want = sorted(a.prueba); n = 0
    while want:
        b = dec.stdout.read(size)
        if len(b) < size:
            break
        t = n / FPS
        if t >= want[0]:
            process(np.frombuffer(b, np.uint8).reshape(H, W, 3), t).save(f"{a.salida}_{want[0]:.1f}s.jpg", quality=88)
            want.pop(0)
        n += 1
    dec.kill()
    sys.exit(0)

# audio cortado igual que el vídeo + normalizado
if HAS_AUDIO:
    asel = sel if len(keep) > 1 or keep[0] != (0.0, IDUR) else "1"
    run(["ffmpeg", "-v", "error", "-y", "-i", a.entrada, "-vn", "-af",
         f"aselect='{asel}',asetpts=N/SR/TB,afftdn=nf=-30,loudnorm=I=-14:TP=-1.5:LRA=7",
         "-ar", "48000", f"{tmp}/audio.wav"])
enc_cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-"]
if HAS_AUDIO:
    enc_cmd += ["-i", f"{tmp}/audio.wav", "-c:a", "aac", "-b:a", "192k", "-shortest"]
enc_cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", a.salida]
enc = subprocess.Popen(enc_cmd, stdin=subprocess.PIPE)
n = 0
while True:
    b = dec.stdout.read(size)
    if len(b) < size:
        break
    enc.stdin.write(process(np.frombuffer(b, np.uint8).reshape(H, W, 3), n / FPS).tobytes())
    n += 1
enc.stdin.close(); enc.wait(); dec.wait()

informe = {
    "duracion_original": round(IDUR, 2), "duracion_nueva": round(n / FPS, 2),
    "cortes_de_pausa": len(jumps), "hueco_max_usado": max_gap,
    "cambios_de_plano": changes, "plano_medio_nuevo": round(NDUR / (len(changes) + 1), 2),
    "plano_medio_referencia": P["ritmo"]["plano_medio"],
    "saturacion_x": round(SAT, 2), "subtitulos": len(groups), "palabras": len(nwords),
}
json.dump({"informe": informe, "palabras": nwords}, open(a.salida + ".json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(informe, indent=1, ensure_ascii=False))
