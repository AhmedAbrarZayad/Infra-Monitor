import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile

SR = 44100
DUR = 21.0
BEAT = 0.5  # 120 bpm
N = int(SR * DUR)
rng = np.random.default_rng(7)

def m2f(n): return 440.0 * 2 ** ((n - 69) / 12)
def buf(): return np.zeros(N)
def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], 'band', fs=SR, output='sos'), x)

def place(dst, src, t, g=1.0):
    i = int(round(t * SR))
    if i >= N: return
    n = min(len(src), N - i)
    dst[i:i + n] += src[:n] * g

def env(n, a, d):
    t = np.arange(n) / SR
    e = np.exp(-t / d)
    na = max(1, int(a * SR)); e[:na] *= np.linspace(0, 1, na)
    return e

# --- instruments
def kick():
    n = int(.45 * SR); t = np.arange(n) / SR
    f = 45 + 80 * np.exp(-t / .045)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t / .22) + 0.25 * np.sin(ph * 2) * np.exp(-t / .02)

def snare():
    n = int(.3 * SR); t = np.arange(n) / SR
    nz = bp(rng.standard_normal(n), 1200, 6000) * np.exp(-t / .09)
    return 0.6 * nz + 0.35 * np.sin(2 * np.pi * 190 * t) * np.exp(-t / .05)

def hat(d=.035):
    n = int(.15 * SR); t = np.arange(n) / SR
    return hp(rng.standard_normal(n), 8000) * np.exp(-t / d)

def saw(f, n, det=0.0):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k in range(1, 14):
        if f * k > 9000: break
        out += np.sin(2 * np.pi * f * k * t * (1 + det)) / k
    return out

def pluck(f, d=.18):
    n = int(.6 * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) + .35 * np.sin(4 * np.pi * f * t) + .12 * np.sin(6 * np.pi * f * t)
    return x * env(n, .003, d)

def bell(f, d=.5):
    n = int(1.4 * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) + .4 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / .15)
    return x * env(n, .002, d)

def riser(length, f0=400, f1=6000):
    n = int(length * SR); t = np.linspace(0, 1, n)
    nz = rng.standard_normal(n)
    out = np.zeros(n); blk = 2048
    for s in range(0, n, blk):
        fc = f0 * (f1 / f0) ** t[s]
        seg = nz[max(0, s - 512):s + blk]
        y = bp(seg, fc * .7, min(fc * 1.4, 20000))
        out[s:s + blk] = y[-len(out[s:s + blk]):]
    return out * t ** 2

def thud():
    n = int(.8 * SR); t = np.arange(n) / SR
    f = 38 + 60 * np.exp(-t / .08)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .35)

# --- harmony: Am F C G per 2s bar
CH = [[57, 60, 64], [53, 57, 60], [55, 60, 64], [55, 59, 62]]
RT = [33, 29, 36, 31]
def bar(t): return int(t // 2) % 4

drums, bass, pad, arp, sfx, sfxwet = buf(), buf(), buf(), buf(), buf(), buf()
K, S = kick(), snare()

steps16 = int(DUR / (BEAT / 4))
for s in range(steps16):
    t = s * BEAT / 4
    b16 = s % 4; beat = s // 4
    # hook 0-3: hats + ticking 16ths, no kick
    if t < 3.0:
        place(drums, hat(.02), t, .10 if b16 else .16)
        if b16 == 0 and t >= 1.0: place(drums, K, t, .45)  # heartbeat after the spike
        continue
    if 20.0 <= t: continue
    if t >= 18.0:  # outro: kick on beats, open hat offbeats
        if b16 == 0 and t < 20.0: place(drums, K, t, .9 if t == 18.0 else .7)
        if b16 == 2 and t < 20.0: place(drums, hat(.08), t, .18)
        continue
    if b16 == 0: place(drums, K, t, .9)
    if b16 == 2: place(drums, hat(.05), t, .2)
    else: place(drums, hat(), t, .08)
    if t >= 6.0 and b16 == 0 and beat % 2 == 1: place(drums, S, t, .38)
    if 17.5 <= t < 18.0: place(drums, S, t, .12 + .3 * (t - 17.5) * 2)  # fill

# kick envelope for sidechain
side = np.ones(N)
for s in range(int(DUR / BEAT)):
    t = s * BEAT
    if t >= 3.0 and t < 20.0 or (1.0 <= t < 3.0):
        i = int(t * SR); n = min(int(.25 * SR), N - i)
        side[i:i + n] = np.minimum(side[i:i + n], 1 - .75 * np.exp(-np.arange(n) / SR / .07))

# bass: 8ths
for s in range(int(DUR / (BEAT / 2))):
    t = s * BEAT / 2
    if t >= 20.0: break
    f = m2f(RT[bar(t)])
    n = int(.24 * SR)
    note = lp(saw(f, n), 300 if t >= 3 else 160) * env(n, .005, .12)
    g = .55 if t >= 3 else .3
    if 18.0 <= t: note = lp(saw(m2f(33), int(1.0 * SR)), 260) * env(int(1.0 * SR), .005, .6); place(bass, note, 18.0, .7); break
    place(bass, note, t, g)
bass *= side

# pad: chord per bar (and final Am at 18)
for k in range(10):
    t0 = k * 2.0
    chord = CH[bar(t0)] if t0 < 18 else [57, 60, 64, 69]
    L = 2.1 if t0 < 18 else 3.0
    n = int(L * SR)
    x = sum(saw(m2f(m), n, d) for m in chord for d in (-.004, .004))
    x = lp(x, 900 if t0 >= 3 else 500 + 200 * (t0 / 3))
    e = np.minimum(1, np.arange(n) / (.25 * SR)) * np.minimum(1, (n - np.arange(n)) / (.3 * SR))
    place(pad, x * e, t0, .06)
    if t0 >= 18: break
pad *= .5 + .5 * side

# arp: 16ths 3-18s
for s in range(int(DUR / (BEAT / 4))):
    t = s * BEAT / 4
    if t < 3.0 or t >= 18.0: continue
    ch = CH[bar(t)]
    pat = [0, 1, 2, 1, 0, 2, 1, 2]
    m = ch[pat[s % 8]] + 12 + (12 if (s % 16) in (6, 14) else 0)
    place(arp, pluck(m2f(m), .12), t, .11 if t < 6 else .14)

# --- SFX (same key, on grid)
for c in (3.0, 6.0, 10.0, 14.0, 18.0):
    place(sfxwet, riser(1.0, 300, 5000), c - 1.0, .10)
place(sfxwet, riser(1.5, 200, 7000), 1.5, .07)          # hook tension into reveal
place(sfx, bell(m2f(81), .35), 1.0, .22)                # anomaly alert A5 / E6
place(sfx, bell(m2f(88), .35), 1.25, .2)
place(sfx, thud(), 3.0, .5)                             # reveal drop
place(sfx, bell(m2f(76), .8), 3.0, .14)
# typing ticks on 16ths
for t in np.arange(6.5, 7.0, .125): place(sfx, hat(.012), t, .12)
for t in np.arange(8.0, 8.625, .125): place(sfx, hat(.01), t, .09)
for t in (7.5, 9.0, 15.0): place(sfx, pluck(m2f(88), .05), t, .2)   # clicks
place(sfx, bell(m2f(76), .3), 7.75, .14); place(sfx, bell(m2f(81), .4), 8.0, .14)  # ready
place(sfx, bell(m2f(84), .3), 9.0, .12)                                           # copied
place(sfx, bell(m2f(81), .3), 11.0, .18); place(sfx, bell(m2f(76), .3), 11.25, .15)  # anomaly
place(sfx, thud(), 12.0, .3)                                                      # incident card
for t in np.arange(15.5, 17.0, .25): place(sfx, pluck(m2f(76 + [0, 3, 7, 12][int(t * 4) % 4]), .06), t, .04)  # streaming shimmer
place(sfx, thud(), 18.0, .6)
for i, t in enumerate((18.25, 18.75, 19.25)): place(sfx, bell(m2f([69, 72, 76][i]), .5), t, .2)

# --- reverb bus
ir_n = int(1.6 * SR)
ir = rng.standard_normal(ir_n) * np.exp(-np.arange(ir_n) / SR / .45)
ir = lp(ir, 5000); ir /= np.sqrt(np.sum(ir ** 2))
wet_in = pad * .5 + arp * .7 + sfx * .6 + sfxwet
wet = fftconvolve(wet_in, ir)[:N] * .35

wl = fftconvolve(wet_in, np.roll(ir, 37))[:N] * .35
dry = drums * .9 + bass + pad + arp + sfx * .85 + sfxwet * .6
st = np.stack([dry + wet, dry + .6 * wet + .4 * wl], 1)
st = hp(st.T, 30).T
fade = np.ones(N); fi = int(.02 * SR); fade[:fi] = np.linspace(0, 1, fi)
fo0 = int(20.2 * SR); fade[fo0:] = np.linspace(1, 0, N - fo0) ** 1.5
st *= fade[:, None]
st /= np.max(np.abs(st)) + 1e-9
st = np.tanh(st * 1.4) / np.tanh(1.4) * .89
wavfile.write('music.wav', SR, (st * 32767).astype(np.int16))
print('ok', st.shape, float(np.max(np.abs(st))))
