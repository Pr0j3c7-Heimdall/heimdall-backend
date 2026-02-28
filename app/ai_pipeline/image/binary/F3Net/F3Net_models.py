"""
F3-Net 모델 아키텍처 정의
RGB 이미지와 주파수 도메인 특징(LFS, FAD)을 입력으로 사용하는 Dual-Stream ConvNeXt V2 Tiny 구조입니다.
"""

import torch
import torch.nn as nn
import timm

class DualStreamConvNeXt(nn.Module):
    """RGB와 주파수 특징을 결합하여 분석하는 듀얼 스트림 신경망 클래스"""

    def __init__(self, num_classes: int = 1):
        """
        모델 레이어 초기화
        :param num_classes: 출력 클래스 수 (이진 분류 시 1, 다중 분류 시 N)
        """
        super(DualStreamConvNeXt, self).__init__()
        
        # RGB Stream (일반 이미지 특징 추출)
        # ConvNeXt V2 Tiny 모델을 Backbone으로 사용
        self.rgb_backbone = timm.create_model('convnextv2_tiny', pretrained=True, num_classes=0)
        
        # Frequency Stream (주파수 특징 추출)
        # LFS와 FAD가 결합된 2채널 입력을 3채널로 변환하여 Backbone에 입력
        self.freq_backbone = timm.create_model('convnextv2_tiny', pretrained=True, num_classes=0)
        self.freq_entry = nn.Conv2d(2, 3, kernel_size=1)
        
        # Classifier (특징 융합 및 분류)
        # 두 스트림의 출력(각 768차원)을 결합하여 분류 수행
        self.classifier = nn.Sequential(
            nn.Linear(768 * 2, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(512, num_classes)
        )

    def forward(self, rgb: torch.Tensor, lfs: torch.Tensor, fad: torch.Tensor) -> torch.Tensor:
        """
        순전파 수행
        :param rgb: RGB 이미지 텐서
        :param lfs: Local Frequency Statistics 텐서
        :param fad: Frequency Artifact Descriptor 텐서
        """
        # RGB 스트림 처리
        rgb_feat = self.rgb_backbone(rgb) # [Batch, 768]
        
        # 주파수 스트림 처리 (LFS와 FAD 결합)
        freq_input = torch.cat([lfs, fad], dim=1) # [Batch, 2, 256, 256]
        freq_input = self.freq_entry(freq_input)  # [Batch, 3, 256, 256]
        freq_feat = self.freq_backbone(freq_input) # [Batch, 768]
        
        # 특징 융합 (Feature Fusion)
        combined = torch.cat([rgb_feat, freq_feat], dim=1) # [Batch, 1536]
        
        # 최종 분류 결과 반환
        return self.classifier(combined)
