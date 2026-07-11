import logging

from app.schemas.extraction import FloorPlanExtraction
from app.schemas.report import Finding

from app.services.engine.rules import (
    space_efficiency,
    ventilation,
    privacy,
    circulation,
    adjacency,
    size_adequacy,
)

logger = logging.getLogger(__name__)

RULES = [
    space_efficiency,
    ventilation,
    privacy,
    circulation,
    adjacency,
    size_adequacy,
]


def run_rules(extraction: FloorPlanExtraction) -> list[Finding]:
    """
    Run all rule modules against the extracted floor plan.
    Returns a flat list of all findings.
    Each rule module is independent — a failure in one does not
    stop the others.
    """
    all_findings: list[Finding] = []

    for rule_module in RULES:
        module_name = rule_module.__name__.split(".")[-1]
        try:
            findings = rule_module.run(extraction)
            logger.info(
                f"Rule '{module_name}' fired {len(findings)} finding(s)"
            )
            all_findings.extend(findings)
        except Exception as e:
            logger.error(
                f"Rule '{module_name}' raised an error and was skipped: {e}",
                exc_info=True,
            )

    logger.info(f"Rule engine total: {len(all_findings)} finding(s)")
    return all_findings