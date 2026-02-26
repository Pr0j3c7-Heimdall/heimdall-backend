# [작업 목표]
다중 분류(Multiclass) 결과가 데이터베이스에 정상적으로 저장되지 않는 누락 버그를 해결합니다. Repository, Service, Pipeline 3개의 파일에 DB 저장 로직을 추가/수정합니다.

---

## Task 1. Repository에 Multiclass 저장 로직 추가
**Target File:** `app/detection/image/repository/image_detection_repository.py`
**Instructions:**
1. `DetectionRepository` 클래스 내부에 `save_multiclass_result(self, image_id: int, data_list: list)` 비동기 메서드를 추가하세요.
2. `data_list`를 반복문으로 돌면서 `ImageMulticlassDetectionResult` 모델 객체를 생성하여 `self.db_session.add()` 하세요.
3. 객체 생성 시 딕셔너리에서 `detection_method`, `predicted_model`, `confidence_score`, `result_json` 4개의 값을 매핑하세요.
4. 반복문이 끝나면 `await self.db_session.commit()`을 호출하여 한 번에 저장하세요.

---

## Task 2. Pipeline에서 Callback에 데이터 실어 보내기
**Target File:** `app/ai_pipeline/image/image_pipeline.py`
**Instructions:**
1. `execute_image_pipeline` 함수의 (Step 4) 블록 맨 아래에 있는 콜백 호출 부분을 수정하세요.
2. 기존 코드: `if progress_callback: await progress_callback(status="MULTICLASS_COMPLETED")`
3. 변경 코드: `status`뿐만 아니라 `data` 파라미터도 함께 넘기도록 수정하세요.
   `await progress_callback(status="MULTICLASS_COMPLETED", data={"multi": multi_res})`

---

## Task 3. Service 계층 Callback에 Multiclass DB 연동
**Target File:** `app/detection/image/service/image_detection_service.py`
**Instructions:**
1. `run_ai_detection` 내부의 `update_progress` 콜백 함수 로직에 분기문을 하나 더 추가하세요.
2. `data` 딕셔너리 안에 `"multi"` 키가 존재한다면 (`if data and "multi" in data:`), Task 1에서 만든 `await repo.save_multiclass_result(image_id, data["multi"])` 를 호출하도록 코드를 추가하세요.