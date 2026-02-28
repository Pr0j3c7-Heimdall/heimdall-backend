"""
UNet 다중 분류 추론 모듈
Stable Diffusion v1.5의 UNet 특징을 추출하여 이미지를 생성한 구체적인 AI 모델을 판별합니다.
"""

import torch
from PIL import Image
import numpy as np
from .UNet_utils import FeatureExtractor, get_transform
from .UNet_model import get_model

# 분석 가능한 AI 모델 클래스 정의
CLASS_NAMES = ["BigGAN", "Dalle-3", "Flux-1.1-pro", "Glide", "GPT-image-1", "Imagen-4.0", "Midjourney-V6", "Nano-Banana-Family", "SD3.5", "SDXL"]

class UNetMultiDetector:
    """UNet 특징 기반 AI 모델 판별기 클래스"""

    def __init__(self, weight_path: str):
        """
        판별기 초기화 및 모델 로드
        :param weight_path: 학습된 다중 분류 가중치 경로 (.pth)
        """
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        # SDM 특징 추출기 및 전처리 도구 로드
        self.extractor = FeatureExtractor(device=self.device)
        self.transform = get_transform()
        
        # 다중 분류 모델 로드 (출력 클래스 10개)
        self.model = get_model('mlp', input_dim=1280, num_classes=10)
        self.model.load(weight_path)

    def predict(self, image_path: str) -> dict:
        """이미지를 분석하여 어떤 AI 모델이 생성했는지 추론합니다."""
        try:
            # 이미지 로드 및 전처리
            image = Image.open(image_path).convert('RGB')
            img_tensor = self.transform(image).unsqueeze(0)
            
            # UNet 특징 추출
            features = self.extractor.extract_features_batch(img_tensor)
            
            # 클래스별 확률 계산
            prob_array = self.model.predict_proba(features)
            probs = prob_array[0]
            
            # 가장 높은 확률의 클래스 선택
            max_idx = np.argmax(probs)
            confidence = probs[max_idx]
            predicted_model = CLASS_NAMES[max_idx]
            
            return {
                "detection_method": "UNet",
                "predicted_model": predicted_model,
                "confidence_score": float(confidence),
                "result_json": {
                    "all_probabilities": {CLASS_NAMES[i]: float(probs[i]) for i in range(len(CLASS_NAMES))}
                }
            }
            
        except Exception as e:
            raise RuntimeError(f"UNet Multiclass Inference failed: {str(e)}")
