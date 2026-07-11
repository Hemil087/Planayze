"""
Phase 7 Gate Tests — Report Builder

Validates:
  1. Score maths for known input sets
  2. Pros / cons split is correct
  3. Cons sorted by severity (violations first)
  4. Score floors at 0 (never negative)
  5. Empty findings produce score 100 and empty lists
  6. Fallback summary produces non-empty string
"""

import pytest
from uuid import uuid4

from backend.app.schemas.report import Finding, Severity, Category, ReportSummary
from backend.app.services.report.report_builder import build_report
from backend.app.services.report.summary_writer import _fallback_summary


# ── Helpers ──────────────────────────────────────────────────────


def _make_finding(
    severity: Severity,
    category: Category = Category.VENTILATION,
    title: str = "Test finding",
    rule_id: str = "TEST_001",
    room_names: list[str] | None = None,
    score_impact: int | None = None,
) -> Finding:
    """Factory for test findings with sensible defaults."""
    if score_impact is None:
        score_impact = {
            Severity.VIOLATION: -10,
            Severity.TRADEOFF: -4,
            Severity.OBSERVATION: -1,
        }[severity]

    return Finding(
        id=str(uuid4()),
        severity=severity,
        category=category,
        title=title,
        detail=f"Detail for {title}",
        room_names=room_names or ["Room 1"],
        rule_id=rule_id,
        score_impact=score_impact,
    )


def _make_positive_observation(
    title: str = "Good feature",
    rule_id: str = "POS_001",
    room_names: list[str] | None = None,
) -> Finding:
    """Factory for a positive observation (score_impact == 0)."""
    return Finding(
        id=str(uuid4()),
        severity=Severity.OBSERVATION,
        category=Category.VENTILATION,
        title=title,
        detail=f"Detail for {title}",
        room_names=room_names or ["Room 1"],
        rule_id=rule_id,
        score_impact=0,
    )


# ── Score Maths ──────────────────────────────────────────────────


class TestScoreMaths:
    def test_no_findings_yields_100(self):
        report = build_report("plan-1", [])
        assert report.overall_score == 100

    def test_single_violation(self):
        findings = [_make_finding(Severity.VIOLATION)]
        report = build_report("plan-1", findings)
        assert report.overall_score == 90  # 100 - 10

    def test_single_tradeoff(self):
        findings = [_make_finding(Severity.TRADEOFF)]
        report = build_report("plan-1", findings)
        assert report.overall_score == 96  # 100 - 4

    def test_single_negative_observation(self):
        findings = [_make_finding(Severity.OBSERVATION)]
        report = build_report("plan-1", findings)
        assert report.overall_score == 99  # 100 - 1

    def test_mixed_severities(self):
        findings = [
            _make_finding(Severity.VIOLATION, rule_id="V1"),
            _make_finding(Severity.VIOLATION, rule_id="V2"),
            _make_finding(Severity.TRADEOFF, rule_id="T1"),
            _make_finding(Severity.OBSERVATION, rule_id="O1"),
        ]
        report = build_report("plan-1", findings)
        # 100 - 10 - 10 - 4 - 1 = 75
        assert report.overall_score == 75

    def test_score_floors_at_zero(self):
        findings = [
            _make_finding(Severity.VIOLATION, rule_id=f"V{i}")
            for i in range(15)  # 15 × -10 = -150 → floor to 0
        ]
        report = build_report("plan-1", findings)
        assert report.overall_score == 0

    def test_positive_observations_dont_affect_score(self):
        findings = [
            _make_positive_observation(rule_id="POS_1"),
            _make_positive_observation(rule_id="POS_2"),
        ]
        report = build_report("plan-1", findings)
        assert report.overall_score == 100


# ── Pros / Cons Split ────────────────────────────────────────────


class TestProsConsSplit:
    def test_positive_findings_go_to_pros(self):
        findings = [
            _make_positive_observation(title="Good ventilation", rule_id="P1"),
            _make_positive_observation(title="Nice layout", rule_id="P2"),
        ]
        report = build_report("plan-1", findings)
        assert len(report.pros) == 2
        assert len(report.cons) == 0

    def test_negative_findings_go_to_cons(self):
        findings = [
            _make_finding(Severity.VIOLATION, rule_id="V1"),
            _make_finding(Severity.TRADEOFF, rule_id="T1"),
        ]
        report = build_report("plan-1", findings)
        assert len(report.pros) == 0
        assert len(report.cons) == 2

    def test_mixed_split(self):
        findings = [
            _make_positive_observation(rule_id="P1"),
            _make_finding(Severity.VIOLATION, rule_id="V1"),
            _make_finding(Severity.TRADEOFF, rule_id="T1"),
            _make_positive_observation(rule_id="P2"),
        ]
        report = build_report("plan-1", findings)
        assert len(report.pros) == 2
        assert len(report.cons) == 2

    def test_cons_sorted_by_severity(self):
        findings = [
            _make_finding(Severity.OBSERVATION, title="Obs", rule_id="O1"),
            _make_finding(Severity.VIOLATION, title="Vio", rule_id="V1"),
            _make_finding(Severity.TRADEOFF, title="Tra", rule_id="T1"),
        ]
        report = build_report("plan-1", findings)
        severities = [f.severity for f in report.cons]
        assert severities == [
            Severity.VIOLATION,
            Severity.TRADEOFF,
            Severity.OBSERVATION,
        ]


# ── Report Metadata ──────────────────────────────────────────────


class TestReportMetadata:
    def test_plan_id_preserved(self):
        report = build_report("my-plan-uuid", [])
        assert report.plan_id == "my-plan-uuid"

    def test_summary_text_starts_empty(self):
        report = build_report("plan-1", [])
        assert report.summary_text == ""

    def test_created_at_populated(self):
        report = build_report("plan-1", [])
        assert report.created_at is not None


# ── Fallback Summary ─────────────────────────────────────────────


class TestFallbackSummary:
    def test_fallback_mentions_score(self):
        report = build_report("plan-1", [
            _make_finding(Severity.VIOLATION, rule_id="V1"),
        ])
        summary = _fallback_summary(report)
        assert "90" in summary
        assert len(summary) > 0

    def test_fallback_with_violations_and_tradeoffs(self):
        report = build_report("plan-1", [
            _make_finding(Severity.VIOLATION, rule_id="V1"),
            _make_finding(Severity.VIOLATION, rule_id="V2"),
            _make_finding(Severity.TRADEOFF, rule_id="T1"),
        ])
        summary = _fallback_summary(report)
        assert "2 violations" in summary
        assert "1 design tradeoff" in summary

    def test_fallback_with_pros(self):
        report = build_report("plan-1", [
            _make_positive_observation(rule_id="P1"),
        ])
        summary = _fallback_summary(report)
        assert "favorable" in summary

    def test_fallback_empty_findings(self):
        report = build_report("plan-1", [])
        summary = _fallback_summary(report)
        assert "100" in summary
        assert len(summary) > 0