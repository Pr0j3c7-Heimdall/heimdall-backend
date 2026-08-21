import os
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from fastapi import UploadFile

from app.audio.model.audio import Audio
from app.detection.audio.model.audio_final_detection_results import AudioFinalDetectionResult
from app.config import get_image_settings
from app.audio.exception.audio_exception import AudioNotFoundException
from app.audio.exception.audio_exception import AudioAccessDeniedException

settings = get_image_settings()

class AudioRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        # 이미지와 동일한 업로드 기본 디렉토리를 공유하되, audio/ 하위에 별도 저장
        self.upload_base_dir = os.path.join(settings.UPLOAD_DIR, "audio")
        os.makedirs(self.upload_base_dir, exist_ok=True)

    async def save_audio_file(self, file: UploadFile, user_id: int, track: str) -> Audio:
        """
        오디오 파일을 로컬 파일 시스템에 저장하고 데이터베이스에 Audio 레코드를 생성함.
        """
        # 충돌 방지를 위한 고유 파일명 생성
        file_extension = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"

        # 파일 관리를 위한 사용자별 하위 디렉토리 생성
        user_upload_dir = os.path.join(self.upload_base_dir, str(user_id))
        os.makedirs(user_upload_dir, exist_ok=True)

        file_path = os.path.join(user_upload_dir, unique_filename)

        # 파일 저장
        with open(file_path, "wb") as buffer:
            while content := await file.read(1024):  # 청크 단위로 읽기
                buffer.write(content)

        audio_url = f"{settings.BASE_URL}/uploads/audio/{user_id}/{unique_filename}"

        new_audio = Audio(
            user_id=user_id,
            filename=file.filename,
            filepath=file_path,
            audio_url=audio_url,
            track=track
        )
        self.db_session.add(new_audio)
        await self.db_session.flush()

        initial_summary = AudioFinalDetectionResult(
            audio_id=new_audio.id
        )
        self.db_session.add(initial_summary)

        await self.db_session.commit()
        await self.db_session.refresh(new_audio)
        return new_audio

    async def get_audio_by_id(self, audio_id: int) -> Audio:
        """
        데이터베이스에서 ID를 기준으로 오디오 레코드를 조회함.
        """
        stmt = select(Audio).where(Audio.id == audio_id)
        result = await self.db_session.execute(stmt)
        audio = result.scalars().first()
        if not audio:
            raise AudioNotFoundException()
        return audio

    async def get_audio_status_and_check_owner(self, audio_id: int, user_id: int) -> str:
        """
        오디오 소유권을 확인하고 현재 분석 상태를 조인(JOIN)하여 한 번에 조회함.
        """
        stmt = (
            select(Audio, AudioFinalDetectionResult.analysis_status)
            .join(AudioFinalDetectionResult, Audio.id == AudioFinalDetectionResult.audio_id)
            .where(Audio.id == audio_id)
        )
        result = await self.db_session.execute(stmt)
        row = result.first()

        if not row:
            raise AudioNotFoundException(message="요청하신 오디오 또는 분석 결과를 찾을 수 없습니다.")

        audio, status = row

        if audio.user_id != user_id:
            raise AudioAccessDeniedException()

        return status
