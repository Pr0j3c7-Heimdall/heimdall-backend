import torch
from PIL import Image
import numpy as np
from .UNet_utils import FeatureExtractor, get_transform
from .UNet_model import get_model

class UNetBinaryDetector:
    def __init__(self, weight_path, threshold=0.5):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.extractor = FeatureExtractor(device=self.device)
        self.transform = get_transform()
        self.model = get_model('mlp', input_dim=1280)
        self.model.load(weight_path)
        self.threshold = threshold

    def predict(self, image_path: str) -> dict:
        image = Image.open(image_path).convert('RGB')
        img_tensor = self.transform(image).unsqueeze(0)
        
        # Extract features
        features = self.extractor.extract_features_batch(img_tensor)
        
        # Predict probability
        # probs is a numpy array of [batch_size] because predict_proba in UNet_model.py returns [:, 1]
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
