"""Touch Index ingestion worker CLI — python -m touch_index [fr|bug] [options].

Workers
-------
  fr   (default)  FR ingestion worker — upserts touch_index_fr_files
  bug              Bug-close ingestion worker — upserts touch_index_bug_files

Common flags (both workers)
----------------------------
  --issue-id <uuid>              Process a single issue by Paperclip UUID
  --lookback-minutes <N>         Look back N minutes (default: 30)
  --dry-run                      Log without writing to DB or transitioning
  --validate                     Run data quality validation after ingestion

Usage
-----
    python -m touch_index [fr|bug]                          # run polling mode
    python -m touch_index [fr|bug] --issue-id <uuid>        # process single issue
    python -m touch_index [fr|bug] --lookback-minutes 60    # custom lookback window
    python -m touch_index [fr|bug] --dry-run                # dry run
    python -m touch_index [fr|bug] --validate               # validate after ingestion
"""

import sys


def _print_help() -> None:
    sys.stdout.write(__doc__.strip() + "\n")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        _print_help()
        return

    worker = "fr"
    if len(sys.argv) > 1 and sys.argv[1] in ("fr", "bug"):
        worker = sys.argv.pop(1)

    if worker == "bug":
        from touch_index.bug_worker import main as bug_main

        bug_main()
    else:
        from touch_index.fr_worker import main as fr_main

        fr_main()


if __name__ == "__main__":
    main()
