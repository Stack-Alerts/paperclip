"""Unit tests for touch_index.git_extractor — git history file extraction.

All subprocess calls are mocked so these tests run offline.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from touch_index.git_extractor import (
    _is_source_file,
    get_commit_hashes,
    get_files_for_commit,
    get_files_for_issue,
)


# ---------------------------------------------------------------------------
# _is_source_file  (pure function, no I/O)
# ---------------------------------------------------------------------------


class TestIsSourceFile:
    def test_source_py(self):
        assert _is_source_file("src/foo/bar.py") is True

    def test_source_js(self):
        assert _is_source_file("src/utils/index.js") is True

    def test_source_ts(self):
        assert _is_source_file("src/utils/index.ts") is True

    def test_source_sql(self):
        assert _is_source_file("src/utils/query.sql") is False

    def test_skips_alembic_prefix(self):
        assert _is_source_file("alembic/versions/abc123.py") is False

    def test_skips_lake_api_prefix(self):
        assert _is_source_file("scripts/LakeAPI/loader.py") is False

    def test_skips_dot_github(self):
        assert _is_source_file(".github/workflows/ci.yml") is False

    def test_skips_docs(self):
        assert _is_source_file("docs/guide.md") is False

    def test_skips_json(self):
        assert _is_source_file("config/settings.json") is False

    def test_skips_yaml(self):
        assert _is_source_file("config/deploy.yaml") is False

    def test_skips_toml(self):
        assert _is_source_file("pyproject.toml") is False

    def test_skips_markdown(self):
        assert _is_source_file("README.md") is False

    def test_skips_csv(self):
        assert _is_source_file("data/export.csv") is False

    def test_skips_shell_script(self):
        assert _is_source_file("scripts/deploy.sh") is False

    def test_skips_lock_file(self):
        assert _is_source_file("requirements.lock") is False

    def test_skips_txt(self):
        assert _is_source_file("requirements.txt") is False

    def test_skips_ini(self):
        assert _is_source_file("setup.cfg") is False

    def test_skips_coveragerc(self):
        assert _is_source_file(".coveragerc") is False

    def test_skips_env_example(self):
        assert _is_source_file(".env.example") is False

    def test_skips_archived_prefix(self):
        assert _is_source_file("scripts/archived/foo.py") is False

    def test_skips_root_archived(self):
        assert _is_source_file("archived/utils_strategy_builder_legacy/foo.py") is False

    def test_skips_rst(self):
        assert _is_source_file("docs/readme.rst") is False

    def test_skips_png(self):
        assert _is_source_file("assets/icon.png") is False

    def test_skips_jpg(self):
        assert _is_source_file("assets/photo.jpg") is False

    def test_skips_jpeg(self):
        assert _is_source_file("assets/photo.jpeg") is False

    def test_skips_gif(self):
        assert _is_source_file("assets/animation.gif") is False

    def test_skips_svg(self):
        assert _is_source_file("assets/diagram.svg") is False

    def test_skips_ico(self):
        assert _is_source_file("favicon.ico") is False

    def test_skips_pdf(self):
        assert _is_source_file("docs/report.pdf") is False

    def test_skips_pyc(self):
        assert _is_source_file("src/module.pyc") is False

    def test_skips_so(self):
        assert _is_source_file("src/lib.so") is False

    def test_skips_o(self):
        assert _is_source_file("src/object.o") is False

    def test_skips_parquet(self):
        assert _is_source_file("data/prices.parquet") is False

    def test_skips_pkl(self):
        assert _is_source_file("data/model.pkl") is False


# ---------------------------------------------------------------------------
# get_commit_hashes
# ---------------------------------------------------------------------------


class TestGetCommitHashes:
    def test_returns_hashes(self):
        with patch("touch_index.git_extractor._run", return_value="abc123\ndef456"):
            hashes = get_commit_hashes("BTCAAAAA-100")
        assert hashes == ["abc123", "def456"]

    def test_empty_when_no_matches(self):
        with patch("touch_index.git_extractor._run", return_value=""):
            hashes = get_commit_hashes("BTCAAAAA-NONEXISTENT")
        assert hashes == []

    def test_whitespace_lines_are_skipped(self):
        with patch(
            "touch_index.git_extractor._run", return_value="  \nabc123\n  \ndef456\n  "
        ):
            hashes = get_commit_hashes("BTCAAAAA-100")
        assert hashes == ["abc123", "def456"]


# ---------------------------------------------------------------------------
# get_files_for_commit
# ---------------------------------------------------------------------------


class TestGetFilesForCommit:
    def test_returns_source_files(self):
        with (
            patch("touch_index.git_extractor._run", return_value="src/a.py\nsrc/b.py"),
            patch("touch_index.git_extractor._is_source_file", return_value=True),
        ):
            files = get_files_for_commit("abc123")
        assert files == ["src/a.py", "src/b.py"]

    def test_filters_non_source_files(self):
        with (
            patch(
                "touch_index.git_extractor._run",
                return_value="src/a.py\nREADME.md\nalembic/x.py",
            ),
            patch(
                "touch_index.git_extractor._is_source_file",
                side_effect=lambda f: f == "src/a.py",
            ),
        ):
            files = get_files_for_commit("abc123")
        assert files == ["src/a.py"]

    def test_blank_lines_skipped(self):
        with (
            patch(
                "touch_index.git_extractor._run", return_value="src/a.py\n\nsrc/b.py"
            ),
            patch("touch_index.git_extractor._is_source_file", return_value=True),
        ):
            files = get_files_for_commit("abc123")
        assert files == ["src/a.py", "src/b.py"]

    def test_rename_arrow_lines_skipped(self):
        with (
            patch(
                "touch_index.git_extractor._run",
                return_value="=> src/renamed.py\nsrc/a.py",
            ),
            patch("touch_index.git_extractor._is_source_file", return_value=True),
        ):
            files = get_files_for_commit("abc123")
        assert files == ["src/a.py"]


# ---------------------------------------------------------------------------
# get_files_for_issue  (integration of above)
# ---------------------------------------------------------------------------


class TestGetFilesForIssue:
    def test_deduplicates_across_commits(self):
        with (
            patch(
                "touch_index.git_extractor.get_commit_hashes",
                return_value=["abc", "def"],
            ),
            patch(
                "touch_index.git_extractor.get_files_for_commit",
                side_effect=[["src/a.py", "src/b.py"], ["src/a.py", "src/c.py"]],
            ),
        ):
            files = get_files_for_issue("BTCAAAAA-100")
        assert files == ["src/a.py", "src/b.py", "src/c.py"]

    def test_empty_commits_returns_empty(self):
        with patch("touch_index.git_extractor.get_commit_hashes", return_value=[]):
            files = get_files_for_issue("BTCAAAAA-NONEXISTENT")
        assert files == []

    def test_respects_max_commits(self):
        with (
            patch(
                "touch_index.git_extractor.get_commit_hashes",
                return_value=["a", "b", "c"],
            ),
            patch(
                "touch_index.git_extractor.get_files_for_commit",
                side_effect=[["src/x.py"], ["src/y.py"]],
            ),
        ):
            files = get_files_for_issue("BTCAAAAA-100", max_commits=2)
        assert len(files) == 2  # 2 commits × 1 file each
