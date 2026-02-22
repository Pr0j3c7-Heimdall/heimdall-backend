## 🔗 Main Context
- 회원 탈퇴 API 구현 (soft delete 기반)
- JWT 인증을 사용하는 DELETE /auth/me 엔드포인트 추가
- User 모델에 status, deleted_at 필드로 탈퇴 상태 관리

---

## 🔑 Key Changes

### 회원 탈퇴 API (DELETE /api/v1/auth/me)
- `Authorization: Bearer {accessToken}` 필수
- refresh token 전체 삭제, access token 블랙리스트 등록
- User soft delete: status=DELETED, deleted_at 저장

### User 모델
- `status` (ACTIVE/DELETED), `deleted_at` 컬럼 추가
- `password` 컬럼 제거 (소셜 로그인만 사용)

### 기타
- `UserStatus` 상수, `AccountDeletedError` 도메인 예외
- `UserRepository.find_by_id`, `withdraw` 추가
- `RefreshTokenRepository.delete_by_user_id` 추가
- `get_current_user_credentials` 의존성 (JWT 검증)

---

## 📝 Memo
- 회원 탈퇴는 idempotent 처리
- access token 블랙리스트는 `TokenBlacklistRepository` Null 구현 사용, 추후 Redis 전환 시 구현체만 교체 예정