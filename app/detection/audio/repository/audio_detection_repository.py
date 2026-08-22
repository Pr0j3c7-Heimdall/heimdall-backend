from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.orm import selectinload
from typing import Optional, TYPE_CHECKING

# 순환 참조 방지를 위해 상대 경로 또는 직접 경로 사용
from ..model.audio_final_detection_results import AudioFinalDetectionResult, AudioAnalysisStatus
from ..model.audio_model_detection_results import AudioModelDetectionResult
from ..model.audio_c2pa_analysis_results import AudioC2paAnalysisResult

if TYPE_CHECKING:
    from app.audio.model.audio import Audio
# 주의: 모듈 최상단에서 app.audio.model.audio를 임포트하지 않음.
# app.audio 패키지는 app.detection.audio.repository를 필요로 하는 라우터 체인을 가지고 있어서,
# 여기서 최상단 임포트하면 app.detection.audio -> app.audio -> app.detection.audio 순환 참조가 발생함.
# 실제 Audio 클래스가 필요한 메서드 내부에서 지연 임포트함(호출 시점엔 두 패키지 모두 로드가 끝난 뒤임).

class AudioDetectionRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_analysis_summary(self, audio_id: int) -> AudioFinalDetectionResult:
        """새로운 분석 요약 레코드를 생성함 (PENDING 상태)"""
        summary = AudioFinalDetectionResult(audio_id=audio_id, analysis_status=AudioAnalysisStatus.PENDING)
        self.db_session.add(summary)
        await self.db_session.flush()
        await self.db_session.commit()
        return summary

    async def get_analysis_summary_by_audio_id(self, audio_id: int) -> AudioFinalDetectionResult:
        """오디오 ID를 기준으로 분석 요약 레코드를 조회함"""
        stmt = select(AudioFinalDetectionResult).where(AudioFinalDetectionResult.audio_id == audio_id)
        result = await self.db_session.execute(stmt)
        return result.scalars().first()

    async def get_full_detection_result(self, audio_id: int) -> "Optional[Audio]":
        """오디오 ID를 기준으로 오디오 정보와 모든 분석 결과를 포함하여 조회함"""
        from app.audio.model.audio import Audio
        stmt = (
            select(Audio)
            .where(Audio.id == audio_id)
            .options(
                selectinload(Audio.analysis_summary),
                selectinload(Audio.model_results),
                selectinload(Audio.c2pa_result)
            )
        )
        result = await self.db_session.execute(stmt)
        return result.scalars().first()

    async def update_analysis_status(self, audio_id: int, status: AudioAnalysisStatus, **kwargs) -> None:
        """오디오 분석 상태 및 추가 필드(결과 등)를 업데이트함"""
        stmt = (
            update(AudioFinalDetectionResult)
            .where(AudioFinalDetectionResult.audio_id == audio_id)
            .values(analysis_status=status, **kwargs)
        )
        await self.db_session.execute(stmt)
        await self.db_session.commit()

    async def get_audio_status_and_check_owner(self, audio_id: int, user_id: int) -> str:
        """
        오디오 소유권을 확인하고 현재 분석 상태를 한 번에 조회함.
        (순환 참조 방지를 위해 AudioDetectionRepository에서 직접 수행)
        """
        from app.audio.model.audio import Audio
        stmt = (
            select(Audio, AudioFinalDetectionResult.analysis_status)
            .join(AudioFinalDetectionResult, Audio.id == AudioFinalDetectionResult.audio_id)
            .where(Audio.id == audio_id)
        )
        result = await self.db_session.execute(stmt)
        row = result.first()

        if not row:
            return None

        audio, status = row

        if audio.user_id != user_id:
            return "FORBIDDEN"

        return status

    async def save_c2pa_result(self, audio_id: int, data: dict) -> None:
        """C2PA 분석 결과를 저장함 (이미지 쪽 save_c2pa_result와 동일한 컬럼 구성)"""
        c2pa_result = AudioC2paAnalysisResult(
            audio_id=audio_id,
            is_c2pa_compliant=data.get("is_c2pa_compliant"),
            created_model=data.get("created_model"),
            converted_model=data.get("converted_model"),
            created_description=data.get("created_description"),
            claim_generator=data.get("claim_generator"),
            claim_generator_info_name=data.get("claim_generator_info_name"),
            synth_id=data.get("synth_id"),
            visible_watermark=data.get("visible_watermark"),
            total_digital_source_type=data.get("total_digital_source_type"),
            synth_id_digital_source_type=data.get("synth_id_digital_source_type"),
            visible_watermark_digital_source_type=data.get("visible_watermark_digital_source_type"),
        )
        self.db_session.add(c2pa_result)
        await self.db_session.commit()

    async def save_model_result(self, audio_id: int, data_list: list) -> None:
        """모델별 판별 결과들을 리스트 단위로 저장함"""
        for data in data_list:
            model_result = AudioModelDetectionResult(
                audio_id=audio_id,
                detection_method=data.get("detection_method"),
                confidence_score=data.get("confidence_score"),
                result_json=data.get("result_json")
            )
            self.db_session.add(model_result)
        await self.db_session.commit()
