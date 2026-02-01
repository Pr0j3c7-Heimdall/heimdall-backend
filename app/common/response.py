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


def success_response(data: Any = None) -> dict:
    """성공 응답 포맷"""
    return {"success": True, "data": data}


def error_response(message: str, code: Optional[str] = None) -> dict:
    """에러 응답 포맷"""
    return {
        "success": False,
        "error": {"message": message, "code": code} if code else {"message": message},
    }
