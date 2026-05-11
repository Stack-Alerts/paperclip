"""Touch Index ingestion worker CLI — python -m touch_index [fr|bug] [options].

Workers
-------
  fr   (default)  FR ingestion worker — upserts touch_index_fr_files
  bug              Bug-close ingestion worker — upserts touch_index_bug_files

Usage
-----
    python -m touch_index fr                          # run FR polling mode
    python -m touch_index bug                         # run bug polling mode
    python -m touch_index fr --issue-id <uuid>        # process a single FR issue
    python -m touch_index bug --issue-id <uuid>       # process a single bug issue
    python -m touch_index bug --lookback-minutes 60   # custom lookback window
    python -m touch_index fr --dry-run                # dry run (no DB writes)
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
