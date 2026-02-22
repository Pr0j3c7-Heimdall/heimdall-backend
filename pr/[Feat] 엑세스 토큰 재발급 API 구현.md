## 🔗 Main Context
액세스 토큰 재발급 API(`POST /api/v1/auth/refresh`)를 추가했습니다. 클라이언트가 보유한 refresh token으로 새로운 access token과 refresh token을 발급하며, 기존 refresh token은 토큰 로테이션 방식으로 무효화합니다.


## 🔑 Key Changes
### 1. 스키마 추가 (`app/auth/schema/`)

- **RefreshRequest**
    - `refreshToken` (alias)
    - `populate_by_name`으로 camelCase 요청 지원
    - 재발급 API 요청 바디 검증용
- **RefreshResponse**
    - `accessToken`, `refreshToken` (alias)
    - 재발급 API 응답 스키마
- **schema `__init__`**
    - `RefreshRequest`, `RefreshResponse` export 추가

### 2. AuthService (`app/auth/service/auth_service.py`)

- **`refresh(request)`**
    - DB에서 `find_valid_by_token`으로 유효한 refresh token 조회 (만료 전만)
    - 토큰 로테이션: `delete_by_token`으로 기존 토큰 삭제
    - `create_access_token(rt_entity.user_id)` 호출
    - `create_refresh_token()` 호출
    - `refresh_token_repository.create`로 새 refresh token DB 저장 (만료 14일)
    - 유효하지 않거나 만료된 경우 `None` 반환
    - 반환: `(access_token, refresh_token) | None`

### 3. 라우터 (`app/auth/router.py`)

- **`POST /api/v1/auth/refresh`**
    - Request: `RefreshRequest` 바디
    - `AuthService`는 `Depends(get_auth_service)`로 주입
    - `service.refresh(request)` 호출
    - 성공: `SuccessResponse(data={accessToken, refreshToken})`
    - 실패: `UnauthorizedException("유효하지 않거나 만료된 리프레시 토큰입니다")` → 401

### 4. 의존성 (`app/auth/dependencies.py`)

- 기존 `get_auth_service` 의존성 그대로 사용 (추가 변경 없음)


## 📝 Memo
> • **토큰 로테이션**: 재발급 시 기존 refresh token은 즉시 무효화되고, 새 refresh token을 클라이언트에 저장해야 함
• **토큰 저장**: DB에는 `SHA256(token_hash)`만 저장하고, raw refresh token은 클라이언트에만 보관
• **클라이언트 흐름**: 로그인 → accessToken + refreshToken 수신 → accessToken 만료 시 `/auth/refresh`로 재발급 → 새 accessToken, refreshToken으로 교체
>

설명 | 스크린샷
-- | --
엑세스토큰 재발급 API | <img width="1024" height="493" alt="image" src="https://github.com/user-attachments/assets/5fea4070-4932-44ab-9bd8-f1778748afd2" />
유효하지 않은 토큰 입력 시 | <img width="1027" height="445" alt="image" src="https://github.com/user-attachments/assets/e73f2618-e622-47a3-b55d-6ef308f60f0f" />
