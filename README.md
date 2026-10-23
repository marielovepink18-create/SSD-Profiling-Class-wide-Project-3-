# SSD Performance Profiling (ECSE 4320/6320, Project 3)

FIO-based characterization of one SSD: QD=1 latency, block-size and read/write-mix sweeps,
queue-depth throughput-latency curve with knee + Little's Law, tail latency, burst vs steady state,
and a demonstration of misleading benchmark setups.

Everything is scripted: `run_experiments.py` writes the FIO job files (`configs/generated/`), runs them,
and stores raw FIO JSON in `data/raw/`; `parse_results.py` and `analyze_plots.py` produce
`data/processed/` and `plots/`.

## What I actually ran (my results)

- **Machine:** HP Laptop 17z-cp000, Samsung MZVLQ128HCHQ-00BH1 NVMe (128 GB), Windows 11, NTFS system drive (C:),
  about 4.6 GB free during the tests (nearly full). Details in `data/env/`.
- **Test file:** 4 GiB at `C:\fio_test\ssd_profile_testfile.bin` (the default 16 GiB did not fit), deleted afterwards.
- **Profile:** `quick` (2 repetitions per point; 8 s measured + 1 s ramp per run; tail runs 20 s; steady-state runs 60 s;
  30 s random-overwrite preconditioning). 65 points, 128 runs.
- **Two batches:** Phase A = `baseline,blocksize,rwmix,qdsweep`; then parse + analyse; Phase B = `tail,lba,datapattern,pitfall,steady`.
  Phase B was run from an Administrator terminal so the drive temperature could be read.
- **Commands (PowerShell, in the repo folder):**
  ```powershell
  python scripts\run_experiments.py --target C:\fio_test\ssd_profile_testfile.bin --size-gib 4 --profile quick --stages baseline,blocksize,rwmix,qdsweep
  python -X utf8 scripts\parse_results.py
  python -X utf8 scripts\analyze_plots.py
  python scripts\run_experiments.py --target C:\fio_test\ssd_profile_testfile.bin --size-gib 4 --profile quick --stages tail,lba,datapattern,pitfall,steady
  python -X utf8 scripts\parse_results.py
  python -X utf8 scripts\analyze_plots.py
  ```
  (`-X utf8` avoids a Windows text-encoding crash when writing `tables.md`.)
- **Pitfall tests:** the two `sync`-engine tests cannot run on Windows (FIO refuses direct I/O with synchronous engines).
  I replaced them with `windowsaio` tests at `iodepth=1` and at 32 jobs; see the report, section 4.
- **Environment:** laptop plugged in, HP Recommended power plan (not High performance), BitLocker off, Defender real-time protection off.

## What "test target" means (and why this is safe)

FIO needs something to read and write. The safe choice, and the one used here, is **one big throwaway
file** inside a folder on the SSD you want to test (the script's default is 16 GiB; I used 4 GiB).
FIO bypasses the Windows file cache (`direct=1`) so the file behaves like raw storage.
Nothing else on the drive is touched, and the script refuses to run if the file already exists and wasn't created
by it, or if you point it at a drive/folder/raw device. Delete the file afterwards.

With the default 16 GiB you need about 20 GiB free on the drive; use `--size-gib` for a smaller file.
Tests on the system drive (C:) work but background Windows activity adds noise.

## One-time setup (Windows)

1. **Python 3.10+** (python.org; tick "Add to PATH"). In the repo folder: `pip install -r requirements.txt`
2. **FIO for Windows**: I installed it with `winget install fio.fio` (version 3.43). Open a *new* PowerShell and check
   `fio --version`. If it isn't found, pass `--fio "C:\path\to\fio.exe"`.
3. Plug in the laptop and close browsers/games/sync clients. Don't use the PC while it runs.
4. Capture the environment for the report (run PowerShell **as Administrator** so SSD temperature/health are readable):
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\capture_env.ps1 -DriveLetter C
   ```
   Then manually note in `data/env/notes.md`: Defender real-time scanning on/off, write-cache policy
   (Device Manager > Disk drives > Properties > Policies), BitLocker on/off, laptop vs desktop.

## Options and notes

- `--dry-run` writes the `.fio` files and runs nothing.
- `--profile standard` (3 reps, 15 s runs, 5 min steady-state runs, about 2 h) exists but was **not** used for my results.
- Order matters: `qdsweep` runs before `tail`; after `qdsweep`, run `parse_results.py` + `analyze_plots.py` once so the
  tail stage can pick its queue depths from the detected knee (`data/processed/knee.json`). If you skip this,
  tail latency uses QD 8/32/128.
- When switching profiles, delete `data/raw` first (or use `--no-resume`) so results aren't mixed.
- `--temp` records drive temperature around every job (slower); the tail and steady stages always do.
- `scripts/` can run on Linux too (libaio); you'd replace `capture_env.ps1` with lsblk/nvme-cli output.

## Repository layout

| Path | Content |
|---|---|
| `scripts/run_experiments.py`, `experiments.py`, `fio_lib.py` | experiment matrix, job-file generation, safety checks, runner |
| `scripts/parse_results.py` | raw FIO JSON -> `data/processed/runs.csv`, `summary.csv` |
| `scripts/analyze_plots.py` | plots, knee detection, Little's Law, tables (`data/processed/tables.md`) |
| `scripts/capture_env.ps1` | hardware/OS/SSD description |
| `configs/generated/` | exact FIO job file of every measured point |
| `data/raw/`, `data/processed/`, `plots/` | measurements, parsed data, figures |
| `tools/make_synthetic_data.py` | fake data for testing the scripts only (output stamped SYNTHETIC) |
| `HYPOTHESES.md` | my pre-experiment predictions |
| `REPORT.md` | the report, including the AI-use note |

## Method summary (details in REPORT.md)

- `direct=1`, async engine (`windowsaio`), incompressible random buffers (`refill_buffers=1`), random offsets aligned to the block size.
- Each point (quick profile): 1 s ramp (discarded) + 8 s measured, 2 repetitions, run order shuffled within each repetition
  to decorrelate thermal drift; mean ± std reported.
- Preconditioning: one full sequential fill and 30 s of 4 KiB random overwrite before measurements.
- Latency percentiles are FIO `clat`; "mean latency" is FIO total `lat`.
