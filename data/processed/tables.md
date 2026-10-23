# Auto-generated tables

### Table 1 - Zero-queue (QD=1) baselines

| Workload (QD=1) | Mean (µs) | p50 (µs) | p95 (µs) | p99 (µs) | p99.9 (µs) | IOPS | MiB/s | reps |
|---|---|---|---|---|---|---|---|---|
| Random read 4k | 236.4 ± 36.5 | 151.6 ± 4.3 | 245.2 ± 67.3 | 633.9 ± 360.6 | 3481.6 ± 1703.0 | 4,209 | 16 | 2 |
| Random write 4k | 178.6 ± 31.5 | 80.4 ± 1.4 | 148.5 ± 14.5 | 554.0 ± 183.9 | 6021.1 ± 4553.0 | 5,519 | 22 | 2 |
| Sequential read 128k | 351.1 ± 42.1 | 183.3 ± 8.7 | 513.0 ± 33.3 | 1341.4 ± 755.9 | 7200.8 ± 4738.4 | 2,829 | 354 | 2 |
| Sequential write 128k | 2378.7 ± 14.4 | 419.8 ± 11.6 | 12451.8 ± 92.7 | 30408.7 ± 185.4 | 32636.9 ± 1112.2 | 416 | 52 | 2 |

Mean ± std over repetitions. Latency = fio completion latency percentiles (clat) except Mean, which is total latency (lat).

### Table 2 - Block-size sweep (same runs give throughput and latency)

| QD | Pattern | Block | IOPS | MiB/s | Mean lat (µs) | p99 (µs) |
|---|---|---|---|---|---|---|
| 32 | Random read | 4k | 19,033 | 74 ± 13 | 960 | 3,875 |
| 32 | Random read | 16k | 18,928 | 296 ± 20 | 1,057 | 3,031 |
| 32 | Random read | 32k | 12,299 | 384 ± 67 | 2,243 | 6,447 |
| 32 | Random read | 64k | 7,867 | 492 ± 26 | 4,048 | 7,537 |
| 32 | Random read | 128k | 3,995 | 500 ± 53 | 7,919 | 22,053 |
| 32 | Random read | 256k | 2,131 | 534 ± 29 | 14,726 | 52,232 |
| 32 | Random write | 4k | 9,679 | 38 ± 2 | 1,760 | 7,307 |
| 32 | Random write | 16k | 4,339 | 68 ± 2 | 6,975 | 32,375 |
| 32 | Random write | 32k | 2,245 | 70 ± 8 | 13,927 | 37,487 |
| 32 | Random write | 64k | 935 | 59 ± 4 | 33,505 | 88,211 |
| 32 | Random write | 128k | 593 | 75 ± 23 | 56,395 | 111,149 |
| 32 | Random write | 256k | 290 | 73 ± 9 | 110,484 | 179,306 |
| 32 | Sequential read | 4k | 12,079 | 47 ± 13 | 1,495 | 6,439 |
| 32 | Sequential read | 16k | 14,365 | 224 ± 89 | 1,280 | 5,857 |
| 32 | Sequential read | 32k | 12,680 | 396 ± 86 | 2,370 | 6,496 |
| 32 | Sequential read | 64k | 6,030 | 377 ± 137 | 4,949 | 19,481 |
| 32 | Sequential read | 128k | 3,996 | 500 ± 7 | 7,871 | 16,941 |
| 32 | Sequential read | 256k | 2,038 | 511 ± 22 | 15,643 | 32,571 |
| 32 | Sequential write | 4k | 9,517 | 37 ± 0 | 1,939 | 14,647 |
| 32 | Sequential write | 16k | 3,822 | 60 ± 5 | 7,873 | 33,358 |
| 32 | Sequential write | 32k | 1,620 | 51 ± 15 | 18,802 | 81,658 |
| 32 | Sequential write | 64k | 992 | 62 ± 1 | 32,087 | 108,790 |
| 32 | Sequential write | 128k | 483 | 61 ± 2 | 65,666 | 310,903 |
| 32 | Sequential write | 256k | 279 | 71 ± 3 | 113,591 | 243,794 |

### Table 3 - Read/write mix at QD32

| Pattern | Read % | Total IOPS | Total MiB/s | Read lat µs | Write lat µs |
|---|---|---|---|---|---|
| rand 4k | 100 | 15,581 | 61 | 1,404 | nan |
| rand 4k | 70 | 17,424 | 68 | 1,250 | 978 |
| rand 4k | 50 | 13,410 | 52 | 1,565 | 1,238 |
| rand 4k | 0 | 10,990 | 43 | nan | 1,596 |
| seq 128k | 100 | 3,983 | 498 | 7,926 | nan |
| seq 128k | 70 | 1,473 | 185 | 22,733 | 19,545 |
| seq 128k | 50 | 884 | 111 | 36,789 | 35,387 |
| seq 128k | 0 | 491 | 62 | nan | 65,193 |

### Table 4 - Queue-depth sweep with Little's Law check

| Workload | QD | IOPS | Mean lat (µs) | p99 (µs) | L = IOPS × lat | L / QD |
|---|---|---|---|---|---|---|
| 4k randread | 1 | 4,508 ± 118 | 218.3 ± 5.6 | 485 | 1.0 | 0.98 |
| 4k randread | 4 | 14,317 ± 2,538 | 243.5 ± 41.2 | 810 | 3.5 | 0.87 |
| 4k randread | 16 | 20,888 ± 4,172 | 486.9 ± 88.4 | 1,608 | 10.2 | 0.64 |
| 4k randread | 64 | 19,312 ± 2,851 | 1,793.8 ± 281.3 | 6,423 | 34.6 | 0.54 |
| 4k randread | 256 | 18,989 ± 3,336 | 6,908.5 ± 1,214.3 | 21,365 | 131.2 | 0.51 |
| 4k randwrite | 1 | 7,314 ± 7 | 132.5 ± 0.0 | 172 | 1.0 | 0.97 |
| 4k randwrite | 4 | 12,640 ± 486 | 239.9 ± 7.1 | 791 | 3.0 | 0.76 |
| 4k randwrite | 16 | 12,484 ± 1,791 | 761.3 ± 103.3 | 4,022 | 9.5 | 0.59 |
| 4k randwrite | 64 | 12,114 ± 976 | 3,035.8 ± 282.6 | 16,482 | 36.8 | 0.57 |
| 4k randwrite | 256 | 12,091 ± 1,582 | 13,472.9 ± 434.2 | 40,370 | 162.9 | 0.64 |

L = IOPS × mean total latency. In a closed loop with fixed QD, L / QD should be ≈ 1; deviations point to latency not measured by fio (device-side queueing after completion, timer resolution) or the ramp/steady-state boundary.

### Table 5 - Knee and effective device concurrency

| Workload | Peak IOPS | Knee QD (chord) | QD for 90% of peak | N* = peak IOPS × QD1 latency |
|---|---|---|---|---|
| 4k randread | 20,888 | 16 | 16 | 4.6 |
| 4k randwrite | 12,640 | 4 | 4 | 1.7 |

N* is the number of requests the SSD can overlap: beyond ≈N* more queue depth only adds latency (W ≈ QD / peak IOPS).

### Table 6 - Tail latency (µs) at mid-QD, near-knee and past-knee QD

| Workload | QD | p50 | p90 | p95 | p99 | p99.9 | p99.99 | p99/p50 | p99.99/p50 | max (µs) |
|---|---|---|---|---|---|---|---|---|---|---|
| 4k randread | 4 | 163 | 226 | 266 | 513 | 2,683 | 26,739 | 3.2 | 164.2 | 191,494 |
| 4k randread | 16 | 520 | 1,090 | 1,458 | 3,981 | 24,117 | 68,026 | 7.7 | 130.8 | 82,848 |
| 4k randread | 64 | 1,819 | 3,506 | 4,121 | 7,389 | 37,749 | 102,629 | 4.1 | 56.4 | 109,004 |
| 4k randwrite | 4 | 166 | 311 | 414 | 1,157 | 6,668 | 64,815 | 7.0 | 390.7 | 148,913 |
| 4k randwrite | 16 | 635 | 1,278 | 1,573 | 3,596 | 17,924 | 88,474 | 5.7 | 139.4 | 208,253 |
| 4k randwrite | 64 | 2,851 | 5,734 | 7,062 | 14,254 | 48,497 | 98,042 | 5.0 | 34.4 | 107,204 |

Latencies are fio clat percentiles (submission-to-completion excluding submit time).

### Table 7 - Burst vs steady-state writes (per-second logs)

| Workload | First 10% (MiB/s) | Last 20% (MiB/s) | Steady/burst | Drop at (s) | Max temp (°C) |
|---|---|---|---|---|---|
| randwrite_4k_qd32 | 40 | 45 | 1.11 | 11 | 79 |
| seqwrite_128k_qd32 | 117 | 67 | 0.57 | 1 | 80 |

A drop is flagged where the 10 s rolling median falls below 70% of the first-10% mean. Cause (SLC-cache exhaustion, GC, thermal throttling) must be argued from the temperature trace and file size, not assumed.

### Table 8 - LBA-range sweep

| Workload | LBA span (GiB) | IOPS | Mean lat (µs) | p99 (µs) |
|---|---|---|---|---|
| 4k randread QD32 | 1 | 22,312 ± 1,450 | 802.7 | 2,298 |
| 4k randread QD32 | 4 | 20,282 ± 4,106 | 890.4 | 3,346 |
| 4k randwrite QD32 | 1 | 12,294 ± 2,400 | 1,428.8 | 5,603 |
| 4k randwrite QD32 | 4 | 12,172 ± 550 | 1,460.4 | 6,324 |

### Table 9 - Misleading-setup demonstration

| Setup | IOPS | Mean lat (µs) | vs control |
|---|---|---|---|
| correct_direct_aio_qd32 | 22,282 ± 1,907 | 814.4 | 1.00× |
| buffered_aio_qd32 | 13,175 ± 118 | 2,262.1 | 0.59× |
| aio_iodepth1_default | 3,177 ± 56 | 307.1 | 0.14× |
| aio_iodepth1_numjobs32 | 29,302 ± 22,753 | 1,556.6 | 1.32× |

### Table 10 - Data-pattern (compressibility) check

| Data pattern | IOPS | Mean lat (µs) | p99 (µs) |
|---|---|---|---|
| compress50 | 13,667 ± 435 | 1,411.1 | 11,338 |
| incompressible | 12,557 ± 88 | 1,475.3 | 10,174 |
| zeros | 12,961 ± 871 | 1,548.6 | 12,583 |

Main experiments use incompressible data (fio refill_buffers=1, buffer_compress_percentage=0).

### Table 11 - Drive temperature around long runs

| Point | Temp before (°C) | Temp after (°C) |
|---|---|---|
| randread_4k_qd16 | 49.0 | 47.0 |
| randread_4k_qd4 | 56.0 | 49.5 |
| randread_4k_qd64 | 52.5 | 50.0 |
| randwrite_4k_qd16 | 52.5 | 60.0 |
| randwrite_4k_qd32_timeseries | 66.0 | 69.0 |
| randwrite_4k_qd4 | 54.5 | 60.5 |
| randwrite_4k_qd64 | 44.0 | 58.0 |
| seqwrite_128k_qd32_timeseries | 60.0 | nan |
