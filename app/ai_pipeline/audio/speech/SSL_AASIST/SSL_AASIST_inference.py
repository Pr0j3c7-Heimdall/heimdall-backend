"""
SSL-AASIST(Wav2Vec2 XLS-R-300M -> AASIST 백엔드) 단건 추론 모듈.
heimdall-vox의 score_test.py(배치/CSV 채점용) forward 로직을, 파일 하나에 대해
즉시 raw_score(softmax 이전 logit)를 반환하는 형태로 옮겼다.
"""
import torch

from app.ai_pipeline.audio.common.audio_preprocessing import load_waveform
from .SSL_AASIST_model import Model


class SSLAasistDetector:
    """SSL-AASIST 단건 추론기."""

    def __init__(self, weight_path: str, device: str | None = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = Model(args=None, device=self.device).to(self.device)
        self.model.load_state_dict(torch.load(weight_path, map_location=self.device))
        self.model.eval()

    @torch.no_grad()
    def predict(self, audio_path: str) -> float:
        """raw_score(softmax 이전 logit, fake - real) 반환."""
        waveform = load_waveform(audio_path)
        x = torch.from_numpy(waveform).unsqueeze(0).to(self.device)
        out = self.model(x)
        return (out[:, 1] - out[:, 0]).item()
