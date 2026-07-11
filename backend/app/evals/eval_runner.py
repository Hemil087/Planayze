"""
Eval Runner — Phase 9

Reads ground truth from evals/ground_truth.json, runs the full
extraction + rule engine pipeline for each plan, and prints a
metrics table.

Usage (inside Docker):
    docker-compose exec backend python -m app.evals.eval_runner

The runner:
  1. Loads ground truth entries
  2. For each plan: reads image → runs extraction with retry →
     runs rule engine (single pass, no consistency filter — eval
     measures raw rule engine accuracy)
  3. Compares predicted findings against expected
  4. Prints per-plan and aggregate metrics
"""

import json
import sys
import logging
from pathlib import Path

from backend.app.evals.metrics import (
    ExpectedFinding,
    evaluate_plan,
    aggregate,
    AggregateMetrics,
    EvalResult,
)
from backend.app.services.extractor.retry import run_extraction_with_retry
from backend.app.services.engine.consistency_filter import run_consistency_filter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# Paths
EVALS_DIR = Path(__file__).parent
GROUND_TRUTH_PATH = EVALS_DIR / "ground_truth.json"
FIXTURES_DIR = EVALS_DIR / "fixtures"

# Targets
TARGET_PRECISION = 0.80
TARGET_HALLUCINATION = 0.10


def load_ground_truth() -> list[dict]:
    """Load and validate ground truth entries."""
    if not GROUND_TRUTH_PATH.exists():
        logger.error(f"Ground truth file not found: {GROUND_TRUTH_PATH}")
        sys.exit(1)

    with open(GROUND_TRUTH_PATH) as f:
        data = json.load(f)

    if not isinstance(data, list) or len(data) == 0:
        logger.error("Ground truth must be a non-empty JSON array")
        sys.exit(1)

    logger.info(f"Loaded {len(data)} ground truth entries")
    return data


def run_pipeline_for_plan(image_path: str) -> list[dict]:
    """
    Run the full production pipeline for a single plan image:
    extraction + consistency filter (N runs of rule engine).

    This mirrors what POST /analysis does, so the eval measures
    the actual output a user would see — not raw single-pass noise.
    """
    full_path = FIXTURES_DIR / image_path
    if not full_path.exists():
        raise FileNotFoundError(f"Fixture image not found: {full_path}")

    image_bytes = full_path.read_bytes()

    # Extract geometry
    extraction = run_extraction_with_retry(image_bytes)

    # Run consistency filter (N extractions + rule engine runs,
    # keeps only findings that recur above threshold)
    hardened_findings = run_consistency_filter(extraction)

    return [f.model_dump(mode="json") for f in hardened_findings]


def print_plan_result(result: EvalResult) -> None:
    """Print metrics for a single plan."""
    print(f"\n{'─' * 60}")
    print(f"  Plan: {result.plan_id}")
    print(f"{'─' * 60}")
    print(f"  Predicted (neg): {result.total_predicted}  |  Expected: {result.total_expected}")
    print(f"  TP: {result.true_positives}  FP: {result.false_positives}  FN: {result.false_negatives}")
    print(f"  Precision:  {result.precision:.2%}")
    print(f"  Recall:     {result.recall:.2%}")
    print(f"  Halluc.:    {result.hallucination_rate:.2%}")
    print(f"  F1:         {result.f1:.2%}")

    if result.unmatched_predicted:
        print(f"\n  False positives (hallucinated):")
        for fp in result.unmatched_predicted:
            print(f"    - {fp}")

    if result.missed_expected:
        print(f"\n  False negatives (missed):")
        for fn in result.missed_expected:
            print(f"    - {fn}")


def print_aggregate(agg: AggregateMetrics) -> None:
    """Print the aggregate metrics table."""
    print(f"\n{'═' * 60}")
    print(f"  AGGREGATE METRICS — {agg.total_plans} plan(s)")
    print(f"{'═' * 60}")
    print(f"  Total TP: {agg.total_tp}  FP: {agg.total_fp}  FN: {agg.total_fn}")
    print(f"  Precision:         {agg.precision:.2%}  (target: ≥ {TARGET_PRECISION:.0%})")
    print(f"  Recall:            {agg.recall:.2%}")
    print(f"  Hallucination:     {agg.hallucination_rate:.2%}  (target: < {TARGET_HALLUCINATION:.0%})")
    print(f"  F1:                {agg.f1:.2%}")

    # Target check
    print(f"\n  {'─' * 40}")
    prec_ok = agg.precision >= TARGET_PRECISION
    hall_ok = agg.hallucination_rate < TARGET_HALLUCINATION
    print(f"  Precision target:      {'✅ PASS' if prec_ok else '❌ FAIL'}")
    print(f"  Hallucination target:  {'✅ PASS' if hall_ok else '❌ FAIL'}")
    print(f"{'═' * 60}\n")


def main():
    entries = load_ground_truth()
    results: list[EvalResult] = []

    for entry in entries:
        plan_id = entry["plan_id"]
        image_path = entry["image"]
        expected = [
            ExpectedFinding(rule_id=e["rule_id"], room=e["room"])
            for e in entry["expected_findings"]
        ]

        logger.info(f"Running eval for {plan_id} ({image_path})...")

        try:
            predicted = run_pipeline_for_plan(image_path)
            result = evaluate_plan(plan_id, predicted, expected)
            results.append(result)
            print_plan_result(result)
        except FileNotFoundError as e:
            logger.error(f"Skipping {plan_id}: {e}")
        except Exception as e:
            logger.error(f"Eval failed for {plan_id}: {e}", exc_info=True)

    if not results:
        print("\n  No plans were evaluated. Check ground truth and fixtures.")
        sys.exit(1)

    agg = aggregate(results)
    print_aggregate(agg)


if __name__ == "__main__":
    main()