from app.common.exception.base_exception import BaseAppException
from app.common.constant import HTTP_400_BAD_REQUEST, HTTP_422_UNPROCESSABLE_ENTITY, HTTP_404_NOT_FOUND, HTTP_403_FORBIDDEN

class AudioUploadException(BaseAppException):
    def __init__(self, message: str = "오디오 업로드에 실패했습니다.", code: str = "AUDIO_UPLOAD_FAILED"):
        super().__init__(HTTP_400_BAD_REQUEST, message, code)

class InvalidAudioFileException(BaseAppException):
    def __init__(self, message: str = "유효하지 않은 오디오 파일입니다. (지원 형식: wav, mp3)", code: str = "INVALID_AUDIO_FILE"):
        super().__init__(HTTP_422_UNPROCESSABLE_ENTITY, message, code)

class InvalidAudioTrackException(BaseAppException):
    def __init__(self, message: str = "유효하지 않은 track 값입니다. (speech 또는 singing)", code: str = "INVALID_AUDIO_TRACK"):
        super().__init__(HTTP_422_UNPROCESSABLE_ENTITY, message, code)

class AudioNotFoundException(BaseAppException):
    def __init__(self, message: str = "오디오를 찾을 수 없습니다.", code: str = "AUDIO_NOT_FOUND"):
        super().__init__(HTTP_404_NOT_FOUND, message, code)

class AudioAccessDeniedException(BaseAppException):
    def __init__(self, message: str = "해당 리소스에 대한 접근 권한이 없습니다", code: str = "FORBIDDEN"):
        super().__init__(HTTP_403_FORBIDDEN, message, code)
