"""
Phase 9 Gate Tests — Eval Metrics

Validates:
  1. Perfect match → precision=1.0, recall=1.0, hallucination=0.0
  2. All false positives → precision=0.0, hallucination=1.0
  3. All false negatives → recall=0.0
  4. Mixed results compute correctly
  5. Positive rules (_POS) are excluded from eval
  6. Room matching is case-insensitive
  7. Aggregate metrics roll up correctly
"""

import pytest
from backend.app.evals.metrics import (
    ExpectedFinding,
    evaluate_plan,
    aggregate,
)


class TestPrecisionRecall:
    def test_perfect_match(self):
        predicted = [
            {"rule_id": "VENT_003", "room_names": ["Bedroom 1"]},
            {"rule_id": "SIZE_BED", "room_names": ["Bedroom 3"]},
        ]
        expected = [
            ExpectedFinding(rule_id="VENT_003", room="Bedroom 1"),
            ExpectedFinding(rule_id="SIZE_BED", room="Bedroom 3"),
        ]
        result = evaluate_plan("test", predicted, expected)
        assert result.precision == 1.0
        assert result.recall == 1.0
        assert result.hallucination_rate == 0.0
        assert result.true_positives == 2
        assert result.false_positives == 0
        assert result.false_negatives == 0

    def test_all_false_positives(self):
        predicted = [
            {"rule_id": "VENT_001", "room_names": ["Kitchen"]},
            {"rule_id": "ADJ_001", "room_names": ["Kitchen", "Bathroom"]},
        ]
        expected = [
            ExpectedFinding(rule_id="SIZE_BED", room="Bedroom 3"),
        ]
        result = evaluate_plan("test", predicted, expected)
        assert result.precision == 0.0
        assert result.hallucination_rate == 1.0
        assert result.false_positives == 2
        assert result.false_negatives == 1

    def test_all_false_negatives(self):
        predicted = []
        expected = [
            ExpectedFinding(rule_id="VENT_003", room="Bedroom 1"),
            ExpectedFinding(rule_id="SIZE_BED", room="Bedroom 3"),
        ]
        result = evaluate_plan("test", predicted, expected)
        assert result.recall == 0.0
        assert result.false_negatives == 2
        assert result.total_predicted == 0

    def test_mixed_results(self):
        predicted = [
            {"rule_id": "VENT_003", "room_names": ["Bedroom 1"]},   # TP
            {"rule_id": "SIZE_BED", "room_names": ["Bedroom 3"]},   # TP
            {"rule_id": "ADJ_001", "room_names": ["Kitchen"]},      # FP
        ]
        expected = [
            ExpectedFinding(rule_id="VENT_003", room="Bedroom 1"),
            ExpectedFinding(rule_id="SIZE_BED", room="Bedroom 3"),
            ExpectedFinding(rule_id="PRIV_002", room="Bedroom 1"),  # FN
        ]
        result = evaluate_plan("test", predicted, expected)
        assert result.true_positives == 2
        assert result.false_positives == 1
        assert result.false_negatives == 1
        assert result.precision == pytest.approx(2 / 3)
        assert result.recall == pytest.approx(2 / 3)


class TestPositiveRuleExclusion:
    def test_positive_rules_excluded(self):
        predicted = [
            {"rule_id": "VENT_003", "room_names": ["Bedroom 1"]},       # negative → counted
            {"rule_id": "VENT_003_POS", "room_names": ["Dining Room"]},  # positive → excluded
            {"rule_id": "SPACE_001_POS", "room_names": ["Entire Floor Plan"]},  # positive → excluded
        ]
        expected = [
            ExpectedFinding(rule_id="VENT_003", room="Bedroom 1"),
        ]
        result = evaluate_plan("test", predicted, expected)
        assert result.total_predicted == 1  # only the negative one
        assert result.true_positives == 1
        assert result.false_positives == 0


class TestRoomMatching:
    def test_case_insensitive(self):
        predicted = [
            {"rule_id": "SIZE_BED", "room_names": ["bedroom 3"]},
        ]
        expected = [
            ExpectedFinding(rule_id="SIZE_BED", room="Bedroom 3"),
        ]
        result = evaluate_plan("test", predicted, expected)
        assert result.true_positives == 1

    def test_multi_room_finding_matches(self):
        """A finding with multiple rooms should match if any room matches."""
        predicted = [
            {"rule_id": "ADJ_003", "room_names": ["Bedroom 1", "Walk-in Closet"]},
        ]
        expected = [
            ExpectedFinding(rule_id="ADJ_003", room="Bedroom 1"),
        ]
        result = evaluate_plan("test", predicted, expected)
        assert result.true_positives == 1


class TestAggregate:
    def test_aggregate_rolls_up(self):
        predicted_1 = [
            {"rule_id": "VENT_003", "room_names": ["Bedroom 1"]},  # TP
        ]
        expected_1 = [
            ExpectedFinding(rule_id="VENT_003", room="Bedroom 1"),
        ]

        predicted_2 = [
            {"rule_id": "SIZE_BED", "room_names": ["Bedroom 3"]},  # TP
            {"rule_id": "ADJ_001", "room_names": ["Kitchen"]},     # FP
        ]
        expected_2 = [
            ExpectedFinding(rule_id="SIZE_BED", room="Bedroom 3"),
            ExpectedFinding(rule_id="PRIV_002", room="Bedroom 1"),  # FN
        ]

        r1 = evaluate_plan("plan1", predicted_1, expected_1)
        r2 = evaluate_plan("plan2", predicted_2, expected_2)
        agg = aggregate([r1, r2])

        assert agg.total_plans == 2
        assert agg.total_tp == 2
        assert agg.total_fp == 1
        assert agg.total_fn == 1
        assert agg.precision == pytest.approx(2 / 3)
        assert agg.recall == pytest.approx(2 / 3)


class TestEdgeCases:
    def test_empty_predictions_and_expectations(self):
        result = evaluate_plan("test", [], [])
        assert result.precision == 1.0
        assert result.recall == 1.0
        assert result.hallucination_rate == 0.0

    def test_no_double_matching(self):
        """Each expected finding should only match once."""
        predicted = [
            {"rule_id": "VENT_003", "room_names": ["Bedroom 1"]},
            {"rule_id": "VENT_003", "room_names": ["Bedroom 1"]},  # duplicate
        ]
        expected = [
            ExpectedFinding(rule_id="VENT_003", room="Bedroom 1"),
        ]
        result = evaluate_plan("test", predicted, expected)
        assert result.true_positives == 1
        assert result.false_positives == 1  # second one is unmatched