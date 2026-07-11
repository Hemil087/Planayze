"""
Eval Metrics — Phase 9

Computes precision, recall, and hallucination rate by comparing
predicted findings (from the rule engine) against hand-labeled
ground truth.

Matching logic:
    A predicted finding matches a ground truth entry if:
      - Same rule_id
      - At least one room in the predicted finding's room_names
        matches the ground truth room (case-insensitive)

    Positive rule_ids (ending in _POS) are excluded from
    hallucination scoring — they represent good properties,
    not issues to validate against ground truth.
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ExpectedFinding:
    """A single hand-labeled expected finding."""
    rule_id: str
    room: str


@dataclass
class EvalResult:
    """Metrics for a single floor plan evaluation."""
    plan_id: str
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    total_predicted: int = 0
    total_expected: int = 0
    matched_rules: list[str] = field(default_factory=list)
    unmatched_predicted: list[str] = field(default_factory=list)
    missed_expected: list[str] = field(default_factory=list)

    @property
    def precision(self) -> float:
        """True positives / (true positives + false positives)."""
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom > 0 else 1.0

    @property
    def recall(self) -> float:
        """True positives / (true positives + false negatives)."""
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom > 0 else 1.0

    @property
    def hallucination_rate(self) -> float:
        """
        False positives / total non-positive predictions.
        Only counts negative findings (not _POS rule_ids).
        """
        denom = self.total_predicted
        return self.false_positives / denom if denom > 0 else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


def _normalize_room(room: str) -> str:
    """Normalize room name for comparison."""
    return room.strip().lower()


def _is_positive_rule(rule_id: str) -> bool:
    """Positive findings (_POS suffix) are excluded from eval."""
    return rule_id.endswith("_POS")


def _finding_matches(
    predicted_rule_id: str,
    predicted_rooms: list[str],
    expected: ExpectedFinding,
) -> bool:
    """
    Check if a predicted finding matches a ground truth entry.
    Match requires same rule_id and at least one overlapping room.
    """
    if predicted_rule_id != expected.rule_id:
        return False

    predicted_normalized = {_normalize_room(r) for r in predicted_rooms}
    expected_normalized = _normalize_room(expected.room)

    return expected_normalized in predicted_normalized


def evaluate_plan(
    plan_id: str,
    predicted_findings: list[dict],
    expected_findings: list[ExpectedFinding],
) -> EvalResult:
    """
    Compare predicted findings against ground truth for a single plan.

    Args:
        plan_id:             Identifier for this eval plan.
        predicted_findings:  List of Finding dicts from the rule engine.
                             Each must have 'rule_id' and 'room_names'.
        expected_findings:   Hand-labeled ExpectedFinding list.

    Returns:
        EvalResult with precision, recall, and hallucination metrics.
    """
    result = EvalResult(plan_id=plan_id)

    # Filter out positive findings — they're not part of the eval
    negative_predicted = [
        f for f in predicted_findings
        if not _is_positive_rule(f["rule_id"])
    ]

    result.total_predicted = len(negative_predicted)
    result.total_expected = len(expected_findings)

    # Track which expected findings have been matched
    matched_expected: set[int] = set()

    for pred in negative_predicted:
        pred_rule_id = pred["rule_id"]
        pred_rooms = pred["room_names"]
        pred_label = f"{pred_rule_id}:{pred_rooms}"

        matched = False
        for i, exp in enumerate(expected_findings):
            if i in matched_expected:
                continue
            if _finding_matches(pred_rule_id, pred_rooms, exp):
                matched = True
                matched_expected.add(i)
                result.true_positives += 1
                result.matched_rules.append(pred_label)
                break

        if not matched:
            result.false_positives += 1
            result.unmatched_predicted.append(pred_label)

    # Any expected findings not matched are false negatives
    for i, exp in enumerate(expected_findings):
        if i not in matched_expected:
            result.false_negatives += 1
            result.missed_expected.append(f"{exp.rule_id}:{exp.room}")

    return result


@dataclass
class AggregateMetrics:
    """Aggregated metrics across all eval plans."""
    total_plans: int = 0
    total_tp: int = 0
    total_fp: int = 0
    total_fn: int = 0
    total_predicted: int = 0
    per_plan: list[EvalResult] = field(default_factory=list)

    @property
    def precision(self) -> float:
        denom = self.total_tp + self.total_fp
        return self.total_tp / denom if denom > 0 else 1.0

    @property
    def recall(self) -> float:
        denom = self.total_tp + self.total_fn
        return self.total_tp / denom if denom > 0 else 1.0

    @property
    def hallucination_rate(self) -> float:
        return self.total_fp / self.total_predicted if self.total_predicted > 0 else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


def aggregate(results: list[EvalResult]) -> AggregateMetrics:
    """Roll up per-plan results into aggregate metrics."""
    agg = AggregateMetrics(total_plans=len(results), per_plan=results)
    for r in results:
        agg.total_tp += r.true_positives
        agg.total_fp += r.false_positives
        agg.total_fn += r.false_negatives
        agg.total_predicted += r.total_predicted
    return agg