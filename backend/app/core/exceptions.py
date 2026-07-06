class PlanalyzeError(Exception):
    """Base exception for all Planalyze errors."""


class ExtractionFailedError(PlanalyzeError):
    """
    Raised when Gemini fails to return a valid FloorPlanExtraction
    after all retry attempts are exhausted.
    """
    def __init__(self, attempts: int, last_error: str):
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"Extraction failed after {attempts} attempts. "
            f"Last error: {last_error}"
        )


class PlanNotFoundError(PlanalyzeError):
    """Raised when a floor plan ID does not exist in the DB."""
    def __init__(self, plan_id: str):
        super().__init__(f"Floor plan not found: {plan_id}")


class StorageError(PlanalyzeError):
    """Raised when an image cannot be read from or written to storage."""