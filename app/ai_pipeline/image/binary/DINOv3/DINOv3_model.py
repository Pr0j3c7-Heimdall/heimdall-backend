"""
DINOv3 MLP 분류기 모델 정의
DINOv3의 특징 벡터(1024차원)를 입력받아 AI 여부 또는 모델 종류를 분류하는 신경망 구조입니다.
"""

import torch.nn as nn

class DINOMlpClassifier(nn.Module):
    """
    DINOv3용 MLP 분류기 클래스
    실험적으로 성능이 가장 우수했던 다층 퍼셉트론 구조를 유지합니다.
    """

    def __init__(self, input_dim: int = 384, num_classes: int = 10):
        """
        신경망 레이어 초기화
        :param input_dim: 입력 특징 벡터의 차원 (DINOv3-L의 경우 1024)
        :param num_classes: 분류할 클래스 수 (이진 분류 시 2)
        """
        super(DINOMlpClassifier, self).__init__()
        
        # 은닉층 구조: 1024 -> 512 -> 256 -> 128 -> 64
        self.layers = nn.Sequential(
            nn.Linear(input_dim, 1024), 
            nn.BatchNorm1d(1024), 
            nn.ReLU(), 
            nn.Dropout(0.5),
            
            nn.Linear(1024, 512),       
            nn.BatchNorm1d(512),  
            nn.ReLU(), 
            nn.Dropout(0.5),
            
            nn.Linear(512, 256),        
            nn.BatchNorm1d(256),  
            nn.ReLU(), 
            nn.Dropout(0.5),
            
            nn.Linear(256, 128),        
            nn.BatchNorm1d(128),  
            nn.ReLU(), 
            nn.Dropout(0.7),
            
            nn.Linear(128, 64),         
            nn.BatchNorm1d(64),   
            nn.ReLU(), 
            nn.Dropout(0.7),
            
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        """순전파 수행"""
        return self.layers(x)
