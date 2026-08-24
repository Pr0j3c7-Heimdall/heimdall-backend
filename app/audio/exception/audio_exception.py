from app.common.exception.base_exception import BaseAppException
from app.common.constant import HTTP_400_BAD_REQUEST, HTTP_413_PAYLOAD_TOO_LARGE, HTTP_422_UNPROCESSABLE_ENTITY, HTTP_404_NOT_FOUND, HTTP_403_FORBIDDEN

class AudioUploadException(BaseAppException):
    def __init__(self, message: str = "오디오 업로드에 실패했습니다.", code: str = "AUDIO_UPLOAD_FAILED"):
        super().__init__(HTTP_400_BAD_REQUEST, message, code)

class InvalidAudioFileException(BaseAppException):
    def __init__(self, message: str = "유효하지 않은 오디오 파일입니다. (지원 형식: wav, mp3)", code: str = "INVALID_AUDIO_FILE"):
        super().__init__(HTTP_422_UNPROCESSABLE_ENTITY, message, code)

class AudioFileTooLargeException(BaseAppException):
    def __init__(self, message: str = "오디오 파일은 최대 200MB까지 업로드할 수 있습니다.", code: str = "AUDIO_FILE_TOO_LARGE"):
        super().__init__(HTTP_413_PAYLOAD_TOO_LARGE, message, code)

class AudioNotFoundException(BaseAppException):
    def __init__(self, message: str = "오디오를 찾을 수 없습니다.", code: str = "AUDIO_NOT_FOUND"):
        super().__init__(HTTP_404_NOT_FOUND, message, code)

class AudioAccessDeniedException(BaseAppException):
    def __init__(self, message: str = "해당 리소스에 대한 접근 권한이 없습니다", code: str = "FORBIDDEN"):
        super().__init__(HTTP_403_FORBIDDEN, message, code)
