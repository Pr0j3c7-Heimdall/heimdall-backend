## 🔗 Main Context
- 마이페이지 이미지 검증 기록 조회 API 구현 (`GET /api/v1/users/me/history/image`)

## 🔑 Key Changes

### 1. 마이페이지 이미지 검증 내역 조회 API 구현
- `GET /api/v1/users/me/history/image`: 사용자가 업로드한 이미지의 AI 검증 기록 목록을 조회할 수 있는 엔드포인트를 추가했습니다.
- 페이지네이션(`page`, `size`), 파일명 검색(`keyword`), 결과 필터(`result_type`) 기능을 지원하여 프론트엔드의 검증 내역 화면 요구사항을 충족합니다.

### 2. User 도메인 리포지토리 및 서비스 로직 확장
- `app/user/repository/user_repository.py`:
  - `images` 테이블과 `image_final_detection_results` 테이블을 조인하여 사용자의 검증 내역을 조회하는 `get_image_detection_history` 메서드를 구현했습니다.
  - `ilike`를 이용한 파일명 검색 및 `result_type`(`ai`/`real`) 필터링 로직을 포함합니다.
- `app/user/service/user_service.py`:
  - 리포지토리에서 가져온 데이터를 프론트엔드 요구사항에 맞게 가공하고, 전체 페이지 수(`total_pages`)를 계산하여 전달하는 `get_image_history` 비즈니스 로직을 구현했습니다.

### 3. 응답 스키마 정의
- `app/user/schema/response/history.py`: 검증 내역 목록 및 페이지네이션 정보(전체 개수, 현재 페이지 등)를 포함하는 데이터 모델(`ImageHistoryResponse`, `ImageHistoryData`, `ImageHistoryItem`)을 정의했습니다.

### 4. 도메인 중심 설계 및 응집도 강화
- 초기 설계 시 `auth` 또는 `detection` 도메인에 위치했던 마이페이지 관련 로직을 `user` 도메인으로 통합하여 유지보수성과 도메인 일관성을 높였습니다.

## 📝 Memo
> 현재는 이미지(`image`) 타입의 검증 내역만 지원합니다. 추후 오디오(`audio`) 등 다른 파일 타입에 대한 확장 가능성을 열어두어 `file_type` 파라미터 처리를 포함했습니다.
