"""오디오 C2PA 분석.

분석 자체는 이미지와 동일한 C2PAAnalyzer를 사용한다. c2patool이 포맷을 판별하고
매니페스트 구조는 포맷과 무관하므로, 오디오 전용 분석 로직은 필요하지 않다.
음성/가창 트랙과도 무관하여 두 파이프라인 공통으로 이 모듈을 쓴다.
"""

import asyncio
import logging
from typing import Any, Dict

try:
    from app.ai_pipeline.image.c2pa.c2pa_analyzer import C2PAAnalyzer
except ImportError as e:  # 가중치/툴 미배치 등으로 임포트가 실패해도 서비스는 떠야 한다
    logging.error(f"Import error (C2PAAnalyzer): {e}", exc_info=True)
    C2PAAnalyzer = None

_NOT_ANALYZED: Dict[str, Any] = {
    "is_c2pa_compliant": False,
    "created_model": None,
    "converted_model": None,
    "created_description": None,
    "claim_generator": None,
    "claim_generator_info_name": None,
    "synth_id": None,
    "visible_watermark": None,
    "total_digital_source_type": None,
    "synth_id_digital_source_type": None,
    "visible_watermark_digital_source_type": None,
}


async def run_c2pa_analysis(audio_path: str) -> Dict[str, Any]:
    """오디오 파일의 C2PA 매니페스트를 분석한다.

    c2patool 실행은 동기 블로킹이므로 스레드로 오프로드한다.
    매니페스트가 없거나 검증에 실패하면 is_c2pa_compliant=False가 반환되며,
    이 경우 호출부는 기존대로 판별 모델로 진행하면 된다.
    """
    if not C2PAAnalyzer:
        logging.warning("C2PA: 분석기를 사용할 수 없어 오디오 C2PA 분석을 건너뜁니다.")
        return dict(_NOT_ANALYZED)

    try:
        return await asyncio.to_thread(C2PAAnalyzer.analyze_file, audio_path)
    except Exception as e:
        logging.error(f"C2PA: 오디오 분석 중 오류: {e}", exc_info=True)
        return dict(_NOT_ANALYZED)
