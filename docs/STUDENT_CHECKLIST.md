# Your checklist for today

The assignment says you must be able to understand, validate and explain everything you submit.
Do these yourself; they also produce the "independently tested" content for the AI-use note.

## Timeline (adjust to your deadline)
1. ~20 min: install fio + Python, `pip install -r requirements.txt`, capture environment, `--dry-run`.
2. Edit `HYPOTHESES.md` for your drive and **git commit it before any measurement**.
3. ~45 min: `--profile quick` smoke test. Parse + plot. Fix anything odd.
4. Start `--profile standard` (~2 h, resumable). Write Methodology and AI-use note meanwhile.
5. Parse, plot, fill in the report using `data/processed/tables.md`.
6. Push to GitHub (raw data + processed data + plots + scripts; the `.bin` test file is git-ignored; delete it).

## Validate by hand (pick at least 3, mention them in the report)
- Open one generated `.fio` file and explain every line. Run it manually: `fio configs\generated\baseline\baseline__randread_4k_qd1__r1.fio` and compare with the stored result.
- Check QD1 4 KiB random read: IOPS × mean latency should be ≈ 1 (Little's Law at QD1).
- Compare peak sequential read bandwidth with the datasheet / interface limit; explain any gap.
- Watch Task Manager during the QD256 run: is one CPU core pegged? (then the plateau may be host-bound).
- Re-run one point on a different day/after a reboot; report the difference.

## Questions you should be able to answer
1. Why `direct=1`? What would buffered I/O have measured?
2. Why is QD1 write latency often lower than read latency on an SSD?
3. State Little's Law and apply it to your QD sweep; what does N* mean?
4. Why does latency stay flat before the knee and grow linearly after it?
5. Why do tail percentiles grow faster than the mean as QD rises?
6. What could make the steady-state write rate lower than the burst rate? Which of those did you actually observe, and how do you know?
7. What is wrong with `ioengine=sync, iodepth=32`?
8. What would change if you tested a raw device instead of a file?
