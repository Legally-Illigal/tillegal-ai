"""Development-only, stateless pilot RAG route."""
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from ai_core.rag_generation import GenerationError
from src.framework.tools.error_handling import ToolExecutionError, ToolTimeoutError
from src.framework.tools.permissions import ToolPermissionDeniedError

router = APIRouter()


class PilotQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=10000)
    top_k: int = Field(default=5, ge=1, le=100, strict=True)
    workflow: Literal["basic", "multi_agent", "draft", "semantic"] = "basic"


@router.post("/pilot/legal-qa")
async def legal_qa(body: PilotQuestion, request: Request):
    try:
        return await request.app.state.legal_qa.answer(body.question, request.state.request_id, body.top_k, body.workflow)
    except ToolPermissionDeniedError:
        raise HTTPException(403, "RETRIEVAL_POLICY_REJECTED") from None
    except (ToolTimeoutError, TimeoutError):
        raise HTTPException(504, "REQUEST_TIMEOUT") from None
    except BlockingIOError:
        raise HTTPException(429, "RESOURCE_BUSY") from None
    except ToolExecutionError as exc:
        if isinstance(exc.__cause__, BlockingIOError):
            raise HTTPException(429, "RESOURCE_BUSY") from None
        raise HTTPException(503, "RETRIEVAL_FAILED") from None
    except GenerationError as exc:
        status = {"PROVIDER_RATE_LIMIT": 429, "PROVIDER_TIMEOUT": 504, "INVALID_OUTPUT": 502}
        raise HTTPException(status.get(exc.code, 503), exc.code) from None
