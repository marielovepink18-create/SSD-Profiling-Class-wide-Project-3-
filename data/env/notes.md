# Environment notes

- Laptop plugged in during all runs: yes
- Windows Defender real-time protection: off
- BitLocker: off
- Device write caching (Device Manager > Disk drives > SSD > Policies): on
- Power plan: HP Recommended (not High performance)
- Free space on C: during tests: about 4.6 GB of about 118 GB (nearly full; could not free more)
- Phase A ran in a normal terminal; Phase B ran as administrator (needed to read drive temperature)

## Commands run, in order
1. python -X utf8 scripts\run_experiments.py --target C:\fio_test\ssd_profile_testfile.bin --size-gib 4 --profile quick --stages baseline,blocksize,rwmix,qdsweep
2. python -X utf8 scripts\parse_results.py ; python -X utf8 scripts\analyze_plots.py
3. python -X utf8 scripts\run_experiments.py --target C:\fio_test\ssd_profile_testfile.bin --size-gib 4 --profile quick --stages tail,lba,datapattern,pitfall,steady
4. sync-engine pitfall jobs failed (Windows does not allow direct I/O with sync engines); replaced with windowsaio iodepth=1 jobs and rerun with --stages pitfall
5. python -X utf8 scripts\parse_results.py ; python -X utf8 scripts\analyze_plots.py