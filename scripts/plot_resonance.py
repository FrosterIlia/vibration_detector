#!/usr/bin/env python3
"""Plot a resonance_map CSV (from MAP_RESONANCES) and estimate resonances.

Window 1: three stacked PSD plots (sensor X, Y, Z). Each plot shows the
response to the X sweep and to the Y sweep. For every curve the dominant
peak (resonance frequency) is marked, and the damping ratio is estimated
with the half-power bandwidth method: zeta = (f2 - f1) / (2 * f_n), where
f1/f2 are the frequencies where the PSD falls to half of the peak value.

Window 2: resonance map over the scanned area, with the resonance frequency
and damping ratio of the X sweep (sensor X) and the Y sweep (sensor Y) at
every grid point.

The damping ratio is only indicative: the PSD is the response to a swept
excitation, not a measured transfer function.

Usage:
  python3 plot_resonance.py resonance_map_XXXX.csv               # mean over all points
  python3 plot_resonance.py resonance_map_XXXX.csv --point 100 100
  python3 plot_resonance.py resonance_map_XXXX.csv --table       # peak per point
  python3 plot_resonance.py resonance_map_XXXX.csv --save out.png  # also writes out_map.png
  python3 plot_resonance.py resonance_map_XXXX.csv --no-map
"""
import argparse
import csv
import sys
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np

SENSOR_AXES = ("x", "y", "z")
EXCITE_COLORS = {"x": "tab:blue", "y": "tab:orange"}


def load_csv(path):
    freqs = []
    first = None
    data = defaultdict(lambda: defaultdict(lambda: [[], [], []]))
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            key = (float(row["x_pos"]), float(row["y_pos"]))
            excite = row["excite_axis"]
            if first is None:
                first = (key, excite)
            if (key, excite) == first:
                freqs.append(float(row["freq_hz"]))
            curves = data[key][excite]
            for i, axis in enumerate(SENSOR_AXES):
                curves[i].append(float(row["psd_" + axis]))
    out = {key: {e: np.array(c) for e, c in by_axis.items()}
           for key, by_axis in data.items()}
    return np.array(freqs), out


def smooth(y, width):
    if width <= 1:
        return y
    kernel = np.ones(width) / width
    return np.convolve(y, kernel, mode="same")


def crossing(freqs, y, i_from, i_to, level):
    """Linearly interpolated frequency where y crosses level, walking from i_from towards i_to."""
    step = 1 if i_to > i_from else -1
    for i in range(i_from, i_to, step):
        j = i + step
        if y[j] <= level < y[i]:
            return freqs[i] + (freqs[j] - freqs[i]) * (y[i] - level) / (y[i] - y[j])
    return None


def analyze(freqs, psd, fmin, fmax, smooth_bins, min_ratio=3.0):
    """dict(f_n, peak, f1, f2, zeta), or None if there is no peak standing out
    of the median level (by min_ratio) inside [fmin, fmax]."""
    mask = (freqs >= fmin) & (freqs <= fmax)
    idx = np.flatnonzero(mask)
    if len(idx) < 3:
        return None
    y = smooth(psd, smooth_bins)
    lo, hi = idx[0], idx[-1]
    k = lo + int(np.argmax(y[lo:hi + 1]))
    if k in (lo, hi) or y[k] <= 0 or y[k] < min_ratio * np.median(y[lo:hi + 1]):
        return None

    a, b, c = y[k - 1], y[k], y[k + 1]
    denom = a - 2 * b + c
    shift = 0.5 * (a - c) / denom if denom != 0 else 0.0
    f_n = freqs[k] + shift * (freqs[1] - freqs[0])
    peak = b - 0.25 * (a - c) * shift

    half = peak / 2
    f1 = crossing(freqs, y, k, lo, half)
    f2 = crossing(freqs, y, k, hi, half)
    zeta = (f2 - f1) / (2 * f_n) if f1 is not None and f2 is not None else None
    return {"f_n": f_n, "peak": peak, "f1": f1, "f2": f2, "zeta": zeta}


def select_curves(data, point):
    if point is None:
        keys = list(data)
        label = f"mean of {len(keys)} points"
    else:
        keys = [min(data, key=lambda k: (k[0] - point[0]) ** 2 + (k[1] - point[1]) ** 2)]
        label = f"point X{keys[0][0]:g} Y{keys[0][1]:g}"
    excites = sorted({e for k in keys for e in data[k]})
    curves = {}
    for e in excites:
        stack = [data[k][e] for k in keys if e in data[k]]
        curves[e] = np.mean(stack, axis=0)
    return curves, label


def fmt_result(r):
    if r is None:
        return "no peak"
    z = f", zeta={r['zeta']:.3f}" if r["zeta"] is not None else ", zeta n/a"
    return f"{r['f_n']:.1f} Hz{z}"


def plot(freqs, curves, label, fmin, fmax, smooth_bins, log_y, title):
    fig, axes = plt.subplots(3, 1, sharex=True, figsize=(11, 9))
    for i, (ax, sensor) in enumerate(zip(axes, SENSOR_AXES)):
        for excite, psd in curves.items():
            color = EXCITE_COLORS.get(excite, "tab:green")
            y = smooth(psd[i], smooth_bins)
            ax.plot(freqs, y, color=color, lw=1.2, label=f"{excite.upper()} sweep")
            ax.fill_between(freqs, y, color=color, alpha=0.15)

            r = analyze(freqs, psd[i], fmin, fmax, smooth_bins)
            if r is None:
                continue
            if r["f1"] is not None and r["f2"] is not None:
                ax.axvspan(r["f1"], r["f2"], color=color, alpha=0.2)
            ax.axvline(r["f_n"], color=color, ls="--", lw=1)
            ax.plot(r["f_n"], r["peak"], "o", color=color, mec="black", ms=7)
            ax.annotate(
                f"{excite.upper()}: {fmt_result(r)}",
                (r["f_n"], r["peak"]),
                xytext=(8, 6 + 14 * (excite == "y")),
                textcoords="offset points",
                fontsize=9,
                color=color,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=color, alpha=0.85),
            )
        ax.set_ylabel(f"sensor {sensor.upper()}\nPSD [mg²/Hz]")
        if log_y:
            ax.set_yscale("log")
        ax.grid(alpha=0.3)
        ax.legend(loc="upper right")
    axes[-1].set_xlabel("Frequency [Hz]")
    axes[-1].set_xlim(0, fmax * 1.25)
    fig.suptitle(f"{title}  ({label})")
    fig.tight_layout()
    return fig


def build_map(freqs, data, fmin, fmax, smooth_bins):
    xs = sorted({k[0] for k in data})
    ys = sorted({k[1] for k in data})
    maps = {(e, q): np.full((len(ys), len(xs)), np.nan)
            for e in ("x", "y") for q in ("f_n", "zeta")}
    for (x, y), by_axis in data.items():
        for e in ("x", "y"):
            if e not in by_axis:
                continue
            r = analyze(freqs, by_axis[e][SENSOR_AXES.index(e)], fmin, fmax, smooth_bins)
            if r is None:
                continue
            maps[(e, "f_n")][ys.index(y), xs.index(x)] = r["f_n"]
            if r["zeta"] is not None:
                maps[(e, "zeta")][ys.index(y), xs.index(x)] = r["zeta"]
    return np.array(xs), np.array(ys), maps


def cell_edges(centers):
    if len(centers) == 1:
        return np.array([centers[0] - 0.5, centers[0] + 0.5])
    mid = (centers[:-1] + centers[1:]) / 2
    return np.concatenate([[centers[0] - (mid[0] - centers[0])], mid,
                           [centers[-1] + (centers[-1] - mid[-1])]])


def plot_map(xs, ys, maps, title):
    fig, axes = plt.subplots(2, 2, figsize=(11, 9.5))
    panels = [
        (("x", "f_n"), "X sweep: resonance [Hz]", "viridis", "{:.1f}"),
        (("y", "f_n"), "Y sweep: resonance [Hz]", "viridis", "{:.1f}"),
        (("x", "zeta"), "X sweep: damping ratio", "magma_r", "{:.3f}"),
        (("y", "zeta"), "Y sweep: damping ratio", "magma_r", "{:.3f}"),
    ]
    xe, ye = cell_edges(xs), cell_edges(ys)
    for ax, (key, name, cmap, fmt) in zip(axes.flat, panels):
        grid = maps[key]
        valid = grid[~np.isnan(grid)]
        mesh = ax.pcolormesh(xe, ye, np.ma.masked_invalid(grid), cmap=cmap, shading="flat")
        cb = fig.colorbar(mesh, ax=ax)
        lo, hi = (valid.min(), valid.max()) if valid.size else (0, 1)
        for j, y in enumerate(ys):
            for i, x in enumerate(xs):
                v = grid[j, i]
                if np.isnan(v):
                    ax.text(x, y, "n/a", ha="center", va="center", fontsize=8, color="gray")
                    continue
                light = (v - lo) / (hi - lo) > 0.5 if hi > lo else True
                ax.text(x, y, fmt.format(v), ha="center", va="center", fontsize=8,
                        color="black" if (light == (cmap == "viridis")) else "white")
        if valid.size:
            ax.set_xlabel(f"X [mm]\nmin {lo:.3g}, max {hi:.3g}, mean {valid.mean():.3g}")
        else:
            ax.set_xlabel("X [mm]\nno data")
        ax.set_ylabel("Y [mm]")
        ax.set_aspect("equal")
        ax.set_title(name)
    fig.suptitle(f"Resonance map  ({title})")
    fig.tight_layout()
    return fig


def print_table(freqs, data, fmin, fmax, smooth_bins):
    print(f"{'x':>8} {'y':>8} {'sweep':>5} {'f_n [Hz]':>10} {'zeta':>7}")
    for (x, y), by_axis in sorted(data.items()):
        for excite, psd in sorted(by_axis.items()):
            r = analyze(freqs, psd[SENSOR_AXES.index(excite)], fmin, fmax, smooth_bins)
            if r is None:
                print(f"{x:8.1f} {y:8.1f} {excite:>5} {'-':>10} {'-':>7}")
            else:
                z = f"{r['zeta']:.3f}" if r["zeta"] is not None else "-"
                print(f"{x:8.1f} {y:8.1f} {excite:>5} {r['f_n']:10.2f} {z:>7}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("csv")
    p.add_argument("--point", nargs=2, type=float, metavar=("X", "Y"),
                   help="use the grid point nearest to X Y (default: mean over all points)")
    p.add_argument("--fmin", type=float, default=10.0, help="lower bound of the peak search [Hz]")
    p.add_argument("--fmax", type=float, default=200.0, help="upper bound of the peak search and plot [Hz]")
    p.add_argument("--smooth", type=int, default=5, help="moving average width in bins (1 = off)")
    p.add_argument("--log", action="store_true", help="logarithmic PSD axis")
    p.add_argument("--table", action="store_true",
                   help="print the resonance of every point (sweep axis = sensor axis) and exit")
    p.add_argument("--no-map", action="store_true", help="skip the resonance map window")
    p.add_argument("--save", metavar="PNG",
                   help="save the figures instead of showing them (map goes to <name>_map.png)")
    args = p.parse_args()

    freqs, data = load_csv(args.csv)
    if not data:
        sys.exit("CSV contains no data")

    if args.table:
        print_table(freqs, data, args.fmin, args.fmax, args.smooth)
        return

    curves, label = select_curves(data, args.point)
    fig = plot(freqs, curves, label, args.fmin, args.fmax, args.smooth, args.log,
               args.csv.split("/")[-1])

    for excite, psd in curves.items():
        for i, sensor in enumerate(SENSOR_AXES):
            r = analyze(freqs, psd[i], args.fmin, args.fmax, args.smooth)
            print(f"{excite.upper()} sweep, sensor {sensor.upper()}: {fmt_result(r)}")

    map_fig = None
    if not args.no_map:
        xs, ys, maps = build_map(freqs, data, args.fmin, args.fmax, args.smooth)
        map_fig = plot_map(xs, ys, maps, args.csv.split("/")[-1])

    if args.save:
        fig.savefig(args.save, dpi=150)
        print(f"saved {args.save}")
        if map_fig is not None:
            map_path = args.save.rsplit(".", 1)[0] + "_map.png"
            map_fig.savefig(map_path, dpi=150)
            print(f"saved {map_path}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
