# 1. 베이스 이미지 설정: GLIBC 2.38 이상을 지원하는 최신 Debian Trixie 기반
FROM python:3.12-slim-trixie

# 2. 환경 변수 설정
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Seoul

# 3. 시스템 필수 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmagic1 \
    libgl1 \
    libglib2.0-0 \
    libimage-exiftool-perl \
    unzip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* 

# 4. 작업 디렉토리 설정
WORKDIR /app 

# 5. 파이썬 의존성 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip gdown && \
    pip install --no-cache-dir -r requirements.txt

# 6. 소스 코드 복사 (현재 폴더의 모든 파일을 /app으로 복사)
COPY . .

# 7. AI 가중치 및 c2patool 다운로드 (공용 볼륨 /shared_data 사용)
RUN mkdir -p /shared_data && \
    gdown --id 1_nj67GnQBYgBYem8DVS8YVm9lFI99Yss -O /shared_data/weights.zip && \
    unzip -o /shared_data/weights.zip -d /shared_data/ && \
    rm -f /shared_data/weights.zip && \
    gdown --id 165r1bSY2AlMgVADh3WdljKpK2XCCTDCX -O /shared_data/c2patool.zip && \
    unzip -o /shared_data/c2patool.zip -d /shared_data/ && \
    rm -f /shared_data/c2patool.zip && \
    chmod -R 777 /shared_data

# 8. 심볼릭 링크 생성
RUN mkdir -p /app/app/ai_pipeline/image/c2pa \
             /app/app/ai_pipeline/image/binary/DINOv3/weights \
             /app/app/ai_pipeline/image/binary/F3Net/weights \
             /app/app/ai_pipeline/image/binary/UNet/weights \
             /app/app/ai_pipeline/image/multiclass/DINOv3/weights \
             /app/app/ai_pipeline/image/multiclass/F3Net/weights \
             /app/app/ai_pipeline/image/multiclass/UNet/weights && \
    # c2patool 관련 링크
    ln -s /shared_data/c2patool/c2patool/anchors.pem /app/app/ai_pipeline/image/c2pa/anchors.pem && \
    ln -s /shared_data/c2patool/c2patool/c2patool /app/app/ai_pipeline/image/c2pa/c2patool && \
    # 이진 분류 모델 가중치 링크
    ln -s /shared_data/heimdall-pth/DINOv3_binary.pth /app/app/ai_pipeline/image/binary/DINOv3/weights/DINOv3_binary.pth && \
    ln -s /shared_data/heimdall-pth/F3Net_binary.pth /app/app/ai_pipeline/image/binary/F3Net/weights/F3Net_binary.pth && \
    ln -s /shared_data/heimdall-pth/UNet_binary.pth /app/app/ai_pipeline/image/binary/UNet/weights/UNet_binary.pth && \
    # 다중 분류 모델 가중치 링크 
    ln -s /shared_data/heimdall-pth/DINOv3_multi.pth /app/app/ai_pipeline/image/multiclass/DINOv3/weights/DINOv3_multi.pth && \
    ln -s /shared_data/heimdall-pth/F3Net_multi.pth /app/app/ai_pipeline/image/multiclass/F3Net/weights/F3Net_multi.pth && \
    ln -s /shared_data/heimdall-pth/UNet_multi.pth /app/app/ai_pipeline/image/multiclass/UNet/weights/UNet_multi.pth

# 9. c2patool 실행 권한 부여 (절대 경로 사용)
RUN chmod +x /shared_data/c2patool/c2patool/c2patool && \
    chmod +x /app/app/ai_pipeline/image/c2pa/c2patool 

# 10. 이미지 업로드 디렉토리 생성
RUN mkdir -p /app/uploads 

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]