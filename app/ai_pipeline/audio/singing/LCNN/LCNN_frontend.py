# Vendored subset from asvspoof-challenge/2021 LA/Baseline-LFCC-LCNN's sandbox/util_frontend.py
# (BSD 3-Clause, Copyright Xin Wang, NII) via heimdall-vox/LCNN. See LICENSE/NOTICE in this
# directory. Only trimf()/delta()/LFCC are ported -- LFB and Spectrogram front-ends are
# unused by this project's LCNN model (which only instantiates LFCC).
import sys

import torch
import torch.nn as torch_nn
import torch.nn.functional as torch_nn_func

from .LCNN_dsp import LinearDCT

# core_scripts.data_io.conf.d_dtype is just torch.float32 -- inlined here rather than
# porting that (training-only) config module for a single constant.
_D_DTYPE = torch.float32


def trimf(x, params):
    """
    trimf: similar to Matlab definition
    https://www.mathworks.com/help/fuzzy/trimf.html?s_tid=srchtitle
    """
    if len(params) != 3:
        print("trimp requires params to be a list of 3 elements")
        sys.exit(1)
    a = params[0]
    b = params[1]
    c = params[2]
    if a > b or b > c:
        print("trimp(x, [a, b, c]) requires a<=b<=c")
        sys.exit(1)
    y = torch.zeros_like(x, dtype=_D_DTYPE)
    if a < b:
        index = torch.logical_and(a < x, x < b)
        y[index] = (x[index] - a) / (b - a)
    if b < c:
        index = torch.logical_and(b < x, x < c)
        y[index] = (c - x[index]) / (c - b)
    y[x == b] = 1
    return y


def delta(x):
    """ By default
    input
    -----
    x (batch, Length, dim)

    output
    ------
    output (batch, Length, dim)

    Delta is calculated along Length dimension
    """
    length = x.shape[1]
    output = torch.zeros_like(x)
    x_temp = torch_nn_func.pad(x.unsqueeze(1), (0, 0, 1, 1),
                               'replicate').squeeze(1)
    output = -1 * x_temp[:, 0:length] + x_temp[:, 2:]
    return output


class LFCC(torch_nn.Module):
    """ Based on asvspoof.org baseline Matlab code.
    Difference: with_energy is added to set the first dimension as energy
    """
    def __init__(self, fl, fs, fn, sr, filter_num,
                 with_energy=False, with_emphasis=True,
                 with_delta=True, flag_for_LFB=False,
                 num_coef=None, min_freq=0, max_freq=1):
        """ Initialize LFCC

        Para:
        -----
          fl: int, frame length, (number of waveform points)
          fs: int, frame shift, (number of waveform points)
          fn: int, FFT points
          sr: int, sampling rate (Hz)
          filter_num: int, number of filters in filter-bank

          with_energy: bool, (default False), whether replace 1st dim to energy
          with_emphasis: bool, (default True), whether pre-emphaze input wav
          with_delta: bool, (default True), whether use delta and delta-delta

          for_LFB: bool (default False), reserved for LFB feature
          num_coef: int or None, number of coeffs to be taken from filter bank.
                    Note that this is only used for LFCC, i.e., for_LFB=False
                    When None, num_coef will be equal to filter_num
          min_freq: float (default 0), min_freq * sr // 2 will be the minimum
                    frequency of extracted FFT spectrum
          max_freq: float (default 1), max_freq * sr // 2 will be the maximum
                    frequency of extracted FFT spectrum
        """
        super(LFCC, self).__init__()
        self.fl = fl
        self.fs = fs
        self.fn = fn
        self.sr = sr
        self.filter_num = filter_num
        self.num_coef = num_coef

        # decide the range of frequency bins
        if min_freq >= 0 and min_freq < max_freq and max_freq <= 1:
            self.min_freq_bin = int(min_freq * (fn//2+1))
            self.max_freq_bin = int(max_freq * (fn//2+1))
            self.num_fft_bins = self.max_freq_bin - self.min_freq_bin
        else:
            print("LFCC cannot work with min_freq {:f} and max_freq {:}".format(
                min_freq, max_freq))
            sys.exit(1)

        # build the triangle filter bank
        f = (sr / 2) * torch.linspace(min_freq, max_freq, self.num_fft_bins)
        filter_bands = torch.linspace(min(f), max(f), filter_num+2)

        filter_bank = torch.zeros([self.num_fft_bins, filter_num])
        for idx in range(filter_num):
            filter_bank[:, idx] = trimf(
                f, [filter_bands[idx],
                    filter_bands[idx+1],
                    filter_bands[idx+2]])
        self.lfcc_fb = torch_nn.Parameter(filter_bank, requires_grad=False)

        # DCT as a linear transformation layer
        self.l_dct = LinearDCT(filter_num, 'dct', norm='ortho')

        # opts
        self.with_energy = with_energy
        self.with_emphasis = with_emphasis
        self.with_delta = with_delta
        self.flag_for_LFB = flag_for_LFB
        if self.num_coef is None:
            self.num_coef = filter_num

        return

    def forward(self, x):
        """

        input:
        ------
         x: tensor(batch, length), where length is waveform length

        output:
        -------
         lfcc_output: tensor(batch, frame_num, dim_num)
        """
        # pre-emphsis
        if self.with_emphasis:
            # to avoid side effect
            x_copy = torch.zeros_like(x) + x
            x_copy[:, 1:] = x[:, 1:] - 0.97 * x[:, 0:-1]
        else:
            x_copy = x

        # STFT
        # torch>=2.0 호환 패치 (LCNN/NOTICE 참고): return_complex 인자가 없으면
        # 더 이상 동작하지 않아 명시하고, view_as_real로 감싸서 아래 torch.norm(...,-1)이
        # 기대하는 기존 (..., 2) real/imag shape을 그대로 유지한다.
        x_stft = torch.view_as_real(torch.stft(
            x_copy, self.fn, self.fs, self.fl,
            window=torch.hamming_window(self.fl).to(x.device),
            onesided=True, pad_mode="constant", return_complex=True))

        # amplitude
        sp_amp = torch.norm(x_stft, 2, -1).pow(2).permute(0, 2, 1).contiguous()

        if self.min_freq_bin > 0 or self.max_freq_bin < (self.fn//2+1):
            sp_amp = sp_amp[:, :, self.min_freq_bin:self.max_freq_bin]

        # filter bank
        fb_feature = torch.log10(torch.matmul(sp_amp, self.lfcc_fb) +
                                 torch.finfo(torch.float32).eps)

        # DCT (if necessary, remove DCT)
        lfcc = self.l_dct(fb_feature) if not self.flag_for_LFB else fb_feature

        # Truncate the output of l_dct when necessary
        if not self.flag_for_LFB and self.num_coef != self.filter_num:
            lfcc = lfcc[:, :, :self.num_coef]

        # Add energy
        if self.with_energy:
            power_spec = sp_amp / self.fn
            energy = torch.log10(power_spec.sum(axis=2) +
                                 torch.finfo(torch.float32).eps)
            lfcc[:, :, 0] = energy

        # Add delta coefficients
        if self.with_delta:
            lfcc_delta = delta(lfcc)
            lfcc_delta_delta = delta(lfcc_delta)
            lfcc_output = torch.cat((lfcc, lfcc_delta, lfcc_delta_delta), 2)
        else:
            lfcc_output = lfcc

        # done
        return lfcc_output
