# Vendored subset from asvspoof-challenge/2021 LA/Baseline-LFCC-LCNN's sandbox/util_dsp.py
# (BSD 3-Clause, Copyright Xin Wang, NII) via heimdall-vox/LCNN. See LICENSE/NOTICE in this
# directory. Only dct()/LinearDCT are ported -- dct1/idct1/idct are dead code on the LFCC
# path used here (heimdall-vox's own NOTICE documents this: LFCC only ever calls
# LinearDCT(..., 'dct', ...)), and porting them would require also patching torch.rfft/irfft
# calls that don't exist in modern torch. dct() already carries the LCNN/NOTICE torch>=1.8
# compat patch (torch.rfft -> torch.fft.fft + view_as_real, values unchanged).
import numpy as np
import torch
import torch.nn as torch_nn


def dct(x, norm=None):
    """
    Discrete Cosine Transform, Type II (a.k.a. the DCT)
    For the meaning of the parameter `norm`, see:
    https://docs.scipy.org/doc/ scipy.fftpack.dct.html
    :param x: the input signal
    :param norm: the normalization, None or 'ortho'
    :return: the DCT-II of the signal over the last dimension
    """
    x_shape = x.shape
    N = x_shape[-1]
    x = x.contiguous().view(-1, N)

    v = torch.cat([x[:, ::2], x[:, 1::2].flip([1])], dim=1)

    Vc = torch.view_as_real(torch.fft.fft(v, dim=1))

    k = - torch.arange(N, dtype=x.dtype, device=x.device)[None, :] * np.pi/(2*N)
    W_r = torch.cos(k)
    W_i = torch.sin(k)

    V = Vc[:, :, 0] * W_r - Vc[:, :, 1] * W_i

    if norm == 'ortho':
        V[:, 0] /= np.sqrt(N) * 2
        V[:, 1:] /= np.sqrt(N / 2) * 2

    V = 2 * V.view(*x_shape)

    return V


class LinearDCT(torch_nn.Linear):
    """Implement any DCT as a linear layer; in practice this executes around
    50x faster on GPU. Unfortunately, the DCT matrix is stored, which will
    increase memory usage.
    :param in_features: size of expected input
    :param type: which dct function in this file to use"""
    def __init__(self, in_features, type, norm=None, bias=False):
        self.type = type
        self.N = in_features
        self.norm = norm
        super(LinearDCT, self).__init__(in_features, in_features, bias=bias)

    def reset_parameters(self):
        # initialise using dct function
        I = torch.eye(self.N)
        if self.type == 'dct':
            self.weight.data = dct(I, norm=self.norm).data.t()
        else:
            raise NotImplementedError(
                f"LinearDCT type={self.type!r} not ported (only 'dct' is used by LFCC here)")
        self.weight.requires_grad = False  # don't learn this!
