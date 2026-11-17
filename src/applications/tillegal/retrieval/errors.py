"""Safe application errors, independent of database and model SDKs."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ErrorCategory(StrEnum):
    INVALID_REQUEST = "INVALID_REQUEST"
    INDEX_UNAVAILABLE = "INDEX_UNAVAILABLE"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    DATABASE_FAILURE = "DATABASE_FAILURE"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    INCONSISTENT_EVIDENCE = "INCONSISTENT_EVIDENCE"
    TIMEOUT = "TIMEOUT"


class RetrievalErrorDetail(BaseModel):
    """Public failure data. Messages must never contain upstream error text."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    category: ErrorCategory
    code: str
    stage: str
    message: str
    retryable: bool = False


class RetrievalServiceError(RuntimeError):
    """Carry a classified failure between application helpers."""

    def __init__(self, detail: RetrievalErrorDetail) -> None:
        super().__init__(detail.message)
        self.detail = detail
