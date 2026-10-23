# SSD Performance Profiling: Report

**Course:** ECSE 4320/6320 Advanced Computer Systems, Project 3  **Author:** `Marie Morales`  **Date:** 10/22/2026


## 0. AI-use note

**Tools:** Claude (Anthropic), in a chat/coding session.

**What it generated:** the FIO job generator and runner, the result parser, the plotting and analysis scripts, the repository layout, the PowerShell environment-capture script, the skeleton of this report, and this draft.

**What I did myself:** I installed Python and FIO, ran every experiment on my own laptop, and examined the results and plots. I applied the fixes below when things broke.
- The default 16 GiB test file did not fit (about 8.3 GB free), so I ran with a 4 GiB file since there was nothing else from my laptop that I could delete.
- The plot script crashed on Windows because of a text-encoding error; I ran all Python scripts with `python -X utf8`.
- The two pitfall tests that used FIO's `sync` engine failed, because Windows refuses direct I/O with synchronous engines. I replaced them with `windowsaio` tests at `iodepth=1` and at 32 jobs, and re-ran that stage.
- I wrote my own predictions for the hypotheses (H1-H9) before running any experiment. 
- I ran the second batch of experiments from an administrator terminal so the drive temperature could be recorded, and I skipped the optional free-space experiment because I could not free up space on the drive.
- I read each results section of this report, checked the numbers against my own tables, and corrected the draft's wording where it did not match what I understood or what the data showed.


## 1. Methodology

| Item | Value |
|---|---|
| SSD | Samsung MZVLQ128HCHQ-00BH1, firmware HPS1NFAV, NVMe, 128 GB, 512-byte sectors, health "Healthy" |
| Filesystem / free space | NTFS on C: (system drive); about 4.6 GB free of about 118 GB during tests (nearly full, could not free more) |
| BitLocker / Defender real-time / write cache | BitLocker off; Defender real-time protection off; device write caching `on` |
| Test target | throwaway file `C:\fio_test\ssd_profile_testfile.bin`, 4 GiB, direct I/O (no OS cache); not a raw device; deleted afterwards |
| Machine | HP Laptop 17z-cp000, AMD Athlon Gold 3150U (2 cores / 4 threads, up to 2.4 GHz), about 10 GB RAM, Windows 11 Home build 22631 |
| Power / load | HP Recommended power plan (not High performance); plugged in; PC left idle during runs |
| FIO / engine | fio-3.43, `windowsaio` |
| Profile | "quick": 8 s measured + 1 s ramp, 2 repetitions per point; tail runs 20 s; steady-state runs 60 s |
| Run order | randomized within each repetition (decorrelates thermal drift) |
| Data pattern | incompressible (`refill_buffers=1`, `buffer_compress_percentage=0`) |
| Preconditioning | one sequential fill of the 4 GiB file, then 30 s of 4 KiB random overwrite |
| Temperature | Windows storage reliability counters, read before/after each tail and steady-state run (Phase B ran as administrator; Phase A did not record temperature) |
| Alignment | random offsets aligned to the block size (FIO default); 512-byte sectors |

Latency percentiles are FIO completion latencies (`clat`); "mean latency" is FIO total latency (`lat`). Results are mean ± standard deviation over 2 repetitions. Because of the small number of repetitions, I treat differences below about 20% as not significant (the same 4 KiB random-read QD32 workload measured 15.6k IOPS in the mix test and 19.0k in the block-size test).

Reproduce: see `README.md`. Commands I ran are listed in `data/env/notes.md`. Every measured point has its FIO job file in `configs/generated/` and its raw JSON in `data/raw/`.

## 2. Hypotheses and outcome

Predictions are in `HYPOTHESES.md`. I wrote them after the first batch of runs had started but before I opened any results, and before the second batch ran. The `sync`-engine tests could not run on Windows, and I did not make predictions for the replacement tests.

| H | Prediction | Outcome |
|---|---|---|
| H1 | QD1 write faster than read | Matched: median 80 µs vs 152 µs |
| H3 | Mixes below the no-interference baseline; read latency rises with writes | Not matched for random (at or above baseline). Read latency rose clearly only for sequential. |
| H4 | Throughput rises then flattens, knee at QD 16–64; latency climbs | Matched for reads (knee 16). Writes knee at QD4 (earlier than predicted). |
| H5 | Tail-to-median gap about constant with QD | Roughly: p99/p50 stays 3–8× with no trend |
| H6 | Clear drop in sustained writes | Sequential: yes. Random: no one-way drop, fluctuation instead. |
| H7 | Range barely matters | Matched |
| H8 | Buffered I/O much faster | Not matched: 0.59× |
| H9 | Compressible data faster | Not matched: no clear effect |

## 3. Results

### 3.1 Zero-queue baselines (Fig. 1, Table 1)

| QD=1 workload | Mean (µs) | p50 | p95 | p99 | p99.9 |
|---|---|---|---|---|---|
| Random read 4k | 236.4 | 152.6 | 245.2 | 634.9 | 3,482.6 |
| Random write 4k |178.6 | 80.4 | 148.5 | 554 | 6,021.1 |
| Sequential read 128k | 351.1 | 183.3 | 513 | 1,341.4 | 7,200.8 |
| Sequential write 128k | 2,378.7 | 419.8 | 12,451.8 | 30,408.7 | 32,636.9 |

Write median latency (80 µs) is about half the read median (152 µs), and the mean agrees (179 µs vs 236 µs), so a typical 4 KiB random write completes faster than a typical read at QD1. This is consistent with the SSD confirming a write as soon as the data reaches its fast internal buffer, before the data has been stored in the flash, while a read has to fetch the data from the flash before it can answer. This is my explanation; I did not look inside the drive. The advantage disappears under sustained load: in section 3.2 writes cap at 60-75 MiB/s while reads reach about 500 MiB/s.
A percentile is a cutoff. A random-read p50 of 152 µs means half of the requests finished in 152 µs or less, and a p99.9 of 3,482 µs means all but the slowest 1 in 1,000 requests finished within about 3.5 ms. Latency rises steadily with the percentile (152 µs at p50, 245 µs at p95, 634 µs at p99, 3,482 µs at p99.9), so rare requests are more than 20 times slower than a typical one. The p99.9 is higher for writes (6,021 µs) than for reads (3,482 µs), but both have large error bars, so I do not treat that difference as certain.
Sequential 128 KiB writes show an especially heavy tail: the median is 420 µs but the mean is 2,379 µs (5.7 times the median) and p99 is 30 ms. A few very slow requests pull the average far above what a typical request sees, which suggests occasional stalls.
The QD1 read latency is higher than I would expect for an NVMe drive. Possible reasons are Windows driver and filesystem overhead and a slow CPU; I did not test these.

### 3.2 Block size and access pattern (Figs. 2–3, Table 2; QD32)

Random and sequential access perform similarly, especially at large blocks (128 KiB read: 3,995 vs 3,996 IOPS; 256 KiB write: 290 vs 279 IOPS). 
At small blocks sequential access was somewhat slower in several cases (4 KiB read: 12,079 vs 19,033 IOPS and p99 6.4 ms vs 3.9 ms; 128 KiB write p99: 311 ms vs 111 ms). 
Because each point has only 2 repetitions and the run-to-run spread is large, I treat these as possible small effects, not firm differences. 
I did not test the cause. The overall result is expected for flash, which has no seek time like a spinning disk. 
Sequential 128 KiB write has a higher p99 than sequential 256 KiB write (311 ms vs 244 ms), 
which is not what block size alone would predict and may be a stall.
### 3.3 Read/write mix (Fig. 4, Table 3; QD32)

"Baseline" is the throughput expected if reads and writes did not interfere: 1 / (p/R + (1−p)/W), computed from my pure-read (R) and pure-write (W) runs.

| Mix | Baseline | Measured | Difference |
|---|---|---|---|
| Random 4k, 70% read | 13,846 IOPS | 17,424 | +26% |
| Random 4k, 50% read | 12,889 | 13,410 | +4% |
| Sequential 128k, 70% read | 160 MiB/s | 185 | +16% |
| Sequential 128k, 50% read | 110 | 111 | +1% |

When reads and writes happen together, the random and sequential mixes behave very differently. 
The random mix has much lower throughput than the sequential mix (52-68 MiB/s vs 111-185 MiB/s), but this is because the random runs use 4 KiB blocks and the sequential runs use 128 KiB blocks, not because random access is slower. 
The random mix actually has far more IOPS (13-17k vs 0.9-1.5k), and its latency stays pretty low (1.2-1.6 ms).
For the sequential mix the IOPS is lower, but the throughput is much higher because each request is bigger. 
The latency also gets very high for both reads and writes (22.7 ms read and 19.5 ms write at 70% read, and 36.8 ms and 35.4 ms at 50% read). 
When it is just sequential writes, the latency is through the roof at 65.2 ms, almost double the 50% mix. 
This matches the queueing check from 3.2: 32 requests of 128 KiB is 4 MiB waiting, and at 62 MiB/s that takes about 65 ms.
To see whether reads and writes get in each other's way, I compared each mix to the baseline, which is the throughput I would expect if they did not interfere (calculated from my pure-read and pure-write runs). 
All four measured mixes were at or above the baseline (for example 185 vs 160 MiB/s for sequential at 70% read), so I found no evidence that reads and writes harm each other. 
This does not match my hypothesis H3, which predicted throughput below the baseline. The +26% for random 4 KiB at 70% read is probably noise, because my pure-read results varied by about 20% between runs. 
The total throughput still drops as writes are added because writes are about 8 times slower than reads.

### 3.4 Queue depth, knee and Little's Law (Figs. 5–6, Tables 4–5)

| 4k random | Peak IOPS | Knee (chord / 90% of peak) | N* = peak IOPS × QD1 latency |
|---|---|---|---|
| Read | 20,888 (QD16) | QD16 / QD16 | 4.6 |
| Write | 12,640 (QD4) | QD4 / QD4 | 1.7 |

Throughput rises with queue depth up to the knee and then stays flat. For random read it peaks at 20.9k IOPS at QD16 and is 19.0k at QD256, a difference within the noise (±4k). 
Past the knee, extra queue depth only adds latency: read latency goes from 487 µs to 1,794 µs to 6,909 µs for QD 16, 64 and 256, roughly proportional to QD, as W ≈ QD / peak IOPS predicts. 
The small N* values (4.6 for read, 1.7 for write) mean the drive overlaps only a few requests, so its throughput saturates at a low queue depth.
Little's Law (L = IOPS × latency) gives L/QD = 0.98 for read and 0.97 for write at QD1, as expected. 
At higher QD it falls to about 0.5-0.65 (for example read at QD256: 131 requests in flight versus 256 set). 
I cannot fully explain this. Possible reasons are that Windows or the single FIO thread is not keeping all requests in flight, 
or that FIO's latency excludes some of the waiting. The 32-job test is evidence for a limit on the host side: 
it gave 29,302 ± 22,753 IOPS, and one of its two repetitions reached about 45k IOPS, above the 22k of the single-job QD32 run.

### 3.5 Tail latency (Fig. 7, Table 6)

| 4k random | QD | p50 (µs) | p99 | p99.9 | p99.99 | p99/p50 |
|---|---|---|---|---|---|---|
| Read | 4 | 163 | 513 | 2,683 | 26,739 | 3.2 |
| Read | 16 | 520 | 3,981 | 24,117 | 68,026 | 7.7 |
| Read | 64 | 1,819 | 7,389 | 37,749 | 102,629 | 4.1 |
| Write | 4 | 166 | 1,157 | 6,668 | 64,815 | 7.0 |
| Write | 16 | 635 | 3,596 | 17,924 | 88,474 | 5.7 |
| Write | 64 | 2,851 | 14,254 | 48,497 | 98,042 | 5.0 |

The p99-to-median ratio stays between about 3 and 8 at every queue depth, without a consistent trend, so my prediction that the gap would stay about the same roughly holds for p99. 
In absolute terms every percentile grows with queue depth (read p99: 513 µs at QD4 to 7,389 µs at QD64), because each request spends more time waiting behind the others in the queue.
The extreme tail is not explained by queueing alone. Even at QD4, where there is almost no queue, the p99.99 is 26.7 ms against a median of 163 µs, 
and the maximum latency is 80-210 ms across the runs. The tail is long even at low queue depth, probably because serving my requests is not the only thing the drive is doing. 
It also has to find free space for new data and run garbage collection, which clears out old unused data and moves still-valid data from the pages it is erasing. 
A request that arrives during this work has to wait, and the same can happen to reads if they are on the same flash chip as a write or erase. 
Other possible causes are read retries and Windows background activity. I did not test any of these. 
The drive was also nearly full, which may make garbage collection worse, but I did not confirm that.
The p99.99 values are noisy because they depend on a few requests per run and I have only 2 repetitions 
(see the error bars in Fig. 7).

### 3.6 Burst vs steady state and temperature (Fig. 8, Tables 7 and 11)

Sequential 128 KiB writes: there is an initial burst of about 270 MiB/s that lasts only 1-2 s, and then throughput settles near 70 MiB/s (about 4 times lower) for the rest of the 60 s. T
he "117 MiB/s first 10%" in Table 7 averages in that spike. This fits a small fast write buffer or cache that fills almost immediately, 
plausibly because the drive is nearly full. I did not verify this. Random 4 KiB writes: there is no one-way drop. Throughput fluctuates between about 19 and 58 MiB/s (about 5k-15k IOPS), 
consistent with the ~12k IOPS from the queue-depth sweep. The script flagged a "drop at 11 s" and a steady/burst ratio of 1.11, 
but both describe a temporary dip, not a lasting drop. So my hypothesis H6 (a clear drop in steady state) held for sequential writes but not for random writes.
Temperature: the drive was 44-66 °C before runs and reached 79-80 °C during sustained writes (Table 7). 
Write runs raised it by 3-14 °C (for example 44 to 58 °C in a 20 s run at QD64). 
I cannot attribute any slowdown to thermal throttling, because the sampler produced only one temperature reading per run, 
so there is no temperature trace to compare with the throughput dips. The sequential write slowdown happened within 1-2 s of starting, 
which is more consistent with a small write buffer filling than with the drive heating up, but without a temperature trace I cannot rule out thermal throttling. 
A slowdown from reaching steady state and one from cooling down would also look the same in the throughput curve, which is another reason I cannot separate them.
A longer test over a larger file would be needed to see SLC-cache exhaustion more clearly.

### 3.7 LBA range (Fig. 9, Table 8)

Random read: 22,312 ± 1,450 IOPS (1 GiB range) vs 20,282 ± 4,106 (4 GiB), a 9% difference that is inside the error bars. 
Random write: 12,294 ± 2,400 vs 12,172 ± 550. The range had no measurable effect over 1-4 GiB, which matches my hypothesis H7. 
Both ranges are tiny compared with the drive, so this does not tell me what happens over the full drive.

### 3.8 Data pattern (Table 10)

Random write IOPS: incompressible 12,557 ± 88, 50% compressible 13,667 ± 435, zeros 12,961 ± 871. 
The differences are small and not in the order compression would give (all-zero data is not faster than 50% compressible), 
and they are smaller than the run-to-run variation I saw elsewhere (about 20%). So I conclude that the controller does not 
exploit compressibility. This does not match my hypothesis H9, which predicted that compressible data would be faster. 
The main experiments use incompressible data.

## 4. Misleading setups and failure cases (Fig. 10, Table 9)

| 4 KiB random read, 1 GiB range | IOPS | Mean latency (µs) | vs control |
|---|---|---|---|
| Correct: direct I/O, `windowsaio`, QD32 | 22,282 ± 1,907 | 814 | 1.00× |
| Buffered I/O (page cache) | 13,175 ± 118 | 2,262 | 0.59× |
| `windowsaio`, iodepth=1 (the FIO default) | 3,177 ± 56 | 307 | 0.14× |
| `windowsaio`, 32 jobs × iodepth 1 | 29,302 ± 22,753 | 1,557 | 1.32× |

Buffered I/O was slower, not faster, than direct I/O (13,175 vs 22,282 IOPS). This is the opposite of my prediction, and I did not test why. 
One possible reason is that the 13-second run was too short for the 1 GiB range to be fully cached, so there were still many cache misses, 
and the cache path adds overhead. A longer run with a pre-warmed cache would be expected to be much faster than the SSD, 
but I did not run it. With iodepth left at its default of 1, FIO only has one request in flight at a time, so the SSD is idle most of the time 
and the test measures the latency of a single request instead of what the drive can do. 
The same drive gave 3,177 IOPS at iodepth 1 and 22,282 IOPS at QD32, so a benchmark that does not set the queue depth makes 
the SSD look about 7 times slower than it is.

## 5. Correctness validation

## 5. Correctness validation

- Little's Law holds at QD1: L/QD = 0.98 for read and 0.97 for write (Table 4). With one request in flight, IOPS × latency should be about 1, so the measured IOPS and latency agree with each other.
- In the bandwidth-bound regime, latency matches QD × block size / throughput within about 2% for 256 KiB reads and writes (15.0 vs 14.7 ms for reads; 109.6 vs 110.5 ms for writes).
- Different experiments agree: random 4 KiB write throughput is about 12k IOPS in the queue-depth sweep (12.1-12.5k for QD of 16 or more), the LBA test (12.2-12.3k), the data-pattern test (12.6k), and the steady-state run (about 40-55 MiB/s, or 10-14k IOPS).
- 124 of the 128 planned runs completed and were parsed. The 4 failures were the sync-engine jobs, which FIO on Windows refuses because they cannot use direct I/O (section 4); I replaced them with windowsaio variants, and each completed run has a job file in `configs/generated/`.

## 6. Honest anomalies

1. **Absolute performance is low for NVMe** (20k read IOPS, 500 MiB/s read ceiling, 60–75 MiB/s write ceiling). Plausible causes, none confirmed: a low-end OEM drive, a nearly full drive (4.6 GB free) leaving the controller little room to work, a slow 2-core CPU with a single FIO thread, Windows driver/filesystem overhead, and heat (79–80 °C).
2. **Little's Law gap at high QD** (L/QD about 0.5–0.65): unexplained (section 3.4).
3. **Large run-to-run variation** (about 20% for the same workload; large error bars in Figs. 5, 7, 10), because I used only 2 repetitions and the laptop environment is noisy.
4. **Mixed 70% workload above the pure-read result** (17.4k vs 15.6k IOPS): within noise; no real benefit is claimed.
5. **Buffered I/O slower than direct** (section 4).
6. **Heavy stalls on sequential writes** (mean 2.4 ms vs median 0.42 ms at QD1).
7. **Temperature sampler gave one point per run**, so thermal effects cannot be separated from housekeeping.

## 7. Limitations

- File-based test through NTFS and the Windows I/O stack, not a raw device (chosen for safety), so filesystem overhead is included.
- Nearly full system drive; the 4 GiB file means SLC-cache exhaustion and garbage-collection effects are only partly observable.
- "Quick" profile: 2 repetitions and 8–20 s runs; error bars are large and p99.99 estimates are noisy.
- One FIO thread for the main sweeps; peak IOPS may be limited by the host (see sections 3.4 and 4).
- Temperature trace too sparse; temperature was not recorded in Phase A.
- Single laptop, single SSD.
- Latencies are measured by FIO at the host, not inside the drive.

## 8. Conclusion

On this laptop's Samsung 128 GB NVMe drive, read performance is capped near 500 MiB/s and 20k random IOPS, and write performance near 60–75 MiB/s and 12k random IOPS. Throughput saturates at low queue depth (QD16 for reads, QD4 for writes), after which latency grows in proportion to queue depth, as queueing theory predicts. Tail latencies are large (p99.99 of tens of milliseconds). Several naive setups (default `iodepth`, buffered I/O) give misleading results. Because of the nearly full drive, few repetitions and a single FIO thread, the absolute numbers should be read as lower bounds on what the drive can do.

## Appendix: figures and tables

`plots/01–10`, `data/processed/tables.md` (Tables 1–11), `data/processed/summary.csv`, `data/processed/runs.csv`.