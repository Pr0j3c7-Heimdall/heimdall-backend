# 🔗 Main Context

- **Heimdall API** 기초 세팅
- FastAPI + MySQL + SQLAlchemy(ORM) 비동기 연동
- auth 도메인 구조 (User 모델, 타입별 폴더)

# 🔑 Key Changes

### 1. 의존성 (requirements.txt)

- FastAPI, uvicorn
- SQLAlchemy, aiomysql (MySQL 비동기 ORM)
- python-dotenv, email-validator
- passlib[bcrypt], python-jose (Auth용, 추후 사용)

### 2. 프로젝트 구조

```
app/
├── auth/                    # auth 도메인
│   ├── model/               # DB 모델
│   │   └── user.py
│   ├── schema/
│   ├── repository/
│   ├── service/
│   └── router.py
└── database.py              # DB 연결 설정

```

### 3. User 모델

- id (BIGINT, PK, auto increment)
- email, password, name
- created_at, updated_at

### 4. API 엔드포인트

- `GET /` - 루트
- `GET /health` - 서버 상태
- `GET /db-health` - DB 연결 확인
- `GET /docs` - Swagger 문서

### 5. 기타

- `.env.example` - 환경변수 템플릿
- `.gitignore` - venv, .env, Python cache 등
- `scripts/commit.sh` - 파일별 분리 커밋 스크립트

---

## 🚀 실행 방법

### 사전 준비 (Mac / Windows 공통)

### 1. Python 3.10+ 확인

```bash
python --version
```

### 2. MySQL 설치 및 실행

|  | Mac | Windows |
| --- | --- | --- |
| 설치 | `brew install mysql` | [MySQL 설치](https://dev.mysql.com/downloads/installer/) |
| 실행 | `brew services start mysql` | 서비스에서 MySQL 시작 |

### 3. DB 생성

```sql
CREATE DATABASE heimdall CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

---

### Mac

```bash
cd heimdall-backend

# 가상환경 생성 (최초 1회)
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# .env 생성 및 수정
cp .env.example .env
# DATABASE_URL=mysql+aiomysql://root:비밀번호@localhost:3306/heimdall

# 서버 실행
 uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

```

---

### Windows

```bash
cd heimdall-backend

# 가상환경 생성 (최초 1회)
python -m venv venv

# 가상환경 활성화
venv\\Scripts\\activate

# 의존성 설치
pip install -r requirements.txt

# .env 생성 및 수정
copy .env.example .env
# DATABASE_URL=mysql+aiomysql://root:비밀번호@localhost:3306/heimdall

# 서버 실행
 uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

```

---

### 실행 후 확인

| 확인 | 사진 |
| --- | --- |
| [http://localhost:8000](http://localhost:8000/) - 루트 | <img width="440" height="150" alt="image" src="https://github.com/user-attachments/assets/039bd247-8926-4b7e-91f7-92c2a99b8426" /> |
| http://localhost:8000/docs - Swagger UI | <img width="1478" height="425" alt="image" src="https://github.com/user-attachments/assets/2c2155f1-2260-4265-a47e-83ba407d3e65" /> |
| http://localhost:8000/db-health - DB 연결 확인 | <img width="366" height="149" alt="image" src="https://github.com/user-attachments/assets/61d93447-af62-4032-ada5-e738838f7e0d" /> |

---

# 📝 Memo
- **init_db**: 앱 시작 시 `user` 테이블 자동 생성
- **기존 테이블 있을 때**: `DROP TABLE IF EXISTS user;` 후 재실행
- **가상환경** 반드시 활성화 후 `pip install` 권장