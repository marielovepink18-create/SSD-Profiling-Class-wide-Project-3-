#!/usr/bin/env python3
"""Parse raw FIO JSON (+ sidecar .meta.json) into data/processed/runs.csv and summary.csv.

  python scripts/parse_results.py [--data-dir data]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

PCTS = {"p50": "50.000000", "p90": "90.000000", "p95": "95.000000",
        "p99": "99.000000", "p999": "99.900000", "p9999": "99.990000"}
MIB = 1024 * 1024


def load_fio_json(path: Path) -> dict:
    txt = path.read_text(errors="replace")
    i, j = txt.find("{"), txt.rfind("}")   # fio may print warnings before/after the JSON
    if i < 0 or j < 0:
        raise ValueError("no JSON object found")
    return json.loads(txt[i:j + 1])


def side_stats(side: dict, prefix: str) -> dict:
    out = {}
    ios = side.get("total_ios", 0) or 0
    out[f"{prefix}_ios"] = ios
    out[f"{prefix}_iops"] = side.get("iops", 0.0) if ios else 0.0
    bwb = side.get("bw_bytes")
    out[f"{prefix}_bw_mibs"] = (bwb / MIB) if bwb is not None else side.get("bw", 0) / 1024
    if not ios:
        return out
    lat = side.get("lat_ns", {})
    clat = side.get("clat_ns", {})
    out[f"{prefix}_lat_mean_us"] = lat.get("mean", np.nan) / 1000
    out[f"{prefix}_lat_max_us"] = lat.get("max", np.nan) / 1000
    out[f"{prefix}_clat_mean_us"] = clat.get("mean", np.nan) / 1000
    pc = clat.get("percentile", {}) or {}
    for k, key in PCTS.items():
        # tolerate formatting differences between fio versions
        val = pc.get(key)
        if val is None:
            for kk, vv in pc.items():
                if abs(float(kk) - float(key)) < 1e-6:
                    val = vv
        out[f"{prefix}_{k}_us"] = (val / 1000) if val is not None else np.nan
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=str(Path(__file__).resolve().parent.parent / "data"))
    a = ap.parse_args()
    data = Path(a.data_dir)
    raw = data / "raw"
    rows, problems = [], []
    for meta_path in sorted(raw.rglob("*.meta.json")):
        meta = json.loads(meta_path.read_text())
        jp = meta_path.with_name(meta_path.name.replace(".meta.json", ".json"))
        if meta.get("returncode", 0) != 0 or not jp.exists():
            problems.append((meta["id"], "fio failed or JSON missing"))
            continue
        try:
            fj = load_fio_json(jp)
            job = fj["jobs"][0]
        except Exception as e:  # noqa: BLE001
            problems.append((meta["id"], f"unparseable JSON: {e}"))
            continue
        row = {k: meta.get(k) for k in ["id", "stage", "label", "rep", "rw", "pattern", "bs", "bs_bytes",
                                        "iodepth", "numjobs", "rwmixread", "span_gib", "direct", "ioengine",
                                        "compress_pct", "runtime_s", "temp_before_c", "temp_after_c"]}
        row.update(side_stats(job.get("read", {}), "r"))
        row.update(side_stats(job.get("write", {}), "w"))
        r_ios, w_ios = row.get("r_ios", 0), row.get("w_ios", 0)
        row["iops"] = row.get("r_iops", 0) + row.get("w_iops", 0)
        row["bw_mibs"] = row.get("r_bw_mibs", 0) + row.get("w_bw_mibs", 0)
        tot = r_ios + w_ios
        if tot:
            lat = 0.0
            if r_ios:
                lat += row["r_lat_mean_us"] * r_ios
            if w_ios:
                lat += row["w_lat_mean_us"] * w_ios
            row["lat_mean_us"] = lat / tot
        # "primary" side stats for pure workloads (used by most plots)
        main_side = "r" if r_ios and not w_ios else "w" if w_ios and not r_ios else None
        for k in ["p50", "p90", "p95", "p99", "p999", "p9999"]:
            row[f"{k}_us"] = row.get(f"{main_side}_{k}_us", np.nan) if main_side else np.nan
        row["clat_mean_us"] = row.get(f"{main_side}_clat_mean_us", np.nan) if main_side else np.nan
        row["lat_max_us"] = row.get(f"{main_side}_lat_max_us", np.nan) if main_side else np.nan
        rows.append(row)

    outdir = data / "processed"
    outdir.mkdir(parents=True, exist_ok=True)
    if not rows:
        print("No parsed runs found under", raw)
        for p in problems:
            print("  problem:", p)
        return
    df = pd.DataFrame(rows)
    df.to_csv(outdir / "runs.csv", index=False)

    num = df.select_dtypes("number").columns.difference(["rep"])
    g = df.groupby(["stage", "label"], sort=False)
    mean = g[list(num)].mean().add_suffix("_mean")
    std = g[list(num)].std(ddof=1).fillna(0).add_suffix("_std")
    n = g.size().rename("n_reps")
    first = g[["rw", "pattern", "bs", "iodepth", "numjobs", "rwmixread", "span_gib", "direct", "ioengine"]].first()
    summ = pd.concat([first, n, mean, std], axis=1).reset_index()
    summ.to_csv(outdir / "summary.csv", index=False)
    print(f"Parsed {len(df)} runs -> {outdir / 'runs.csv'}, {len(summ)} points -> summary.csv")
    if problems:
        print(f"{len(problems)} problem runs (excluded):")
        for p in problems:
            print("  ", p)
        pd.DataFrame(problems, columns=["id", "problem"]).to_csv(outdir / "problems.csv", index=False)


if __name__ == "__main__":
    main()
