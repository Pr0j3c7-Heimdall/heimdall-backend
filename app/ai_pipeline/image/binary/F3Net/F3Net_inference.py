import os
import cv2
import torch
import numpy as np
import scipy.fftpack as fftpack
import torchvision.transforms.functional as TF
import importlib.util
import sys

# 하이픈(-)이 포함된 파일명을 임포트하기 위한 처리
spec = importlib.util.spec_from_file_location("F3_Net_models", os.path.join(os.path.dirname(__file__), "F3-Net_models.py"))
f3_models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f3_models)
DualStreamConvNeXt = f3_models.DualStreamConvNeXt

class F3NetBinaryDetector:
    def __init__(self, weight_path: str, threshold: float = 0.5):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.threshold = threshold
        self.img_size = 256
        
        # 1. 모델 로드 및 가중치 적용
        self.model = DualStreamConvNeXt(num_classes=1).to(self.device)
        self.model.load_state_dict(torch.load(weight_path, map_location=self.device))
        self.model.eval()

    # --- 수학적 변환 함수 (preprocessing.py에서 가져옴) ---
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
        """이미지 1장을 읽어 rgb, lfs, fad 텐서로 변환 (utils.py 로직 결합)"""
        # 1. OpenCV로 읽고 리사이즈
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Cannot read image: {image_path}")
        img = cv2.resize(img, (self.img_size, self.img_size))
        
        # 2. Grayscale 변환 및 주파수 특징 추출
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        lfs = self._calculate_lfs(gray)
        fad = self._calculate_fad(gray)
        
        # 3. 0~255 uint8 변환 (학습 때와 동일한 환경 맞추기)
        lfs = cv2.normalize(lfs, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        fad = cv2.normalize(fad, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        
        # 4. 차원 변경 및 Float(0.0~1.0) 변환 (utils.py의 __getitem__ 로직)
        # cv2는 BGR이므로 RGB로 변경 후 (H,W,C) -> (C,H,W)
        rgb_tensor = torch.from_numpy(img[:, :, [2, 1, 0]]).permute(2, 0, 1).float() / 255.0
        lfs_tensor = torch.from_numpy(lfs).unsqueeze(0).float() / 255.0
        fad_tensor = torch.from_numpy(fad).unsqueeze(0).float() / 255.0

        # 5. 정규화 (Normalize)
        rgb_tensor = TF.normalize(rgb_tensor, [0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        lfs_tensor = (lfs_tensor - 0.5) / 0.5
        fad_tensor = (fad_tensor - 0.5) / 0.5

        # 6. 배치 차원(Batch dimension) 추가: (C,H,W) -> (1,C,H,W)
        return rgb_tensor.unsqueeze(0), lfs_tensor.unsqueeze(0), fad_tensor.unsqueeze(0)

    def predict(self, image_path: str) -> dict:
        """API에서 호출할 단일 이미지 추론 메서드"""
        try:
            # 1. 전처리
            rgb, lfs, fad = self._preprocess_image(image_path)
            rgb, lfs, fad = rgb.to(self.device), lfs.to(self.device), fad.to(self.device)
            
            with torch.no_grad():
                # 2. 모델 추론
                output = self.model(rgb, lfs, fad)
                
                # F3-Net은 BCEWithLogitsLoss를 썼으므로 Sigmoid를 거쳐 확률 계산
                prob = torch.sigmoid(output).item() 
                is_fake = bool(prob >= self.threshold)
                
            return {
                "detection_method": "F3-Net",
                "is_detected": is_fake,
                "confidence_score": prob,
                "result_json": {
                    "fake_prob": prob,
                    "real_prob": 1.0 - prob
                }
            }
            
        except Exception as e:
            raise RuntimeError(f"F3-Net Inference failed: {str(e)}")