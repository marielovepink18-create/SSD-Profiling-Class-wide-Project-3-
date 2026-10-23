# Pre-experiment hypotheses

> **Commit this file (git commit) BEFORE running any experiment**, so the timestamp shows the predictions came first.
> Edit it to match your drive (NVMe vs SATA) and delete the branch that doesn't apply. These are starting
> points written from general SSD knowledge; make sure you understand and agree with each reason, because you
> are responsible for explaining them.

Drive under test: `<<internal C: SSD (model/interface to be recorded), ~118GB, NTFS, 4 GiB test file>>`

## H1. Zero-queue latency (QD=1)
- I expect a 4 GiB random write to be faster than a 4 GiB random read, because the SSD can confirm from a fast internal buffer before the data is actually stored in the flash.

## H2. Block-size sweep
- I expect throughput (IOPS) to rise as I increase queue depth and then flatten, because more request in the flight keep more of the SSD's flash chips busy until all of them are busy. After it flattens I expect latency to climb steeply, because extra request can't be served any faster and just wait in the line. 

## H3. Read/write mix
- I expect read latency to rise as writes are added to the mix. Writing flash is slower than reading by hundreds of microseconds, and at QD32 the flash chips are all busy, so a read that lands on a chip that is busy writing has to wait.
- I expect total throughput (IOPS) for any mix with writes to be lower than the pure-read result, because writes take longer than reads.
- I expect total throughput to keep falling as the write share grows, so the 50% read mix will be lower than the 70% read mix, and pure writes will be lowest. [Delete this if you think pure writes will be fast.]
- I expect measured throughput for the mixes to come out below the "no interference" calculation, because reads wait behind writes.

## H4. Queue-depth sweep, knee, Little's Law
I expect throughput (IOPS) to rise with queue depth and then flatten, with the knee around QD 16-64, because more requests in flight keep more flash chips busy until all of them are busy.
After the knee I expect latency to climb steeply, because extra requests can't be served any faster and just wait in line.

## H5. Tail latency
I expect p99 and p99.9 to be much larger than the median, but I expect the size of that gap (the ratio) to stay about the same as queue depth rises.

## H6. Burst vs steady state, device state
I expect p99 and p99.9 to be much larger than the median, but I expect the size of that gap (the ratio) to stay about the same as queue depth rises.

## H7. LBA range
I expect IOPS to barely change between the 1 GiB and 4 GiB ranges, because SSDs have no seek time and both ranges are tiny compared with the drive.

## H8. Misleading setups
- Buffered I/O: I expect it to be many times faster than direct I/O, because after warm-up Windows serves the reads from RAM, so it measures memory instead of the SSD.
- `sync` engine with iodepth=32 (one thread): I expect about the same IOPS as the correct QD32 result.
- `sync` engine with 32 threads: I expect higher IOPS than the correct QD32 result.

## H9. Data pattern
- I expect that compressible vs incompressible data should look about the same since most SSD controllers don't compress data.