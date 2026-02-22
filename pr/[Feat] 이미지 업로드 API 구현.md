## 🔗 Main Context
- 이미지 업로드 API 구현 (`POST /api/v1/images/upload`)
- JWT 인증을 통해 사용자를 식별하고, 업로드된 이미지를 사용자별로 관리합니다.
- 파일 저장 후 비동기 AI 검증 작업을 트리거하는 구조를 포함합니다.

---

## 🔑 Key Changes

### 1. Image 도메인 신설 (`app/image`)
- **API Endpoint**: `POST /api/v1/images/upload`
- **Model**: `Image` (images 테이블: user_id, filename, filepath, image_url 등)
- **Repository**: `ImageRepository` (파일 저장 및 DB 레코드 생성)
- **Service**: `ImageService` (업로드 비즈니스 로직, 파일 유효성 검사, 비동기 작업 호출)
- **Schema**: `ImageUploadResponse`, `ImageUploadData` 등 요청/응답 스키마
- **Dependencies**: `get_image_service`, `get_image_repository`
- **Exception**: `InvalidImageFileException`, `ImageNotFoundException` 등

### 2. 파일 저장 로직
- **저장 위치**: `{UPLOAD_DIR}/{user_id}/` (사용자별 디렉토리)
- **파일 이름**: UUID를 사용하여 고유한 파일명 생성 (`{uuid}.{extension}`)
- **URL 생성**: `{BASE_URL}/uploads/{user_id}/{unique_filename}` 형식의 접근 URL을 생성하여 DB에 저장합니다.

### 3. 비동기 처리
- `BackgroundTasks`를 사용하여 이미지 저장 후 AI 검증 로직(`_run_ai_validation`)을 비동기로 실행합니다.
- 현재 AI 검증은 5초 지연을 시뮬레이션하는 임시 함수입니다.

### 4. 인증
- `Authorization: Bearer {accessToken}` 헤더를 통해 사용자를 인증하고, `user_id`를 이미지 레코드와 파일 경로에 사용합니다.

---

### 실행 후 확인

| 설명 | 사진 |
| --- | --- |
| 로그인을 하지 않고 파일을 업로드 할 때 | <img width="306" height="133" alt="로그인하지 않고 사진 업로드" src="https://github.com/user-attachments/assets/7c1ec9a3-331f-4b4a-8609-dc1238a6320e" /> |
| 지원하지 않는 파일을 업로드 할 때 | <img width="470" height="136" alt="txt같이 지원하지 않는 파일을 올렸을 때" src="https://github.com/user-attachments/assets/31bb2da2-25a6-4818-9bdf-977394e9e812" /> |
| jpg 업로드 확인 | <img width="771" height="159" alt="이미지 성공적으로 저장" src="https://github.com/user-attachments/assets/adf8aae7-c91d-4349-b034-89a55f37645e" /> |
| png 업로드 확인 | <img width="770" height="158" alt="이미지 성공적으로 저장2" src="https://github.com/user-attachments/assets/c0685d35-bb22-4bdc-beab-4d4026347406" /> |
| ./uploads/{user_id}에 이미지 저장 확인 | <img width="351" height="83" alt="업로드한 파일들이 user_id 폴더에 저장되는 것 확인" src="https://github.com/user-attachments/assets/ec57c357-695d-412f-a320-bb6544f54f61" /> |
| DB 저장 확인 | <img width="1321" height="96" alt="업로드한 파일들이 db에 제대로 저장되는 것 확인" src="https://github.com/user-attachments/assets/3e3b8451-23d5-4807-a9e6-69b4b12840fa" /> |

---

## 📝 Memo
- **환경변수 설정**: `.env` 파일에 이미지 업로드 디렉토리(`UPLOAD_DIR`)와 서비스 기본 URL(`BASE_URL`) 설정이 필요합니다.
- **파일 유효성 검사**: 현재 `image/jpeg`, `image/png`, `image/webp` 형식만 허용됩니다.
- **AI 검증**: `_run_ai_validation` 함수는 실제 AI 서비스 호출 로직으로 대체되어야 합니다.
- **정적 파일 서빙**: 업로드된 이미지에 접근하려면 FastAPI 앱에 정적 파일 마운트 설정이 필요합니다. (예: `app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")`)
