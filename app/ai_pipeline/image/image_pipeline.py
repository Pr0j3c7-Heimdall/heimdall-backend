"""
AI 이미지 검증 파이프라인 모듈
C2PA 분석, 이진 분류(AI 여부), 다중 분류(생성 모델 판별) 프로세스를 제어합니다.
"""

import os
import json
import torch
import asyncio
import logging
from typing import Optional, Callable, Dict, Any, List

try:
    from .c2pa.c2pa_analyzer import C2PAAnalyzer
except ImportError as e:
    logging.error(f"Import error (C2PAAnalyzer): {e}", exc_info=True)
    C2PAAnalyzer = None

try:
    from .metadata.metadata_extractor import extract_metadata
except ImportError as e:
    logging.error(f"Import error (extract_metadata): {e}", exc_info=True)
    extract_metadata = None

# --- AI 모델 임포트 ---

# DINOv3 Binary
try:
    from .binary.DINOv3.DINOv3_inference import Dinov3BinaryDetector
except ImportError as e:
    logging.error(f"Import error (Dinov3BinaryDetector): {e}", exc_info=True)
    Dinov3BinaryDetector = None

# F3Net Binary
try:
    from .binary.F3Net.F3Net_inference import F3NetBinaryDetector
except ImportError as e:
    logging.error(f"Import error (F3NetBinaryDetector): {e}", exc_info=True)
    F3NetBinaryDetector = None

# UNet Binary
try:
    from .binary.UNet.UNet_inference import UNetBinaryDetector
except ImportError as e:
    logging.error(f"Import error (UNetBinaryDetector): {e}", exc_info=True)
    UNetBinaryDetector = None

# DINOv3 Multiclass
try:
    from .multiclass.DINOv3.DINOv3_inference import Dinov3MultiDetector
except ImportError as e:
    logging.error(f"Import error (Dinov3MulticlassDetector): {e}", exc_info=True)
    Dinov3MulticlassDetector = None

# F3Net Multiclass
try:
    from .multiclass.F3Net.F3Net_inference import F3NetMultiDetector
except ImportError as e:
    logging.error(f"Import error (F3NetMulticlassDetector): {e}", exc_info=True)
    F3NetMultiDetector = None

# UNet Multiclass
try:
    from .multiclass.UNet.UNet_inference import UNetMultiDetector
except ImportError as e:
    logging.error(f"Import error (UNetMulticlassDetector): {e}", exc_info=True)
    UNetMultiDetector = None

# --- 모델 가중치 경로 설정 ---
DINOV3_WEIGHTS = "app/ai_pipeline/image/binary/DINOv3/weights/DINOv3_binary.pth"
F3NET_WEIGHTS = "app/ai_pipeline/image/binary/F3Net/weights/F3Net_binary.pth"
UNET_BINARY_WEIGHTS = "app/ai_pipeline/image/binary/UNet/weights/UNet_binary.pth"
DINOV3_MULTI_WEIGHTS = "app/ai_pipeline/image/multiclass/DINOv3/weights/DINOv3_multi.pth"
F3NET_MULTI_WEIGHTS = "app/ai_pipeline/image/multiclass/F3Net/weights/F3Net_multi.pth"
UNET_MULTI_WEIGHTS = "app/ai_pipeline/image/multiclass/UNet/weights/UNet_multi.pth"

# heimdall-image 리포지토리에서 검증 정확도 기반으로 산출한 이진분류 Soft Voting 가중치
_BINARY_FUSION_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fusion", "binary_fusion.json")

# --- 전역 변수로 모델 인스턴스 초기화 ---
dinov3_detector = None
f3net_detector = None
unet_detector = None
dinov3_multi_detector = None
f3net_multi_detector = None
unet_multi_detector = None
_binary_fusion: Optional[Dict[str, Any]] = None


def _load_binary_fusion() -> Dict[str, Any]:
    with open(_BINARY_FUSION_JSON, encoding="utf-8") as f:
        return json.load(f)


def init_models():
    """가중치 파일 존재 여부를 확인하여 각 AI 모델 인스턴스를 초기화합니다."""
    global dinov3_detector, f3net_detector, unet_detector, \
           dinov3_multi_detector, f3net_multi_detector, unet_multi_detector, \
           _binary_fusion

    try:
        _binary_fusion = _load_binary_fusion()
    except Exception as e:
        logging.error(f"Error loading binary_fusion.json: {e}", exc_info=True)

    # 1. Binary DINOv3
    try:
        if Dinov3BinaryDetector and os.path.exists(DINOV3_WEIGHTS):
            dinov3_detector = Dinov3BinaryDetector(weight_path=DINOV3_WEIGHTS)
    except Exception as e:
        logging.error(f"Error initializing Binary DINOv3: {e}", exc_info=True)

    # 2. Binary F3-Net
    try:
        if F3NetBinaryDetector and os.path.exists(F3NET_WEIGHTS):
            f3net_detector = F3NetBinaryDetector(weight_path=F3NET_WEIGHTS)
    except Exception as e:
        logging.error(f"Error initializing Binary F3-Net: {e}", exc_info=True)

    # 3. Multiclass DINOv3
    try:
        if Dinov3MultiDetector and os.path.exists(DINOV3_MULTI_WEIGHTS):
            dinov3_multi_detector = Dinov3MultiDetector(weight_path=DINOV3_MULTI_WEIGHTS)
    except Exception as e:
        logging.error(f"Error initializing Multiclass DINOv3: {e}", exc_info=True)

    # 4. Multiclass F3-Net
    try:
        if F3NetMultiDetector and os.path.exists(F3NET_MULTI_WEIGHTS):
            f3net_multi_detector = F3NetMultiDetector(weight_path=F3NET_MULTI_WEIGHTS)
    except Exception as e:
        logging.error(f"Error initializing Multiclass F3-Net: {e}", exc_info=True)

    # 5. Binary UNet
    try:
        if UNetBinaryDetector and os.path.exists(UNET_BINARY_WEIGHTS):
            unet_detector = UNetBinaryDetector(weight_path=UNET_BINARY_WEIGHTS)
    except Exception as e:
        logging.error(f"Error initializing Binary UNet: {e}", exc_info=True)

    # 6. Multiclass UNet
    try:
        if UNetMultiDetector and os.path.exists(UNET_MULTI_WEIGHTS):
            unet_multi_detector = UNetMultiDetector(weight_path=UNET_MULTI_WEIGHTS)
    except Exception as e:
        logging.error(f"Error initializing Multiclass UNet: {e}", exc_info=True)

init_models()

async def run_c2pa_analysis(image_path: str) -> Dict[str, Any]:
    """C2PA 정보를 분석하여 변조 여부 및 출처 정보를 반환합니다."""
    if C2PAAnalyzer:
        try:
            # 동기 함수 블로킹 방지를 위해 별도의 스레드(executor)에서 실행
            return await asyncio.get_event_loop().run_in_executor(None, C2PAAnalyzer.analyze_file, image_path)
        except Exception as e:
            logging.error(f"C2PA Analysis Error: {e}", exc_info=True)
    
    return {
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
        "visible_watermark_digital_source_type": None
    }

_BINARY_DETECTOR_NAMES = {
    "DINOv3": lambda: dinov3_detector,
    "F3-Net": lambda: f3net_detector,
    "UNet": lambda: unet_detector,
}


async def run_binary_detection(image_path: str) -> Dict[str, Any]:
    """DINOv3, F3-Net, UNet 모델을 실행해 confidence_score를 구하고,
    binary_fusion.json의 고정 가중치(Soft Voting)로 결합해 최종 판정을 낸다."""
    if _binary_fusion is None:
        raise RuntimeError("binary_fusion.json이 로드되지 않았습니다. init_models()를 확인하세요.")

    order = _binary_fusion["models"]
    missing = [name for name in order if _BINARY_DETECTOR_NAMES[name]() is None]
    if missing:
        raise RuntimeError(f"다음 모델의 가중치가 로드되지 않았습니다: {missing}")

    results = []
    raw_scores: Dict[str, float] = {}
    for name in order:
        detector = _BINARY_DETECTOR_NAMES[name]()
        res = await asyncio.to_thread(detector.predict, image_path)
        results.append(res)
        raw_scores[name] = res["confidence_score"]

    weights = _binary_fusion["weights"]
    avg_ai_prob = sum(weights[name] * raw_scores[name] for name in order)
    final_is_ai = avg_ai_prob >= 0.5

    return {
        "binary_list": results,
        "avg_ai_prob": avg_ai_prob,
        "final_is_ai": final_is_ai
    }

async def run_multiclass_detection(image_path: str) -> List[Dict[str, Any]]:
    """다중 분류 모델을 실행하여 이미지를 생성한 구체적인 AI 모델을 판별합니다."""
    results = []
    
    # 1. DINOv3 다중 분류
    if dinov3_multi_detector:
        try:
            res_dino = await asyncio.to_thread(dinov3_multi_detector.predict, image_path)
            results.append(res_dino)
        except Exception as e:
            logging.error(f"DINOv3 Multiclass Error: {e}", exc_info=True)
            
    # 2. F3Net 다중 분류
    if f3net_multi_detector:
        try:
            res_f3 = await asyncio.to_thread(f3net_multi_detector.predict, image_path)
            results.append(res_f3)
        except Exception as e:
            logging.error(f"F3Net Multiclass Error: {e}", exc_info=True)

    # 3. UNet 다중 분류
    if unet_multi_detector:
        try:
            res_unet = await asyncio.to_thread(unet_multi_detector.predict, image_path)
            results.append(res_unet)
        except Exception as e:
            logging.error(f"UNet Multiclass Error: {e}", exc_info=True)
            
    return results

async def execute_image_pipeline(image_path: str, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
    """
    이미지 검증 전체 파이프라인을 실행합니다.
    C2PA 분석 -> (선택적) 이진 분류 -> (AI 판정 시) 다중 분류 / (현실 사진 판정 시) 메타데이터 추출 순으로 진행됩니다.
    """
    pipeline_result = {
        "c2pa": None,
        "binary": [],
        "multi": [],
        "metadata": None,
        "final_result": {}
    }

    # 1단계: C2PA 분석
    if progress_callback:
        await progress_callback(status="C2PA_PROCESSING")

    c2pa_data = await run_c2pa_analysis(image_path)
    pipeline_result["c2pa"] = c2pa_data

    if progress_callback:
        await progress_callback(status="C2PA_COMPLETED", data={"c2pa": c2pa_data})

    # 판정 변수 초기화
    final_is_ai = False
    avg_ai_prob = 0.0
    is_c2pa_compliant = c2pa_data.get("is_c2pa_compliant", False)

    if is_c2pa_compliant:
        # C2PA 충족 시 이진 분류를 건너뛰고 AI로 확정 판정
        final_is_ai = True
        avg_ai_prob = 1.0
    else:
        # 2단계: 이진 분류 (AI 여부 판정)
        if progress_callback:
            await progress_callback(status="BINARY_PROCESSING")

        binary_res = await run_binary_detection(image_path)
        pipeline_result["binary"] = binary_res["binary_list"]
        final_is_ai = binary_res["final_is_ai"]
        avg_ai_prob = binary_res["avg_ai_prob"]

        if progress_callback:
            await progress_callback(status="BINARY_COMPLETED", data={"binary": binary_res["binary_list"]})

    # 3단계: 다중 분류 또는 메타데이터 추출
    requires_multiclass = False
    final_generator_model = None

    if final_is_ai:
        if progress_callback:
            await progress_callback(status="MULTICLASS_PROCESSING", data=None)

        multi_res = await run_multiclass_detection(image_path)
        pipeline_result["multi"] = multi_res
        requires_multiclass = True

        # 신뢰도(confidence_score)가 가장 높은 모델을 최종 결과로 선택
        if multi_res:
            best_res = max(multi_res, key=lambda x: x["confidence_score"])
            final_generator_model = best_res["predicted_model"]

        if progress_callback:
            await progress_callback(status="MULTICLASS_COMPLETED", data={"multi": multi_res})
    else:
        # 현실 사진으로 판정되었을 때 메타데이터 추출
        if extract_metadata:
            if progress_callback:
                await progress_callback(status="METADATA_PROCESSING")

            metadata_res = await extract_metadata(image_path)
            pipeline_result["metadata"] = metadata_res

            if progress_callback:
                await progress_callback(status="METADATA_COMPLETED", data={"metadata": metadata_res})

    # 최종 결과 취합
    pipeline_result["final_result"] = {
        "final_is_ai": final_is_ai,
        "final_ai_probability": avg_ai_prob,
        "requires_multiclass": requires_multiclass,
        "final_generator_model": final_generator_model
    }

    return pipeline_result