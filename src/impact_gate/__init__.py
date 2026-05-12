"""
Impact Gate — FR acceptance + bug regression test gating for Paperclip issues.

Entry points
------------
- impact_gate.worker  : polling worker that runs the gate on in_review issues
- impact_gate.worker.scan_done_issues : scan done fix/bug issues for gate coverage
- scripts.impact_gate_runner : CLI runner for manual/ad-hoc gate checks
"""
