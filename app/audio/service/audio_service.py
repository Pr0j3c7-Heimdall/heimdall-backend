from fastapi import UploadFile, BackgroundTasks

from app.audio.repository.audio_repository import AudioRepository
from app.audio.model.audio import Audio, AudioTrack
from app.audio.exception.audio_exception import InvalidAudioFileException, InvalidAudioTrackException
from app.detection.audio.repository.audio_detection_repository import AudioDetectionRepository
from app.detection.audio.service.audio_detection_service import AudioDetectionService

import magic

# 모듈 레벨 상수로 분리 (soundfile/libsndfile이 결정적으로 다룰 수 있는 포맷만 허용)
# flac은 제외: AI 모델 추론 파이프라인에서 검증되지 않아 허용하지 않음
ALLOWED_MIME_TYPES = frozenset(["audio/x-wav", "audio/wav", "audio/wave", "audio/mpeg", "audio/mp3"])
ALLOWED_TRACKS = frozenset(t.value for t in AudioTrack)

class AudioService:
    def __init__(self, audio_repository: AudioRepository, detection_repository: AudioDetectionRepository, detection_service: AudioDetectionService):
        self.audio_repository = audio_repository
        self.detection_repository = detection_repository
        self.detection_service = detection_service

    async def upload_audio(self, file: UploadFile, track: str, user_id: int, background_tasks: BackgroundTasks) -> Audio:
        if track not in ALLOWED_TRACKS:
            raise InvalidAudioTrackException()

        # 파일의 실제 데이터(바이트)를 조금 읽어서 MIME 타입 확인
        file_header = await file.read(4096)
        actual_mime_type = magic.from_buffer(file_header, mime=True)

        # 제대로 저장하기 위해 파일의 처음으로 포인터를 되돌려 놓기
        await file.seek(0)

        # 클라이언트가 보낸 헤더가 아니라, 실제 파악한 MIME 타입으로 검증
        if actual_mime_type not in ALLOWED_MIME_TYPES:
            raise InvalidAudioFileException(message="지원하지 않거나 변조된 오디오 파일 형식입니다.")

        new_audio = await self.audio_repository.save_audio_file(file, user_id, track)

        # 검증 도메인에 분석 시작을 위임 (오디오 ID, 파일 경로, 트랙 전달)
        background_tasks.add_task(
            self.detection_service.run_ai_detection,
            audio_id=new_audio.id,
            audio_path=new_audio.filepath,
            track=track
        )

        return new_audio
