import math

import numpy as np

MG_TO_MMS2 = 9.80665


def plan(dist, speed, accel, dwell, repeats):
    v = min(speed, math.sqrt(dist * accel))
    ta = v / accel
    tc = dist / v - ta
    t_move = 2 * ta + tc
    moves = []
    t = 0.
    for rep in range(repeats):
        for sign in (1, -1):
            moves.append((t, sign, rep))
            t += t_move + dwell
    return moves, ta, tc, t


def move_template(ta, tc, accel, fs):
    t = np.arange(int(math.ceil((2 * ta + tc) * fs))) / fs
    a = np.zeros(len(t))
    a[t < ta] = accel
    a[t >= ta + tc] = -accel
    return a


def xcorr(a, b):
    n = len(a) + len(b)
    c = np.fft.irfft(np.fft.rfft(a, n) * np.conj(np.fft.rfft(b, n)), n)
    return c[:len(a) - len(b) + 1]


def bandpass(acc, fs, lo, hi):
    f = np.fft.rfftfreq(len(acc), 1 / fs)
    gain = (np.clip((f - lo / 2) / (lo / 2), 0, 1)
            * np.clip((1.5 * hi - f) / (0.5 * hi), 0, 1))
    return np.fft.irfft(np.fft.rfft(acc, axis=0) * gain[:, None],
                        len(acc), axis=0)


def to_mms2(samples, fs, band=None):
    acc = samples.astype(float)
    acc -= np.median(acc, axis=0)
    acc *= MG_TO_MMS2
    if band:
        acc = bandpass(acc, fs, *band)
    return acc


def analyze(samples, fs, moves, ta, tc, accel, offset, window, search=0.05,
            band=None):
    raw = to_mms2(samples, fs)
    acc = bandpass(raw, fs, *band) if band else raw

    tmpl = move_template(ta, tc, accel, fs)
    full = np.zeros(int(round(moves[-1][0] * fs)) + len(tmpl))
    for t0, sign, _ in moves:
        i = int(round(t0 * fs))
        full[i:i + len(tmpl)] += sign * tmpl
    if len(acc) < len(full):
        raise ValueError(f"capture too short ({len(acc)} samples, "
                         f"moves need {len(full)})")

    best = None
    for ax in range(3):
        c = xcorr(raw[:, ax], full)
        k = int(np.argmax(np.abs(c)))
        if best is None or abs(c[k]) > best[0]:
            best = (abs(c[k]), ax, k, np.sign(c[k]))
    _, ax, lag, sgn = best
    along = raw[:, ax] * sgn

    s = int(search * fs)
    drift = 0
    starts = []
    results = []
    for t0, sign, rep in moves:
        planned = lag + int(round(t0 * fs))
        lo = max(planned + drift - s, 0)
        seg = along[lo:planned + drift + s + len(tmpl)]
        if len(seg) < len(tmpl):
            break
        start = lo + int(np.argmax(np.correlate(seg, sign * tmpl, 'valid')))
        drift = start - planned
        starts.append((t0, start))

        i0 = start + len(tmpl) + int(offset * fs)
        i1 = i0 + int(window * fs)
        if i1 > len(acc):
            break
        w = acc[i0:i1]
        total = math.sqrt(np.mean(np.sum(w ** 2, axis=1)))
        al = math.sqrt(np.mean(w[:, ax] ** 2))
        results.append({
            'direction': '+' if sign > 0 else '-',
            'repeat': rep,
            'rms_along': al,
            'rms_cross': math.sqrt(max(total ** 2 - al ** 2, 0.)),
            'rms_total': total,
            'start': start,
            'stop': start + len(tmpl),
            'window': (i0, i1),
        })

    fs_est = fs
    if len(starts) > 1:
        fs_est = (starts[-1][1] - starts[0][1]) / (starts[-1][0] - starts[0][0])
    return results, ax, fs_est
