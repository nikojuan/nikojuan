"""Cut the voice-over: drop everything before `--start`, remove pauses > 0.1 s.

Inputs: voice wav (mono), words.json from the transcription
([{"w": word, "s": start, "e": end}, ...], times in the original file).
Outputs: the cut voice wav and timing.json with every word re-timed.

Usage: python3 voice_edit.py voice.wav words.json out.wav timing.json --start 3.5 --lead 0.15
"""
import argparse
import json
import wave

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("voice"); ap.add_argument("words"); ap.add_argument("out"); ap.add_argument("timing")
ap.add_argument("--start", type=float, default=0.0, help="discard audio before this time (e.g. a misread line)")
ap.add_argument("--lead", type=float, default=0.15, help="silence kept before the first word")
ap.add_argument("--max-gap", type=float, default=0.10, help="pauses longer than this are cut")
ap.add_argument("--pad", type=float, default=0.05, help="audio kept either side of each speech chunk")
ap.add_argument("--thresh-db", type=float, default=-38.0)
a = ap.parse_args()

w = wave.open(a.voice)
sr = w.getframerate()
x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
hop = int(0.01 * sr)
rms = np.sqrt(np.convolve(x ** 2, np.ones(hop) / hop, "same"))[::hop]
db = 20 * np.log10(rms + 1e-9)
loud = db > a.thresh_db

# speech chunks (10 ms frames), after --start
chunks, cur = [], None
for i, v in enumerate(loud):
    t = i * 0.01
    if t < a.start:
        continue
    if v and cur is None:
        cur = [t, t]
    elif v:
        cur[1] = t
    elif cur is not None and t - cur[1] > a.max_gap:
        chunks.append(cur); cur = None
if cur:
    chunks.append(cur)
chunks = [(max(a.start, s - a.pad), e + 0.01 + a.pad) for s, e in chunks if e - s > 0.04]
# merge chunks that now overlap / sit within max_gap
merged = []
for s, e in chunks:
    if merged and s - merged[-1][1] <= a.max_gap:
        merged[-1][1] = e
    else:
        merged.append([s, e])

fade = int(0.008 * sr)
pieces = [np.zeros(int(a.lead * sr), np.float32)]
mapping = []  # (orig_start, orig_end, new_start)
pos = a.lead
for s, e in merged:
    seg = x[int(s * sr): int(e * sr)].copy()
    seg[:fade] *= np.linspace(0, 1, fade)
    seg[-fade:] *= np.linspace(1, 0, fade)
    pieces.append(seg)
    mapping.append((s, e, pos))
    pos += len(seg) / sr
out = np.concatenate(pieces)


def remap(t):
    for s, e, n in mapping:
        if t < s:
            return n  # word starting inside a removed gap snaps to the next chunk
        if t <= e:
            return n + (t - s)
    return pos


words = json.load(open(a.words))
timed = []
for wd in words:
    if wd["e"] <= a.start:
        continue
    timed.append(dict(w=wd["w"], s=round(remap(max(wd["s"], a.start)), 3), e=round(remap(wd["e"]), 3)))

with wave.open(a.out, "wb") as o:
    o.setnchannels(1); o.setsampwidth(2); o.setframerate(sr)
    o.writeframes((np.clip(out, -1, 1) * 32767).astype(np.int16).tobytes())
json.dump(dict(duration=round(pos, 3), words=timed), open(a.timing, "w"), ensure_ascii=False, indent=1)
print(f"original {len(x)/sr:.2f}s -> cut {pos:.2f}s, {len(merged)} chunks, {len(timed)} words")
