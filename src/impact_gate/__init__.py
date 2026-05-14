"""
Impact Gate — FR acceptance + bug regression test gating for Paperclip issues.

Entry points
------------
- impact_gate.worker  : core gate logic with single-issue, poll, and scan-done modes
- impact_gate.worker.process_issue : run gate on a single in_review fix issue
- impact_gate.worker.scan_done_issues : scan done fix issues for gate coverage
- impact_gate.worker --poll --retroactive : 5-min polling loop for done fix issues
- scripts/impact_gate_runner : CLI runner for manual/ad-hoc gate checks
"""
