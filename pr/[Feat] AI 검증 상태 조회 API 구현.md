## 🔗 Main Context
- 이미지 업로드 API 구현 (`GET  /api/v1/images/{image_id}/status`)

## 🔑 Key Changes

### 1. 이미지 분석 상태 관리 모델 도입
- `app/image/model/image_analysis_summary.py`: `ImageAnalysisSummary` 테이블을 추가하여 분석 상태(`analysis_status`), AI 여부(`final_is_ai`), 분석 완료 시간 등을 관리합니다.
- `Image` 모델과 1:1 관계를 형성합니다.

### 2. 이미지 상태 조회 API 구현
- `GET /images/{image_id}/status`: 특정 이미지의 AI 분석 상태를 조회할 수 있는 엔드포인트를 추가했습니다.
- `app/image/router.py`: 이미지 소유자 확인 기능 및 서비스 연동 로직을 구현했습니다.

### 3. 리포지토리 및 서비스 로직 고도화
- `app/image/repository/image_repository.py`:
  - 이미지 업로드 시 초기 분석 상태(`PENDING`) 레코드 생성 로직 추가.
  - 소유권 확인 기능이 포함된 `get_image_status_and_check_owner` 메서드 구현.
  - 상태 업데이트를 위한 `update_image_status` 메서드 구현.
- `app/image/service/image_service.py`:
  - `_run_ai_validation` 백그라운드 태스크에서 비동기 세션을 사용하여 실제 DB의 분석 상태를 `COMPLETED`로 업데이트하도록 개선했습니다. (60초 지연 시뮬레이션 포함)

### 4. 스키마 및 예외 처리
- `app/image/schema/response/status.py`: 상태 응답을 위한 데이터 모델(`ImageStatusResponse`, `ImageStatusData`) 정의.
- `app/image/exception/image_exception.py`: 타인의 이미지 상태 조회를 방지하기 위해 `ImageAccessDeniedException` 예외를 추가했습니다.


## 📝 Memo
> 현재 AI 분석 로직은 60초 지연 후 `COMPLETED`로 상태만 변경하는 시뮬레이션 단계입니다. 실제 분석 로직(DINOv3 등)은 추후 연동이 필요합니다.
