"""
DINOv3 이진 분류 추론 모듈
Facebook의 DINOv3 ViT-L/16 모델을 특징 추출기로 사용하고, 학습된 MLP 분류기를 통해 AI 생성 여부를 판별합니다.
"""

import os
import torch
import torchvision.transforms as T
from PIL import Image
from transformers import AutoModel
from .DINOv3_model import DINOMlpClassifier

class Dinov3BinaryDetector:
    """DINOv3 기반 AI 이미지 탐지기 클래스"""

    def __init__(self, weight_path: str, crop_type: str = '5crop', res: int = 224, threshold: float = 0.5):
        """
        탐지기 초기화 및 모델 로드
        :param weight_path: 학습된 MLP 분류기 가중치 경로
        :param crop_type: 전처리 방식 ('center' 또는 '5crop')
        :param res: 이미지 리사이즈 해상도
        :param threshold: AI 판정 임계값
        """
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.crop_type = crop_type
        self.threshold = threshold
        self.res = res
        
        # DINOv3 특징 추출기(Backbone) 로드
        self.feature_extractor = AutoModel.from_pretrained("facebook/dinov3-vitl16-pretrain-lvd1689m").to(self.device)
        self.feature_extractor.eval()
        
        # 전처리 Transform 설정
        self.transform = self._get_transform(self.crop_type, self.res)
        
        # MLP 분류기 로드 및 가중치 적용
        self.mlp_classifier = DINOMlpClassifier(input_dim=1024, num_classes=2).to(self.device)
        self.mlp_classifier.load_state_dict(torch.load(weight_path, map_location=self.device, weights_only=True))
        self.mlp_classifier.eval()

    def _get_transform(self, crop_type: str, res: int):
        """DINOv3 입력 규격에 맞는 전처리 파이프라인을 생성합니다."""
        norm = T.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))
        if crop_type == 'center':
            return T.Compose([T.Resize(256, interpolation=3), T.CenterCrop(res), T.ToTensor(), norm])
        elif crop_type == '5crop':
            return T.Compose([
                T.Resize(256, interpolation=3),
                T.FiveCrop(res),
                T.Lambda(lambda crops: torch.stack([norm(T.ToTensor()(crop)) for crop in crops]))
            ])

    def predict(self, image_path: str) -> dict:
        """단일 이미지에 대해 AI 생성 여부를 추론합니다."""
        try:
            # 이미지 로드 및 전처리
            img = Image.open(image_path).convert('RGB')
            img_tensor = self.transform(img).to(self.device)
            
            with torch.no_grad():
                # Backbone을 통한 특징 추출 (CLS 토큰 활용)
                if self.crop_type == '5crop':
                    # 5-Crop 처리: 각 크롭 영역의 특징을 추출 후 평균 계산
                    n, c, h, w = img_tensor.shape
                    outputs = self.feature_extractor(img_tensor)
                    features = outputs.last_hidden_state[:, 0] # (5, 1024)
                    
                    # MLP 추론 및 결과 앙상블
                    logits = self.mlp_classifier(features) # (5, 2)
                    logits = logits.mean(dim=0, keepdim=True) # (1, 2)
                else:
                    img_tensor = img_tensor.unsqueeze(0)
                    outputs = self.feature_extractor(img_tensor)
                    features = outputs.last_hidden_state[:, 0] # (1, 1024)
                    
                    logits = self.mlp_classifier(features)
                
                # 확률 계산 및 최종 판정
                probs = torch.softmax(logits, dim=1)
                fake_prob = probs[0, 1].item()
                is_fake = bool(fake_prob >= self.threshold)
                
            return {
                "detection_method": "DINOv3",
                "is_detected": is_fake,
                "confidence_score": fake_prob,
                "result_json": {
                    "crop_type": self.crop_type,
                    "real_prob": probs[0, 0].item(),
                    "fake_prob": fake_prob
                }
            }
            
        except Exception as e:
            raise RuntimeError(f"DINOv3 Inference failed: {str(e)}")
