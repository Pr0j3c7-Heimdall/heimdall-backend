# [작업 목표]
이미지 AI 다중 분류(Multiclass) 파이프라인 연동을 위해 F3-Net과 DINOv3의 다중 분류용 추론 클래스를 각각 생성하고, 파이프라인 매니저에 연결합니다. 명시된 파일 이외의 코드는 임의로 수정하지 마세요.

---

## Task 1. 다중 분류용 F3-Net 추론 클래스 신규 생성
**Target File:** `app/ai_pipeline/image/multiclass/F3Net/F3Net_inference.py`
**Instructions:**
1. 기존 이진 분류에 사용했던 F3Net 전처리 로직(DCT, LFS, FAD 등)과 동일하게 작동하는 `F3NetMulticlassDetector` 클래스를 만드세요.
2. `from .F3Net_models import DualStreamConvNeXt` 로 모델을 임포트하고, `num_classes=10`으로 초기화하세요.
3. 클래스 외부 상단에 학습 시 사용된 클래스 이름 리스트 `CLASS_NAMES`를 10개 정의하세요. (예: `["00_BigGAN", "01_Dalle-3", "02_Flux-1.1-pro", "03_Glide", "04_GPT-image-1", "05_Imagen-4.0", "06_Midjourney-V6", "07_Nano-Banana-Family", "08_SD3.5", "09_SDXL"]`)
4. `predict(self, image_path: str) -> dict` 메서드를 구현하세요:
   - 전처리된 텐서를 모델에 통과시킵니다.
   - `probs = torch.softmax(output, dim=1)[0]` 를 사용하여 10개 클래스에 대한 확률을 구합니다.
   - `torch.max(probs, dim=0)` 를 이용해 가장 높은 확률(`confidence`)과 인덱스(`predicted_idx`)를 추출합니다.
   - `CLASS_NAMES`에서 인덱스에 해당하는 모델 이름(`predicted_model`)을 가져옵니다.
   - 반환 딕셔너리 구조:
     ```python
     {
         "detection_method": "F3Net",
         "predicted_model": predicted_model,
         "confidence_score": confidence.item(),
         "result_json": {
             "all_probabilities": {CLASS_NAMES[i]: probs[i].item() for i in range(10)}
         }
     }
     ```

---

## Task 2. 다중 분류용 DINOv3 추론 클래스 신규 생성
**Target File:** `app/ai_pipeline/image/multiclass/DINOv3/DINOv3_inference.py`
**Instructions:**
1. 기존 이진 분류에 사용했던 `get_transform` 전처리 및 Hugging Face 모델 로드 로직과 동일하게 작동하는 `Dinov3MulticlassDetector` 클래스를 만드세요.
2. `from .DINOv3_mlp_model import DINOMlpClassifier` 로 다중 분류기를 임포트하고, `DINOMlpClassifier(input_dim=1024, num_classes=10)` 으로 초기화하세요.
3. 클래스 외부 상단에 Task 1과 동일한 `CLASS_NAMES` 리스트를 10개 정의하세요.
4. `predict(self, image_path: str) -> dict` 메서드를 구현하세요:
   - Hugging Face DINOv3로 특징(feature)을 추출한 뒤 MLP에 통과시킵니다. (5crop 평균화 처리 포함)
   - `probs = torch.softmax(logits, dim=1)[0]` 를 구하고, 가장 높은 확률과 인덱스를 추출하여 모델 이름을 매핑합니다.
   - 반환 딕셔너리 구조 (detection_method는 "DINOv3_MLP_Multi" 사용):
     ```python
     {
         "detection_method": "DINOv3",
         "predicted_model": predicted_model,
         "confidence_score": confidence.item(),
         "result_json": {
             "crop_type": self.crop_type,
             "all_probabilities": {CLASS_NAMES[i]: probs[i].item() for i in range(10)}
         }
     }
     ```

---

## Task 3. 파이프라인 매니저에 Multiclass 연결 및 앙상블 로직 추가
**Target File:** `app/ai_pipeline/image/image_pipeline.py`
**Instructions:**
1. 상단에 방금 만든 2개의 다중 분류기를 임포트하세요. 
   - `from .multiclass.F3Net.F3Net_inference import F3NetMulticlassDetector`
   - `from .multiclass.DINOv3.DINOv3_inference import Dinov3MulticlassDetector`
2. 전역 변수에 두 모델을 메모리에 적재하세요. (가중치 경로는 알아서 유추하되 파일 누락 시 에러가 나지 않도록 try-except로 감싸세요)
3. 모의 함수였던 `run_multiclass_detection(image_path: str)` 내부를 실제 로직으로 변경하세요:
   - 두 모델의 `predict` 메서드를 각각 호출합니다.
   - 두 결과를 담은 리스트를 반환합니다. `return [f3net_res, dinov3_res]`
4. `execute_image_pipeline` 함수의 **(Step 4) 다중 분류 검사** 분기문 안을 다음과 같이 업데이트하세요:
   - 콜백 호출: `if progress_callback: await progress_callback(status="MULTICLASS_PROCESSING", data=None)`
   - `run_multiclass_detection` 호출 후 `pipeline_result["multi"]`에 할당.
   - 🌟 앙상블 로직: 반환된 결과 리스트에서 `confidence_score`가 가장 높은 딕셔너리를 찾습니다. 해당 딕셔너리의 `predicted_model` 값을 `pipeline_result["final_result"]["final_generator_model"]` 에 할당하세요. (단, 결과 리스트가 비어있지 않은 경우에만 수행)
    
    
