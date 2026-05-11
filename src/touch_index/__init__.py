"""Touch Index ingestion package.

Maintains touch_index_fr_files and touch_index_bug_files in PostgreSQL,
derived from:
  - FDR (fdr-labelled) issues → git commits referencing the issue ID
  - Bug (title-prefixed) issues closed → git commits referencing the issue ID
"""
