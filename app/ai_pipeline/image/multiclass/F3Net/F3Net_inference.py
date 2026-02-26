import os
import cv2
import torch
import numpy as np
import scipy.fftpack as fftpack
import torchvision.transforms.functional as TF
from .F3Net_models import DualStreamConvNeXt

CLASS_NAMES = ["BigGAN", "Dalle-3", "Flux-1.1-pro", "Glide", "GPT-image-1", "Imagen-4.0", "Midjourney-V6", "Nano-Banana-Family", "SD3.5", "SDXL"]

class F3NetMulticlassDetector:
    def __init__(self, weight_path: str):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.img_size = 256
        
        # 1. 모델 로드 및 가중치 적용
        self.model = DualStreamConvNeXt(num_classes=10).to(self.device)
        self.model.load_state_dict(torch.load(weight_path, map_location=self.device, weights_only=False))
        self.model.eval()

    def _dct_2d(self, x):
        return fftpack.dct(fftpack.dct(x.T, norm='ortho').T, norm='ortho')

    def _calculate_lfs(self, img_gray):
        dct = self._dct_2d(img_gray)
        log_spectrum = np.log(np.abs(dct) + 1e-12)
        return log_spectrum

    def _calculate_fad(self, img_gray):
        f = np.fft.fft2(img_gray)
        fshift = np.fft.fftshift(f)
        rows, cols = img_gray.shape
        crow, ccol = rows//2 , cols//2
        mask_size = 30
        fshift[crow-mask_size:crow+mask_size, ccol-mask_size:ccol+mask_size] = 0
        f_ishift = np.fft.ifftshift(fshift)
        img_back = np.fft.ifft2(f_ishift)
        return np.abs(img_back)

    def _preprocess_image(self, image_path: str):
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Cannot read image: {image_path}")
        img = cv2.resize(img, (self.img_size, self.img_size))
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        lfs = self._calculate_lfs(gray)
        fad = self._calculate_fad(gray)
        
        lfs = cv2.normalize(lfs, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        fad = cv2.normalize(fad, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        
        rgb_tensor = torch.from_numpy(img[:, :, [2, 1, 0]]).permute(2, 0, 1).float() / 255.0
        lfs_tensor = torch.from_numpy(lfs).unsqueeze(0).float() / 255.0
        fad_tensor = torch.from_numpy(fad).unsqueeze(0).float() / 255.0

        rgb_tensor = TF.normalize(rgb_tensor, [0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        lfs_tensor = (lfs_tensor - 0.5) / 0.5
        fad_tensor = (fad_tensor - 0.5) / 0.5

        return rgb_tensor.unsqueeze(0), lfs_tensor.unsqueeze(0), fad_tensor.unsqueeze(0)

    def predict(self, image_path: str) -> dict:
        try:
            rgb, lfs, fad = self._preprocess_image(image_path)
            rgb, lfs, fad = rgb.to(self.device), lfs.to(self.device), fad.to(self.device)
            
            with torch.no_grad():
                output = self.model(rgb, lfs, fad)
                probs = torch.softmax(output, dim=1)[0]
                confidence, predicted_idx = torch.max(probs, dim=0)
                predicted_model = CLASS_NAMES[predicted_idx.item()]
                
            return {
                "detection_method": "F3Net",
                "predicted_model": predicted_model,
                "confidence_score": confidence.item(),
                "result_json": {
                    "all_probabilities": {CLASS_NAMES[i]: probs[i].item() for i in range(10)}
                }
            }
            
        except Exception as e:
            raise RuntimeError(f"F3Net Multiclass Inference failed: {str(e)}")
