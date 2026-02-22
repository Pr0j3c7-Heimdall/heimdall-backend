## 🔗 Main Context
- 로그아웃 API를 구현했습니다. refresh token 삭제와 access token 블랙리스트 등록을 위한 구조를 추가하고, 추후 Redis로 확장 가능하도록 설계했습니다.

## 🔑 Key Changes
- **POST /api/v1/auth/logout** 추가
  - refresh token DB 삭제
  - access token 블랙리스트 등록 준비 (`TokenBlacklistRepository` 인터페이스 + Null 구현, 추후 Redis로 교체 가능)
- TokenBlacklistRepository 프로토콜 및 Null 구현 추가
- LogoutRequest 스키마 추가 (`refreshToken` 필수, `accessToken` 선택)
- AuthService.logout() 구현

## 📝 Memo

설명 | 스크린샷
-- | --
로그아웃 | <img width="2072" height="910" alt="image" src="https://github.com/user-attachments/assets/e9e49058-462e-4a81-b593-811bb5ad5e8d" />


<!-- notionvc: 35a92959-2e77-47b1-bdee-a1cc5f264571 -->
- 로그아웃은 idempotent 처리 (refresh token 없음/만료 시에도 200 OK 반환)
- `TokenBlacklistRepository`는 현재 Null 구현이 주입되며, Redis 도입 시 `get_token_blacklist_repository` 구현체만 교체하면 됨