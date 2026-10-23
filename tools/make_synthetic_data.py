#!/usr/bin/env python3
"""Generate FAKE fio-style results from a toy queueing model, ONLY to test the parser/plot scripts.

Output goes to _synthetic/data (never to data/). A SYNTHETIC marker file makes analyze_plots.py
stamp every figure and table "SYNTHETIC - NOT REAL DATA". Never submit these numbers.

  python tools/make_synthetic_data.py && python scripts/parse_results.py --data-dir _synthetic/data \
      && python scripts/analyze_plots.py --data-dir _synthetic/data
"""
import json, sys, random
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import experiments as ex
from fio_lib import Config, job_id

rng = np.random.default_rng(7)
OUT = ROOT / "_synthetic" / "data"


def side(job, bs, qd, is_read, share=1.0):
    kb = bs / 1024
    seq = job.pattern == "sequential"
    if is_read:
        s0 = 75 + bs / 3.2e3 * 1e0 * (1 if seq else 1)    # us unloaded service latency
        cap = min(650e3 if not seq else 1e9, 3.4e9 / bs)
    else:
        s0 = 18 + bs / 2.4e3
        cap = min(420e3 if not seq else 1e9, 2.6e9 / bs)
    eff_qd = qd * job.numjobs
    if job.ioengine == "sync":
        eff_qd = job.numjobs
    x = min(eff_qd / (s0 * 1e-6), cap) * share
    if job.direct == 0:
        x, s0 = 1.6e6 * share, 4.0
        eff_qd = max(eff_qd, 1)
    x *= rng.normal(1, 0.012)
    w = eff_qd / max(x / share, 1) * 1e6 * share if share else s0   # Little: W = N / X  (us)
    w = max(w, s0) * rng.normal(1, 0.01)
    pct = {"50.000000": w * 0.97, "90.000000": w * 1.25, "95.000000": w * 1.45,
           "99.000000": w * (1.9 + 0.01 * np.log2(eff_qd + 1) * 8), "99.900000": w * (3.2 + 0.2 * np.log2(eff_qd + 1)),
           "99.990000": w * (7 + 0.5 * np.log2(eff_qd + 1))}
    rt = job.runtime or 15
    ios = int(x * rt)
    return {"io_bytes": int(ios * bs), "bw_bytes": x * bs, "bw": x * bs / 1024, "iops": x, "runtime": rt * 1000,
            "total_ios": ios,
            "lat_ns": {"min": s0 * 800, "max": w * 30000, "mean": w * 1000, "stddev": w * 300, "N": ios},
            "clat_ns": {"min": s0 * 700, "max": w * 29000, "mean": w * 990, "stddev": w * 300, "N": ios,
                        "percentile": {k: v * 1000 for k, v in pct.items()}}}


def main():
    cfg = Config(target="SYNTH.bin", **ex.PROFILES["quick"])
    cfg.ioengine = "windowsaio"
    (OUT.parent).mkdir(parents=True, exist_ok=True)
    (OUT.parent / "SYNTHETIC").write_text("fake data for testing scripts\n")
    (OUT).mkdir(parents=True, exist_ok=True)
    (OUT / "SYNTHETIC").write_text("fake data for testing scripts\n")
    for stage in ex.STAGES:
        sd = OUT / "raw" / stage
        sd.mkdir(parents=True, exist_ok=True)
        for job in ex.build_jobs(stage, cfg, ROOT / "_synthetic"):
            reps = job.reps or cfg.reps
            for rep in range(1, reps + 1):
                jid = job_id(job, rep)
                bs = job.bs_bytes()
                r = {}
                w = {}
                is_mix = job.rwmixread is not None
                if job.rw in ("randread", "read") or (is_mix and job.rwmixread > 0):
                    sh = job.rwmixread / 100 if is_mix else 1.0
                    r = side(job, bs, job.iodepth, True, sh)
                if job.rw in ("randwrite", "write") or (is_mix and job.rwmixread < 100):
                    sh = 1 - job.rwmixread / 100 if is_mix else 1.0
                    w = side(job, bs, job.iodepth, False, sh)
                empty = {"io_bytes": 0, "bw": 0, "iops": 0.0, "total_ios": 0}
                fj = {"fio version": "fio-synthetic", "jobs": [{"jobname": jid, "read": r or empty, "write": w or empty}]}
                (sd / f"{jid}.json").write_text("fio: synthetic warning line\n" + json.dumps(fj))
                meta = {"id": jid, "stage": stage, "label": job.label, "rep": rep, "rw": job.rw, "pattern": job.pattern,
                        "bs": job.bs, "bs_bytes": bs, "iodepth": job.iodepth, "numjobs": job.numjobs,
                        "rwmixread": job.rwmixread, "span_gib": job.span_gib or cfg.size_gib, "direct": job.direct,
                        "ioengine": job.ioengine or cfg.ioengine, "compress_pct": job.compress_pct, "runtime_s": job.runtime or cfg.runtime,
                        "returncode": 0, "temp_before_c": 38 + rng.normal(0, 1), "temp_after_c": 44 + rng.normal(0, 1),
                        "temp_series": [[t, 40 + t / 12 + rng.normal(0, .5)] for t in range(0, (job.runtime or 15), 20)] if job.sample_temp else None}
                (sd / f"{jid}.meta.json").write_text(json.dumps(meta))
                if job.logs:
                    T = job.runtime
                    bw, io = [], []
                    cap_t = 0.4 * T   # fake SLC-cache exhaustion
                    for t in range(1, T + 1):
                        base = 2400e3 if job.pattern == "sequential" else 1100e3
                        v = base if t < cap_t else base * 0.28
                        v *= rng.normal(1, 0.03)
                        bw.append(f"{t*1000}, {int(v)}, 1, {bs}, 0")
                        io.append(f"{t*1000}, {int(v*1024/bs)}, 1, {bs}, 0")
                    (sd / f"{jid}_bw.1.log").write_text("\n".join(bw))
                    (sd / f"{jid}_iops.1.log").write_text("\n".join(io))
    print("synthetic data written to", OUT)


main()
