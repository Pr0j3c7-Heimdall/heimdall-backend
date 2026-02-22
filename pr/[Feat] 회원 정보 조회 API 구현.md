## 🔗 Main Context
- User 도메인 분리 및 마이페이지 회원정보 조회 API 구현
- Auth와 User 관심사 분리, 라우터 구조 정리

---

## 🔑 Key Changes

### User 도메인 신설
- **model**: User, UserStatus (str Enum)
- **repository**: UserRepository (find_by_id, find_by_provider_sub, create, withdraw, restore)
- **schema**: MeResponse (name, email, createdAt)
- **service**: UserService.get_me()
- **router**: GET /api/v1/users/me (회원정보 조회)
- **dependencies**: get_user_repository, get_user_service

### Auth 도메인 정리
- User 모델, UserRepository 제거 후 User 도메인으로 이동
- Router 구조 변경: `router.py` → `router/auth.py`, `__init__.py`는 export만 담당
- User 관련 import를 `app.user`로 변경

### 의존성
- `get_user_repository`를 `app.user.dependencies`로 이동
- Auth는 User 도메인을 import해 사용

---

## 📝 Memo
- 마이페이지 관련 기능은 이후 User 도메인에서 확장 예정
- Auth 도메인은 RefreshToken 등 토큰/인증만 담당
- `GET /users/me`는 인증(Authorization: Bearer) 필요