from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.common.constant import HTTP_422_UNPROCESSABLE_ENTITY, STATUS_TO_CODE
from app.common.schema import ErrorDetail, ErrorResponse


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        message = exc.detail
        code = STATUS_TO_CODE.get(exc.status_code)
        if isinstance(exc.detail, dict):
            message = exc.detail.get("message", str(exc.detail))
            code = exc.detail.get("code", code)
        body = ErrorResponse(error=ErrorDetail(message=str(message), code=code))
        return JSONResponse(status_code=exc.status_code, content=body.model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        if errors:
            error_details = [
                f"{' -> '.join(map(str, e['loc']))}: {e['msg']}" for e in errors
            ]
            message = "; ".join(error_details)
        else:
            message = "입력값이 올바르지 않습니다"
        body = ErrorResponse(
            error=ErrorDetail(message=message, code=HTTP_422_UNPROCESSABLE_ENTITY.name)
        )
        return JSONResponse(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            content=body.model_dump(),
        )
