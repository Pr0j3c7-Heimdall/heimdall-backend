"""
DINOv3 다중 분류 추론 모듈
DINOv3 특징 추출기를 사용하여 이미지를 생성한 구체적인 AI 모델(Dalle-3, Midjourney 등)을 판별합니다.
"""

import os
import torch
import torchvision.transforms as T
from PIL import Image
from transformers import AutoModel
from .DINOv3_model import DINOMlpClassifier

# 분석 가능한 AI 모델 클래스 정의
CLASS_NAMES = ["BigGAN", "Dalle-3", "Flux-1.1-pro", "Glide", "GPT-image-1", "Imagen-4.0", "Midjourney-V6", "Nano-Banana-Family", "SD3.5", "SDXL"]

class Dinov3MultiDetector:
    """DINOv3 기반 AI 모델 판별기 클래스"""

    def __init__(self, weight_path: str, crop_type: str = '5crop', res: int = 224):
        """
        판별기 초기화 및 다중 분류 모델 로드
        :param weight_path: 학습된 다중 분류 MLP 가중치 경로
        :param crop_type: 전처리 방식 ('center' 또는 '5crop')
        :param res: 이미지 리사이즈 해상도
        """
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.crop_type = crop_type
        self.res = res
        
        # DINOv3 특징 추출기 로드
        self.feature_extractor = AutoModel.from_pretrained("facebook/dinov3-vitl16-pretrain-lvd1689m").to(self.device)
        self.feature_extractor.eval()
        
        # 전처리 Transform 설정
        self.transform = self._get_transform(self.crop_type, self.res)
        
        # MLP 분류기 로드 (출력 클래스 10개)
        self.mlp_classifier = DINOMlpClassifier(input_dim=1024, num_classes=10).to(self.device)
        self.mlp_classifier.load_state_dict(torch.load(weight_path, map_location=self.device, weights_only=True))
        self.mlp_classifier.eval()

    def _get_transform(self, crop_type: str, res: int):
        """이미지 전처리 파이프라인 생성"""
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
        """이미지를 분석하여 어떤 AI 모델이 생성했는지 추론합니다."""
        try:
            # 이미지 로드 및 전처리
            img = Image.open(image_path).convert('RGB')
            img_tensor = self.transform(img).to(self.device)
            
            with torch.no_grad():
                # 특징 추출
                if self.crop_type == '5crop':
                    n, c, h, w = img_tensor.shape
                    outputs = self.feature_extractor(img_tensor)
                    features = outputs.last_hidden_state[:, 0]
                    logits = self.mlp_classifier(features)
                    logits = logits.mean(dim=0, keepdim=True)
                else:
                    img_tensor = img_tensor.unsqueeze(0)
                    outputs = self.feature_extractor(img_tensor)
                    features = outputs.last_hidden_state[:, 0]
                    logits = self.mlp_classifier(features)
                
                # 클래스별 확률 계산
                probs = torch.softmax(logits, dim=1)[0]
                confidence, predicted_idx = torch.max(probs, dim=0)
                predicted_model = CLASS_NAMES[predicted_idx.item()]
                
            return {
                "detection_method": "DINOv3",
                "predicted_model": predicted_model,
                "confidence_score": confidence.item(),
                "result_json": {
                    "crop_type": self.crop_type,
                    "all_probabilities": {CLASS_NAMES[i]: probs[i].item() for i in range(10)}
                }
            }
            
        except Exception as e:
            raise RuntimeError(f"DINOv3 Multiclass Inference failed: {str(e)}")
