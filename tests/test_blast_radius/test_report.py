"""Smoke tests for blast_radius.report — no DB or network required."""

from blast_radius.report import extract_touched_files, render_report
from blast_radius.query import BlastRadiusData, FRImpact, RegressionRisk


class TestExtractTouchedFiles:
    def test_json_block(self):
        desc = '```json\n{"touchedFiles": ["src/foo.py", "src/bar.py"]}\n```'
        assert extract_touched_files(desc) == ["src/foo.py", "src/bar.py"]

    def test_bare_json(self):
        desc = 'Some text\n"touchedFiles": ["a.py"]\nmore text'
        assert extract_touched_files(desc) == ["a.py"]

    def test_markdown_list(self):
        desc = "## Touched Files\n- src/foo.py\n- src/bar.py\n"
        result = extract_touched_files(desc)
        assert "src/foo.py" in result
        assert "src/bar.py" in result

    def test_empty(self):
        assert extract_touched_files("No files here.") == []


class TestRenderReport:
    def test_renders_with_no_data(self):
        data = BlastRadiusData()
        md = render_report(
            issue_identifier="BTCAAAAA-999",
            issue_title="Fix something",
            touched_files=["src/foo.py"],
            data=data,
        )
        assert "## Blast Radius Report" in md
        assert "BTCAAAAA-999" in md
        assert "src/foo.py" in md
        assert "_None_" in md
        assert "Phase 2" in md

    def test_renders_fr_impact(self):
        data = BlastRadiusData(
            fr_impact_set=[
                FRImpact(
                    fr_identifier="FDR-100",
                    fr_owner_agent_id="agent-uuid-1",
                    fr_issue_id="issue-uuid-1",
                )
            ]
        )
        md = render_report(
            issue_identifier="BTCAAAAA-999",
            issue_title="Fix X",
            touched_files=["src/x.py"],
            data=data,
            agent_names={"agent-uuid-1": "CoderAgent"},
        )
        assert "FDR-100" in md
        assert "CoderAgent" in md
        assert "agent-uuid-1" in md

    def test_renders_regression_risk(self):
        data = BlastRadiusData(
            regression_set=[
                RegressionRisk(bug_identifier="BTCAAAAA-500", bug_issue_id="bug-uuid-1")
            ]
        )
        md = render_report(
            issue_identifier="BTCAAAAA-999",
            issue_title="Fix Y",
            touched_files=["src/y.py"],
            data=data,
        )
        assert "BTCAAAAA-500" in md
