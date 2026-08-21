"""
RawNet3(백본 + 1-neuron 분류 헤드) 단건 추론 모듈. 음성/가창 두 트랙이 공유하는
아키텍처지만, 이 백엔드는 현재 음성 트랙만 다룬다.
"""
import torch

from app.ai_pipeline.audio.common.audio_preprocessing import load_waveform
from .RawNet3_model import RawNet3Classifier


class RawNet3Detector:
    """RawNet3 단건 추론기."""

    def __init__(self, weight_path: str, embedding_dim: int = 256, device: str | None = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = RawNet3Classifier(embedding_dim=embedding_dim).to(self.device)
        self.model.load_state_dict(torch.load(weight_path, map_location=self.device))
        self.model.eval()

    @torch.no_grad()
    def predict(self, audio_path: str) -> float:
        """raw_score(sigmoid 이전 1-neuron logit) 반환."""
        waveform = load_waveform(audio_path)
        x = torch.from_numpy(waveform).unsqueeze(0).to(self.device)
        logit = self.model(x)
        return logit.item()
