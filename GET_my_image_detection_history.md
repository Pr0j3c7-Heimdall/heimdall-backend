## API Description

마이페이지에서 사용자가 업로드한 파일들의 AI 검증 기록 목록을 조회합니다.
페이지네이션, 파일명 검색, 결과 및 타입 필터링 기능을 제공하여 프론트엔드의 검증 내역 화면을 완벽하게 지원합니다.

---

## Request

### Request Header

| 헤더 | 필수 | 설명 |
| --- | --- | --- |
| `Authorization` | O | `Bearer {accessToken}` |

### Path Variable / Query Parameter / Request Body

- **Method**: `GET`
- **URL**: `/api/v1/auth/me/history/image`
- **Path Variable**: 없음
- **Request Body**: 없음

**Query Parameter** (모두 선택적 파라미터입니다)

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| page | integer | X | 요청할 페이지 번호 (기본값: `1`) |
| size | integer | X | 한 페이지당 항목 수 (기본값: `10`) |
| keyword | string | X | 파일명 검색어 (예: `interview`) |
| file_type | string | X | 파일 타입 필터 (`image`, `audio`, 기본값: 전체) |
| result_type | string | X | 결과 필터 (`ai`, `real`, 기본값: 전체) |

---

## Flow

1. **인증 및 인가**: 클라이언트의 JWT를 검증하고, 토큰에서 `user_id`를 추출합니다.
2. **데이터베이스 조회**:
    - `images` 테이블과 `image_fimal_detection_results` 테이블을 `image_id` 기준으로 조인(Join)합니다.
    - `images.user_id`가 추출한 `user_id`와 일치하는 데이터만 필터링합니다.
3. **검색 및 필터링 적용**:
    - `keyword`가 존재하면 `images.filename`에 해당 문자열이 포함된(LIKE) 데이터만 남깁니다.
    - `result_type`이 `ai`면 `final_is_ai = true`, `real`이면 `final_is_ai = false` 인 데이터를 필터링합니다.
4. **정렬 및 페이징**: `images.created_at` 기준으로 최신순(DESC) 정렬한 뒤, `page`와 `size`에 맞게 데이터를 잘라서 반환합니다.

---

## Response

### ✅ Success

**200 Ok**

```json
{
  "success": true,
  "data": {
    "total_count": 42,
    "total_pages": 5,
    "current_page": 1,
    "histories": [
      {
        "image_id": 201,
        "filename": "photo.jpg",
        "file_type": "image",
        "analysis_status": "COMPLETED",
        "is_ai": false,
        "ai_probability": 0.08,
        "created_at": "2025-01-24T10:15:00Z"
      },
      {
        "image_id": 200,
        "filename": "art.png",
        "file_type": "image",
        "analysis_status": "COMPLETED",
        "is_ai": true,
        "ai_probability": 0.78,
        "created_at": "2025-01-23T09:00:00Z"
      }
    ]
  }
}
```

| **필드** | **타입** | **설명** |
| --- | --- | --- |
| success | boolean | 항상 `true` |
| data | object | 페이지네이션 및 목록 데이터 |
| data.total_count | integer | 조건에 맞는 전체 데이터 개수 |
| data.total_pages | integer | 전체 페이지 수 |
| data.current_page | integer | 현재 페이지 번호 |
| data.histories | array | 검증 내역 목록 (최신순) |
| data.histories[].history_id | biginteger | 분석 요약 테이블(`image_analysis_summary`)의 PK |
| data.histories[].image_id | biginteger | 원본 이미지(`images`)의 PK |
| data.histories[].filename | string | 사용자가 업로드한 원본 파일명 (UI '파일명' 매핑) |
| data.histories[].file_type | string | 파일 종류 (`image` 또는 `audio`) |
| data.histories[].analysis_status | string | 파이프라인 진행 상태 (`COMPLETED`, `PENDING` 등) |
| data.histories[].is_ai | boolean | 최종 AI 판별 결과 (`true`: AI, `false`: 자연) |
| data.histories[].ai_probability | float | AI 확률 (0.0 ~ 1.0). 프론트엔드에서 100을 곱해 %로 변환 (UI '신뢰도' 매핑) |
| data.histories[].created_at | string | 파일 업로드 날짜 및 시간 (ISO 8601, UI '날짜' 매핑) |

### ❌ Failure

**공통 구조**

**표준 에러 코드**

```python
{
  "success": false,
  "error": {
    "message": "에러 메시지",
    "code": "에러_코드"
  }
}`
```

| **필드** | **타입** | **설명** |
| --- | --- | --- |
| success | boolean | 항상 `false` |
| error | object | 에러 상세 정보 |
| error.message | string | 사용자에게 보여줄 메시지 |
| error.code | string | 에러 코드 (표준 코드 참고) |

**표준 에러 코드**

| **코드** | **설명** | **HTTP 상태** | **예시 message** |
| --- | --- | --- | --- |
| `BAD_REQUEST` | 잘못된 요청 | 400 | image_id 형식이 올바르지 않습니다 |
| `UNAUTHORIZED` | 인증 실패 | 401 | 인증되지 않은 사용자입니다 |
| `FORBIDDEN` | 접근 권한 부족 | 403 | 본인이 업로드한 이미지만 조회할 수 있습니다 |
| `NOT_FOUND` | 리소스 없음 | 404 | 분석이 완료되지 않았거나 이미지를 찾을 수 없습니다 |
| `INTERNAL_SERVER_ERROR` | 서버 내부 오류 | 500 | 서버 내부 오류가 발생했습니다 |

**에러 응답 예시**

**400 Bad Request**

```json
{
  "success": false,
  "error": {
    "message": "잘못된 요청입니다",
    "code": "BAD_REQUEST"
  }
}
```

**401 Unauthorized**

```json
{
  "success": false,
  "error": {
    "message": "인증되지 않은 사용자입니다",
    "code": "UNAUTHORIZED"
  }
}
```

**403 Forbidden**

```json
{
  "success": false,
  "error": {
    "message": "해당 리소스에 대한 접근 권한이 없습니다",
    "code": "FORBIDDEN"
  }
}
```

**404 Not Found**

```json
{
  "success": false,
  "error": {
    "message": "요청하신 이미지 또는 분석 결과를 찾을 수 없습니다",
    "code": "NOT_FOUND"
  }
}
```

**500 Internal Server Error**

```json
{
  "success": false,
  "error": {
    "message": "서버 내부 오류가 발생했습니다",
    "code": "INTERNAL_SERVER_ERROR"
  }
}
```