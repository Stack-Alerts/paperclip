"""Unit tests for blast_radius.report -- markdown rendering and file extraction."""

from __future__ import annotations

from blast_radius.query import BlastRadiusData, FRImpact, RegressionRisk
from blast_radius.report import render_report, extract_touched_files


# ---------------------------------------------------------------------------
# render_report
# ---------------------------------------------------------------------------


class TestRenderReport:
    _BASE_DATA = BlastRadiusData()

    def test_contains_fix_identifier_and_title(self):
        md = render_report("BTCAAAAA-100", "Fix null pointer", ["src/a.py"], self._BASE_DATA)
        assert "BTCAAAAA-100" in md
        assert "Fix null pointer" in md

    def test_contains_touched_files(self):
        md = render_report("BTCAAAAA-100", "Fix", ["src/a.py", "src/b.py"], self._BASE_DATA)
        assert "src/a.py" in md
        assert "src/b.py" in md

    def test_no_touched_files_shows_none(self):
        md = render_report("BTCAAAAA-100", "Fix", [], self._BASE_DATA)
        assert "_None_" in md

    def test_fr_impact_set_rendered(self):
        data = BlastRadiusData(
            fr_impact_set=[
                FRImpact(fr_identifier="FDR-850", fr_owner_agent_id="agent-1", fr_issue_id="fr-uuid"),
            ],
        )
        md = render_report("BTCAAAAA-100", "Fix", ["src/a.py"], data, agent_names={"agent-1": "Alice"})
        assert "FDR-850" in md
        assert "Alice" in md

    def test_fr_impact_set_no_agent_names(self):
        data = BlastRadiusData(
            fr_impact_set=[
                FRImpact(fr_identifier="FDR-850", fr_owner_agent_id="agent-1", fr_issue_id="fr-uuid"),
            ],
        )
        md = render_report("BTCAAAAA-100", "Fix", ["src/a.py"], data, agent_names=None)
        assert "FDR-850" in md
        assert "agent-1" in md  # falls back to raw agent ID

    def test_fr_impact_set_empty(self):
        md = render_report("BTCAAAAA-100", "Fix", ["src/a.py"], self._BASE_DATA)
        assert "FR Impact Set" in md
        assert "_None_" in md

    def test_regression_set_rendered(self):
        data = BlastRadiusData(
            regression_set=[
                RegressionRisk(bug_identifier="BTCAAAAA-50", bug_issue_id="bug-uuid"),
            ],
        )
        md = render_report("BTCAAAAA-100", "Fix", ["src/a.py"], data)
        assert "BTCAAAAA-50" in md

    def test_regression_set_empty(self):
        md = render_report("BTCAAAAA-100", "Fix", ["src/a.py"], self._BASE_DATA)
        assert "Regression Risk" in md
        assert "_None_" in md

    def test_downstream_set_empty_shows_phase_2_note(self):
        md = render_report("BTCAAAAA-100", "Fix", ["src/a.py"], self._BASE_DATA)
        assert "Phase 2" in md

    def test_downstream_set_populated(self):
        data = BlastRadiusData(downstream_set=["src/dep.py"])
        md = render_report("BTCAAAAA-100", "Fix", ["src/a.py"], data)
        assert "src/dep.py" in md
        assert "Not available yet" not in md

    def test_sorted_file_list(self):
        md = render_report("BTCAAAAA-100", "Fix", ["src/z.py", "src/a.py"], self._BASE_DATA)
        a_pos = md.index("src/a.py")
        z_pos = md.index("src/z.py")
        assert a_pos < z_pos

    def test_multiple_fr_issues(self):
        data = BlastRadiusData(
            fr_impact_set=[
                FRImpact(fr_identifier="FDR-850", fr_owner_agent_id="a1", fr_issue_id="f1"),
                FRImpact(fr_identifier="FDR-851", fr_owner_agent_id="a2", fr_issue_id="f2"),
            ],
        )
        md = render_report("BTCAAAAA-100", "Fix", ["src/a.py"], data, agent_names={"a1": "Alice", "a2": "Bob"})
        assert "FDR-850" in md
        assert "FDR-851" in md
        assert "Alice" in md
        assert "Bob" in md

    def test_agent_mention_format(self):
        data = BlastRadiusData(
            fr_impact_set=[
                FRImpact(fr_identifier="FDR-850", fr_owner_agent_id="agent-1", fr_issue_id="fr-uuid"),
            ],
        )
        md = render_report("BTCAAAAA-100", "Fix", ["src/a.py"], data, agent_names={"agent-1": "Alice"})
        # agent mentions use the pattern [@name](agent://id)
        assert "[@Alice](agent://agent-1)" in md


# ---------------------------------------------------------------------------
# extract_touched_files
# ---------------------------------------------------------------------------


class TestExtractTouchedFiles:
    def test_json_code_block(self):
        desc = 'Some text\n```json\n{"touchedFiles": ["src/foo.py", "src/bar.py"]}\n```\nMore text'
        assert extract_touched_files(desc) == ["src/foo.py", "src/bar.py"]

    def test_bare_json_object(self):
        desc = 'Some text {"touchedFiles": ["src/baz.py"]} more text'
        assert extract_touched_files(desc) == ["src/baz.py"]

    def test_markdown_section(self):
        desc = """## Touched Files
- src/alpha.py
- src/beta.py
"""
        assert extract_touched_files(desc) == ["src/alpha.py", "src/beta.py"]

    def test_markdown_section_with_backticks(self):
        desc = """## Touched Files
- `src/gamma.py`
- `src/delta.py`
"""
        assert extract_touched_files(desc) == ["src/gamma.py", "src/delta.py"]

    def test_no_matches(self):
        assert extract_touched_files("No files here.") == []

    def test_empty_string(self):
        assert extract_touched_files("") == []

    def test_json_block_first_match_wins(self):
        """JSON block takes priority over markdown section."""
        desc = '```json\n{"touchedFiles": ["src/json.py"]}\n```\n## Touched Files\n- src/md.py\n'
        assert extract_touched_files(desc) == ["src/json.py"]

    def test_malformed_json_skips_to_markdown(self):
        desc = '```json\n{"touchedFiles": [bad}\n```\n## Touched Files\n- src/fallback.py\n'
        assert extract_touched_files(desc) == ["src/fallback.py"]

    def test_multiple_files_in_bare_json(self):
        desc = '{"touchedFiles": ["src/a.py", "src/b.py", "src/c.py"]}'
        assert extract_touched_files(desc) == ["src/a.py", "src/b.py", "src/c.py"]

    def test_markdown_section_with_extra_whitespace(self):
        desc = """## Touched Files
  -   src/padded.py  
  - src/also.py   
"""
        result = extract_touched_files(desc)
        assert len(result) == 2
        assert "src/padded.py" in result
        assert "src/also.py" in result

    def test_json_block_without_language_tag(self):
        desc = '```\n{"touchedFiles": ["src/no_lang.py"]}\n```'
        assert extract_touched_files(desc) == ["src/no_lang.py"]

    def test_empty_json_array(self):
        desc = '{"touchedFiles": []}'
        assert extract_touched_files(desc) == []

    def test_markdown_section_empty_list(self):
        desc = "## Touched Files\n"
        assert extract_touched_files(desc) == []

    def test_description_is_none(self):
        assert extract_touched_files(None) == []

    def test_complex_json_block_with_extra_fields(self):
        desc = '```json\n{"touchedFiles": ["src/complex.py"], "otherField": "value"}\n```'
        assert extract_touched_files(desc) == ["src/complex.py"]

    def test_json_block_with_invalid_array_content(self):
        """JSON block regex matches but json.loads fails."""
        desc = '```json\n{"touchedFiles": [{invalid}]}\n```'
        assert extract_touched_files(desc) == []

    def test_bare_json_with_invalid_array_content(self):
        """Bare JSON regex matches but json.loads fails."""
        desc = '{"touchedFiles": [{invalid}]}'
        assert extract_touched_files(desc) == []
