"""
Regression tests for BTCAAAAA-1168: Blast Radius Report generator + query API/CLI.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1168
Fixed in commit: a0707ee
Components: src/blast_radius/

Root cause: N/A — this was a feature rather than a bug fix.

This file is the canonical bug regression location.  The test coverage
verifies core Blast Radius pipeline components:
  1. Markdown report rendering (render_report)
  2. Issue description file extraction (extract_touched_files)
  3. BlastRadiusData serialization (to_json_dict)
  4. Dataclass construction for FRImpact / RegressionRisk
  5. HTTP server run-header generation
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from blast_radius.query import BlastRadiusData, FRImpact, RegressionRisk, to_json_dict
from blast_radius.report import extract_touched_files, render_report

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1168"),
    pytest.mark.regression,
]


# ---------------------------------------------------------------------------
# render_report — markdown rendering
# ---------------------------------------------------------------------------


class TestRenderReportRegression:
    _BASE_DATA = BlastRadiusData()

    def test_contains_issue_link(self):
        md = render_report("BTCAAAAA-1168", "Blast Radius Report", ["src/a.py"], self._BASE_DATA)
        assert "[BTCAAAAA-1168]" in md
        assert "Blast Radius Report" in md

    def test_lists_single_touched_file(self):
        md = render_report("BTCAAAAA-1", "Fix", ["src/blast_radius/report.py"], self._BASE_DATA)
        assert "src/blast_radius/report.py" in md

    def test_lists_multiple_touched_files(self):
        md = render_report(
            "BTCAAAAA-1", "Fix", ["src/a.py", "src/b.py", "src/c.py"], self._BASE_DATA
        )
        assert "src/a.py" in md
        assert "src/b.py" in md
        assert "src/c.py" in md

    def test_empty_touched_files_shows_none(self):
        md = render_report("BTCAAAAA-1", "Fix", [], self._BASE_DATA)
        assert "_None_" in md

    def test_fr_impact_set_with_agent_mention(self):
        data = BlastRadiusData(
            fr_impact_set=[
                FRImpact(fr_identifier="FDR-850", fr_owner_agent_id="agent-a", fr_issue_id="f1"),
            ],
        )
        md = render_report("BTCAAAAA-1", "Fix", ["src/a.py"], data, agent_names={"agent-a": "Alice"})
        assert "FDR-850" in md
        assert "[@Alice](agent://agent-a)" in md

    def test_fr_impact_set_empty(self):
        md = render_report("BTCAAAAA-1", "Fix", ["src/a.py"], self._BASE_DATA)
        assert "_None_" in md

    def test_regression_risk_section_rendered(self):
        data = BlastRadiusData(
            regression_set=[
                RegressionRisk(bug_identifier="BTCAAAAA-50", bug_issue_id="bug-uuid"),
            ],
        )
        md = render_report("BTCAAAAA-1", "Fix", ["src/a.py"], data)
        assert "BTCAAAAA-50" in md

    def test_regression_risk_empty(self):
        md = render_report("BTCAAAAA-1", "Fix", ["src/a.py"], self._BASE_DATA)
        assert "_None_" in md

    def test_downstream_phase_two_note_when_empty(self):
        md = render_report("BTCAAAAA-1", "Fix", ["src/a.py"], self._BASE_DATA)
        assert "Phase 2" in md

    def test_downstream_set_populated(self):
        data = BlastRadiusData(downstream_set=["src/dep.py", "src/dep2.py"])
        md = render_report("BTCAAAAA-1", "Fix", ["src/a.py"], data)
        assert "src/dep.py" in md
        assert "src/dep2.py" in md

    def test_files_sorted_alphabetically(self):
        md = render_report("BTCAAAAA-1", "Fix", ["src/z.py", "src/a.py", "src/m.py"], self._BASE_DATA)
        a_pos = md.index("src/a.py")
        m_pos = md.index("src/m.py")
        z_pos = md.index("src/z.py")
        assert a_pos < m_pos < z_pos

    def test_multiple_fr_issues_all_rendered(self):
        data = BlastRadiusData(
            fr_impact_set=[
                FRImpact(fr_identifier="FDR-1", fr_owner_agent_id="a1", fr_issue_id="f1"),
                FRImpact(fr_identifier="FDR-2", fr_owner_agent_id="a2", fr_issue_id="f2"),
            ],
        )
        md = render_report(
            "BTCAAAAA-1", "Fix", ["src/a.py"], data,
            agent_names={"a1": "Alice", "a2": "Bob"},
        )
        assert "FDR-1" in md
        assert "FDR-2" in md


# ---------------------------------------------------------------------------
# extract_touched_files — issue description parsing
# ---------------------------------------------------------------------------


class TestExtractTouchedFilesRegression:
    def test_parse_json_code_block(self):
        desc = 'More\n```json\n{"touchedFiles": ["src/a.py", "src/b.py"]}\n```\nEnd'
        assert extract_touched_files(desc) == ["src/a.py", "src/b.py"]

    def test_parse_bare_json_object(self):
        desc = '{"touchedFiles": ["src/bare.py"]}'
        assert extract_touched_files(desc) == ["src/bare.py"]

    def test_parse_markdown_section(self):
        desc = "## Touched Files\n- src/md1.py\n- src/md2.py\n"
        assert extract_touched_files(desc) == ["src/md1.py", "src/md2.py"]

    def test_parse_markdown_with_backtick_paths(self):
        desc = "## Touched Files\n- `src/tick.py`\n"
        assert extract_touched_files(desc) == ["src/tick.py"]

    def test_no_matches_returns_empty_list(self):
        assert extract_touched_files("No files listed here") == []

    def test_empty_string_returns_empty_list(self):
        assert extract_touched_files("") == []

    def test_none_returns_empty_list(self):
        assert extract_touched_files(None) == []

    def test_json_block_takes_priority(self):
        desc = '```json\n{"touchedFiles": ["src/json.py"]}\n```\n## Touched Files\n- src/md.py'
        assert extract_touched_files(desc) == ["src/json.py"]

    def test_malformed_json_falls_back_to_markdown(self):
        desc = '```json\n{"touchedFiles": [bad}\n```\n## Touched Files\n- src/fallback.py'
        assert extract_touched_files(desc) == ["src/fallback.py"]

    def test_handles_whitespace_in_markdown_list(self):
        desc = "## Touched Files\n  -   src/padded.py  \n  - src/also.py  "
        result = extract_touched_files(desc)
        assert len(result) == 2
        assert "src/padded.py" in result
        assert "src/also.py" in result

    def test_empty_json_array(self):
        desc = '{"touchedFiles": []}'
        assert extract_touched_files(desc) == []

    def test_json_block_without_language_tag(self):
        desc = '```\n{"touchedFiles": ["src/no_lang.py"]}\n```'
        assert extract_touched_files(desc) == ["src/no_lang.py"]


# ---------------------------------------------------------------------------
# BlastRadiusData and dataclass construction
# ---------------------------------------------------------------------------


class TestBlastRadiusDataRegression:
    def test_default_construction(self):
        data = BlastRadiusData()
        assert data.fr_impact_set == []
        assert data.regression_set == []
        assert data.downstream_set == []

    def test_fr_impact_fields(self):
        fr = FRImpact(fr_identifier="FDR-100", fr_owner_agent_id="agent-uuid", fr_issue_id="issue-uuid")
        assert fr.fr_identifier == "FDR-100"
        assert fr.fr_owner_agent_id == "agent-uuid"
        assert fr.fr_issue_id == "issue-uuid"

    def test_regression_risk_fields(self):
        r = RegressionRisk(bug_identifier="BTCAAAAA-500", bug_issue_id="bug-uuid")
        assert r.bug_identifier == "BTCAAAAA-500"
        assert r.bug_issue_id == "bug-uuid"


# ---------------------------------------------------------------------------
# to_json_dict serialization
# ---------------------------------------------------------------------------


class TestToJsonDictRegression:
    def test_empty_data(self):
        result = to_json_dict(BlastRadiusData())
        assert result["fr_impact_set"] == []
        assert result["regression_set"] == []
        assert result["downstream_set"] == []

    def test_populated_data(self):
        data = BlastRadiusData(
            fr_impact_set=[
                FRImpact(fr_identifier="FDR-1", fr_owner_agent_id="a1", fr_issue_id="f1"),
            ],
            regression_set=[
                RegressionRisk(bug_identifier="BTCAAAAA-1", bug_issue_id="b1"),
            ],
            downstream_set=["src/dep.py"],
        )
        result = to_json_dict(data)
        assert result["fr_impact_set"][0]["fr_identifier"] == "FDR-1"
        assert result["regression_set"][0]["bug_identifier"] == "BTCAAAAA-1"
        assert result["downstream_set"] == ["src/dep.py"]
        assert result["downstream_note"] is None

    def test_downstream_note_when_empty(self):
        result = to_json_dict(BlastRadiusData())
        assert result["downstream_note"] == "Phase 2 dep graph not yet available"


# ---------------------------------------------------------------------------
# generator internals — run headers
# ---------------------------------------------------------------------------


class TestRunHeadersRegression:
    def test_empty_when_no_run_id(self):
        with patch("blast_radius.generator.PAPERCLIP_RUN_ID", ""):
            from blast_radius.generator import _run_headers
            assert _run_headers() == {}

    def test_includes_run_id_when_set(self):
        with patch("blast_radius.generator.PAPERCLIP_RUN_ID", "run-1168"):
            from blast_radius.generator import _run_headers
            assert _run_headers() == {"X-Paperclip-Run-Id": "run-1168"}
