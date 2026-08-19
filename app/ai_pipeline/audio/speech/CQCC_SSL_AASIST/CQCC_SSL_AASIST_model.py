"""
CQCC + SSL(Wav2Vec2 XLS-R) + AASIST 조합 모델. 공개 구현체가 없어서 heimdall-vox 팀이 직접
설계한 것을 그대로 포팅 ("Two Views, One Truth" 논문 기반: 스펙트럴 특징 + SSL 특징을
cross-attention으로 결합해 AASIST류 백엔드에 넣는 구조). 원본은 SSL-AASIST/model.py와 파일명이
같아 importlib 우회로 클래스를 재사용했는데(heimdall-vox 참고), 여기서는 파일명이 이미
고유해서(SSL_AASIST_model.py) 평범한 파이썬 import로 그대로 재사용한다.

구성 요소:
  - CQCC : spafe로 추출하는 고정 특징, 학습되지 않음. nb_samp=64600 기준 402프레임 x 60차원
           (20차원 기본 계수 + delta + delta-delta).
  - SSL  : SSL_AASIST_model.SSLModel을 재사용, 파라미터 동결(학습 안 함).
  - Fusion: CQCC/SSL을 각각 128차원으로 projection한 뒤 cross-attention으로 결합.
  - AASIST 분류기: SSL_AASIST_model에 이미 vendoring된 그래프 어텐션 구성요소를 그대로
           재사용해서 세 번째 복사를 피한다.
"""
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from spafe.features.cqcc import cqcc
from spafe.utils.cepstral import deltas
from spafe.utils.preprocessing import SlidingWindow

from app.ai_pipeline.audio.speech.SSL_AASIST.SSL_AASIST_model import (
    GraphAttentionLayer,
    GraphPool,
    HtrgGraphAttentionLayer,
    Residual_block,
    SSLModel,
)


class CQCCFeatureExtractor:
    """CQT 기반 CQCC 정적 계수 + delta + delta-delta. 학습되지 않는 고정 변환(scipy/numpy).

    발화 단위 CMVN(cepstral mean-variance normalization)을 마지막에 적용한다 — CQCC 저차
    계수(에너지 관련)가 다른 계수보다 스케일이 훨씬 크고 학습 안 된 cqcc_proj(nn.Linear)를
    그대로 거쳐 cross-attention의 query로 들어가면서, attention이 학습 신호가 아니라 CQCC의
    원시 스케일에 휘둘리는 문제가 있어 추가됨 (heimdall-vox PLAN.md 참고)."""

    def __init__(self, fs=16000, num_ceps=20, number_of_bins_per_octave=96):
        self.fs = fs
        self.num_ceps = num_ceps
        self.number_of_bins_per_octave = number_of_bins_per_octave
        self.window = SlidingWindow(win_len=0.025, win_hop=0.01, win_type="hamming")

    def __call__(self, waveform_np):
        """waveform_np: 1D float64 numpy array -> (frames, num_ceps*3) float32 numpy array."""
        static = cqcc(waveform_np, fs=self.fs, num_ceps=self.num_ceps,
                       window=self.window, number_of_bins_per_octave=self.number_of_bins_per_octave)
        d1 = deltas(static)
        d2 = deltas(d1)
        feat = np.concatenate([static, d1, d2], axis=1)

        # 발화 단위 CMVN: 프레임(시간) 축 기준으로 계수별 평균 0, 분산 1로 정규화.
        mean = feat.mean(axis=0, keepdims=True)
        std = feat.std(axis=0, keepdims=True)
        feat = (feat - mean) / (std + 1e-8)

        return feat.astype(np.float32)


class CrossAttentionFusion(nn.Module):
    """CQCC(query) x SSL(key/value) 멀티헤드 cross-attention.
    프레임 수가 다른(CQCC 402 vs SSL ~200) 두 시퀀스를 이어붙이지 않고 결합한다."""

    def __init__(self, dim=128, num_heads=4, dropout=0.1):
        super().__init__()
        self.attn = nn.MultiheadAttention(embed_dim=dim, num_heads=num_heads,
                                           dropout=dropout, batch_first=True)
        self.norm = nn.LayerNorm(dim)

    def forward(self, cqcc_feat, ssl_feat):
        attn_out, _ = self.attn(query=cqcc_feat, key=ssl_feat, value=ssl_feat)
        return self.norm(cqcc_feat + attn_out)


class Model(nn.Module):
    def __init__(self, device, cqcc_dim=60, fusion_dim=128,
                 ssl_pretrained="facebook/wav2vec2-xls-r-300m"):
        super().__init__()
        self.device = device

        # AASIST 파라미터 — SSL_AASIST_model.Model.__init__과 동일 (같은 분류기 아키텍처)
        filts = [128, [1, 32], [32, 32], [32, 64], [64, 64]]
        gat_dims = [64, 32]
        pool_ratios = [0.5, 0.5, 0.5, 0.5]
        temperatures = [2.0, 2.0, 100.0, 100.0]

        # ---- 프론트엔드: CQCC(고정, 호출부에서 미리 계산되어 forward()로 전달됨) + SSL(동결)
        # -> cross-attention fusion(학습) ----
        self.cqcc_proj = nn.Sequential(nn.Linear(cqcc_dim, fusion_dim), nn.LayerNorm(fusion_dim))

        self.ssl_model = SSLModel(device, pretrained_name=ssl_pretrained)
        for p in self.ssl_model.parameters():
            p.requires_grad = False  # SSL은 학습하지 않음
        self.ssl_proj = nn.Sequential(nn.Linear(self.ssl_model.out_dim, fusion_dim), nn.LayerNorm(fusion_dim))

        self.fusion = CrossAttentionFusion(dim=fusion_dim)

        # ---- 백엔드: SSL-AASIST와 동일한 그래프 어텐션 분류기 ----
        self.first_bn = nn.BatchNorm2d(num_features=1)
        self.first_bn1 = nn.BatchNorm2d(num_features=64)
        self.drop = nn.Dropout(0.5, inplace=True)
        self.drop_way = nn.Dropout(0.2, inplace=True)
        self.selu = nn.SELU(inplace=True)

        self.encoder = nn.Sequential(
            nn.Sequential(Residual_block(nb_filts=filts[1], first=True)),
            nn.Sequential(Residual_block(nb_filts=filts[2])),
            nn.Sequential(Residual_block(nb_filts=filts[3])),
            nn.Sequential(Residual_block(nb_filts=filts[4])),
            nn.Sequential(Residual_block(nb_filts=filts[4])),
            nn.Sequential(Residual_block(nb_filts=filts[4])))

        self.attention = nn.Sequential(
            nn.Conv2d(64, 128, kernel_size=(1, 1)),
            nn.SELU(inplace=True),
            nn.BatchNorm2d(128),
            nn.Conv2d(128, 64, kernel_size=(1, 1)),
        )
        self.pos_S = nn.Parameter(torch.randn(1, 42, filts[-1][-1]))
        self.master1 = nn.Parameter(torch.randn(1, 1, gat_dims[0]))
        self.master2 = nn.Parameter(torch.randn(1, 1, gat_dims[0]))

        self.GAT_layer_S = GraphAttentionLayer(filts[-1][-1], gat_dims[0], temperature=temperatures[0])
        self.GAT_layer_T = GraphAttentionLayer(filts[-1][-1], gat_dims[0], temperature=temperatures[1])
        self.HtrgGAT_layer_ST11 = HtrgGraphAttentionLayer(gat_dims[0], gat_dims[1], temperature=temperatures[2])
        self.HtrgGAT_layer_ST12 = HtrgGraphAttentionLayer(gat_dims[1], gat_dims[1], temperature=temperatures[2])
        self.HtrgGAT_layer_ST21 = HtrgGraphAttentionLayer(gat_dims[0], gat_dims[1], temperature=temperatures[2])
        self.HtrgGAT_layer_ST22 = HtrgGraphAttentionLayer(gat_dims[1], gat_dims[1], temperature=temperatures[2])

        self.pool_S = GraphPool(pool_ratios[0], gat_dims[0], 0.3)
        self.pool_T = GraphPool(pool_ratios[1], gat_dims[0], 0.3)
        self.pool_hS1 = GraphPool(pool_ratios[2], gat_dims[1], 0.3)
        self.pool_hT1 = GraphPool(pool_ratios[2], gat_dims[1], 0.3)
        self.pool_hS2 = GraphPool(pool_ratios[2], gat_dims[1], 0.3)
        self.pool_hT2 = GraphPool(pool_ratios[2], gat_dims[1], 0.3)

        self.out_layer = nn.Linear(5 * gat_dims[1], 2)

    def forward(self, x, cqcc_feat):
        """x: (bs, samples) 원시 waveform. cqcc_feat: (bs, 402, 60) 호출부가 미리 계산해
        넘겨준 CQCC 특징 (CQCCFeatureExtractor 참고)."""
        # ---- 프론트엔드 ----
        cqcc_feat = self.cqcc_proj(cqcc_feat.to(x.device, dtype=x.dtype))  # (bs, 402, 128)

        with torch.no_grad():
            ssl_feat = self.ssl_model.extract_feat(x)  # (bs, ~200, 1024)
        ssl_feat = self.ssl_proj(ssl_feat)  # (bs, ~200, 128)

        x = self.fusion(cqcc_feat, ssl_feat)  # (bs, 402, 128)

        # ---- 백엔드 (SSL_AASIST_model.Model.forward()와 동일) ----
        x = x.transpose(1, 2)
        x = x.unsqueeze(dim=1)
        x = F.max_pool2d(x, (3, 3))
        x = self.first_bn(x)
        x = self.selu(x)

        x = self.encoder(x)
        x = self.first_bn1(x)
        x = self.selu(x)

        w = self.attention(x)

        w1 = F.softmax(w, dim=-1)
        m = torch.sum(x * w1, dim=-1)
        e_S = m.transpose(1, 2) + self.pos_S

        gat_S = self.GAT_layer_S(e_S)
        out_S = self.pool_S(gat_S)

        w2 = F.softmax(w, dim=-2)
        m1 = torch.sum(x * w2, dim=-2)
        e_T = m1.transpose(1, 2)

        gat_T = self.GAT_layer_T(e_T)
        out_T = self.pool_T(gat_T)

        master1 = self.master1.expand(x.size(0), -1, -1)
        master2 = self.master2.expand(x.size(0), -1, -1)

        out_T1, out_S1, master1 = self.HtrgGAT_layer_ST11(out_T, out_S, master=self.master1)
        out_S1 = self.pool_hS1(out_S1)
        out_T1 = self.pool_hT1(out_T1)

        out_T_aug, out_S_aug, master_aug = self.HtrgGAT_layer_ST12(out_T1, out_S1, master=master1)
        out_T1 = out_T1 + out_T_aug
        out_S1 = out_S1 + out_S_aug
        master1 = master1 + master_aug

        out_T2, out_S2, master2 = self.HtrgGAT_layer_ST21(out_T, out_S, master=self.master2)
        out_S2 = self.pool_hS2(out_S2)
        out_T2 = self.pool_hT2(out_T2)

        out_T_aug, out_S_aug, master_aug = self.HtrgGAT_layer_ST22(out_T2, out_S2, master=master2)
        out_T2 = out_T2 + out_T_aug
        out_S2 = out_S2 + out_S_aug
        master2 = master2 + master_aug

        out_T1 = self.drop_way(out_T1)
        out_T2 = self.drop_way(out_T2)
        out_S1 = self.drop_way(out_S1)
        out_S2 = self.drop_way(out_S2)
        master1 = self.drop_way(master1)
        master2 = self.drop_way(master2)

        out_T = torch.max(out_T1, out_T2)
        out_S = torch.max(out_S1, out_S2)
        master = torch.max(master1, master2)

        T_max, _ = torch.max(torch.abs(out_T), dim=1)
        T_avg = torch.mean(out_T, dim=1)
        S_max, _ = torch.max(torch.abs(out_S), dim=1)
        S_avg = torch.mean(out_S, dim=1)

        last_hidden = torch.cat([T_max, T_avg, S_max, S_avg, master.squeeze(1)], dim=1)
        last_hidden = self.drop(last_hidden)
        output = self.out_layer(last_hidden)

        return output
