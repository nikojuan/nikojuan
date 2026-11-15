"""Efectos de sonido sintetizados (whoosh en los barridos, pop en las tarjetas).

Lee timing.json y coloca cada efecto en la palabra que lo dispara; nunca hay
dos efectos a menos de 1 s.  Uso: python3 sfx.py timing.json sfx.wav
"""
import json
import sys
import wave

import numpy as np

SR = 48000
tm = json.load(open(sys.argv[1]))
ws = [w["s"] for w in tm["words"]]
out = np.zeros(int(tm["duration"] * SR), np.float32)
rng = np.random.default_rng(5)


def whoosh(d=0.32):
    n = int(d * SR); t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    # band-limited noise: running mean whose window shrinks -> rising brightness
    k = 48; lp = np.convolve(noise, np.ones(k) / k, "same")
    env = np.sin(np.pi * t / d) ** 2
    return (lp * 3.2 + noise * 0.08 * t / d) * env * 0.5


def pop(d=0.09):
    n = int(d * SR); t = np.arange(n) / SR
    f = 620 * np.exp(-t * 14) + 260
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 55) * 0.6


events = [(ws[21] - 0.16, whoosh), (ws[27] - 0.18, whoosh), (ws[50] - 0.16, whoosh), (ws[67] - 0.16, whoosh),
          (ws[77] - 0.1, whoosh), (0.1, pop), (ws[8], pop), (ws[12], pop), (ws[39], pop), (ws[48], pop),
          (ws[54], pop), (ws[61], pop), (ws[81] + 0.55, pop)]
events.sort(key=lambda e: e[0])
last = -9
for t, fn in events:
    if t - last < 1.0:
        continue
    s = fn(); i = int(max(0, t) * SR)
    out[i:i + len(s)] += s[: len(out) - i]
    last = t
w = wave.open(sys.argv[2], "w"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((np.clip(out, -1, 1) * 32767).astype(np.int16).tobytes())
