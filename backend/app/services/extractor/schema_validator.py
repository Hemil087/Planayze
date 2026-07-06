from pydantic import ValidationError
from app.schemas.extraction import FloorPlanExtraction


class ValidationResult:
    def __init__(
        self,
        success: bool,
        data: FloorPlanExtraction | None = None,
        error_summary: str | None = None,
    ):
        self.success = success
        self.data = data
        self.error_summary = error_summary


def validate_extraction(raw: dict) -> ValidationResult:
    try:
        extraction = FloorPlanExtraction(**raw)
        return ValidationResult(success=True, data=extraction)

    except ValidationError as e:
        errors = e.errors()
        lines = []
        for err in errors:
            location = " -> ".join(str(loc) for loc in err["loc"])
            lines.append(f"  - {location}: {err['msg']}")

        error_summary = (
            f"{len(errors)} validation error(s):\n" + "\n".join(lines)
        )
        return ValidationResult(success=False, error_summary=error_summary)

    except Exception as e:
        return ValidationResult(
            success=False,
            error_summary=f"Unexpected error during validation: {str(e)}",
        )
