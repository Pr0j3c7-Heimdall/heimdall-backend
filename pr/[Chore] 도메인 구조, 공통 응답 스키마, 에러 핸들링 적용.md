## 🔗 Main Context

- 도메인 구조, 공통 응답 스키마, 에러 핸들링 적용

## 🔑 Key Changes

### 도메인 구조
- auth 도메인: model, schema, repository, service, router 폴더
- User 모델 (id, email, password, name, created_at, updated_at)

### 공통 응답 스키마
- 성공: `{ "success": true, "data": ... }`
- 실패: `{ "success": false, "error": { "message": "...", "code": "..." } }`
- `SuccessResponse`, `ErrorResponse` 스키마 사용, `response_model` 적용

### 에러 핸들링
- HTTPException, RequestValidationError 통합 핸들러
- BaseAppException, BadRequestException, NotFoundException 등
- HTTP 상태코드/에러코드 상수 (constant.py)

## 📝 Memo
- **성공 응답**: `response_model=SuccessResponse`, `return SuccessResponse(data=...)`
- **에러**: `raise NotFoundException("메시지")` 형태로 사용
- **에러 code**: optional이라 필요할 때만 지정
- **새 도메인**: auth 구조 참고해서 model, schema, repository, service, router 추가
- **상수**: `app/common/constant`에서 HTTP_, 에러 code import