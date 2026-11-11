"""Analiza un vídeo de referencia y guarda su "perfil de edición".

Mide, sin ayuda manual:
  - Ritmo: cada corte (tiempo), duración de cada plano, media/mediana, cortes por segundo.
  - Pausas: huecos de silencio que quedan en la voz (lo "apretada" que va la edición).
  - Colores: brillo, contraste, saturación, temperatura, y la curva de cada canal R/G/B
    (percentiles) para copiar el etalonado con una LUT.
  - Subtítulos: posición vertical de la franja de texto, colores dominantes del texto,
    y una hoja de fotogramas + recortes para revisar a ojo la fuente, mayúsculas y
    palabras por subtítulo.

Lo que no se puede medir de forma fiable (fuente exacta, palabras por subtítulo, efecto
de la palabra activa) va en la sección "subtitulos" del JSON con valores propuestos;
se revisan mirando `hoja.jpg` y se corrigen a mano antes de aplicar.

Uso: python3 analizar_referencia.py referencia.mp4 carpeta_salida/ [--excluir x0,y0,x1,y1 ...]
Salida: carpeta_salida/perfil.json, hoja.jpg, subs_*.jpg
"""
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

REF, OUT = sys.argv[1], sys.argv[2]
# --excluir x0,y0,x1,y1 (fracciones 0-1, repetible): zonas con gráficos fijos encima del vídeo
# (paneles, logos) que no deben contar para el color
EXCL = [tuple(float(v) for v in sys.argv[i + 1].split(",")) for i, a_ in enumerate(sys.argv) if a_ == "--excluir"]
os.makedirs(OUT, exist_ok=True)


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,width,height,r_frame_rate:format=duration",
                        "-of", "json", path], capture_output=True, text=True, check=True)
    j = json.loads(r.stdout)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    n, d = v["r_frame_rate"].split("/")
    has_audio = any(s["codec_type"] == "audio" for s in j["streams"])
    return int(v["width"]), int(v["height"]), float(n) / float(d), float(j["format"]["duration"]), has_audio


def frames(path, w, h, fps=None):
    """Yield RGB frames (h, w, 3) uint8, scaled to w x h."""
    vf = f"scale={w}:{h}:flags=area" + (f",fps={fps}" if fps else "")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", vf, "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    size = w * h * 3
    while True:
        b = p.stdout.read(size)
        if len(b) < size:
            break
        yield np.frombuffer(b, np.uint8).reshape(h, w, 3)
    p.wait()


W0, H0, FPS, DUR, HAS_AUDIO = probe(REF)

# ------------------------------------------------------------------ cortes
SW, SH = 72, 128  # miniatura para detectar cortes
diffs, hist_d, small = [], [], []
prev = prev_h = None
for f in frames(REF, SW, SH):
    g = f.astype(np.float32)
    hst = np.concatenate([np.histogram(f[..., c], 16, (0, 256))[0] for c in range(3)]).astype(np.float32)
    hst /= hst.sum()
    if prev is not None:
        diffs.append(np.abs(g - prev).mean() / 255)
        hist_d.append(0.5 * np.abs(hst - prev_h).sum())
    else:
        diffs.append(0.0); hist_d.append(0.0)
    prev, prev_h = g, hst
    small.append(f)
diffs, hist_d = np.array(diffs), np.array(hist_d)
score = diffs + hist_d
# umbral adaptativo: muy por encima del movimiento normal (zooms, gestos)
med = np.median(score)
mad = np.median(np.abs(score - med)) + 1e-6
thr = max(0.12, med + 12 * mad)
cut_idx = []
for i in range(1, len(score)):
    local = score[max(0, i - 3): i + 4]
    if score[i] > thr and score[i] == local.max():
        if (not cut_idx or i - cut_idx[-1] >= int(0.25 * FPS)) and i / FPS < DUR - 0.2:
            cut_idx.append(i)
cuts = [round(i / FPS, 3) for i in cut_idx]
bounds = [0.0] + cuts + [round(DUR, 3)]
shots = [round(b - a, 3) for a, b in zip(bounds, bounds[1:]) if b - a > 0.02]

# zooms/empujes dentro de cada plano: cambio de escala entre principio y final
def zoom_ratio(a, b):
    """Estimación barata: compara la energía de bordes (más zoom = bordes más grandes y escasos)."""
    def edge(f):
        g = f.mean(2)
        return np.abs(np.diff(g, axis=0)).mean() + np.abs(np.diff(g, axis=1)).mean()
    return edge(a) / (edge(b) + 1e-6)

# ------------------------------------------------------------------ pausas (voz)
gaps = []
if HAS_AUDIO:
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", REF, "-af", "silencedetect=n=-35dB:d=0.06",
                        "-f", "null", "-"], capture_output=True, text=True)
    st = None
    for line in r.stderr.splitlines():
        if "silence_start" in line:
            st = float(line.split("silence_start:")[1].split()[0])
        elif "silence_end" in line and st is not None:
            en = float(line.split("silence_end:")[1].split()[0])
            if st > 0.05 and en < DUR - 0.05:
                gaps.append(round(en - st, 3))
            st = None

# ------------------------------------------------------------------ color
CW, CH = 180, 320
samp = list(frames(REF, CW, CH, fps=4))
# el etalonado se mide en los planos "normales": se descartan los fotogramas cuyo brillo
# se aleja mucho de la mediana (tarjetas de papel, pantallas en blanco, fundidos a negro)
fl = np.array([f.mean() for f in samp])
normal = [f for f, m in zip(samp, fl) if abs(m - np.median(fl)) < 40] or samp
mask = np.ones((CH, CW), bool)
for x0, y0, x1, y1 in EXCL:
    mask[int(y0 * CH):int(y1 * CH), int(x0 * CW):int(x1 * CW)] = False
px = np.concatenate([f[mask] for f in normal]).astype(np.float32)
pct = [1, 5, 10, 25, 50, 75, 90, 95, 99]
curves = {c: [float(np.percentile(px[:, i], pct)[k]) for k in range(len(pct))] for i, c in enumerate("rgb")}
lum = px @ np.array([0.2126, 0.7152, 0.0722], np.float32)
mx, mn = px.max(1), px.min(1)
sat = np.where(mx > 0, (mx - mn) / (mx + 1e-6), 0)
color = {
    "brillo_medio": round(float(lum.mean()), 1),
    "contraste_std": round(float(lum.std()), 1),
    "saturacion_media": round(float(sat.mean()), 3),
    "temperatura_r_menos_b": round(float(px[:, 0].mean() - px[:, 2].mean()), 1),
    "percentiles": pct,
    "curvas_rgb": curves,
}
# paleta dominante (k-means simple)
rng = np.random.default_rng(0)
sub = px[rng.choice(len(px), min(20000, len(px)), replace=False)]
cent = sub[rng.choice(len(sub), 6, replace=False)]
for _ in range(15):
    lab = ((sub[:, None] - cent[None]) ** 2).sum(2).argmin(1)
    cent = np.array([sub[lab == k].mean(0) if (lab == k).any() else cent[k] for k in range(6)])
cnt = np.bincount(lab, minlength=6)
color["paleta"] = ["#%02X%02X%02X" % tuple(int(v) for v in cent[k]) for k in np.argsort(-cnt)]

# ------------------------------------------------------------------ subtítulos
# El texto quemado = píxeles muy claros o muy saturados con bordes fuertes que
# aparecen en muchos fotogramas. Se busca la franja horizontal donde más se concentran.
rows = np.zeros(CH)
text_px = []
for f in samp:
    g = f.astype(np.float32)
    l = g.mean(2)
    edge = np.zeros_like(l)
    edge[:, 1:] += np.abs(np.diff(l, axis=1))
    edge[1:, :] += np.abs(np.diff(l, axis=0))
    m = (edge > 60)
    rows += m.mean(1)
    text_px.append((g, m))
rows /= len(samp)
rows_s = np.convolve(rows, np.ones(9) / 9, "same")
# ignora el 5 % de arriba y abajo (bordes del vídeo)
lo, hi = int(CH * 0.05), int(CH * 0.95)
peak = lo + int(rows_s[lo:hi].argmax())
band = [peak, peak]
while band[0] > lo and rows_s[band[0]] > rows_s[peak] * 0.45:
    band[0] -= 1
while band[1] < hi and rows_s[band[1]] > rows_s[peak] * 0.45:
    band[1] += 1
# solo píxeles dentro de la franja de subtítulos
tp = np.concatenate([g[band[0]:band[1] + 1].reshape(-1, 3) for g, _ in text_px])
bright = tp[(tp.min(1) > 225)]
colorful = tp[((tp.max(1) - tp.min(1)) > 70) & (tp.max(1) > 150)]
def hexc(a):
    return "#%02X%02X%02X" % tuple(int(v) for v in np.median(a, 0)) if len(a) else None
def dominant(a, k=4):
    # color más repetido entre los saturados (cuantizado a 32 niveles)
    if len(a) < 50:
        return None
    q = (a // 32).astype(int)
    keys = q[:, 0] * 64 + q[:, 1] * 8 + q[:, 2]
    top = np.bincount(keys).argmax()
    return hexc(a[keys == top])

subs = {
    "_nota": "Medido: posicion_y y colores. Revisar a ojo en hoja.jpg y subs_*.jpg el resto.",
    "posicion_y": round((band[0] + band[1]) / 2 / CH, 3),      # 0 = arriba, 1 = abajo
    "alto_franja": round((band[1] - band[0]) / CH, 3),
    "color_texto": hexc(bright) or "#FFFFFF",
    "color_resalte": dominant(colorful),
    "fuente": "Archivo ExtraBold",          # revisar: la más parecida a la de la referencia
    "tamano": 78,                           # px sobre 1920 de alto; revisar
    "mayusculas": False,                    # revisar
    "palabras_por_subtitulo": 3,            # revisar
    "palabra_activa": "caja",               # caja | color | ninguna; revisar
    "contorno": 0, "sombra": 6,
}

# ------------------------------------------------------------------ hoja de revisión
TW = 216
thumbs_t = np.linspace(0.3, DUR - 0.3, 12)
sheet = Image.new("RGB", (TW * 6, int(TW * 16 / 9) * 2), "black")
th = int(TW * 16 / 9)
for k, t in enumerate(thumbs_t):
    i = min(int(t / 0.25), len(samp) - 1)
    im = Image.fromarray(samp[i]).resize((TW, th))
    ImageDraw.Draw(im).text((6, 6), f"{t:.1f}s", fill="yellow")
    sheet.paste(im, ((k % 6) * TW, (k // 6) * th))
sheet.save(f"{OUT}/hoja.jpg", quality=85)
# recortes de la franja de subtítulos a resolución completa
y0, y1 = max(0, band[0] / CH - 0.05), min(1, band[1] / CH + 0.05)
for k, t in enumerate(np.linspace(0.5, DUR - 0.5, 4)):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", REF, "-frames:v", "1",
                    "-vf", f"crop=iw:ih*{y1 - y0:.3f}:0:ih*{y0:.3f}", f"{OUT}/subs_{k}.jpg"], check=True)

perfil = {
    "referencia": os.path.basename(REF),
    "formato": {"ancho": W0, "alto": H0, "fps": round(FPS, 3), "duracion": round(DUR, 3)},
    "ritmo": {
        "cortes": cuts,
        "planos": shots,
        "plano_medio": round(float(np.mean(shots)), 3),
        "plano_mediana": round(float(np.median(shots)), 3),
        "plano_min": round(float(np.min(shots)), 3),
        "plano_max": round(float(np.max(shots)), 3),
        "cortes_por_segundo": round(len(cuts) / DUR, 3),
        # patrón relativo: el vídeo nuevo repite esta secuencia de duraciones escalada a su largo
        "patron_relativo": [round(s / DUR, 4) for s in shots],
    },
    "pausas": {
        "huecos": gaps,
        "hueco_max_tipico": round(float(np.percentile(gaps, 90)), 3) if gaps else 0.1,
        "hueco_medio": round(float(np.mean(gaps)), 3) if gaps else 0.1,
    },
    "color": color,
    "subtitulos": subs,
}
json.dump(perfil, open(f"{OUT}/perfil.json", "w"), indent=2, ensure_ascii=False)
print(json.dumps({k: perfil[k] for k in ("formato", "ritmo")}, indent=1)[:1500])
print("pausas:", perfil["pausas"]["hueco_max_tipico"], "| color:", {k: color[k] for k in list(color)[:4]})
print("subs:", {k: subs[k] for k in ("posicion_y", "color_texto", "color_resalte")})
