"""Blast Radius worker CLI — python -m blast_radius [options].

Usage
-----
    python -m blast_radius                         # run once, then exit
    python -m blast_radius --issue-id <uuid>        # process a single issue
    python -m blast_radius --issue-id <uuid> --old-status in_progress
    python -m blast_radius --loop <seconds>         # poll continuously
    python -m blast_radius --dry-run
    python -m blast_radius --force-reprocess
"""

from blast_radius.worker import main

if __name__ == "__main__":
    main()
