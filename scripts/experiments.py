"""Experiment matrix. One function per stage; each returns a list of Job."""
from __future__ import annotations

import json
from pathlib import Path

from fio_lib import Config, Job

BLOCK_SIZES = ["4k", "16k", "32k", "64k", "128k", "256k"]
STAGES = ["baseline", "blocksize", "rwmix", "qdsweep", "tail", "lba",
          "datapattern", "pitfall", "steady"]

PROFILES = {
    # smoke test / fallback: ~35-45 min on a typical NVMe
    "quick": dict(runtime=8, ramp=1, reps=2, tail_runtime=20, steady_seconds=60,
                  precondition_seconds=30, cooldown=1, bs_qds=(32,),
                  qds=(1, 4, 16, 64, 256)),
    # what the report should be based on: roughly 2 h
    "standard": dict(runtime=15, ramp=2, reps=3, tail_runtime=60, steady_seconds=300,
                     precondition_seconds=120, cooldown=2, bs_qds=(1, 32),
                     qds=(1, 2, 4, 8, 16, 32, 64, 128, 256)),
}


def baseline(cfg: Config):
    """Zero-queue (QD=1, one job) latency baselines."""
    return [
        Job("baseline", "randread_4k_qd1", "randread", "4k", 1),
        Job("baseline", "randwrite_4k_qd1", "randwrite", "4k", 1),
        Job("baseline", "seqread_128k_qd1", "read", "128k", 1),
        Job("baseline", "seqwrite_128k_qd1", "write", "128k", 1),
    ]


def blocksize(cfg: Config):
    jobs = []
    for qd in cfg.bs_qds:
        for rw, tag in [("randread", "randread"), ("randwrite", "randwrite"),
                        ("read", "seqread"), ("write", "seqwrite")]:
            for bs in BLOCK_SIZES:
                jobs.append(Job("blocksize", f"{tag}_{bs}_qd{qd}", rw, bs, qd))
    return jobs


def rwmix(cfg: Config):
    jobs = []
    for pat_rw, bs, tag in [("randrw", "4k", "rand4k"), ("rw", "128k", "seq128k")]:
        for mix in (100, 70, 50, 0):
            jobs.append(Job("rwmix", f"{tag}_r{mix}_qd32", pat_rw, bs, 32, rwmixread=mix))
    return jobs


def qdsweep(cfg: Config):
    jobs = []
    for rw, tag in [("randread", "randread"), ("randwrite", "randwrite")]:
        for qd in cfg.qds:
            jobs.append(Job("qdsweep", f"{tag}_4k_qd{qd}", rw, "4k", qd))
    return jobs


def _knee_qds(cfg: Config, root: Path):
    """Tail-latency QDs: mid-QD, near-knee, past-knee (from the QD sweep if analysed)."""
    kf = root / "data" / "processed" / "knee.json"
    if kf.exists():
        k = json.loads(kf.read_text())
        knee = int(k.get("randread_knee_qd_chord") or k.get("randread_knee_qd_90pct") or 32)
    else:
        knee = 32
    mid = max(2, knee // 4)
    return sorted({mid, knee, min(256, knee * 4)})


def tail(cfg: Config, root: Path):
    jobs = []
    for qd in _knee_qds(cfg, root):
        for rw, tag in [("randread", "randread"), ("randwrite", "randwrite")]:
            jobs.append(Job("tail", f"{tag}_4k_qd{qd}", rw, "4k", qd,
                            runtime=cfg.tail_runtime, sample_temp=True))
    return jobs


def lba(cfg: Config):
    jobs = []
    spans = [s for s in (1, 4) if s < cfg.size_gib] + [cfg.size_gib]
    for rw, tag in [("randread", "randread"), ("randwrite", "randwrite")]:
        for s in spans:
            jobs.append(Job("lba", f"{tag}_4k_qd32_span{s:g}g", rw, "4k", 32, span_gib=s))
    return jobs


def datapattern(cfg: Config):
    return [
        Job("datapattern", "randwrite_4k_qd32_incompressible", "randwrite", "4k", 32, compress_pct=0),
        Job("datapattern", "randwrite_4k_qd32_compress50", "randwrite", "4k", 32, compress_pct=50),
        Job("datapattern", "randwrite_4k_qd32_zeros", "randwrite", "4k", 32,
            extra={"zero_buffers": 1, "refill_buffers": None, "buffer_compress_percentage": None}),
    ]


def pitfall(cfg: Config):
    """Deliberately 'naive' setups next to the correct one (all 4KiB random read, 1 GiB range)."""
    common = dict(span_gib=1)
    return [
        Job("pitfall", "correct_direct_aio_qd32", "randread", "4k", 32, **common,
            note="control: direct I/O, async engine, real QD32"),
        Job("pitfall", "buffered_aio_qd32", "randread", "4k", 32, direct=0, ramp=5, **common,
            note="PITFALL: page cache serves reads of the 1 GiB range -> not the SSD"),
        Job("pitfall", "aio_iodepth1_default", "randread", "4k", 1, **common,
            note="PITFALL: iodepth left at its default of 1 -> effective QD=1 (sync engines cannot use direct I/O on Windows)"),
        Job("pitfall", "aio_iodepth1_numjobs32", "randread", "4k", 1, numjobs=32, **common,
            note="32 parallel jobs at iodepth 1 -> effective QD=32"),
    ]


def steady(cfg: Config):
    return [
        Job("steady", "randwrite_4k_qd32_timeseries", "randwrite", "4k", 32,
            runtime=cfg.steady_seconds, ramp=0, logs=True, reps=1, sample_temp=True,
            note="sustained writes; per-second logs show burst -> steady state / throttling"),
        Job("steady", "seqwrite_128k_qd32_timeseries", "write", "128k", 32,
            runtime=cfg.steady_seconds, ramp=0, logs=True, reps=1, sample_temp=True),
    ]


def build_jobs(stage: str, cfg: Config, root: Path):
    if stage == "tail":
        return tail(cfg, root)
    return globals()[stage](cfg)
