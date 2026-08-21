"""
CQCC-SSL-AASIST(CQCC 고정 특징 + SSL 동결 특징 -> cross-attention -> AASIST 백엔드)
단건 추론 모듈. CQCC 추출은 heimdall-vox에서 CQCCPrecomputedDataset이 DataLoader
워커에서 미리 계산해 배치로 넘기던 걸, 여기서는 파일 하나에 대해 즉시 계산한다.
"""
import torch

from app.ai_pipeline.audio.common.audio_preprocessing import load_waveform
from .CQCC_SSL_AASIST_model import CQCCFeatureExtractor, Model


class CqccSslAasistDetector:
    """CQCC-SSL-AASIST 단건 추론기."""

    def __init__(self, weight_path: str, device: str | None = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = Model(device=self.device).to(self.device)
        self.model.load_state_dict(torch.load(weight_path, map_location=self.device))
        self.model.eval()
        self.cqcc_extractor = CQCCFeatureExtractor()

    @torch.no_grad()
    def predict(self, audio_path: str) -> float:
        """raw_score(softmax 이전 logit, fake - real) 반환."""
        waveform = load_waveform(audio_path)
        cqcc_feat = self.cqcc_extractor(waveform.astype("float64"))
        x = torch.from_numpy(waveform).unsqueeze(0).to(self.device)
        cqcc = torch.from_numpy(cqcc_feat).unsqueeze(0).to(self.device)
        out = self.model(x, cqcc)
        return (out[:, 1] - out[:, 0]).item()
