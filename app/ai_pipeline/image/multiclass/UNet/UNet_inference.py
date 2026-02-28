import torch
from PIL import Image
import numpy as np
from .UNet_utils import FeatureExtractor, get_transform
from .UNet_model import get_model

CLASS_NAMES = ["BigGAN", "Dalle-3", "Flux-1.1-pro", "Glide", "GPT-image-1", "Imagen-4.0", "Midjourney-V6", "Nano-Banana-Family", "SD3.5", "SDXL"]

class UNetMultiDetector:
    def __init__(self, weight_path):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.extractor = FeatureExtractor(device=self.device)
        self.transform = get_transform()
        self.model = get_model('mlp', input_dim=1280, num_classes=10)
        self.model.load(weight_path)

    def predict(self, image_path: str) -> dict:
        image = Image.open(image_path).convert('RGB')
        img_tensor = self.transform(image).unsqueeze(0)
        
        # Extract features
        features = self.extractor.extract_features_batch(img_tensor)
        
        # Predict all probabilities
        # probs in UNet_model.py returns [batch_size, 10]
        prob_array = self.model.predict_proba(features)
        probs = prob_array[0] # Probability array for the first image
        
        # Find index with max probability
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
