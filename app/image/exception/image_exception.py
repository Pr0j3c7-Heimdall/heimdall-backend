from app.common.exception.base_exception import BaseAppException
from app.common.constant import HTTP_400_BAD_REQUEST, HTTP_422_UNPROCESSABLE_ENTITY, HTTP_404_NOT_FOUND

class ImageUploadException(BaseAppException):
    def __init__(self, message: str = "이미지 업로드에 실패했습니다.", code: str = "IMAGE_UPLOAD_FAILED"):
        super().__init__(HTTP_400_BAD_REQUEST, message, code)

class InvalidImageFileException(BaseAppException):
    def __init__(self, message: str = "유효하지 않은 이미지 파일입니다. (지원 형식: jpg, jpeg, png, webp)", code: str = "INVALID_IMAGE_FILE"):
        super().__init__(HTTP_422_UNPROCESSABLE_ENTITY, message, code)

class ImageNotFoundException(BaseAppException):
    def __init__(self, message: str = "이미지를 찾을 수 없습니다.", code: str = "IMAGE_NOT_FOUND"):
        super().__init__(HTTP_404_NOT_FOUND, message, code)

class ImageAccessDeniedException(BaseAppException):
    def __init__(self, message: str = "해당 리소스에 대한 접근 권한이 없습니다", code: str = "FORBIDDEN"):
        super().__init__(403, message, code)
