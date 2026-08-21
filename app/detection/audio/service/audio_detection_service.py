from ..repository.audio_detection_repository import AudioDetectionRepository
from ..exception.audio_detection_exception import AudioAnalysisNotFoundException, AudioForbiddenAccessException
from ..schema.response.audio_status import AudioDetectionStatusData
from ..schema.response.audio_result import AudioDetectionResultData, ModelResultSchema
from ..model.audio_final_detection_results import AudioAnalysisStatus
from app.ai_pipeline.audio.speech_pipeline import run_speech_detection
from app.ai_pipeline.audio.singing_pipeline import run_singing_detection

from datetime import datetime, timezone
import logging
from app.database import AsyncSessionLocal

class AudioDetectionService:
    def __init__(self, detection_repo: AudioDetectionRepository):
        self.detection_repo = detection_repo

    async def get_detection_status(self, audio_id: int, user_id: int) -> AudioDetectionStatusData:
        # AudioDetectionRepository의 JOIN 메서드 호출 (순환 참조 방지용)
        status = await self.detection_repo.get_audio_status_and_check_owner(audio_id, user_id)

        if status is None:
            raise AudioAnalysisNotFoundException(message="요청하신 오디오 또는 분석 결과를 찾을 수 없습니다.")

        if status == "FORBIDDEN":
            raise AudioForbiddenAccessException(message="본인이 업로드한 오디오만 조회할 수 있습니다.")

        return AudioDetectionStatusData(
            audio_id=audio_id,
            analysis_status=status
        )

    async def get_detection_result(self, audio_id: int, user_id: int) -> AudioDetectionResultData:
        """오디오 ID를 기준으로 모든 모델의 분석 결과를 포함하여 조회함"""
        audio = await self.detection_repo.get_full_detection_result(audio_id)

        if not audio:
            raise AudioAnalysisNotFoundException(message="요청하신 오디오 또는 분석 결과를 찾을 수 없습니다.")

        if audio.user_id != user_id:
            raise AudioForbiddenAccessException(message="본인이 업로드한 오디오만 조회할 수 있습니다.")

        summary = audio.analysis_summary
        if not summary or summary.analysis_status != AudioAnalysisStatus.COMPLETED:
            raise AudioAnalysisNotFoundException(message="분석이 완료되지 않았거나 오디오를 찾을 수 없습니다.")

        model_results = []
        if audio.model_results:
            model_results = [
                ModelResultSchema(
                    model_result_id=res.id,
                    detection_method=res.detection_method,
                    confidence_score=res.confidence_score,
                    result_json=res.result_json,
                ) for res in audio.model_results
            ]

        return AudioDetectionResultData(
            audio_id=audio.id,
            audio_url=audio.audio_url,
            track=audio.track,
            final_is_ai=summary.final_is_ai,
            final_ai_probability=summary.final_ai_probability,
            completed_at=summary.completed_at,
            models=model_results
        )

    async def run_ai_detection(self, audio_id: int, audio_path: str, track: str):
        """
        AI 분석 파이프라인(음성/가창 트랙)을 실행하고 결과를 DB에 반영합니다.
        """
        logging.info(f"DEBUG: Starting AI detection for audio ID: {audio_id} (track={track})")

        async with AsyncSessionLocal() as session:
            repo = AudioDetectionRepository(session)
            await repo.update_analysis_status(audio_id=audio_id, status=AudioAnalysisStatus.PROCESSING)

        # 트랙별 파이프라인 실행 (음성/가창 자동 라우팅은 미구현 - 업로드 시 클라이언트가 지정한 트랙을 그대로 사용)
        if track == "singing":
            pipeline_result = await run_singing_detection(audio_path)
            model_list = pipeline_result["singing_list"]
        else:
            pipeline_result = await run_speech_detection(audio_path)
            model_list = pipeline_result["speech_list"]

        async with AsyncSessionLocal() as session:
            repo = AudioDetectionRepository(session)
            await repo.save_model_result(audio_id=audio_id, data_list=model_list)
            await repo.update_analysis_status(
                audio_id=audio_id,
                status=AudioAnalysisStatus.COMPLETED,
                final_is_ai=pipeline_result["final_is_ai"],
                final_ai_probability=pipeline_result["final_ai_probability"],
                completed_at=datetime.now(timezone.utc)
            )

        logging.info(f"DEBUG: AI detection COMPLETED for audio ID: {audio_id}")
