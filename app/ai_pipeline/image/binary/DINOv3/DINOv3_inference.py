import os
import torch
import torchvision.transforms as T
from PIL import Image
from transformers import AutoModel
from .DINOv3_mlp_model import DINOMlpClassifier # 기존 파일 임포트

class Dinov3BinaryDetector:
    def __init__(self, weight_path: str, crop_type: str = '5crop', res: int = 224, threshold: float = 0.5):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.crop_type = crop_type
        self.threshold = threshold
        self.res = res
        
        # 1. Hugging Face DINOv3 특징 추출기 로드
        self.feature_extractor = AutoModel.from_pretrained("facebook/dinov3-vitl16-pretrain-lvd1689m").to(self.device)
        self.feature_extractor.eval()
        
        # 2. 전처리 Transform 설정 (기존 코드 활용)
        self.transform = self._get_transform(self.crop_type, self.res)
        
        # 3. MLP 분류기 로드
        self.mlp_classifier = DINOMlpClassifier(input_dim=1024, num_classes=2).to(self.device)
        self.mlp_classifier.load_state_dict(torch.load(weight_path, map_location=self.device))
        self.mlp_classifier.eval()

    def _get_transform(self, crop_type, res):
        """기존 extract_features.py의 전처리 로직 그대로 사용"""
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
        """API에서 호출할 단일 이미지 추론 메서드"""
        try:
            # 1. 이미지 로드 및 전처리
            img = Image.open(image_path).convert('RGB')
            img_tensor = self.transform(img).to(self.device)
            
            with torch.no_grad():
                # 2. 특징 추출 (Feature Extraction)
                if self.crop_type == '5crop':
                    # 5crop의 경우 차원(b, n, c, h, w) 처리
                    n, c, h, w = img_tensor.shape
                    outputs = self.feature_extractor(img_tensor)
                    features = outputs.last_hidden_state[:, 0] # CLS token (5, 1024)
                    
                    # 3. MLP 추론
                    logits = self.mlp_classifier(features) # (5, 2)
                    logits = logits.mean(dim=0, keepdim=True) # 5개 결과의 평균 (1, 2)
                else:
                    img_tensor = img_tensor.unsqueeze(0) # 배치 차원 추가 (1, c, h, w)
                    outputs = self.feature_extractor(img_tensor)
                    features = outputs.last_hidden_state[:, 0] # (1, 1024)
                    
                    # 3. MLP 추론
                    logits = self.mlp_classifier(features)
                
                # 4. 확률 및 판별 (기존 test.py 로직)
                probs = torch.softmax(logits, dim=1)
                fake_prob = probs[0, 1].item()
                is_fake = bool(fake_prob >= self.threshold)
                
            return {
                # 테이블보고 판단
                "detection_method": "DINOv3_MLP",
                "is_detected": is_fake,
                "confidence_score": fake_prob,
                "result_json": {
                    "crop_type": self.crop_type,
                    "real_prob": probs[0, 0].item(),
                    "fake_prob": fake_prob
                }
            }
            
        except Exception as e:
            # 로깅 처리 필요
            raise RuntimeError(f"DINOv3 Inference failed: {str(e)}")