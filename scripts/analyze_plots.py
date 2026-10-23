#!/usr/bin/env python3
"""Make all plots and tables from data/processed/{summary,runs}.csv (run parse_results.py first).

  python scripts/analyze_plots.py [--data-dir data] [--plots-dir plots]

Outputs: plots/*.png, data/processed/tables.md, data/processed/knee.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

# categorical slots 1,2,3,7 of the reference palette (+ distinct markers so colour is never the only cue)
C = ["#2a78d6", "#eb6834", "#1baf7a", "#6250d6"]
MK = ["o", "s", "^", "D"]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
NAMES = {"randread": "Random read", "randwrite": "Random write", "read": "Sequential read", "write": "Sequential write"}
ORDER = ["randread", "randwrite", "read", "write"]
BS_ORDER = ["4k", "16k", "32k", "64k", "128k", "256k"]

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 200, "font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True, "legend.frameon": False, "axes.titlesize": 11, "axes.titleweight": "bold",
})

SYNTH = False
TABLES: list[str] = []


def stamp(fig):
    if SYNTH:
        fig.text(0.5, 0.5, "SYNTHETIC - NOT REAL DATA", rotation=28, ha="center", va="center",
                 fontsize=44, color="#cc0000", alpha=0.18)


def save(fig, plots: Path, name: str):
    stamp(fig)
    fig.tight_layout()
    fig.savefig(plots / name)
    plt.close(fig)
    print("  wrote", name)


def md_table(df: pd.DataFrame, title: str, note: str = "") -> str:
    cols = list(df.columns)
    lines = [f"### {title}", ""]
    if SYNTH:
        lines += ["> **SYNTHETIC - NOT REAL DATA**", ""]
    lines += ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    if note:
        lines += ["", note]
    txt = "\n".join(lines) + "\n"
    TABLES.append(txt)
    return txt


def pm(m, s, fmt="{:.1f}"):
    return (fmt + " ± " + fmt).format(m, 0 if pd.isna(s) else s)


def sel(S, stage, **kw):
    d = S[S.stage == stage]
    for k, v in kw.items():
        d = d[d[k] == v]
    return d


def label_end(ax, x, y, text, color, dx=4, dy=0):
    ax.annotate(text, (x, y), xytext=(dx, dy), textcoords="offset points", color=color, fontsize=8,
                va="center", ha="left")


# ------------------------------------------------------------------ plots
def p_baseline(S, plots):
    d = sel(S, "baseline")
    if d.empty:
        return
    rows = []
    for rw in ORDER:
        r = d[d.rw == rw]
        if r.empty:
            continue
        r = r.iloc[0]
        rows.append({"Workload (QD=1)": f"{NAMES[rw]} {r.bs}",
                     "Mean (µs)": pm(r.lat_mean_us_mean, r.lat_mean_us_std),
                     "p50 (µs)": pm(r.p50_us_mean, r.p50_us_std),
                     "p95 (µs)": pm(r.p95_us_mean, r.p95_us_std),
                     "p99 (µs)": pm(r.p99_us_mean, r.p99_us_std),
                     "p99.9 (µs)": pm(r.p999_us_mean, r.p999_us_std),
                     "IOPS": f"{r.iops_mean:,.0f}", "MiB/s": f"{r.bw_mibs_mean:,.0f}", "reps": int(r.n_reps)})
    md_table(pd.DataFrame(rows), "Table 1 - Zero-queue (QD=1) baselines", "Mean ± std over repetitions. Latency = fio completion latency percentiles (clat) except Mean, which is total latency (lat).")
    fig, ax = plt.subplots(figsize=(7.2, 4))
    labs, w = [], 0.2
    ks = [("p50_us", "p50"), ("p95_us", "p95"), ("p99_us", "p99"), ("p999_us", "p99.9")]
    present = [rw for rw in ORDER if not d[d.rw == rw].empty]
    for i, (k, nm) in enumerate(ks):
        vals = [d[d.rw == rw][f"{k}_mean"].iloc[0] for rw in present]
        errs = [d[d.rw == rw][f"{k}_std"].iloc[0] for rw in present]
        ax.bar(np.arange(len(present)) + (i - 1.5) * w, vals, w * 0.9, yerr=errs, label=nm,
               color=["#9ec5f0", C[0], "#164c8a", "#0a2a52"][i], error_kw={"lw": 1})
    ax.set_xticks(range(len(present)))
    ax.set_xticklabels([f"{NAMES[r]}\n{d[d.rw == r].bs.iloc[0]}" for r in present])
    ax.set_yscale("log")
    ax.set_ylabel("Latency (µs, log scale)")
    ax.set_title("QD=1 latency percentiles")
    ax.legend(ncol=4, loc="upper left")
    save(fig, plots, "01_baseline_latency.png")


def p_blocksize(S, plots):
    d = S[S.stage == "blocksize"]
    if d.empty:
        return
    qds = sorted(d.iodepth.unique())
    for metric, ylabel, fname, log in [("bw_mibs", "Throughput (MiB/s)", "02_blocksize_throughput.png", True),
                                       ("lat_mean_us", "Mean latency (µs)", "03_blocksize_latency.png", True)]:
        fig, axes = plt.subplots(1, len(qds), figsize=(5.2 * len(qds), 4), sharey=True, squeeze=False)
        for ax, qd in zip(axes[0], qds):
            for i, rw in enumerate(ORDER):
                r = d[(d.iodepth == qd) & (d.rw == rw)]
                r = r.set_index("bs").reindex([b for b in BS_ORDER if b in set(r.bs)])
                if r.empty:
                    continue
                x = np.arange(len(r))
                ax.errorbar(x, r[f"{metric}_mean"], yerr=r[f"{metric}_std"], color=C[i], marker=MK[i], lw=1.8,
                            ms=5, capsize=2, label=NAMES[rw])
                if metric == "lat_mean_us":
                    ax.plot(x, r["p99_us_mean"], color=C[i], ls=":", lw=1.2)
            ax.set_xticks(range(len(BS_ORDER)))
            ax.set_xticklabels(BS_ORDER)
            ax.set_xlabel("Block size")
            ax.set_title(f"Queue depth {qd}" + ("  (dotted = p99)" if metric == "lat_mean_us" else ""))
            if log:
                ax.set_yscale("log")
        axes[0][0].set_ylabel(ylabel)
        axes[0][0].legend(loc="best", fontsize=8)
        save(fig, plots, fname)
    rows = []
    for qd in qds:
        for rw in ORDER:
            for bs in BS_ORDER:
                r = d[(d.iodepth == qd) & (d.rw == rw) & (d.bs == bs)]
                if r.empty:
                    continue
                r = r.iloc[0]
                rows.append({"QD": qd, "Pattern": NAMES[rw], "Block": bs, "IOPS": f"{r.iops_mean:,.0f}",
                             "MiB/s": pm(r.bw_mibs_mean, r.bw_mibs_std, "{:,.0f}"),
                             "Mean lat (µs)": f"{r.lat_mean_us_mean:,.0f}", "p99 (µs)": f"{r.p99_us_mean:,.0f}"})
    md_table(pd.DataFrame(rows), "Table 2 - Block-size sweep (same runs give throughput and latency)")


def p_rwmix(S, plots):
    d = S[S.stage == "rwmix"]
    if d.empty:
        return
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    rows = []
    for row, (rw, bs, unit, key) in enumerate([("randrw", "4k", "IOPS (thousands)", "iops"), ("rw", "128k", "Throughput (MiB/s)", "bw_mibs")]):
        r = d[(d.rw == rw)].sort_values("rwmixread", ascending=False)
        if r.empty:
            continue
        x = np.arange(len(r))
        sc = 1e3 if key == "iops" else 1
        rd = r[f"r_{key}_mean"].fillna(0) / sc
        wr = r[f"w_{key}_mean"].fillna(0) / sc
        ax = axes[row][0]
        ax.bar(x, rd, 0.6, color=C[0], label="read")
        ax.bar(x, wr, 0.6, bottom=rd, color=C[1], label="write")
        ax.set_xticks(x)
        ax.set_xticklabels([f"{int(m)}% read" for m in r.rwmixread])
        ax.set_ylabel(unit)
        ax.set_title(f"{'Random 4 KiB' if rw == 'randrw' else 'Sequential 128 KiB'}, QD32: total throughput")
        ax.set_ylim(0, max((rd + wr).max() * 1.25, 1))
        ax.legend(loc="upper left", ncol=2)
        ax = axes[row][1]
        for i, (side, nm) in enumerate([("r", "read"), ("w", "write")]):
            col = f"{side}_lat_mean_us_mean"
            if col in r:
                ax.plot(x, r[col], marker=MK[i], color=C[i], lw=1.8, label=f"{nm} mean")
            pc = f"{side}_p99_us_mean"
            if pc in r:
                ax.plot(x, r[pc], marker=MK[i], color=C[i], lw=1, ls=":", label=f"{nm} p99")
        ax.set_xticks(x)
        ax.set_xticklabels([f"{int(m)}% read" for m in r.rwmixread])
        ax.set_yscale("log")
        ax.set_ylabel("Latency (µs, log)")
        ax.set_title("Per-direction latency")
        ax.legend(fontsize=8, ncol=2)
        for _, q in r.iterrows():
            rows.append({"Pattern": f"{'rand' if rw == 'randrw' else 'seq'} {bs}", "Read %": int(q.rwmixread),
                         "Total IOPS": f"{q.iops_mean:,.0f}", "Total MiB/s": f"{q.bw_mibs_mean:,.0f}",
                         "Read lat µs": f"{q.get('r_lat_mean_us_mean', np.nan):,.0f}",
                         "Write lat µs": f"{q.get('w_lat_mean_us_mean', np.nan):,.0f}"})
    save(fig, plots, "04_rwmix.png")
    md_table(pd.DataFrame(rows), "Table 3 - Read/write mix at QD32")


def find_knee(df):
    """df sorted by qd with columns iodepth, iops_mean, lat_mean_us_mean."""
    qd, y, lat = df.iodepth.values.astype(float), df.iops_mean.values, df.lat_mean_us_mean.values
    out = {"max_iops": float(y.max())}
    ok = np.where(y >= 0.9 * y.max())[0]
    out["knee_qd_90pct"] = int(qd[ok[0]])
    yn = (y - y[0]) / max(y.max() - y[0], 1e-9)
    xl = np.log(lat / lat.min())
    xn = xl / max(xl.max(), 1e-9)
    out["knee_qd_chord"] = int(qd[int(np.argmax(yn - xn))])
    out["n_star_littles"] = float(y.max() * lat[0] * 1e-6)   # X_max * unloaded latency = IOs the SSD can overlap
    return out


def p_qdsweep(S, plots, procdir):
    d = S[S.stage == "qdsweep"]
    if d.empty:
        return
    knees = {}
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    rows, little_rows = [], []
    for i, rw in enumerate(["randread", "randwrite"]):
        r = d[d.rw == rw].sort_values("iodepth")
        if len(r) < 3:
            continue
        k = find_knee(r)
        knees.update({f"{rw}_{kk}": vv for kk, vv in k.items()})
        # panel 1: throughput vs latency, one curve per workload
        ax = axes[0]
        ax.errorbar(r.lat_mean_us_mean, r.iops_mean, xerr=r.lat_mean_us_std, yerr=r.iops_std, color=C[i], marker=MK[i],
                    lw=1.8, ms=5, capsize=2, label=f"4 KiB {NAMES[rw].lower()}")
        for _, q in r.iterrows():
            ax.annotate(f"{int(q.iodepth)}", (q.lat_mean_us_mean, q.iops_mean), xytext=(3, -9), textcoords="offset points",
                        fontsize=7, color=MUTED)
        kr = r[r.iodepth == k["knee_qd_chord"]].iloc[0]
        ax.scatter([kr.lat_mean_us_mean], [kr.iops_mean], s=150, facecolors="none", edgecolors=C[i], linewidths=2, zorder=5)
        ax.annotate(f"knee QD≈{k['knee_qd_chord']}", (kr.lat_mean_us_mean, kr.iops_mean), xytext=(10, -22 - 14 * i),
                    textcoords="offset points", color=C[i], fontsize=9, arrowprops=dict(arrowstyle="-", color=C[i]))
        # panel 2: Little's Law  L_est = X * W vs QD
        ax2 = axes[1]
        lest = r.iops_mean * r.lat_mean_us_mean * 1e-6
        ax2.plot(r.iodepth, lest, marker=MK[i], color=C[i], lw=1.8, ms=5, label=f"{NAMES[rw]}: X·W")
        for _, q in r.iterrows():
            L = q.iops_mean * q.lat_mean_us_mean * 1e-6
            rows.append({"Workload": f"4k {rw}", "QD": int(q.iodepth), "IOPS": pm(q.iops_mean, q.iops_std, "{:,.0f}"),
                         "Mean lat (µs)": pm(q.lat_mean_us_mean, q.lat_mean_us_std, "{:,.1f}"),
                         "p99 (µs)": f"{q.p99_us_mean:,.0f}",
                         "L = IOPS × lat": f"{L:.1f}", "L / QD": f"{L / q.iodepth:.2f}"})
        little_rows.append({"Workload": f"4k {rw}", "Peak IOPS": f"{k['max_iops']:,.0f}",
                            "Knee QD (chord)": k["knee_qd_chord"], "QD for 90% of peak": k["knee_qd_90pct"],
                            "N* = peak IOPS × QD1 latency": f"{k['n_star_littles']:.1f}"})
    axes[0].set_xscale("log")
    axes[0].xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    axes[0].xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    axes[0].set_xlabel("Mean latency (µs, log scale)")
    axes[0].set_ylabel("Throughput (IOPS)")
    axes[0].set_title("Throughput-latency curve (labels = queue depth)")
    axes[0].legend(loc="lower right")
    ref = d.iodepth.unique()
    axes[1].plot([ref.min(), ref.max()], [ref.min(), ref.max()], color=MUTED, ls="--", lw=1)
    axes[1].annotate("L = QD (ideal closed loop)", (ref.max(), ref.max()), xytext=(-6, -14), textcoords="offset points",
                     ha="right", color=MUTED, fontsize=8)
    axes[1].set_xscale("log", base=2)
    axes[1].set_yscale("log", base=2)
    axes[1].set_xlabel("Queue depth (fio iodepth)")
    axes[1].set_ylabel("Little's Law estimate  L = X · W")
    axes[1].set_title("Little's Law check")
    axes[1].legend(loc="upper left")
    save(fig, plots, "05_qd_throughput_latency.png")

    # supplementary: vs QD
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for i, rw in enumerate(["randread", "randwrite"]):
        r = d[d.rw == rw].sort_values("iodepth")
        if r.empty:
            continue
        axes[0].errorbar(r.iodepth, r.iops_mean, yerr=r.iops_std, color=C[i], marker=MK[i], lw=1.8, ms=5, capsize=2, label=NAMES[rw])
        axes[1].errorbar(r.iodepth, r.lat_mean_us_mean, yerr=r.lat_mean_us_std, color=C[i], marker=MK[i], lw=1.8, ms=5, capsize=2, label=f"{NAMES[rw]} mean")
        axes[1].plot(r.iodepth, r.p99_us_mean, color=C[i], ls=":", lw=1.4, label=f"{NAMES[rw]} p99")
        axes[2].plot(r.iodepth, r.iops_mean / r.iops_mean.max(), color=C[i], marker=MK[i], lw=1.8, ms=5, label=NAMES[rw])
    for ax in axes:
        ax.set_xscale("log", base=2)
        ax.set_xlabel("Queue depth")
    axes[0].set_ylabel("IOPS")
    axes[0].set_title("Throughput vs queue depth")
    axes[1].set_yscale("log")
    axes[1].set_ylabel("Latency (µs, log)")
    axes[1].set_title("Latency vs queue depth")
    axes[1].legend(fontsize=8)
    axes[2].axhline(0.9, color=MUTED, ls="--", lw=1)
    axes[2].set_ylabel("Fraction of peak IOPS")
    axes[2].set_title("Diminishing returns (dashed = 90% of peak)")
    axes[0].legend()
    save(fig, plots, "06_qd_sweep_vs_qd.png")
    md_table(pd.DataFrame(rows), "Table 4 - Queue-depth sweep with Little's Law check",
             "L = IOPS × mean total latency. In a closed loop with fixed QD, L / QD should be ≈ 1; deviations point to latency not measured by fio (device-side queueing after completion, timer resolution) or the ramp/steady-state boundary.")
    md_table(pd.DataFrame(little_rows), "Table 5 - Knee and effective device concurrency",
             "N* is the number of requests the SSD can overlap: beyond ≈N* more queue depth only adds latency (W ≈ QD / peak IOPS).")
    (procdir / "knee.json").write_text(json.dumps(knees, indent=2))
    return knees


def p_tail(S, plots):
    d = S[S.stage == "tail"]
    if d.empty:
        return
    keys = [("p50_us", "p50", 50), ("p90_us", "p90", 90), ("p95_us", "p95", 95), ("p99_us", "p99", 99),
            ("p999_us", "p99.9", 99.9), ("p9999_us", "p99.99", 99.99)]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=False)
    rows = []
    for ax, rw in zip(axes, ["randread", "randwrite"]):
        r = d[d.rw == rw].sort_values("iodepth")
        for i, (_, q) in enumerate(r.iterrows()):
            ys = [q[f"{k}_mean"] for k, _, _ in keys]
            es = [q[f"{k}_std"] for k, _, _ in keys]
            ax.errorbar(range(len(keys)), ys, yerr=es, color=C[i % 4], marker=MK[i % 4], lw=1.8, ms=5, capsize=2,
                        label=f"QD {int(q.iodepth)}")
            rows.append({"Workload": f"4k {rw}", "QD": int(q.iodepth), **{nm: f"{q[f'{k}_mean']:,.0f}" for k, nm, _ in keys},
                         "p99/p50": f"{q.p99_us_mean / q.p50_us_mean:.1f}", "p99.99/p50": f"{q.p9999_us_mean / q.p50_us_mean:.1f}",
                         "max (µs)": f"{q.lat_max_us_mean:,.0f}"})
        ax.set_xticks(range(len(keys)))
        ax.set_xticklabels([nm for _, nm, _ in keys])
        ax.set_yscale("log")
        ax.set_xlabel("Percentile")
        ax.set_ylabel("Completion latency (µs, log)")
        ax.set_title(f"4 KiB {NAMES[rw].lower()}: tail latency")
        ax.legend()
    save(fig, plots, "07_tail_latency.png")
    md_table(pd.DataFrame(rows), "Table 6 - Tail latency (µs) at mid-QD, near-knee and past-knee QD",
             "Latencies are fio clat percentiles (submission-to-completion excluding submit time).")


def read_log(path: Path):
    df = pd.read_csv(path, header=None, usecols=[0, 1], names=["t_ms", "v"], skipinitialspace=True)
    return df.t_ms / 1000.0, df.v


def p_steady(raw, plots):
    sd = raw / "steady"
    metas = sorted(sd.glob("*.meta.json")) if sd.exists() else []
    if not metas:
        return
    fig, axes = plt.subplots(2, len(metas), figsize=(6 * len(metas), 6.2), sharex="col",
                             gridspec_kw={"height_ratios": [3, 1.4]}, squeeze=False)
    rows = []
    for j, mp in enumerate(metas):
        m = json.loads(mp.read_text())
        bw = sorted(sd.glob(f"{m['id']}_bw*.log"))
        ax, axt = axes[0][j], axes[1][j]
        ax.set_title(m["label"].replace("_timeseries", "").replace("_", " "))
        if not bw:
            ax.text(0.5, 0.5, "no bw log found", transform=ax.transAxes, ha="center")
            continue
        t, v = read_log(bw[0])
        mibs = v / 1024.0
        ax.plot(t, mibs, color=C[j % 4], lw=1.4)
        ax.set_ylabel("Write throughput (MiB/s)")
        n = len(mibs)
        burst = mibs.iloc[:max(3, n // 10)].mean()
        steady = mibs.iloc[-max(3, n // 5):].mean()
        roll = mibs.rolling(10, min_periods=5, center=True).median()
        below = np.where(roll < 0.7 * burst)[0]
        drop_t = float(t.iloc[below[0]]) if len(below) else None
        ax.axhline(burst, color=MUTED, ls=":", lw=1)
        ax.axhline(steady, color=MUTED, ls="--", lw=1)
        ax.annotate(f"first 10%: {burst:,.0f} MiB/s", (t.iloc[-1], burst), xytext=(-4, 4), textcoords="offset points", ha="right", fontsize=8, color=MUTED)
        ax.annotate(f"last 20%: {steady:,.0f} MiB/s", (t.iloc[-1], steady), xytext=(-4, -11), textcoords="offset points", ha="right", fontsize=8, color=MUTED)
        if drop_t is not None:
            ax.axvline(drop_t, color=C[1], lw=1.2)
            ax.annotate(f"drop ≈ {drop_t:.0f}s", (drop_t, ax.get_ylim()[1]), xytext=(4, -12), textcoords="offset points", color=C[1], fontsize=9)
        ax.set_ylim(bottom=0)
        ts = m.get("temp_series")
        if ts:
            ts = np.array(ts)
            axt.plot(ts[:, 0], ts[:, 1], color=C[2], marker="o", ms=3, lw=1.4)
            axt.set_ylabel("Drive temp (°C)")
        else:
            axt.text(0.5, 0.5, "no temperature samples", transform=axt.transAxes, ha="center", color=MUTED)
        axt.set_xlabel("Time (s)")
        rows.append({"Workload": m["label"].replace("_timeseries", ""), "First 10% (MiB/s)": f"{burst:,.0f}",
                     "Last 20% (MiB/s)": f"{steady:,.0f}", "Steady/burst": f"{steady / burst:.2f}",
                     "Drop at (s)": f"{drop_t:.0f}" if drop_t is not None else "none detected",
                     "Max temp (°C)": f"{np.max(ts[:, 1]):.0f}" if ts is not None and len(ts) else "n/a"})
    save(fig, plots, "08_steady_state.png")
    md_table(pd.DataFrame(rows), "Table 7 - Burst vs steady-state writes (per-second logs)",
             "A drop is flagged where the 10 s rolling median falls below 70% of the first-10% mean. Cause (SLC-cache exhaustion, GC, thermal throttling) must be argued from the temperature trace and file size, not assumed.")


def p_lba(S, plots):
    d = S[S.stage == "lba"]
    if d.empty:
        return
    fig, ax = plt.subplots(figsize=(6, 4))
    rows = []
    for i, rw in enumerate(["randread", "randwrite"]):
        r = d[d.rw == rw].sort_values("span_gib")
        if r.empty:
            continue
        ax.errorbar(r.span_gib, r.iops_mean, yerr=r.iops_std, color=C[i], marker=MK[i], lw=1.8, ms=5, capsize=2, label=NAMES[rw])
        for _, q in r.iterrows():
            rows.append({"Workload": f"4k {rw} QD32", "LBA span (GiB)": f"{q.span_gib:g}", "IOPS": pm(q.iops_mean, q.iops_std, "{:,.0f}"),
                         "Mean lat (µs)": f"{q.lat_mean_us_mean:,.1f}", "p99 (µs)": f"{q.p99_us_mean:,.0f}"})
    ax.set_xscale("log", base=2)
    ax.set_xlabel("LBA range touched (GiB)")
    ax.set_ylabel("IOPS")
    ax.set_title("Working-set / LBA-range effect")
    ax.legend()
    save(fig, plots, "09_lba_range.png")
    md_table(pd.DataFrame(rows), "Table 8 - LBA-range sweep")


def p_pitfall(S, plots):
    d = S[S.stage == "pitfall"]
    if d.empty:
        return
    names = {"correct_direct_aio_qd32": "Correct:\ndirect, async,\nQD32",
             "buffered_aio_qd32": "Buffered\n(page cache)",
             "aio_iodepth1_default": "windowsaio,\niodepth=1 default\n(really QD1)",
             "aio_iodepth1_numjobs32": "windowsaio,\n32 jobs x iodepth 1\n(really QD32)"}
    d = d.set_index("label").reindex([k for k in names if k in set(d.label)])
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    cols = [C[0], C[1], C[1], C[2]]
    for ax, (m, yl) in zip(axes, [("iops", "IOPS (log)"), ("lat_mean_us", "Mean latency (µs, log)")]):
        x = np.arange(len(d))
        ax.bar(x, d[f"{m}_mean"], 0.6, yerr=d[f"{m}_std"], color=cols[:len(d)], error_kw={"lw": 1})
        ax.set_xticks(x)
        ax.set_xticklabels([names[k] for k in d.index], fontsize=8)
        ax.set_yscale("log")
        ax.set_ylabel(yl)
    ctrl = d.loc["correct_direct_aio_qd32", "iops_mean"] if "correct_direct_aio_qd32" in d.index else None
    if ctrl:
        for xi, (k, q) in enumerate(d.iterrows()):
            axes[0].annotate(f"{q.iops_mean / ctrl:.2f}×", (xi, q.iops_mean), xytext=(0, 4), textcoords="offset points", ha="center", fontsize=9)
    axes[0].set_title("Misleading setups vs the correct one (4 KiB random read, 1 GiB range)")
    save(fig, plots, "10_pitfalls.png")
    rows = [{"Setup": k, "IOPS": pm(q.iops_mean, q.iops_std, "{:,.0f}"), "Mean lat (µs)": f"{q.lat_mean_us_mean:,.1f}",
             "vs control": f"{q.iops_mean / ctrl:.2f}×" if ctrl else ""} for k, q in d.iterrows()]
    md_table(pd.DataFrame(rows), "Table 9 - Misleading-setup demonstration")


def p_datapattern(S, plots):
    d = S[S.stage == "datapattern"]
    if d.empty:
        return
    rows = [{"Data pattern": q.label.replace("randwrite_4k_qd32_", ""), "IOPS": pm(q.iops_mean, q.iops_std, "{:,.0f}"),
             "Mean lat (µs)": f"{q.lat_mean_us_mean:,.1f}", "p99 (µs)": f"{q.p99_us_mean:,.0f}"} for _, q in d.iterrows()]
    md_table(pd.DataFrame(rows), "Table 10 - Data-pattern (compressibility) check",
             "Main experiments use incompressible data (fio refill_buffers=1, buffer_compress_percentage=0).")


def temp_table(runs):
    d = runs[runs.stage.isin(["tail", "steady"])].dropna(subset=["temp_before_c"]) if "temp_before_c" in runs else runs.iloc[0:0]
    if d.empty:
        return
    g = d.groupby("label")[["temp_before_c", "temp_after_c"]].mean().round(1).reset_index()
    g.columns = ["Point", "Temp before (°C)", "Temp after (°C)"]
    md_table(g, "Table 11 - Drive temperature around long runs")


def main():
    global SYNTH
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=str(ROOT / "data"))
    ap.add_argument("--plots-dir", default=None)
    a = ap.parse_args()
    data = Path(a.data_dir)
    plots = Path(a.plots_dir) if a.plots_dir else (data.parent / "plots")
    plots.mkdir(parents=True, exist_ok=True)
    SYNTH = (data / "SYNTHETIC").exists()
    proc = data / "processed"
    if not (proc / "summary.csv").exists():
        raise SystemExit("Run scripts/parse_results.py first (no summary.csv found).")
    S = pd.read_csv(proc / "summary.csv")
    runs = pd.read_csv(proc / "runs.csv")
    print("Plotting" + (" (SYNTHETIC data!)" if SYNTH else "") + " ->", plots)
    p_baseline(S, plots)
    p_blocksize(S, plots)
    p_rwmix(S, plots)
    p_qdsweep(S, plots, proc)
    p_tail(S, plots)
    p_steady(data / "raw", plots)
    p_lba(S, plots)
    p_pitfall(S, plots)
    p_datapattern(S, plots)
    temp_table(runs)
    head = "# Auto-generated tables\n\n" + ("**SYNTHETIC - NOT REAL DATA**\n\n" if SYNTH else "")
    (proc / "tables.md").write_text(head + "\n".join(TABLES))
    print("  wrote", proc / "tables.md")


if __name__ == "__main__":
    main()
