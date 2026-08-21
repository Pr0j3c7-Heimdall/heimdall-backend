"""
AASIST(plain, raw waveform SincConv 프론트엔드) 단건 추론 모듈. 가창 트랙 전용
(음성 트랙은 Wav2Vec2 프론트엔드를 쓰는 SSL_AASIST_model.Model을 사용).
"""
import torch

from app.ai_pipeline.audio.common.audio_preprocessing import load_waveform
from .AASIST_model import Model

# heimdall-vox AASIST/config/AASIST_ep30.conf의 model_config 그대로.
_MODEL_CONFIG = {
    "architecture": "AASIST",
    "nb_samp": 64600,
    "first_conv": 128,
    "filts": [70, [1, 32], [32, 32], [32, 64], [64, 64]],
    "gat_dims": [64, 32],
    "pool_ratios": [0.5, 0.7, 0.5, 0.5],
    "temperatures": [2.0, 2.0, 100.0, 100.0],
}


class AasistDetector:
    """AASIST(plain) 단건 추론기."""

    def __init__(self, weight_path: str, device: str | None = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = Model(_MODEL_CONFIG).to(self.device)
        self.model.load_state_dict(torch.load(weight_path, map_location=self.device))
        self.model.eval()

    @torch.no_grad()
    def predict(self, audio_path: str) -> float:
        """raw_score(softmax 이전 logit, fake - real) 반환."""
        waveform = load_waveform(audio_path)
        x = torch.from_numpy(waveform).unsqueeze(0).to(self.device)
        _, out = self.model(x)
        return (out[:, 1] - out[:, 0]).item()
