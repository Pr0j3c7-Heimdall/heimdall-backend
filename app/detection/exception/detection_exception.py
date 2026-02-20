from app.common.exception.base_exception import BaseAppException
from app.common.constant import HTTP_404_NOT_FOUND, HTTP_403_FORBIDDEN

class AnalysisNotFoundException(BaseAppException):
    def __init__(self, message: str = "분석 결과를 찾을 수 없습니다.", code: str = "NOT_FOUND"):
        super().__init__(HTTP_404_NOT_FOUND, message, code)

class ForbiddenAccessException(BaseAppException):
    def __init__(self, message: str = "본인이 업로드한 이미지만 조회할 수 있습니다.", code: str = "FORBIDDEN"):
        super().__init__(HTTP_403_FORBIDDEN, message, code)
