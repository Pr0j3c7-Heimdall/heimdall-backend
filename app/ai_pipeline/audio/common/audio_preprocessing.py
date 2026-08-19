"""
음성 판별 모델 공통 전처리. heimdall-vox의 HeimdallListDataset이 채점/평가(train=False)
시 쓰는 결정적 경로(모노 다운믹스 + 고정 길이 crop/pad, 증강 없음)를 단일 파일 추론용으로
포팅했다 — 학습 전용 RawBoost 증강은 추론에 필요 없어 제외.
"""
import numpy as np
import soundfile as sf

NB_SAMP = 64600


def load_waveform(audio_path: str, nb_samp: int = NB_SAMP) -> np.ndarray:
    """오디오 파일을 읽어 모노로 다운믹스하고, nb_samp 길이로 결정적으로 자르거나
    반복 패딩한다. 학습/평가 때와 다른 전처리를 쓰면 raw_score가 어긋나므로
    heimdall-vox common/dataset.py의 HeimdallListDataset과 동일한 규칙을 따른다."""
    x, _ = sf.read(audio_path)
    x = x.astype(np.float64)
    if x.size == 0:
        raise ValueError(f"빈 오디오 파일입니다: {audio_path}")
    if x.ndim > 1:
        # 스테레오/멀티채널 파일은 채널 평균으로 다운믹스 (모델은 모노 입력을 전제로 함)
        x = x.mean(axis=1)

    x = x.astype(np.float32)
    nb_time = x.shape[0]
    if nb_time > nb_samp:
        return x[:nb_samp]
    if nb_time < nb_samp:
        nb_dup = int(nb_samp / nb_time) + 1
        return np.tile(x, nb_dup)[:nb_samp]
    return x
