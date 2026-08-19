# Vendored from asvspoof-challenge/2021 LA/Baseline-LFCC-LCNN's project/baseline_LA/model.py
# (BSD 3-Clause, Copyright Xin Wang, NII) via heimdall-vox/LCNN. See LICENSE/NOTICE in this
# directory.
#
# This is an inference-only subset of the original Model class. Dropped: forward() and its
# supporting protocol_parse()/_get_target()/_get_target_eval() (training-time target lookup)
# and the Loss class. heimdall-vox's own LCNN/project/baseline_LA/score_test.py already
# established that inference never calls forward() -- it calls _compute_embedding() and
# _compute_score() directly, bypassing the target-lookup path entirely (see
# LCNN_inference.py). Dropping forward() here removes the need to also port
# core_scripts.data_io.seq_info and core_scripts.other_tools.debug (training-only utilities
# forward() depended on), which are otherwise unused by any inference path in this project.
# input_mean/input_std/output_mean/output_std are kept (unused functionally at inference,
# always zeros/ones since this project never passes mean_std) because they are registered
# nn.Parameters and therefore part of the saved checkpoint's state_dict.
import torch
import torch.nn as torch_nn

from .LCNN_blocks import MaxFeatureMap2D, BLSTMLayer
from .LCNN_frontend import LFCC


class Model(torch_nn.Module):
    """ Model definition
    """
    def __init__(self, in_dim, out_dim, args, prj_conf, mean_std=None):
        super(Model, self).__init__()

        ##### required part, no need to change #####

        # mean std of input and output
        in_m, in_s, out_m, out_s = self.prepare_mean_std(in_dim, out_dim,
                                                         args, mean_std)
        self.input_mean = torch_nn.Parameter(in_m, requires_grad=False)
        self.input_std = torch_nn.Parameter(in_s, requires_grad=False)
        self.output_mean = torch_nn.Parameter(out_m, requires_grad=False)
        self.output_std = torch_nn.Parameter(out_s, requires_grad=False)

        ####
        # on input waveform and output target
        ####
        # Working sampling rate
        self.m_target_sr = 16000

        ####
        # front-end configuration
        #  multiple front-end configurations may be used
        #  by default, use a single front-end
        ####
        # frame shift (number of waveform points)
        self.frame_hops = [160]
        # frame length
        self.frame_lens = [320]
        # FFT length
        self.fft_n = [1024]

        # LFCC dim (base component)
        self.lfcc_dim = [20]
        self.lfcc_with_delta = True
        # only uses [0, 0.5 * Nyquist_freq range for LFCC]
        self.lfcc_max_freq = 0.5

        # window type
        self.win = torch.hann_window
        # floor in log-spectrum-amplitude calculating (not used)
        self.amp_floor = 0.00001

        # number of frames to be kept for each trial
        # no truncation
        self.v_truncate_lens = [None for x in self.frame_hops]

        # number of sub-models (by default, a single model)
        self.v_submodels = len(self.frame_lens)

        # dimension of embedding vectors
        # here, the embedding is just the activation before sigmoid()
        self.v_emd_dim = 1

        ####
        # create network
        ####
        # 1st part of the classifier
        self.m_transform = []
        #
        self.m_before_pooling = []
        # 2nd part of the classifier
        self.m_output_act = []
        # front-end
        self.m_frontend = []

        # it can handle models with multiple front-end configuration
        # by default, only a single front-end
        for idx, (trunc_len, fft_n, lfcc_dim) in enumerate(zip(
                self.v_truncate_lens, self.fft_n, self.lfcc_dim)):

            fft_n_bins = fft_n // 2 + 1
            if self.lfcc_with_delta:
                lfcc_dim = lfcc_dim * 3

            self.m_transform.append(
                torch_nn.Sequential(
                    torch_nn.Conv2d(1, 64, [5, 5], 1, padding=[2, 2]),
                    MaxFeatureMap2D(),
                    torch.nn.MaxPool2d([2, 2], [2, 2]),

                    torch_nn.Conv2d(32, 64, [1, 1], 1, padding=[0, 0]),
                    MaxFeatureMap2D(),
                    torch_nn.BatchNorm2d(32, affine=False),
                    torch_nn.Conv2d(32, 96, [3, 3], 1, padding=[1, 1]),
                    MaxFeatureMap2D(),

                    torch.nn.MaxPool2d([2, 2], [2, 2]),
                    torch_nn.BatchNorm2d(48, affine=False),

                    torch_nn.Conv2d(48, 96, [1, 1], 1, padding=[0, 0]),
                    MaxFeatureMap2D(),
                    torch_nn.BatchNorm2d(48, affine=False),
                    torch_nn.Conv2d(48, 128, [3, 3], 1, padding=[1, 1]),
                    MaxFeatureMap2D(),

                    torch.nn.MaxPool2d([2, 2], [2, 2]),

                    torch_nn.Conv2d(64, 128, [1, 1], 1, padding=[0, 0]),
                    MaxFeatureMap2D(),
                    torch_nn.BatchNorm2d(64, affine=False),
                    torch_nn.Conv2d(64, 64, [3, 3], 1, padding=[1, 1]),
                    MaxFeatureMap2D(),
                    torch_nn.BatchNorm2d(32, affine=False),

                    torch_nn.Conv2d(32, 64, [1, 1], 1, padding=[0, 0]),
                    MaxFeatureMap2D(),
                    torch_nn.BatchNorm2d(32, affine=False),
                    torch_nn.Conv2d(32, 64, [3, 3], 1, padding=[1, 1]),
                    MaxFeatureMap2D(),
                    torch_nn.MaxPool2d([2, 2], [2, 2]),

                    torch_nn.Dropout(0.7)
                )
            )

            self.m_before_pooling.append(
                torch_nn.Sequential(
                    BLSTMLayer((lfcc_dim//16) * 32, (lfcc_dim//16) * 32),
                    BLSTMLayer((lfcc_dim//16) * 32, (lfcc_dim//16) * 32)
                )
            )

            self.m_output_act.append(
                torch_nn.Linear((lfcc_dim // 16) * 32, self.v_emd_dim)
            )

            self.m_frontend.append(
                LFCC(self.frame_lens[idx],
                    self.frame_hops[idx],
                    self.fft_n[idx],
                    self.m_target_sr,
                    self.lfcc_dim[idx],
                    with_energy=True,
                    max_freq=self.lfcc_max_freq)
            )

        self.m_frontend = torch_nn.ModuleList(self.m_frontend)
        self.m_transform = torch_nn.ModuleList(self.m_transform)
        self.m_output_act = torch_nn.ModuleList(self.m_output_act)
        self.m_before_pooling = torch_nn.ModuleList(self.m_before_pooling)

        # done
        return

    def prepare_mean_std(self, in_dim, out_dim, args, data_mean_std=None):
        """ prepare mean and std for data processing
        This is required for the Pytorch project, but not relevant to this code
        """
        if data_mean_std is not None:
            in_m = torch.from_numpy(data_mean_std[0])
            in_s = torch.from_numpy(data_mean_std[1])
            out_m = torch.from_numpy(data_mean_std[2])
            out_s = torch.from_numpy(data_mean_std[3])
        else:
            in_m = torch.zeros([in_dim])
            in_s = torch.ones([in_dim])
            out_m = torch.zeros([out_dim])
            out_s = torch.ones([out_dim])

        return in_m, in_s, out_m, out_s

    def normalize_input(self, x):
        """ normalizing the input data
        This is required for the Pytorch project, but not relevant to this code
        """
        return (x - self.input_mean) / self.input_std

    def normalize_target(self, y):
        """ normalizing the target data
        This is required for the Pytorch project, but not relevant to this code
        """
        return (y - self.output_mean) / self.output_std

    def denormalize_output(self, y):
        """ denormalizing the generated output from network
        This is required for the Pytorch project, but not relevant to this code
        """
        return y * self.output_std + self.output_mean

    def _front_end(self, wav, idx, trunc_len, datalength):
        """ simple fixed front-end to extract features

        input:
        ------
          wav: waveform
          idx: idx of the trial in mini-batch
          trunc_len: number of frames to be kept after truncation
          datalength: list of data length in mini-batch

        output:
        -------
          x_sp_amp: front-end featues, (batch, frame_num, frame_feat_dim)
        """

        with torch.no_grad():
            x_sp_amp = self.m_frontend[idx](wav.squeeze(-1))

        # return
        return x_sp_amp

    def _compute_embedding(self, x, datalength):
        """ definition of forward method
        Assume x (batchsize, length, dim)
        Output x (batchsize * number_filter, output_dim)
        """
        # number of sub models
        batch_size = x.shape[0]

        # buffer to store output scores from sub-models
        output_emb = torch.zeros([batch_size * self.v_submodels,
                                  self.v_emd_dim],
                                  device=x.device, dtype=x.dtype)

        # compute scores for each sub-models
        for idx, (fs, fl, fn, trunc_len, m_trans, m_be_pool, m_output) in \
            enumerate(
                zip(self.frame_hops, self.frame_lens, self.fft_n,
                    self.v_truncate_lens, self.m_transform,
                    self.m_before_pooling, self.m_output_act)):

            # extract front-end feature
            x_sp_amp = self._front_end(x, idx, trunc_len, datalength)

            # compute scores
            #  1. unsqueeze to (batch, 1, frame_length, fft_bin)
            #  2. compute hidden features
            hidden_features = m_trans(x_sp_amp.unsqueeze(1))

            #  3. (batch, channel, frame//N, feat_dim//N) ->
            #     (batch, frame//N, channel * feat_dim//N)
            #     where N is caused by conv with stride
            hidden_features = hidden_features.permute(0, 2, 1, 3).contiguous()
            frame_num = hidden_features.shape[1]
            hidden_features = hidden_features.view(batch_size, frame_num, -1)

            #  4. pooling
            #  4. pass through LSTM then summing
            hidden_features_lstm = m_be_pool(hidden_features)

            #  5. pass through the output layer
            tmp_emb = m_output((hidden_features_lstm + hidden_features).mean(1))

            output_emb[idx * batch_size: (idx+1) * batch_size] = tmp_emb

        return output_emb

    def _compute_score(self, feature_vec, inference=False):
        """
        """
        # feature_vec is [batch * submodel, 1]
        if inference:
            return feature_vec.squeeze(1)
        else:
            return torch.sigmoid(feature_vec).squeeze(1)
