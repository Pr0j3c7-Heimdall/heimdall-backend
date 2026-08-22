import pytest
from unittest.mock import AsyncMock, patch
from app.ai_pipeline.image.image_pipeline import execute_image_pipeline

# patch()는 async 함수를 자동으로 AsyncMock으로 대체하므로, return_value에 코루틴이나
# Future가 아니라 "await 결과값"을 그대로 넣어야 한다.


@pytest.mark.asyncio
async def test_execute_image_pipeline_c2pa_compliant():
    # C2PA가 충족된 경우의 테스트
    mock_c2pa_data = {
        "is_c2pa_compliant": True,
        "created_model": "C2PA_Model"
    }

    mock_multi_res = [
        {"predicted_model": "Multi_Model_A", "confidence_score": 0.8},
        {"predicted_model": "Multi_Model_B", "confidence_score": 0.9}
    ]

    with patch("app.ai_pipeline.image.image_pipeline.run_c2pa_analysis", return_value=mock_c2pa_data) as mock_c2pa, \
         patch("app.ai_pipeline.image.image_pipeline.run_binary_detection") as mock_binary, \
         patch("app.ai_pipeline.image.image_pipeline.run_multiclass_detection", return_value=mock_multi_res) as mock_multi:

        progress_callback = AsyncMock(return_value=None)

        result = await execute_image_pipeline("test_path", progress_callback)

        # 검증
        # 1. C2PA 분석은 실행되어야 함
        mock_c2pa.assert_called_once()

        # 2. 이진 분류는 실행되지 않아야 함 (C2PA 충족 시 건너뜀)
        mock_binary.assert_not_called()

        # 3. 다중 분류는 실행되어야 함 (final_is_ai가 True이므로)
        mock_multi.assert_called_once()

        # 4. 결과값 확인
        assert result["final_result"]["final_is_ai"] is True
        assert result["final_result"]["final_ai_probability"] == 1.0
        assert result["final_result"]["final_generator_model"] == "Multi_Model_B" # confidence_score가 높은 것
        assert result["final_result"]["requires_multiclass"] is True


@pytest.mark.asyncio
async def test_execute_image_pipeline_not_c2pa_compliant_ai():
    # C2PA 미충족, 이진 분류 결과 AI인 경우
    mock_c2pa_data = {"is_c2pa_compliant": False}
    mock_binary_data = {
        "binary_list": [{"method": "DINO", "confidence_score": 0.9}],
        "avg_ai_prob": 0.9,
        "final_is_ai": True
    }
    mock_multi_res = [{"predicted_model": "Multi_Model_A", "confidence_score": 0.8}]

    with patch("app.ai_pipeline.image.image_pipeline.run_c2pa_analysis", return_value=mock_c2pa_data) as mock_c2pa, \
         patch("app.ai_pipeline.image.image_pipeline.run_binary_detection", return_value=mock_binary_data) as mock_binary, \
         patch("app.ai_pipeline.image.image_pipeline.run_multiclass_detection", return_value=mock_multi_res) as mock_multi:

        result = await execute_image_pipeline("test_path")

        # 검증
        mock_c2pa.assert_called_once()
        mock_binary.assert_called_once()
        mock_multi.assert_called_once()

        assert result["final_result"]["final_is_ai"] is True
        assert result["final_result"]["final_ai_probability"] == 0.9
        assert result["final_result"]["final_generator_model"] == "Multi_Model_A"


@pytest.mark.asyncio
async def test_execute_image_pipeline_not_c2pa_compliant_not_ai():
    # C2PA 미충족, 이진 분류 결과 AI 아님
    mock_c2pa_data = {"is_c2pa_compliant": False}
    mock_binary_data = {
        "binary_list": [{"method": "DINO", "confidence_score": 0.1}],
        "avg_ai_prob": 0.1,
        "final_is_ai": False
    }

    with patch("app.ai_pipeline.image.image_pipeline.run_c2pa_analysis", return_value=mock_c2pa_data) as mock_c2pa, \
         patch("app.ai_pipeline.image.image_pipeline.run_binary_detection", return_value=mock_binary_data) as mock_binary, \
         patch("app.ai_pipeline.image.image_pipeline.run_multiclass_detection") as mock_multi, \
         patch("app.ai_pipeline.image.image_pipeline.extract_metadata", return_value={"Make": "TestCam"}) as mock_meta:

        result = await execute_image_pipeline("test_path")

        # 검증
        mock_c2pa.assert_called_once()
        mock_binary.assert_called_once()
        mock_multi.assert_not_called() # AI가 아니면 다중 분류 안함
        mock_meta.assert_called_once() # 대신 메타데이터를 추출함

        assert result["final_result"]["final_is_ai"] is False
        assert result["final_result"]["final_ai_probability"] == 0.1
        assert result["final_result"]["final_generator_model"] is None
        assert result["metadata"] == {"Make": "TestCam"}
