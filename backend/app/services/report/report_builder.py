"""

Assembles hardened findings into a scored ReportSummary.

Scoring:
    Start at 100.
    VIOLATION   → -10 each
    TRADEOFF    → -4  each
    OBSERVATION → -1  each  (negative observations only; positive ones have score_impact == 0)
    Floor at 0.

Pros vs cons split:
    score_impact == 0  → pro  (positive observations)
    score_impact <  0  → con  (violations, tradeoffs, negative observations)

Cons are sorted by severity: VIOLATION first, then TRADEOFF, then OBSERVATION.
"""

import logging

from app.schemas.report import Finding, ReportSummary, Severity

logger = logging.getLogger(__name__)

# Severity ordering for sorting cons — worst first
_SEVERITY_ORDER = {
    Severity.VIOLATION:   0,
    Severity.TRADEOFF:    1,
    Severity.OBSERVATION: 2,
}


def build_report(plan_id: str, findings: list[Finding]) -> ReportSummary:
    """
    Build a ReportSummary from a hardened list of findings.

    Args:
        plan_id:   UUID string of the FloorPlan row.
        findings:  Hardened findings from the consistency filter.

    Returns:
        ReportSummary with computed score and pros/cons split.
        summary_text is left empty — call summary_writer separately.
    """
    pros: list[Finding] = []
    cons: list[Finding] = []

    for finding in findings:
        if finding.score_impact == 0:
            pros.append(finding)
        else:
            cons.append(finding)

    # Sort cons by severity (violations first), then alphabetically by title
    cons.sort(key=lambda f: (_SEVERITY_ORDER.get(f.severity, 99), f.title))

    # ── Compute overall score ─────────────────────────────────────
    total_deduction = sum(abs(f.score_impact) for f in cons)
    overall_score = max(0, 100 - total_deduction)

    logger.info(
        f"Report built for plan {plan_id}: "
        f"score={overall_score}, "
        f"{len(pros)} pro(s), {len(cons)} con(s), "
        f"total deduction={total_deduction}"
    )

    return ReportSummary(
        plan_id=plan_id,
        overall_score=overall_score,
        pros=pros,
        cons=cons,
        summary_text="",  # filled by summary_writer
    )