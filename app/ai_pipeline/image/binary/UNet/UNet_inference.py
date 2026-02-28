"""
UNet 이진 분류 추론 모듈
Stable Diffusion v1.5의 UNet 디코더 특징을 추출하고, MLP 분류기를 통해 AI 생성 여부를 판별합니다.
"""

import torch
from PIL import Image
import numpy as np
from .UNet_utils import FeatureExtractor, get_transform
from .UNet_model import get_model

class UNetBinaryDetector:
    """UNet 특징 기반 AI 이미지 탐지기 클래스"""

    def __init__(self, weight_path: str, threshold: float = 0.5):
        """
        탐지기 초기화 및 모델 로드
        :param weight_path: 학습된 MLP 분류기 가중치 경로 (.pth)
        :param threshold: AI 판정 임계값
        """
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        # SDM 특징 추출기 및 전처리 도구 로드
        self.extractor = FeatureExtractor(device=self.device)
        self.transform = get_transform()
        
        # MLP 모델 로드 (UNet 특징 차원 1280)
        self.model = get_model('mlp', input_dim=1280)
        self.model.load(weight_path)
        self.threshold = threshold

    def predict(self, image_path: str) -> dict:
        """단일 이미지에 대해 UNet 특징 기반 AI 여부 추론을 수행합니다."""
        try:
            # 이미지 로드 및 전처리
            image = Image.open(image_path).convert('RGB')
            img_tensor = self.transform(image).unsqueeze(0)
            
            # UNet 디코더 특징 추출
            features = self.extractor.extract_features_batch(img_tensor)
            
            # 확률 계산
            probs = self.model.predict_proba(features)
            fake_prob = float(probs[0])
            is_fake = bool(fake_prob >= self.threshold)
            
            return {
                "detection_method": "UNet",
                "is_detected": is_fake,
                "confidence_score": fake_prob,
                "result_json": {
                    "real_prob": 1.0 - fake_prob,
                    "fake_prob": fake_prob
                }
            }
            
        except Exception as e:
            raise RuntimeError(f"UNet Inference failed: {str(e)}")
