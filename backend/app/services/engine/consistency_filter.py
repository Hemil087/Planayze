import logging
from collections import defaultdict

from backend.app.schemas.extraction import FloorPlanExtraction
from backend.app.schemas.report import Finding
from backend.app.services.engine.rule_runner import run_rules
from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _finding_key(finding: Finding) -> str:
    """
    Stable identity key for a finding.
    Two findings are considered the same if they have the same
    rule_id and affect the same rooms — regardless of UUID or wording.
    """
    rooms = tuple(sorted(finding.room_names))
    return f"{finding.rule_id}::{rooms}"


def run_consistency_filter(
    extraction: FloorPlanExtraction,
    n_runs: int | None = None,
    threshold: int | None = None,
) -> list[Finding]:
    """
    Run the rule engine N times over the same extraction.
    Keep only findings that appear in at least `threshold` runs.

    Since the rule engine is deterministic, all findings will appear
    in every run — making this a stability check rather than a filter
    under normal conditions.

    If any rule raises an intermittent error (e.g. due to floating-point
    edge cases or future probabilistic rules), findings from failed runs
    are simply excluded, and only consistently-produced findings survive.

    Args:
        extraction:  Validated FloorPlanExtraction from Gemini.
        n_runs:      Number of times to run the rule engine. Defaults to
                     CONSISTENCY_RUNS from config (default 5).
        threshold:   Minimum runs a finding must appear in to be kept.
                     Defaults to CONSISTENCY_THRESHOLD from config (default 3).

    Returns:
        Hardened list[Finding] — only findings that recurred >= threshold times.
    """
    n_runs   = n_runs   or settings.CONSISTENCY_RUNS
    threshold = threshold or settings.CONSISTENCY_THRESHOLD

    logger.info(
        f"Consistency filter: {n_runs} runs, threshold={threshold}/{n_runs}"
    )

    # key → list of Finding objects (one per run it appeared in)
    occurrences: dict[str, list[Finding]] = defaultdict(list)
    successful_runs = 0

    for run in range(1, n_runs + 1):
        try:
            findings = run_rules(extraction)
            successful_runs += 1
            for finding in findings:
                key = _finding_key(finding)
                occurrences[key].append(finding)
        except Exception as e:
            logger.warning(f"Consistency run {run} failed and was skipped: {e}")

    if successful_runs == 0:
        logger.error("All consistency runs failed — returning empty findings")
        return []

    # ── Keep only findings that hit the threshold ────────────────
    hardened: list[Finding] = []
    suppressed = 0

    for key, appearances in occurrences.items():
        count = len(appearances)
        if count >= threshold:
            # Use the first appearance as the canonical finding
            hardened.append(appearances[0])
            logger.debug(f"Kept finding {key} ({count}/{successful_runs} runs)")
        else:
            suppressed += 1
            logger.info(
                f"Suppressed flaky finding {key} "
                f"(appeared {count}/{successful_runs} runs, "
                f"threshold={threshold})"
            )

    logger.info(
        f"Consistency filter complete: "
        f"{len(hardened)} hardened, {suppressed} suppressed "
        f"(from {successful_runs}/{n_runs} successful runs)"
    )

    return hardened