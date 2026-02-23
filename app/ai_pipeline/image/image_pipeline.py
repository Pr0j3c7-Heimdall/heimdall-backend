import os
import torch
import asyncio
from typing import Optional, Callable, Dict, Any, List

# AI 모델 임포트
try:
    from .binary.DINOv3.DINOv3_inference import Dinov3BinaryDetector
    from .binary.F3Net.F3Net_inference import F3NetBinaryDetector
except ImportError as e:
    print(f"Import error in image_pipeline: {e}")
    # 파일명 불일치 이슈가 있을 경우를 대비해 예외 처리 및 추후 수정 가능성 열어둠

# 모델 가중치 경로
DINOV3_WEIGHTS = "app/ai_pipeline/image/binary/DINOv3/weights/dinov3_mlp.pth"
F3NET_WEIGHTS = "app/ai_pipeline/image/binary/F3Net/weights/F3Net.pth"

# 전역 변수로 모델 초기화
dinov3_detector = None
f3net_detector = None

try:
    if os.path.exists(DINOV3_WEIGHTS):
        dinov3_detector = Dinov3BinaryDetector(weight_path=DINOV3_WEIGHTS)
    if os.path.exists(F3NET_WEIGHTS):
        f3net_detector = F3NetBinaryDetector(weight_path=F3NET_WEIGHTS)
except Exception as e:
    print(f"Error initializing AI models: {e}")

async def run_c2pa_analysis(image_path: str) -> Dict[str, Any]:
    """C2PA 분석 모의(Mock) 함수"""
    # 현재는 로직이 없으므로 기본값 반환
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

async def run_binary_detection(image_path: str) -> Dict[str, Any]:
    """DINOv3와 F3-Net 추론 실행 및 결과 취합"""
    results = []
    
    # 1. DINOv3 실행
    if dinov3_detector:
        res_dino = dinov3_detector.predict(image_path)
        results.append(res_dino)
    
    # 2. F3-Net 실행
    if f3net_detector:
        res_f3 = f3net_detector.predict(image_path)
        results.append(res_f3)
    
    if not results:
        return {"binary_list": [], "avg_ai_prob": 0.0, "final_is_ai": False}

    # 평균 점수 계산
    avg_ai_prob = sum(r["confidence_score"] for r in results) / len(results)
    final_is_ai = avg_ai_prob >= 0.5
    
    return {
        "binary_list": results,
        "avg_ai_prob": avg_ai_prob,
        "final_is_ai": final_is_ai
    }

async def run_multiclass_detection(image_path: str) -> List[Dict[str, Any]]:
    """다중 분류 모의(Mock) 함수"""
    return []

async def execute_image_pipeline(image_path: str, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
    """전체 AI 검증 파이프라인 제어 (Step 1 ~ Step 4)"""
    pipeline_result = {
        "c2pa": None,
        "binary": [],
        "multi": [],
        "final_result": {}
    }

    # (Step 1) C2PA 분석
    if progress_callback:
        await progress_callback(status="C2PA_PROCESSING")
    
    c2pa_data = await run_c2pa_analysis(image_path)
    pipeline_result["c2pa"] = c2pa_data
    
    if progress_callback:
        await progress_callback(status="C2PA_COMPLETED", data={"c2pa": c2pa_data})

    # (Step 2) C2PA 충족 시 조기 종료
    if c2pa_data.get("is_c2pa_compliant"):
        pipeline_result["final_result"] = {
            "final_is_ai": False,
            "final_ai_probability": 0.0,
            "requires_multiclass": False
        }
        return pipeline_result

    # (Step 3) Binary Detection
    if progress_callback:
        await progress_callback(status="BINARY_PROCESSING")
    
    binary_res = await run_binary_detection(image_path)
    pipeline_result["binary"] = binary_res["binary_list"]
    
    if progress_callback:
        await progress_callback(status="BINARY_COMPLETED", data={"binary": binary_res["binary_list"]})

    # (Step 4) AI 판정 시 Multiclass Detection 진행
    final_is_ai = binary_res["final_is_ai"]
    requires_multiclass = False
    
    if final_is_ai:
        if progress_callback:
            await progress_callback(status="MULTICLASS_PROCESSING")
        
        multi_res = await run_multiclass_detection(image_path)
        pipeline_result["multi"] = multi_res
        requires_multiclass = True
        
        if progress_callback:
            await progress_callback(status="MULTICLASS_COMPLETED")

    # 최종 결과 요약 세팅
    pipeline_result["final_result"] = {
        "final_is_ai": final_is_ai,
        "final_ai_probability": binary_res["avg_ai_prob"],
        "requires_multiclass": requires_multiclass
    }

    return pipeline_result
