"""
UNet 특징 기반 분류기 모델 정의
추출된 UNet 특징 벡터를 입력받아 최종 판정을 수행하는 MLP 및 KNN 모델 구조를 정의합니다.
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
import numpy as np

class TorchKNN:
    """GPU 가속을 지원하는 K-최근접 이웃(KNN) 분류기"""

    def __init__(self, n_neighbors: int = 20, device: str = 'cuda'):
        self.k = n_neighbors
        self.device = device
        self.X_train = None
        self.y_train = None

    def fit(self, X: torch.Tensor, y: torch.Tensor):
        """학습 데이터를 GPU로 이동하고 정규화합니다."""
        self.X_train = X.clone().detach().float().to(self.device)
        self.y_train = y.clone().detach().long().to(self.device)
        
        mean = self.X_train.mean(dim=1, keepdim=True)
        std = self.X_train.std(dim=1, keepdim=True)
        self.X_train = (self.X_train - mean) / (std + 1e-8)

    def predict_proba(self, X: torch.Tensor) -> np.ndarray:
        """입력 특징과 학습 데이터 간의 코사인 유사도를 기반으로 확률을 계산합니다."""
        X_test = X.clone().detach().float().to(self.device)
        mean = X_test.mean(dim=1, keepdim=True)
        std = X_test.std(dim=1, keepdim=True)
        X_test = (X_test - mean) / (std + 1e-8)
        
        prob_list = []
        batch_size = 1000 
        
        with torch.no_grad():
            for i in range(0, len(X_test), batch_size):
                X_batch = X_test[i:i+batch_size]
                # 행렬 곱을 통한 유사도 계산
                similarity = torch.mm(X_batch, self.X_train.t())
                _, indices = torch.topk(similarity, self.k, dim=1)
                
                # 상위 K개 이웃의 라벨 평균으로 확률 도출
                k_labels = self.y_train[indices]
                prob_batch = k_labels.float().mean(dim=1)
                prob_list.extend(prob_batch.cpu().numpy())
                
        return np.array(prob_list)

    def save(self, filepath: str):
        torch.save({'X_train': self.X_train.cpu(), 'y_train': self.y_train.cpu(), 'k': self.k}, filepath)
        
    def load(self, filepath: str):
        data = torch.load(filepath, map_location=self.device)
        self.X_train = data['X_train'].to(self.device)
        self.y_train = data['y_train'].to(self.device)
        self.k = data['k']

class TorchMLP(nn.Module):
    """UNet 특징 분류를 위한 다층 퍼셉트론(MLP) 모델"""

    def __init__(self, input_dim: int, hidden_dim: int = 640, output_dim: int = 2):
        super(TorchMLP, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim)
        )
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.to(self.device)

    def fit(self, X: torch.Tensor, y: torch.Tensor, epochs: int = 1000, lr: float = 3e-4, batch_size: int = 32, patience: int = 15):
        """모델 학습 및 조기 종료(Early Stopping)를 수행합니다."""
        X_np, y_np = X.numpy(), y.numpy()
        X_train, X_val, y_train, y_val = train_test_split(X_np, y_np, test_size=0.2, random_state=42, stratify=y_np)
        
        X_t = torch.tensor(X_train, dtype=torch.float32).to(self.device)
        y_t = torch.tensor(y_train, dtype=torch.long).to(self.device)
        loader = DataLoader(TensorDataset(X_t, y_t), batch_size=batch_size, shuffle=True)
        
        X_v = torch.tensor(X_val, dtype=torch.float32).to(self.device)
        y_v = torch.tensor(y_val, dtype=torch.long).to(self.device)
        
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.AdamW(self.parameters(), lr=lr)
        
        best_acc = 0.0
        patience_counter = 0
        best_state = None
        
        for epoch in range(epochs):
            self.train()
            for batch_X, batch_y in loader:
                optimizer.zero_grad()
                outputs = self.net(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
            
            self.eval()
            with torch.no_grad():
                val_outputs = self.net(X_v)
                _, predicted = torch.max(val_outputs, 1)
                val_acc = (predicted == y_v).float().mean().item()
            
            if val_acc > best_acc:
                best_acc = val_acc
                patience_counter = 0
                best_state = {k: v.cpu().clone() for k, v in self.state_dict().items()}
            else:
                patience_counter += 1
                
            if patience_counter >= patience:
                break
                
        if best_state is not None:
            self.load_state_dict(best_state)

    def predict_proba(self, X: torch.Tensor) -> np.ndarray:
        """입력 특징에 대해 AI 생성물일 확률(클래스 1)을 반환합니다."""
        self.eval()
        X_tensor = X.clone().detach().float().to(self.device)
        with torch.no_grad():
            outputs = self.net(X_tensor)
            probs = torch.softmax(outputs, dim=1)[:, 1].cpu().numpy()
        return probs

    def save(self, filepath: str):
        torch.save(self.state_dict(), filepath)
        
    def load(self, filepath: str):
        self.load_state_dict(torch.load(filepath, map_location=self.device))

def get_model(model_name: str, input_dim: int = None, **kwargs):
    """설정에 맞는 분류기 모델 인스턴스를 생성하여 반환합니다."""
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    if model_name == 'knn':
        return TorchKNN(n_neighbors=kwargs.get('n_neighbors', 101), device=device)
    elif model_name.startswith('mlp'):
        if input_dim is None: raise ValueError("MLP requires input_dim")
        return TorchMLP(input_dim, hidden_dim=640).to(device)
    else:
        raise ValueError(f"Unknown model: {model_name}")
