#!/usr/bin/env python3
"""Show a whole RINGING_TEST capture for one axis, shaper off vs on.

Top plot: shaper off, bottom plot: shaper on, same time axis and scale.
Gray = head is moving, green = the window after each stop where ringing
is measured; the number above it is the RMS acceleration in that window.

Usage:
  python3.13 plot_ringing.py                     # newest run, X axis
  python3.13 plot_ringing.py --axis y
  python3.13 plot_ringing.py ringing_XXXX.csv --axis x
  python3.13 plot_ringing.py --band 5 150        # filter out the stepper buzz first
"""
import argparse
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "klipper_module" / "resonance_mapper"))
import analysis  # noqa: E402

STAMPED = re.compile(r"ringing_(\d{8}_\d{6})\.csv$")


def find_csv(arg):
    p = Path(arg) if arg else REPO / "resonance_data"
    if p.is_file():
        return p
    files = sorted(f for f in p.glob("ringing_*.csv") if STAMPED.search(f.name))
    if not files:
        sys.exit(f"no ringing_*.csv in {p}")
    return files[-1]


def load(npz, args):
    d = np.load(npz)
    fs = float(d["fs"])
    accel = float(d["accel"])
    moves, ta, tc, _ = analysis.plan(float(d["dist"]), float(d["speed"]),
                                     accel, float(d["dwell"]), int(d["repeats"]))
    band = tuple(args.band) if args.band else None
    res, ax, _ = analysis.analyze(d["samples"], fs, moves, ta, tc, accel,
                                  args.offset, args.window, band=band)
    acc = analysis.to_mms2(d["samples"], fs, band)[:, ax]
    return fs, res, acc


def main():
    p = argparse.ArgumentParser()
    p.add_argument("path", nargs="?")
    p.add_argument("--axis", default="x", choices=["x", "y"])
    p.add_argument("--band", nargs=2, type=float, metavar=("LO", "HI"))
    p.add_argument("--offset", type=float, default=0.02)
    p.add_argument("--window", type=float, default=0.2)
    args = p.parse_args()

    csv_path = find_csv(args.path)
    stamp = STAMPED.search(csv_path.name).group(1)

    fig, plots = plt.subplots(2, 1, figsize=(16, 8), sharex=True, sharey=True)
    for plot, cond in zip(plots, ("off", "on")):
        npz = csv_path.parent / f"ringing_{stamp}_{args.axis}_{cond}.npz"
        if not npz.exists():
            plot.set_title(f"shaper {cond}: no capture")
            continue
        fs, res, acc = load(npz, args)
        t0 = res[0]["start"]
        t = (np.arange(len(acc)) - t0) / fs

        plot.plot(t, acc, lw=0.5, color="tab:blue")
        for r in res:
            plot.axvspan((r["start"] - t0) / fs, (r["stop"] - t0) / fs,
                         color="gray", alpha=0.2)
            a, b = ((i - t0) / fs for i in r["window"])
            plot.axvspan(a, b, color="tab:green", alpha=0.3)
            plot.text((a + b) / 2, 1.0, f"{r['rms_along']:.0f}",
                      transform=plot.get_xaxis_transform(), ha="center",
                      va="bottom", color="tab:green", fontweight="bold")

        mean = np.mean([r["rms_along"] for r in res])
        plot.set_title(f"shaper {cond}: average ringing {mean:.0f} mm/s²",
                       loc="left", pad=18)
        plot.set_ylabel("accel along move (mm/s²)")

    plots[1].set_xlabel("time since first move (s)")
    band = f", filtered {args.band[0]:g}-{args.band[1]:g} Hz" if args.band else ""
    fig.suptitle(f"{csv_path.name}, {args.axis} moves{band}   "
                 f"(gray = moving, green = ringing window)")
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
