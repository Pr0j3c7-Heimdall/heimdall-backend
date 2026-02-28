# Heimdall AI Backend

## 실행 방법

### 1. 가상환경 설정 및 의존성 설치

```bash
cd heimdall-backend

# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate
# 가상환경 활성화 (Mac/Linux)
source venv/bin/activate

# 필수 패키지 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정 (.env)

`notion` > `개발` > `.env` 참고

### 3. AI 모델 가중치 배치

정상적인 분석을 위해 아래 경로에 각 모델의 학습된 가중치(`.pth`) 파일이 있어야 합니다.
[여기](https://drive.google.com/file/d/1_nj67GnQBYgBYem8DVS8YVm9lFI99Yss/view?usp=sharing)에서 다운로드 받은 후 해당 경로에 넣어주세요.

- **DINOv3 이진분류**: `app/ai_pipeline/image/binary/DINOv3/weights/DINOv3_binary.pth`
- **F3Net 이진분류**: `app/ai_pipeline/image/binary/F3Net/weights/F3Net_binary.pth`
- **UNet 이진분류**: `app/ai_pipeline/image/binary/UNet/weights/UNet_binary.pth`

- **DINOv3 다중 분류**: `app/ai_pipeline/image/multiclass/DINOv3/weights/DINOv3_multi.pth`
- **F3-Net 다중 분류**: `app/ai_pipeline/image/multiclass/F3Net/weights/F3Net_multi.pth`
- **UNet 다중 분류**: `app/ai_pipeline/image/multiclass/UNet/weights/UNet_multi.pth`

### 4. MySQL 설치 및 실행

|  | Mac | Windows | Linux |
| --- | --- | --- | --- |
| 설치 | `brew install mysql` | [MySQL 설치](https://dev.mysql.com/downloads/installer/) | `install mysql-server` |
| 실행 | `brew services start mysql` | 서비스에서 MySQL 시작 | `service mysql start` |

```sql
-- DB 생성
CREATE DATABASE heimdall CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 5. Hugging Face 로그인 하기

1. Hugging Face 사이트에 로그인

2. `Setting` > `Access Tokens` > `+Create new token`

3. 발급받은 토큰 복사
<img width="600" height="300" alt="Token Example" src="https://github.com/user-attachments/assets/912c6f7d-01a4-462f-8e27-7bc6d38e92b1" />

4. cli에서 로그인하기

    - cli에 ```hf auth login``` 입력
    - email 입력 > 복사한 토큰 붙여넣기


### 6. 서버 실행

```bash
# 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
