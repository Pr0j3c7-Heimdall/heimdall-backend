import os
import torch
import torchvision.transforms as T
from PIL import Image
from transformers import AutoModel
from .DINOv3_mlp_model import DINOMlpClassifier

CLASS_NAMES = ["BigGAN", "Dalle-3", "Flux-1.1-pro", "Glide", "GPT-image-1", "Imagen-4.0", "Midjourney-V6", "Nano-Banana-Family", "SD3.5", "SDXL"]

class Dinov3MulticlassDetector:
    def __init__(self, weight_path: str, crop_type: str = '5crop', res: int = 224):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.crop_type = crop_type
        self.res = res
        
        # 1. Hugging Face DINOv3 특징 추출기 로드
        self.feature_extractor = AutoModel.from_pretrained("facebook/dinov3-vitl16-pretrain-lvd1689m", trust_remote_code=True).to(self.device)
        self.feature_extractor.eval()
        
        # 2. 전처리 Transform 설정
        self.transform = self._get_transform(self.crop_type, self.res)
        
        # 3. MLP 분류기 로드
        self.mlp_classifier = DINOMlpClassifier(input_dim=1024, num_classes=10).to(self.device)
        self.mlp_classifier.load_state_dict(torch.load(weight_path, map_location=self.device, weights_only=False))
        self.mlp_classifier.eval()

    def _get_transform(self, crop_type, res):
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
        try:
            img = Image.open(image_path).convert('RGB')
            img_tensor = self.transform(img).to(self.device)
            
            with torch.no_grad():
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
