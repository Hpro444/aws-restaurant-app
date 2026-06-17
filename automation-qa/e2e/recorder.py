"""Result models and the recorder that collects every executed test step."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DbCheck(BaseModel):
    """Outcome of a single DynamoDB verification attached to a test step."""

    table: str
    expectation: str
    before: str = ""
    after: str = ""
    passed: bool


class StepResult(BaseModel):
    """Full record of one executed endpoint test step."""

    step: str
    name: str
    method: str
    path: str
    auth_user: str = "anonymous"
    request_query: dict | None = None
    request_body: dict | None = None
    expected: str
    status_code: int | None = None
    response_body: str = ""
    http_passed: bool
    reason: str = ""
    db_checks: list[DbCheck] = Field(default_factory=list)
    duration_ms: float = 0.0

    @property
    def db_passed(self) -> bool:
        """Return True when every attached DB check passed (or none exist)."""
        return all(check.passed for check in self.db_checks)

    @property
    def passed(self) -> bool:
        """Return True when both the HTTP assertion and all DB checks passed."""
        return self.http_passed and self.db_passed


class Recorder:
    """Accumulates StepResult records across all suites for the final report."""

    def __init__(self) -> None:
        """Initialize an empty result list."""
        self.results: list[StepResult] = []

    def add(self, result: StepResult) -> None:
        """Append a finished step result."""
        self.results.append(result)

    @property
    def passed_count(self) -> int:
        """Return the number of fully passed steps."""
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_count(self) -> int:
        """Return the number of failed steps."""
        return len(self.results) - self.passed_count
