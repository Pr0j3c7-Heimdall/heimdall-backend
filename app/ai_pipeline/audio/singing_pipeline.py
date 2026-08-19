"""
AI 가창 판별 파이프라인 모듈 (가창 트랙 전용).
AASIST(plain), RawNet3, LFCC-LCNN 3개 모델을 앙상블(simple_mean)하여 판정한다.

speech_pipeline.py와 동일한 설계 — 모델별 raw_score를 Platt scaling으로 보정한 뒤,
fusion JSON의 "method"에 따라 결합한다(공용 로직은 common/fusion_combine.py).

음성(Speech) 트랙은 모델 구성이 다르고, 음성/가창을 나누는 YAMNet 라우팅도 아직 구현되지
않아(임계값 미확정) 이 파이프라인은 현재 가창 트랙만 다룬다.
"""
import json
import logging
import os
from typing import Any, Dict, Optional

from app.ai_pipeline.audio.singing.AASIST.AASIST_inference import AasistDetector
from app.ai_pipeline.audio.common.RawNet3.RawNet3_inference import RawNet3Detector
from app.ai_pipeline.audio.singing.LCNN.LCNN_inference import LcnnDetector
from app.ai_pipeline.audio.common.fusion_combine import calibrate, combine_scores

# --- 모델 가중치 경로 설정 (이미지 파이프라인과 동일한 컨벤션: /shared_data 공용 볼륨에서 심볼릭 링크) ---
# RawNet3는 음성/가창 두 트랙이 아키텍처를 공유해 common/에 있음 (체크포인트만 트랙별로 다름)
AASIST_WEIGHTS = "app/ai_pipeline/audio/singing/AASIST/weights/AASIST_singing.pth"
RAWNET3_WEIGHTS = "app/ai_pipeline/audio/common/RawNet3/weights/RawNet3_singing.pth"
LCNN_WEIGHTS = "app/ai_pipeline/audio/singing/LCNN/weights/LFCC-LCNN_singing.pth"

_FUSION_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fusion", "singing_fusion.json")

# --- 전역 변수로 모델 인스턴스 초기화 (이미지 파이프라인과 동일하게 프로세스당 1회 로드) ---
aasist_detector: Optional[AasistDetector] = None
rawnet3_detector: Optional[RawNet3Detector] = None
lcnn_detector: Optional[LcnnDetector] = None
_singing_fusion: Optional[Dict[str, Any]] = None


def _load_singing_fusion() -> Dict[str, Any]:
    with open(_FUSION_JSON, encoding="utf-8") as f:
        fusion = json.load(f)
    if fusion["track"] != "singing":
        raise ValueError(f"singing_fusion.json이 아닙니다: track={fusion['track']!r}")
    return fusion


def init_models() -> None:
    """가중치 파일 존재 여부를 확인하여 각 모델 인스턴스와 fusion 파라미터를 초기화한다."""
    global aasist_detector, rawnet3_detector, lcnn_detector, _singing_fusion

    try:
        _singing_fusion = _load_singing_fusion()
    except Exception as e:
        logging.error(f"Error loading singing_fusion.json: {e}", exc_info=True)

    try:
        if os.path.exists(AASIST_WEIGHTS):
            aasist_detector = AasistDetector(weight_path=AASIST_WEIGHTS)
    except Exception as e:
        logging.error(f"Error initializing AASIST(plain): {e}", exc_info=True)

    try:
        if os.path.exists(RAWNET3_WEIGHTS):
            rawnet3_detector = RawNet3Detector(weight_path=RAWNET3_WEIGHTS)
    except Exception as e:
        logging.error(f"Error initializing RawNet3: {e}", exc_info=True)

    try:
        if os.path.exists(LCNN_WEIGHTS):
            lcnn_detector = LcnnDetector(weight_path=LCNN_WEIGHTS)
    except Exception as e:
        logging.error(f"Error initializing LFCC-LCNN: {e}", exc_info=True)


init_models()


_DETECTOR_NAMES = {
    "AASIST": lambda: aasist_detector,
    "RawNet3": lambda: rawnet3_detector,
    "LCNN": lambda: lcnn_detector,
}


async def run_singing_detection(audio_path: str) -> Dict[str, Any]:
    """가창 트랙 3개 모델을 실행해 raw_score를 구하고, fusion 파라미터로 결합해 최종 판정을 낸다."""
    if _singing_fusion is None:
        raise RuntimeError("singing_fusion.json이 로드되지 않았습니다. init_models()를 확인하세요.")

    order = _singing_fusion["models"]
    missing = [name for name in order if _DETECTOR_NAMES[name]() is None]
    if missing:
        raise RuntimeError(f"다음 모델의 가중치가 로드되지 않았습니다: {missing}")

    raw_scores: Dict[str, float] = {}
    for name in order:
        detector = _DETECTOR_NAMES[name]()
        raw_scores[name] = detector.predict(audio_path)

    calibrated = calibrate(raw_scores, _singing_fusion, order)
    final_prob = combine_scores(calibrated, _singing_fusion, order)

    return {
        "singing_list": [
            {
                "detection_method": name,
                "confidence_score": calibrated[name],
                "result_json": {"raw_score": raw_scores[name]},
            }
            for name in order
        ],
        "final_ai_probability": final_prob,
        "final_is_ai": final_prob >= 0.5,
    }
