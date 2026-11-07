"""Original, royalty-free lo-fi / minimal-pop bed synthesised from scratch.

75 BPM (feels 150 with 8th-note hats), Fmaj7 - Em7 - Dm7 - Cmaj7, one bar each
(3.2 s, the same length as most scenes). The outro bar is lifted ~+3 dB.

Usage: python3 music.py out.wav [duration_s]
"""
import math
import sys
import wave

import numpy as np

SR = 48000
OUT = sys.argv[1]
DUR = float(sys.argv[2]) if len(sys.argv) > 2 else 26.0
BPM = 75
BEAT = 60 / BPM
BAR = 4 * BEAT
N = int(DUR * SR)
rng = np.random.default_rng(3)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


CHORDS = [  # (bass, voicing)
    (41, [57, 60, 64, 69]),  # Fmaj7
    (40, [55, 59, 62, 67]),  # Em7
    (38, [57, 60, 62, 65]),  # Dm7
    (36, [55, 59, 60, 64]),  # Cmaj7
]

mix = {k: np.zeros(N, np.float32) for k in ("keys", "bass", "drums", "bell")}


def add(track, t0, sig):
    i = int(t0 * SR)
    if i >= N:
        return
    j = min(N, i + len(sig))
    mix[track][i:j] += sig[: j - i]


def epiano(freq, dur, vel=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    env = np.exp(-t * 2.2) * np.minimum(1, t / 0.008)
    trem = 1 + 0.08 * np.sin(2 * math.pi * 4.5 * t)
    s = (np.sin(2 * math.pi * freq * t) + 0.35 * np.sin(2 * math.pi * 2 * freq * t) * np.exp(-t * 5)
         + 0.12 * np.sin(2 * math.pi * 3 * freq * t) * np.exp(-t * 9))
    return (s * env * trem * vel * 0.10).astype(np.float32)


def bass(freq, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    env = np.minimum(1, t / 0.01) * np.exp(-t * 1.4)
    s = np.sin(2 * math.pi * freq * t) + 0.25 * np.sin(2 * math.pi * 2 * freq * t)
    return (np.tanh(1.5 * s) * env * 0.30).astype(np.float32)


def kick():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = 50 + 90 * np.exp(-t * 30)
    return (np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t * 9) * 0.55).astype(np.float32)


def snare():
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    noise = noise - np.convolve(noise, np.ones(8) / 8, "same")  # rough high-pass
    body = np.sin(2 * math.pi * 190 * t) * np.exp(-t * 25)
    return ((noise * 0.5 * np.exp(-t * 16) + body * 0.4) * 0.30).astype(np.float32)


def hat(open_=False):
    n = int((0.12 if open_ else 0.04) * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    noise = noise - np.convolve(noise, np.ones(4) / 4, "same")
    return (noise * np.exp(-t * (25 if open_ else 80)) * 0.09).astype(np.float32)


def bell(freq, dur=0.9):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.sin(2 * math.pi * freq * t) + 0.3 * np.sin(2 * math.pi * freq * 2.76 * t) * np.exp(-t * 6)
    return (s * np.exp(-t * 4) * np.minimum(1, t / 0.004) * 0.07).astype(np.float32)


MELODY = [  # (beat offset in bar, semitone above chord root voicing top) per chord
    [(0.5, 72), (1.5, 76), (2.5, 74), (3.0, 72)],
    [(0.5, 71), (1.5, 74), (2.5, 71), (3.5, 67)],
    [(0.5, 69), (1.5, 72), (2.0, 74), (3.0, 72)],
    [(0.5, 67), (1.5, 71), (2.5, 72), (3.5, 76)],
]

n_bars = int(math.ceil(DUR / BAR))
for b in range(n_bars):
    t_bar = b * BAR
    root, voicing = CHORDS[b % 4]
    # keys: chord on 1 (slightly strummed) and a push on the "and" of 2
    for k, note in enumerate(voicing):
        add("keys", t_bar + k * 0.012, epiano(midi(note), BAR * 0.9))
        add("keys", t_bar + 1.5 * BEAT + k * 0.01, epiano(midi(note), BEAT * 1.2, 0.45))
    # bass: root on 1, fifth on the "and" of 3
    add("bass", t_bar, bass(midi(root), 2.4 * BEAT))
    add("bass", t_bar + 2.5 * BEAT, bass(midi(root + 7), 1.3 * BEAT))
    # drums from bar 1 (first bar is keys + hats only, so the hook breathes)
    for beat in range(4):
        tb = t_bar + beat * BEAT
        if b > 0 and beat in (0, 2):
            add("drums", tb, kick())
        if b > 0 and beat == 2:
            add("drums", tb + 0.5 * BEAT, kick() * 0.6)
        if beat in (1, 3) and b > 0:
            add("drums", tb, snare())
        add("drums", tb, hat())
        add("drums", tb + 0.5 * BEAT, hat(open_=(beat == 3)))
    # bell melody from bar 2
    if b >= 2:
        for off, note in MELODY[b % 4]:
            add("bell", t_bar + off * BEAT, bell(midi(note)))


def lowpass(x, a):
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):  # one-pole; fine for 26 s
        acc += a * (v - acc)
        y[i] = acc
    return y


keys = lowpass(mix["keys"], 0.18)  # warm, "lo-fi" top end
out = keys + mix["bass"] + mix["drums"] * 0.9 + mix["bell"]

# side-chain style pump on the keys from the kick grid
t = np.arange(N) / SR
pump = 1 - 0.25 * np.exp(-((t % (BEAT * 2)) / 0.12))
out = out * pump

# vinyl-ish noise floor
out += (rng.standard_normal(N) * 0.0025).astype(np.float32)

# arrangement gain: lift the outro (from 22.6 s) ~+3 dB, fade in/out
gain = np.ones(N, np.float32)
gain[t >= 22.6] = 1.41
gain *= np.minimum(1, t / 0.25)
gain *= np.clip((DUR - t) / 0.9, 0, 1)
out = np.tanh(out * gain * 1.2) * 0.8

with wave.open(OUT, "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((np.clip(out, -1, 1) * 32767).astype(np.int16).tobytes())
