from typing import Optional

from starlette.exceptions import HTTPException

from app.common.constant import (
    BAD_REQUEST,
    FORBIDDEN,
    NOT_FOUND,
    UNAUTHORIZED,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)


class BaseAppException(HTTPException):
    """공통 에러 베이스 - message, code 지정해서 raise"""

    def __init__(
        self,
        status_code: int = HTTP_400_BAD_REQUEST,
        message: str = "요청을 처리할 수 없습니다",
        code: Optional[str] = None,
    ):
        super().__init__(
            status_code=status_code,
            detail={"message": message, "code": code or BAD_REQUEST},
        )


class BadRequestException(BaseAppException):
    def __init__(self, message: str = "잘못된 요청입니다", code: Optional[str] = None):
        super().__init__(HTTP_400_BAD_REQUEST, message, code or BAD_REQUEST)


class UnauthorizedException(BaseAppException):
    def __init__(self, message: str = "인증이 필요합니다", code: Optional[str] = None):
        super().__init__(HTTP_401_UNAUTHORIZED, message, code or UNAUTHORIZED)


class ForbiddenException(BaseAppException):
    def __init__(self, message: str = "접근 권한이 없습니다", code: Optional[str] = None):
        super().__init__(HTTP_403_FORBIDDEN, message, code or FORBIDDEN)


class NotFoundException(BaseAppException):
    def __init__(self, message: str = "찾을 수 없습니다", code: Optional[str] = None):
        super().__init__(HTTP_404_NOT_FOUND, message, code or NOT_FOUND)
