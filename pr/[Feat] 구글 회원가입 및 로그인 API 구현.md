## 🔗 Main Context

구글 로그인·회원가입 API(POST /api/v1/auth/login)를 구현했습니다. 구글 ID Token 검증, 자동 가입, JWT 토큰 발급까지 포함하며, 세션·캐시 관련은 추후 Redis 도입을 검토할 예정입니다.

---

## 🔑 Key Changes

### 1. API

| 구분 | 내용 |
| --- | --- |
| **엔드포인트** | `POST /api/v1/auth/login` |
| **Request** | `provider`, `idToken` (구글 ID Token) |
| **Response** | `accessToken`, `refreshToken`, `isNewUser` |
| **에러** | 400 (provider 검증), 401 (ID Token 검증 실패) |

---

### 2. Auth 도메인

**모델**

- **User**
    - 테이블: `users` (MySQL `user` 예약어 회피)
    - 필드: email, name, provider, provider_sub, password(nullable)
    - 제약: provider + provider_sub 유니크
- **RefreshToken**
    - 테이블: `refresh_token`
    - 필드: user_id (FK), token_hash (SHA256), expires_at

**리포지토리**

- UserRepository: `find_by_provider_sub`, `create`
- RefreshTokenRepository: `create`, `find_valid_by_token`, `delete_by_token`

**서비스**

- AuthService: 구글 ID Token 검증 → 기존 유저 조회 / 없으면 신규 가입 → 토큰 발급
- accessToken: JWT, 24시간
- refreshToken: 64바이트 랜덤, 14일 유효

---

### 4️⃣ 인프라 / 설정

| 구분 | 내용 |
| --- | --- |
| CORS | localhost:3000, credentials 허용 |
| DB | `init_db`로 users, refresh_token 테이블 자동 생성 |
| 환경변수 | .env.example (GOOGLE_CLIENT_ID, JWT_SECRET_KEY 등) |
| 의존성 | google-auth, python-jose, passlib 등 추가 |
| 테스트 | pytest, TestClient fixture 추가 |

---

## 📝 Memo

- `users` 테이블 사용 (MySQL `user` 예약어 회피)
- 현재 `google` provider만 지원
- refreshToken 갱신 API는 추후 구현 예정
- 에러 응답은 `error` 키 사용 (템플릿 `details` 형식과 다름)

설명 | 스크린샷
-- | --
구글 로그인 및 회원가입 API | <img width="2048" height="1218" alt="image" src="https://github.com/user-attachments/assets/eed1f6fb-84ba-4f29-8772-a1f99f8db065" />
users 테이블 확인 | <img width="1138" height="158" alt="image" src="https://github.com/user-attachments/assets/428ad95b-7cc6-498a-9603-9d876be6f5d4" />
token 테이블 확인 | <img width="1486" height="222" alt="image" src="https://github.com/user-attachments/assets/0598853f-1ad8-4c7b-a211-954d4c3b7a1f" />


<!-- notionvc: 37cd5440-563f-4dc6-b46b-fef00909b824 -->