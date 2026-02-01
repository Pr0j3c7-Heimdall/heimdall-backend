from typing import Any, Optional

from pydantic import BaseModel


class SuccessResponse(BaseModel):
    success: bool = True
    data: Any = None


class ErrorDetail(BaseModel):
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
