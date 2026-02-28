"""
F3-Net 이진 분류 추론 모듈
RGB 스트림과 주파수 스트림(LFS, FAD)을 결합한 Dual-Stream ConvNeXt 구조를 사용하여 AI 생성 여부를 판별합니다.
"""

import os
import cv2
import torch
import numpy as np
import scipy.fftpack as fftpack
import torchvision.transforms.functional as TF
from .F3Net_models import DualStreamConvNeXt

class F3NetBinaryDetector:
    """F3-Net 기반 AI 이미지 탐지기 클래스"""

    def __init__(self, weight_path: str, threshold: float = 0.5):
        """
        탐지기 초기화 및 모델 로드
        :param weight_path: 학습된 모델 가중치 경로 (.pth)
        :param threshold: AI 판정 임계값
        """
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.threshold = threshold
        self.img_size = 256
        
        # 모델 로드 및 가중치 적용
        self.model = DualStreamConvNeXt(num_classes=1).to(self.device)
        self.model.load_state_dict(torch.load(weight_path, map_location=self.device, weights_only=True))
        self.model.eval()

    # --- 주파수 특징 추출 함수 ---

    def _dct_2d(self, x: np.ndarray) -> np.ndarray:
        """2D 이산 코사인 변환(DCT)을 수행합니다."""
        return fftpack.dct(fftpack.dct(x.T, norm='ortho').T, norm='ortho')

    def _calculate_lfs(self, img_gray: np.ndarray) -> np.ndarray:
        """Local Frequency Statistics (LFS)를 계산합니다."""
        dct = self._dct_2d(img_gray)
        log_spectrum = np.log(np.abs(dct) + 1e-12)
        return log_spectrum

    def _calculate_fad(self, img_gray: np.ndarray) -> np.ndarray:
        """Frequency Artifact Descriptor (FAD)를 계산합니다."""
        f = np.fft.fft2(img_gray)
        fshift = np.fft.fftshift(f)
        rows, cols = img_gray.shape
        crow, ccol = rows//2 , cols//2
        mask_size = 30
        # 고주파 성분만 남기기 위해 저주파 필터링
        fshift[crow-mask_size:crow+mask_size, ccol-mask_size:ccol+mask_size] = 0
        f_ishift = np.fft.ifftshift(fshift)
        img_back = np.fft.ifft2(f_ishift)
        return np.abs(img_back)

    def _preprocess_image(self, image_path: str):
        """이미지를 읽어 RGB 텐서와 주파수 특징(LFS, FAD) 텐서로 변환합니다."""
        # 이미지 로드 및 리사이즈
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Cannot read image: {image_path}")
        img = cv2.resize(img, (self.img_size, self.img_size))
        
        # Grayscale 변환 및 주파수 특징 추출
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        lfs = self._calculate_lfs(gray)
        fad = self._calculate_fad(gray)
        
        # 정규화 (0~255)
        lfs = cv2.normalize(lfs, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        fad = cv2.normalize(fad, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        
        # 텐서 변환 (H,W,C) -> (C,H,W) 및 스케일링 (0.0~1.0)
        rgb_tensor = torch.from_numpy(img[:, :, [2, 1, 0]]).permute(2, 0, 1).float() / 255.0
        lfs_tensor = torch.from_numpy(lfs).unsqueeze(0).float() / 255.0
        fad_tensor = torch.from_numpy(fad).unsqueeze(0).float() / 255.0

        # ImageNet 통계 기반 정규화
        rgb_tensor = TF.normalize(rgb_tensor, [0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        lfs_tensor = (lfs_tensor - 0.5) / 0.5
        fad_tensor = (fad_tensor - 0.5) / 0.5

        return rgb_tensor.unsqueeze(0), lfs_tensor.unsqueeze(0), fad_tensor.unsqueeze(0)

    def predict(self, image_path: str) -> dict:
        """단일 이미지에 대해 F3-Net 추론을 수행합니다."""
        try:
            # 전처리
            rgb, lfs, fad = self._preprocess_image(image_path)
            rgb, lfs, fad = rgb.to(self.device), lfs.to(self.device), fad.to(self.device)
            
            with torch.no_grad():
                # 모델 추론
                output = self.model(rgb, lfs, fad)
                
                # Sigmoid를 거쳐 최종 확률 도출
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
