"""Touch Index ingestion worker CLI — python -m touch_index [options].

Usage
-----
    python -m touch_index                          # run polling mode (30 min lookback)
    python -m touch_index --issue-id <uuid>        # process a single FDR issue
    python -m touch_index --lookback-minutes 60    # custom lookback window
    python -m touch_index --dry-run                # dry run (no DB writes)
"""

from touch_index.fr_worker import main

if __name__ == "__main__":
    main()
