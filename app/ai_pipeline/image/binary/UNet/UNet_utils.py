"""
UNet 특징 추출 및 이미지 전처리 유틸리티
Stable Diffusion v1.5 모델을 로드하여 이미지의 잠재 공간 및 UNet 디코더 특징을 추출합니다.
"""

import torch
from diffusers import StableDiffusionPipeline
from torchvision import transforms

def get_transform():
    """UNet 분석을 위한 이미지 전처리 파이프라인을 반환합니다. (512x512)"""
    return transforms.Compose([
        transforms.Resize((512, 512)),
        transforms.ToTensor(),
        transforms.Normalize([0.5], [0.5])
    ])

class FeatureExtractor:
    """Stable Diffusion UNet을 사용한 특징 추출기 클래스"""

    def __init__(self, device: str = 'cuda'):
        """
        특징 추출기 초기화 및 모델 로드
        :param device: 실행 장치 (cuda 또는 cpu)
        """
        self.device = device
        
        # SDM v1.5 파이프라인 로드
        self.pipe = StableDiffusionPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
        )
        
        if torch.cuda.is_available():
            self.pipe.enable_model_cpu_offload()
        
        self.pipe.set_progress_bar_config(disable=True)
        self.unet = self.pipe.unet
        self.vae = self.pipe.vae
        
        self.features = {}
        self._register_hooks()

    def _hook_fn(self, module, input, output):
        """UNet의 특정 레이어(디코더의 16x16 해상도 지점)에서 특징을 캡처하는 훅"""
        self.features['decoder_16'] = torch.mean(output, dim=(2, 3))

    def _register_hooks(self):
        """특징 추출을 위해 UNet 레이어에 훅을 등록합니다."""
        # up_blocks[0]의 출력 특징을 사용
        layer_to_hook = self.unet.up_blocks[0]
        layer_to_hook.register_forward_hook(self._hook_fn)

    @torch.no_grad()
    def extract_features_batch(self, images_tensor: torch.Tensor) -> torch.Tensor:
        """
        이미지 텐서 묶음에서 UNet 특징을 추출합니다.
        :param images_tensor: 전처리된 이미지 텐서
        :return: 추출된 특징 텐서
        """
        pipeline_device = self.pipe.device
        images_tensor = images_tensor.to(pipeline_device)

        if self.pipe.dtype == torch.float16:
            images_tensor = images_tensor.half()

        # VAE를 통한 이미지 인코딩 (결정론적 결과를 위해 mode() 사용)
        latents = self.vae.encode(images_tensor).latent_dist.mode()
        latents = latents * self.vae.config.scaling_factor

        batch_size = images_tensor.shape[0]
        timesteps = torch.zeros((batch_size,), device=pipeline_device, dtype=torch.long)
        
        # 텍스트 인코더에 빈 입력 전달 (Unconditioned 특징)
        dummy_text_input = self.pipe.tokenizer(
            [""] * batch_size, 
            return_tensors="pt", 
            padding="max_length", 
            max_length=self.pipe.tokenizer.model_max_length, 
            truncation=True
        )
        encoder_hidden_states = self.pipe.text_encoder(dummy_text_input.input_ids.to(pipeline_device))[0]
        
        if self.pipe.dtype == torch.float16:
            encoder_hidden_states = encoder_hidden_states.half()

        # UNet 순전파 (훅을 통해 특징이 저장됨)
        self.unet(latents, timesteps, encoder_hidden_states=encoder_hidden_states)
        
        # 캡처된 특징 반환
        return self.features['decoder_16'].float().cpu()
