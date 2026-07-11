"""
Summary Writer — Phase 7

Prompts Gemini with the findings JSON only (no image) to produce
a 3–4 sentence plain-English summary.

Key constraint: the LLM must not introduce any issues that are not
already in the findings list. The summary is a narration of what the
rule engine found — not new analysis.
"""

import json
import logging

from vertexai.generative_models import GenerationConfig, SafetySetting, HarmCategory, HarmBlockThreshold

from backend.app.core.gemini import get_gemini_model
from backend.app.schemas.report import ReportSummary

logger = logging.getLogger(__name__)

_SUMMARY_PROMPT = """\
You are a real-estate analyst writing a brief summary for an apartment buyer.

Below is a structured JSON report of findings about a floor plan.
Each finding has a severity (VIOLATION, TRADEOFF, OBSERVATION), a category,
a title, and a detail explanation.

Write a 3–4 sentence plain-English summary that a non-technical buyer can
understand. The summary should:

1. Lead with the overall score and a one-sentence verdict.
2. Highlight the most critical violations (if any).
3. Mention notable positives (if any).
4. End with a one-sentence actionable recommendation.

STRICT RULES:
- Do NOT introduce any issues, rooms, or concerns that are not in the findings list.
- Do NOT mention specific rule IDs or technical codes (NBC, RERA) — keep it buyer-friendly.
- Keep it under 100 words.
- Do NOT use bullet points or numbered lists. Write in flowing prose.

FINDINGS JSON:
{findings_json}

OVERALL SCORE: {score}/100
PROS COUNT: {pros_count}
CONS COUNT: {cons_count}
"""


async def write_summary(report: ReportSummary) -> str:
    """
    Generate a plain-English summary from the report's findings.

    Args:
        report: ReportSummary with pros, cons, and score already computed.

    Returns:
        Summary string (3–4 sentences). On failure, returns a fallback.
    """
    # Build a compact findings representation for the prompt
    findings_for_prompt = []
    for finding in report.cons + report.pros:
        findings_for_prompt.append({
            "severity": finding.severity.value,
            "category": finding.category.value,
            "title": finding.title,
            "detail": finding.detail,
            "rooms": finding.room_names,
        })

    prompt = _SUMMARY_PROMPT.format(
        findings_json=json.dumps(findings_for_prompt, indent=2),
        score=report.overall_score,
        pros_count=len(report.pros),
        cons_count=len(report.cons),
    )

    try:
        model = get_gemini_model()
        # Relax safety filters — the findings JSON contains benign
        # architectural terms ("violation", "noise") that can trip
        # Vertex AI's content filter.
        safety_settings = [
            SafetySetting(
                category=category,
                threshold=HarmBlockThreshold.OFF,
            )
            for category in [
                HarmCategory.HARM_CATEGORY_HARASSMENT,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            ]
        ]

        response = model.generate_content(
            [prompt],
            generation_config=GenerationConfig(
                temperature=0.3,
                max_output_tokens=8192,
            ),
            safety_settings=safety_settings,
        )

        # Vertex AI raises ValueError on .text if response has no
        # candidates (content filter, empty generation, etc.)
        if not response.candidates:
            logger.warning(
                f"Gemini returned no candidates for plan {report.plan_id} — "
                f"using fallback summary"
            )
            return _fallback_summary(report)

        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            logger.warning(
                f"Gemini candidate has no content for plan {report.plan_id} — "
                f"finish_reason={candidate.finish_reason}, "
                f"using fallback summary"
            )
            return _fallback_summary(report)

        summary = candidate.content.parts[0].text.strip()
        logger.info(
            f"Summary generated for plan {report.plan_id} "
            f"({len(summary)} chars)"
        )
        return summary

    except Exception as e:
        logger.error(
            f"Summary generation failed for plan {report.plan_id}: {e}",
            exc_info=True,
        )
        # Deterministic fallback — never leave summary_text empty
        return _fallback_summary(report)


def _fallback_summary(report: ReportSummary) -> str:
    """
    Deterministic fallback summary when Gemini is unavailable.
    """
    parts = [f"This floor plan scored {report.overall_score} out of 100."]

    violation_count = sum(
        1 for f in report.cons if f.severity.value == "VIOLATION"
    )
    tradeoff_count = sum(
        1 for f in report.cons if f.severity.value == "TRADEOFF"
    )

    if violation_count > 0:
        parts.append(
            f"The analysis identified {violation_count} "
            f"violation{'s' if violation_count != 1 else ''} "
            f"against building standards."
        )
    if tradeoff_count > 0:
        parts.append(
            f"There {'are' if tradeoff_count != 1 else 'is'} "
            f"{tradeoff_count} design "
            f"tradeoff{'s' if tradeoff_count != 1 else ''} worth considering."
        )
    if report.pros:
        parts.append(
            f"On the positive side, {len(report.pros)} "
            f"favorable aspect{'s were' if len(report.pros) != 1 else ' was'} "
            f"noted."
        )

    return " ".join(parts)