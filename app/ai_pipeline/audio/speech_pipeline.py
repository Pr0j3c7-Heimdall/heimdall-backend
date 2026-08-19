"""
AI 음성 판별 파이프라인 모듈 (음성 트랙 전용).
SSL-AASIST, RawNet3, CQCC-SSL-AASIST 3개 모델을 앙상블(soft_voting)하여 판정한다.

heimdall-vox의 fusion/predict_speech.py와 동일한 설계를 따른다 — 모델별 raw_score를
Platt scaling으로 보정한 뒤, fusion JSON의 "method"에 따라 결합한다. method를 하드코딩하지
않고 JSON에서 분기하는 이유는 heimdall-vox 쪽 K-Fold 재검증 결과에 따라 최종 방식이 이미
한 번 바뀐 적이 있어서다(logreg_C10.0 -> soft_voting, FUSION.md 참고).

가창(Singing) 트랙은 모델 구성이 다르고, 음성/가창을 나누는 YAMNet 라우팅도 아직 구현되지
않아(임계값 미확정) 이 파이프라인은 현재 음성 트랙만 다룬다.
"""
import json
import logging
import os
from typing import Any, Dict, Optional

from app.ai_pipeline.audio.speech.SSL_AASIST.SSL_AASIST_inference import SSLAasistDetector
from app.ai_pipeline.audio.common.RawNet3.RawNet3_inference import RawNet3Detector
from app.ai_pipeline.audio.speech.CQCC_SSL_AASIST.CQCC_SSL_AASIST_inference import CqccSslAasistDetector
from app.ai_pipeline.audio.common.fusion_combine import calibrate, combine_scores

# --- 모델 가중치 경로 설정 (이미지 파이프라인과 동일한 컨벤션: /shared_data 공용 볼륨에서 심볼릭 링크) ---
# RawNet3는 음성/가창 두 트랙이 아키텍처를 공유해 common/에 있음 (체크포인트만 트랙별로 다름)
SSL_AASIST_WEIGHTS = "app/ai_pipeline/audio/speech/SSL_AASIST/weights/SSL_AASIST_speech.pth"
RAWNET3_WEIGHTS = "app/ai_pipeline/audio/common/RawNet3/weights/RawNet3_speech.pth"
CQCC_SSL_AASIST_WEIGHTS = "app/ai_pipeline/audio/speech/CQCC_SSL_AASIST/weights/CQCC_SSL_AASIST_speech.pth"

_FUSION_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fusion", "speech_fusion.json")

# --- 전역 변수로 모델 인스턴스 초기화 (이미지 파이프라인과 동일하게 프로세스당 1회 로드) ---
ssl_aasist_detector: Optional[SSLAasistDetector] = None
rawnet3_detector: Optional[RawNet3Detector] = None
cqcc_ssl_aasist_detector: Optional[CqccSslAasistDetector] = None
_speech_fusion: Optional[Dict[str, Any]] = None


def _load_speech_fusion() -> Dict[str, Any]:
    with open(_FUSION_JSON, encoding="utf-8") as f:
        fusion = json.load(f)
    if fusion["track"] != "speech":
        raise ValueError(f"speech_fusion.json이 아닙니다: track={fusion['track']!r}")
    return fusion


def init_models() -> None:
    """가중치 파일 존재 여부를 확인하여 각 모델 인스턴스와 fusion 파라미터를 초기화한다."""
    global ssl_aasist_detector, rawnet3_detector, cqcc_ssl_aasist_detector, _speech_fusion

    try:
        _speech_fusion = _load_speech_fusion()
    except Exception as e:
        logging.error(f"Error loading speech_fusion.json: {e}", exc_info=True)

    try:
        if os.path.exists(SSL_AASIST_WEIGHTS):
            ssl_aasist_detector = SSLAasistDetector(weight_path=SSL_AASIST_WEIGHTS)
    except Exception as e:
        logging.error(f"Error initializing SSL-AASIST: {e}", exc_info=True)

    try:
        if os.path.exists(RAWNET3_WEIGHTS):
            rawnet3_detector = RawNet3Detector(weight_path=RAWNET3_WEIGHTS)
    except Exception as e:
        logging.error(f"Error initializing RawNet3: {e}", exc_info=True)

    try:
        if os.path.exists(CQCC_SSL_AASIST_WEIGHTS):
            cqcc_ssl_aasist_detector = CqccSslAasistDetector(weight_path=CQCC_SSL_AASIST_WEIGHTS)
    except Exception as e:
        logging.error(f"Error initializing CQCC-SSL-AASIST: {e}", exc_info=True)


init_models()


_DETECTOR_NAMES = {
    "SSL-AASIST": lambda: ssl_aasist_detector,
    "RawNet3": lambda: rawnet3_detector,
    "CQCC-SSL-AASIST": lambda: cqcc_ssl_aasist_detector,
}


async def run_speech_detection(audio_path: str) -> Dict[str, Any]:
    """음성 트랙 3개 모델을 실행해 raw_score를 구하고, fusion 파라미터로 결합해 최종 판정을 낸다.
    가중치가 없어 로드되지 않은 모델은 건너뛴다(이미지 파이프라인의 각 detector가
    None일 때 건너뛰는 것과 동일한 방식) — 단, fusion 결합은 3개 모델 점수를 전제로
    fit됐으므로 하나라도 빠지면 계산하지 않고 예외를 낸다."""
    if _speech_fusion is None:
        raise RuntimeError("speech_fusion.json이 로드되지 않았습니다. init_models()를 확인하세요.")

    order = _speech_fusion["models"]
    missing = [name for name in order if _DETECTOR_NAMES[name]() is None]
    if missing:
        raise RuntimeError(f"다음 모델의 가중치가 로드되지 않았습니다: {missing}")

    raw_scores: Dict[str, float] = {}
    for name in order:
        detector = _DETECTOR_NAMES[name]()
        raw_scores[name] = detector.predict(audio_path)

    calibrated = calibrate(raw_scores, _speech_fusion, order)
    final_prob = combine_scores(calibrated, _speech_fusion, order)

    return {
        "speech_list": [
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
