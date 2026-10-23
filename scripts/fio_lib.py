"""Shared helpers: job description, FIO job-file generation, temperature reading.

Everything that decides *what FIO is told to do* lives here, so the generated
.fio files in configs/generated/ are the single source of truth for methodology.
"""
from __future__ import annotations

import platform
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

PERCENTILES = "50:90:95:99:99.9:99.99"


def default_ioengine() -> str:
    if IS_WINDOWS:
        return "windowsaio"
    if IS_LINUX:
        return "libaio"
    return "posixaio"


def fio_filename(path: str) -> str:
    """FIO treats ':' as a file separator, so a Windows drive colon must be escaped."""
    p = str(path)
    return p.replace(":", r"\:") if IS_WINDOWS else p


@dataclass
class Config:
    target: str                  # path of the throwaway test file (or raw device)
    size_gib: float = 16.0       # size of the test file == max LBA span used
    runtime: int = 15            # seconds per measured point
    ramp: int = 2                # seconds discarded at start of each point
    reps: int = 3                # repetitions per point
    tail_runtime: int = 60
    steady_seconds: int = 300
    precondition_seconds: int = 120
    cooldown: int = 2            # seconds idle between jobs
    bs_qds: tuple = (1, 32)      # queue depths used for the block-size sweep
    qds: tuple = (1, 2, 4, 8, 16, 32, 64, 128, 256)
    ioengine: str = field(default_factory=default_ioengine)
    fio_bin: str = "fio"
    profile: str = "standard"


@dataclass
class Job:
    stage: str
    label: str                       # unique inside a stage (without the rep suffix)
    rw: str                          # read | write | randread | randwrite | randrw | rw
    bs: str = "4k"
    iodepth: int = 1
    numjobs: int = 1
    rwmixread: Optional[int] = None
    span_gib: Optional[float] = None  # LBA range used (default: whole test file)
    runtime: Optional[int] = None
    ramp: Optional[int] = None
    direct: int = 1
    ioengine: Optional[str] = None
    compress_pct: int = 0
    logs: bool = False                # write per-second bw/iops/lat logs
    reps: Optional[int] = None        # override Config.reps
    sample_temp: bool = False
    note: str = ""
    extra: dict = field(default_factory=dict)  # fio options; value None = drop the key

    @property
    def pattern(self) -> str:
        return "random" if self.rw.startswith("rand") else "sequential"

    def bs_bytes(self) -> int:
        s = self.bs.lower()
        mult = {"k": 1024, "m": 1024 ** 2}
        return int(float(s[:-1]) * mult[s[-1]]) if s[-1] in mult else int(s)


def job_id(job: Job, rep: int) -> str:
    return f"{job.stage}__{job.label}__r{rep}"


def job_options(job: Job, cfg: Config, rep: int) -> dict:
    """Ordered dict of FIO options for one measured point."""
    jid = job_id(job, rep)
    runtime = job.runtime if job.runtime is not None else cfg.runtime
    ramp = job.ramp if job.ramp is not None else cfg.ramp
    span = job.span_gib if job.span_gib is not None else cfg.size_gib
    o: dict = {
        "name": jid,
        "filename": fio_filename(cfg.target),
        "ioengine": job.ioengine or cfg.ioengine,
        "direct": job.direct,
        "rw": job.rw,
        "bs": job.bs,
        "iodepth": job.iodepth,
        "numjobs": job.numjobs,
        "size": f"{int(span * 1024)}m",
        "offset": 0,
        "time_based": 1,
        "runtime": runtime,
        "ramp_time": ramp,
        "group_reporting": 1,
        "randrepeat": 0,
        "refill_buffers": 1,
        "buffer_compress_percentage": job.compress_pct,
        "percentile_list": PERCENTILES,
    }
    if job.rwmixread is not None:
        o["rwmixread"] = job.rwmixread
    if job.pattern == "random":
        o["norandommap"] = 1   # random offsets are bs-aligned (fio default blockalign=bs)
    if job.logs:
        o["write_bw_log"] = jid
        o["write_iops_log"] = jid
        o["write_lat_log"] = jid
        o["log_avg_msec"] = 1000
    for k, v in job.extra.items():
        if v is None:
            o.pop(k, None)
        else:
            o[k] = v
    return o


def job_file_text(job: Job, cfg: Config, rep: int) -> str:
    lines = [f"; stage={job.stage} label={job.label} rep={rep}"]
    if job.note:
        lines.append(f"; {job.note}")
    lines.append("[global]")  # intentionally empty; every option is explicit below
    lines.append(f"[{job_id(job, rep)}]")
    for k, v in job_options(job, cfg, rep).items():
        if k == "name":
            continue
        lines.append(f"{k}={v}")
    return "\n".join(lines) + "\n"


def prep_file_text(cfg: Config) -> str:
    """Lay out (fully write) the test file sequentially: this also acts as the first fill."""
    return "\n".join([
        "; prep: write the whole test file once (layout + sequential fill)",
        "[global]",
        "[prep_fill]",
        f"filename={fio_filename(cfg.target)}",
        f"ioengine={cfg.ioengine}",
        "direct=1",
        "rw=write",
        "bs=1m",
        "iodepth=16",
        f"size={int(cfg.size_gib * 1024)}m",
        "refill_buffers=1",
        "buffer_compress_percentage=0",
        "",
    ])


def precondition_file_text(cfg: Config) -> str:
    return "\n".join([
        "; precondition: sustained 4KiB random overwrite of the full range",
        "[global]",
        "[prep_randwrite]",
        f"filename={fio_filename(cfg.target)}",
        f"ioengine={cfg.ioengine}",
        "direct=1",
        "rw=randwrite",
        "bs=4k",
        "iodepth=32",
        f"size={int(cfg.size_gib * 1024)}m",
        "time_based=1",
        f"runtime={cfg.precondition_seconds}",
        "randrepeat=0",
        "norandommap=1",
        "refill_buffers=1",
        "buffer_compress_percentage=0",
        "",
    ])


# ----------------------------------------------------------------- temperature
def drive_letter(path: str) -> Optional[str]:
    p = str(path)
    return p[0].upper() if len(p) > 1 and p[1] == ":" else None


def read_temperature(target: str) -> Optional[float]:
    """Drive temperature in deg C via Windows storage reliability counters (None if unavailable)."""
    if not IS_WINDOWS:
        return None
    letter = drive_letter(target)
    if not letter:
        return None
    ps = (
        f"$dn=(Get-Partition -DriveLetter {letter}).DiskNumber;"
        "Get-PhysicalDisk | Where-Object { $_.DeviceId -eq $dn } | "
        "Get-StorageReliabilityCounter | Select-Object -ExpandProperty Temperature"
    )
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, timeout=30).stdout.strip()
        return float(out.splitlines()[0]) if out else None
    except Exception:
        return None


def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p
