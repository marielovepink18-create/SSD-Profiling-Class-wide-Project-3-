#!/usr/bin/env python3
"""Run the SSD profiling experiments with FIO.

Examples (from the repo root):
  python scripts/run_experiments.py --target D:\\fio_test\\ssd_profile_testfile.bin --dry-run
  python scripts/run_experiments.py --target D:\\fio_test\\ssd_profile_testfile.bin --profile quick
  python scripts/run_experiments.py --target D:\\fio_test\\ssd_profile_testfile.bin --profile standard

Safety: only ever writes to --target (a throwaway file, created by this script).
Raw devices are refused unless you pass --allow-raw-device AND type the device path.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import experiments as ex  # noqa: E402
from fio_lib import (Config, IS_WINDOWS, default_ioengine, ensure_dir, job_file_text,  # noqa: E402
                     job_id, precondition_file_text, prep_file_text, read_temperature)

ROOT = Path(__file__).resolve().parent.parent
MARKER = ".ssd_profile_marker"


def die(msg: str):
    print(f"\nERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def is_raw_device(p: str) -> bool:
    return p.startswith("\\\\.\\") or p.startswith("/dev/")


def safety_checks(cfg: Config, args):
    t = cfg.target
    if is_raw_device(t):
        if not args.allow_raw_device:
            die("Target looks like a raw device. Refusing. Use a throwaway FILE instead "
                "(e.g. D:\\fio_test\\ssd_profile_testfile.bin).")
        print(f"!!! RAW DEVICE {t}: every byte in the used range will be OVERWRITTEN.")
        if input("Type the device path again to confirm: ").strip() != t:
            die("Confirmation did not match.")
        return
    p = Path(t)
    if p.suffix == "" or p.is_dir():
        die("--target must be a FILE path (e.g. D:\\fio_test\\ssd_profile_testfile.bin), not a folder/drive.")
    ensure_dir(p.parent)
    marker = p.parent / MARKER
    if p.exists() and not marker.exists():
        die(f"{p} already exists and was not created by this tool. Refusing to overwrite it. "
            "Choose a new file name.")
    free = shutil.disk_usage(p.parent).free
    need = int(cfg.size_gib * 1024 ** 3 * 1.1) if not p.exists() else 0
    if free < need:
        die(f"Not enough free space: need ~{need / 1024**3:.1f} GiB, have {free / 1024**3:.1f} GiB. "
            "Lower --size-gib.")
    marker.write_text("Created by ssd-profiling. Safe to delete the test file in this folder.\n")


def estimate_minutes(plan, cfg: Config) -> float:
    secs = 0.0
    for job, reps in plan:
        rt = job.runtime if job.runtime is not None else cfg.runtime
        rp = job.ramp if job.ramp is not None else cfg.ramp
        secs += reps * (rt + rp + cfg.cooldown + 2)
    secs += cfg.precondition_seconds + cfg.size_gib * 1024 / 1500  # fill at >= ~1.5 GB/s worst case
    return secs / 60


class TempSampler(threading.Thread):
    def __init__(self, target, every=20):
        super().__init__(daemon=True)
        self.target, self.every, self.series, self._halt = target, every, [], threading.Event()
        self.t0 = time.time()

    def run(self):
        while not self._halt.is_set():
            t = read_temperature(self.target)
            if t is not None:
                self.series.append([round(time.time() - self.t0, 1), t])
            self._halt.wait(self.every)

    def stop(self):
        self._halt.set()
        self.join(timeout=35)


def fio_version(fio_bin):
    try:
        return subprocess.run([fio_bin, "--version"], capture_output=True, text=True).stdout.strip()
    except Exception:
        return "unknown"


def run_fio(fio_bin, jobfile: Path, out_json: Path, cwd: Path, timeout=None):
    cmd = [fio_bin, "--output-format=json", f"--output={out_json}", str(jobfile)]
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", help="path of the throwaway test FILE FIO will create and use")
    ap.add_argument("--size-gib", type=float, default=16.0, help="test file size / max LBA span (default 16)")
    ap.add_argument("--profile", choices=list(ex.PROFILES), default="standard")
    ap.add_argument("--stages", default="all", help=f"comma list from: {','.join(ex.STAGES)} (default all, in order)")
    ap.add_argument("--ioengine", default=default_ioengine())
    ap.add_argument("--fio", default="fio", help="path to the fio executable")
    ap.add_argument("--temp", action="store_true", help="record drive temperature before/after every job (slower)")
    ap.add_argument("--no-resume", action="store_true", help="re-run points even if raw results exist")
    ap.add_argument("--skip-prep", action="store_true", help="skip layout/precondition (file already filled)")
    ap.add_argument("--dry-run", action="store_true", help="write job files and print the plan only")
    ap.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    ap.add_argument("--allow-raw-device", action="store_true")
    args = ap.parse_args()

    prof = dict(ex.PROFILES[args.profile])
    cfg = Config(target=args.target or "DRYRUN.bin", size_gib=args.size_gib, ioengine=args.ioengine,
                 fio_bin=args.fio, profile=args.profile, **prof)
    stages = ex.STAGES if args.stages == "all" else [s.strip() for s in args.stages.split(",")]
    for s in stages:
        if s not in ex.STAGES:
            die(f"unknown stage {s}")

    plan, all_jobs = [], []
    for s in stages:
        for job in ex.build_jobs(s, cfg, ROOT):
            reps = job.reps if job.reps is not None else cfg.reps
            plan.append((job, reps))
            all_jobs.append((job, reps))

    # --- write every job file (these are the deliverable "FIO configs")
    gen = ensure_dir(ROOT / "configs" / "generated")
    (gen / "prep_fill.fio").write_text(prep_file_text(cfg))
    (gen / "prep_precondition.fio").write_text(precondition_file_text(cfg))
    for job, reps in plan:
        d = ensure_dir(gen / job.stage)
        for r in range(1, reps + 1):
            (d / f"{job_id(job, r)}.fio").write_text(job_file_text(job, cfg, r))

    njobs = sum(r for _, r in plan)
    est = estimate_minutes(plan, cfg)
    print(f"Profile={cfg.profile}  stages={','.join(stages)}  distinct points={len(plan)}  runs={njobs}")
    print(f"Estimated time: ~{est:.0f} min.  Test file: {cfg.size_gib:g} GiB.  Engine: {cfg.ioengine}")
    print("Write volume warning: write tests are sustained; expect hundreds of GB to a few TB written in "
          "total on the 'standard' profile (well within any modern SSD's endurance rating, but be aware).")
    if args.dry_run:
        print(f"Dry run: job files written to {gen}. Nothing was executed.")
        return
    if not args.target:
        die("--target is required (unless --dry-run)")

    safety_checks(cfg, args)
    if not args.yes:
        print(f"\nThis will create and repeatedly read/write the file: {cfg.target}")
        if input("Type YES to start: ").strip() != "YES":
            die("Aborted by user.")

    raw = ensure_dir(ROOT / "data" / "raw")
    ver = fio_version(cfg.fio_bin)
    (raw / "run_config.json").write_text(json.dumps({
        "started": dt.datetime.now().isoformat(timespec="seconds"), "fio_version": ver,
        "config": cfg.__dict__, "stages": stages}, indent=2, default=str))
    print(f"fio version: {ver}")

    if not args.skip_prep:
        prep_dir = ensure_dir(raw / "prep")
        for name, jf in [("prep_fill", gen / "prep_fill.fio"), ("prep_precondition", gen / "prep_precondition.fio")]:
            out = prep_dir / f"{name}.json"
            if out.exists() and not args.no_resume:
                print(f"[prep] {name}: already done, skipping")
                continue
            print(f"[prep] {name} ... (this takes a while)")
            t0 = time.time()
            res = run_fio(cfg.fio_bin, jf, out, prep_dir)
            if res.returncode != 0:
                die(f"fio failed in {name}:\n{res.stdout}\n{res.stderr}")
            print(f"[prep] {name} done in {time.time() - t0:.0f}s")

    done = failed = 0
    t_start = time.time()
    for stage in stages:
        jobs = [(j, r) for j, r in plan if j.stage == stage]
        if not jobs:
            continue
        sdir = ensure_dir(raw / stage)
        maxrep = max(r for _, r in jobs)
        print(f"\n=== stage {stage}: {len(jobs)} points x up to {maxrep} reps ===")
        for rep in range(1, maxrep + 1):
            order = [j for j, r in jobs if rep <= r]
            random.Random(1000 * rep + len(stage)).shuffle(order)   # decorrelate thermal drift
            for job in order:
                jid = job_id(job, rep)
                out = sdir / f"{jid}.json"
                if out.exists() and not args.no_resume:
                    done += 1
                    continue
                jobfile = gen / stage / f"{jid}.fio"
                t_before = read_temperature(cfg.target) if (args.temp or job.sample_temp) else None
                sampler = None
                if job.sample_temp and t_before is not None:
                    sampler = TempSampler(cfg.target)
                    sampler.start()
                t0 = time.time()
                start = dt.datetime.now().isoformat(timespec="seconds")
                try:
                    res = run_fio(cfg.fio_bin, jobfile, out, sdir)
                    rc, err = res.returncode, (res.stderr or "")[-500:]
                except Exception as e:  # noqa: BLE001
                    rc, err = -1, repr(e)
                wall = time.time() - t0
                if sampler:
                    sampler.stop()
                t_after = read_temperature(cfg.target) if (args.temp or job.sample_temp) else None
                meta = {
                    "id": jid, "stage": stage, "label": job.label, "rep": rep, "rw": job.rw,
                    "pattern": job.pattern, "bs": job.bs, "bs_bytes": job.bs_bytes(),
                    "iodepth": job.iodepth, "numjobs": job.numjobs, "rwmixread": job.rwmixread,
                    "span_gib": job.span_gib if job.span_gib is not None else cfg.size_gib,
                    "direct": job.direct, "ioengine": job.ioengine or cfg.ioengine,
                    "compress_pct": job.compress_pct, "note": job.note,
                    "extra": {k: v for k, v in job.extra.items()},
                    "runtime_s": job.runtime if job.runtime is not None else cfg.runtime,
                    "start": start, "wall_s": round(wall, 1), "returncode": rc, "stderr_tail": err,
                    "temp_before_c": t_before, "temp_after_c": t_after,
                    "temp_series": sampler.series if sampler else None, "fio_version": ver,
                }
                (sdir / f"{jid}.meta.json").write_text(json.dumps(meta, indent=2))
                if rc != 0:
                    failed += 1
                    print(f"  FAILED {jid} (rc={rc}): {err.strip()[:200]}")
                else:
                    done += 1
                    el = (time.time() - t_start) / 60
                    print(f"  ok  {jid}  [{done}/{njobs}, {el:.0f} min elapsed]")
                time.sleep(cfg.cooldown)

    print(f"\nFinished: {done} ok/skipped, {failed} failed, {(time.time() - t_start) / 60:.0f} min.")
    print("Next: python scripts/parse_results.py && python scripts/analyze_plots.py")
    print(f"You can delete the test file now: {cfg.target}")


if __name__ == "__main__":
    main()
