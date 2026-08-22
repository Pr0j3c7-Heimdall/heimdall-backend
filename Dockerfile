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
RUN pip install --no-cache-dir --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. 소스 코드 복사 (현재 폴더의 모든 파일을 /app으로 복사)
COPY . .

# 7. AI 가중치 및 c2patool은 빌드 타임에 받지 않는다.
#    docker-compose 의 init 서비스(init.sh)가 heimdall-vol 볼륨에 1회 다운로드하고,
#    런타임에 그 볼륨이 /shared_data 에 마운트된다.
#    (예전에는 여기서도 같은 zip 4개를 받았지만, 볼륨 마운트가 그대로 덮어써서
#     이미지 용량과 빌드 시간만 낭비하고 실제로는 쓰이지 않았다.)

# 8. 심볼릭 링크 생성 (대상은 런타임에 /shared_data 볼륨으로 채워진다)
RUN mkdir -p /app/app/ai_pipeline/image/c2pa \
             /app/app/ai_pipeline/image/binary/DINOv3/weights \
             /app/app/ai_pipeline/image/binary/F3Net/weights \
             /app/app/ai_pipeline/image/binary/UNet/weights \
             /app/app/ai_pipeline/image/multiclass/DINOv3/weights \
             /app/app/ai_pipeline/image/multiclass/F3Net/weights \
             /app/app/ai_pipeline/image/multiclass/UNet/weights \
             /app/app/ai_pipeline/audio/speech/SSL_AASIST/weights \
             /app/app/ai_pipeline/audio/speech/CQCC_SSL_AASIST/weights \
             /app/app/ai_pipeline/audio/singing/AASIST/weights \
             /app/app/ai_pipeline/audio/singing/LCNN/weights \
             /app/app/ai_pipeline/audio/common/RawNet3/weights && \
    # c2patool 관련 링크
    ln -s /shared_data/c2patool/anchors.pem /app/app/ai_pipeline/image/c2pa/anchors.pem && \
    ln -s /shared_data/c2patool/c2patool /app/app/ai_pipeline/image/c2pa/c2patool && \
    # 이진 분류 모델 가중치 링크
    ln -s /shared_data/heimdall-pth/DINOv3_binary.pth /app/app/ai_pipeline/image/binary/DINOv3/weights/DINOv3_binary.pth && \
    ln -s /shared_data/heimdall-pth/F3Net_binary.pth /app/app/ai_pipeline/image/binary/F3Net/weights/F3Net_binary.pth && \
    ln -s /shared_data/heimdall-pth/UNet_binary.pth /app/app/ai_pipeline/image/binary/UNet/weights/UNet_binary.pth && \
    # 다중 분류 모델 가중치 링크
    ln -s /shared_data/heimdall-pth/DINOv3_multi.pth /app/app/ai_pipeline/image/multiclass/DINOv3/weights/DINOv3_multi.pth && \
    ln -s /shared_data/heimdall-pth/F3Net_multi.pth /app/app/ai_pipeline/image/multiclass/F3Net/weights/F3Net_multi.pth && \
    ln -s /shared_data/heimdall-pth/UNet_multi.pth /app/app/ai_pipeline/image/multiclass/UNet/weights/UNet_multi.pth && \
    # 음성 트랙 모델 가중치 링크
    ln -s /shared_data/heimdall-speech-pth/SSL_AASIST_speech.pth /app/app/ai_pipeline/audio/speech/SSL_AASIST/weights/SSL_AASIST_speech.pth && \
    ln -s /shared_data/heimdall-speech-pth/CQCC_SSL_AASIST_speech.pth /app/app/ai_pipeline/audio/speech/CQCC_SSL_AASIST/weights/CQCC_SSL_AASIST_speech.pth && \
    ln -s /shared_data/heimdall-speech-pth/RawNet3_speech.pth /app/app/ai_pipeline/audio/common/RawNet3/weights/RawNet3_speech.pth && \
    # 가창 트랙 모델 가중치 링크
    ln -s /shared_data/heimdall-singing-pth/AASIST_singing.pth /app/app/ai_pipeline/audio/singing/AASIST/weights/AASIST_singing.pth && \
    ln -s /shared_data/heimdall-singing-pth/LFCC-LCNN_singing.pth /app/app/ai_pipeline/audio/singing/LCNN/weights/LFCC-LCNN_singing.pth && \
    ln -s /shared_data/heimdall-singing-pth/RawNet3_singing.pth /app/app/ai_pipeline/audio/common/RawNet3/weights/RawNet3_singing.pth

# 9. c2patool 실행 권한은 init.sh 의 `chmod -R 777 /shared_data` 가 부여한다.
#    (빌드 시점에는 심볼릭 링크의 대상 파일이 아직 없어 chmod 가 실패한다)

# 10. 이미지 업로드 디렉토리 생성 (compose 의 uploads-data 볼륨이 마운트되는 지점)
RUN mkdir -p /app/uploads 

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
