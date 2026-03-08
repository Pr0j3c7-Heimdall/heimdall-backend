# 1. Base Image
FROM python:3.12-slim-bookworm

# 2. Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Seoul

# 3. Install packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmagic1 \
    libgl1 \
    libglib2.0-0 \
    libimage-exiftool-perl \
    unzip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 4. Set working directory
WORKDIR /app

# 5. Install Python dependencies (gdown 추가)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip gdown && \
    pip install --no-cache-dir -r requirements.txt

# 6. Copy application code
COPY . .

# 7. Download files
RUN mkdir -p /shared_data && \
    gdown --id 1_nj67GnQBYgBYem8DVS8YVm9lFI99Yss -O /shared_data/weights.zip && \
    unzip -o /shared_data/weights.zip -d /shared_data/ && \
    rm -f /shared_data/weights.zip && \
    gdown --id 165r1bSY2AlMgVADh3WdljKpK2XCCTDCX -O /shared_data/c2patool.zip && \
    unzip -o /shared_data/c2patool.zip -d /shared_data/ && \
    rm -f /shared_data/c2patool.zip && \
    chmod -R 777 /shared_data

# 8. Link weight files
RUN mkdir -p app/ai_pipeline/image/c2pa \
             app/ai_pipeline/image/binary/DINOv3/weights \
             app/ai_pipeline/image/binary/F3Net/weights \
             app/ai_pipeline/image/binary/UNet/weights \
             app/ai_pipeline/image/multiclass/DINOv3/weights \
             app/ai_pipeline/image/multiclass/F3Net/weights \
             app/ai_pipeline/image/multiclass/UNet/weights && \
    ln -s /shared_data/c2patool/c2patool/anchors.pem app/ai_pipeline/image/c2pa/anchors.pem && \
    ln -s /shared_data/c2patool/c2patool/c2patool app/ai_pipeline/image/c2pa/c2patool && \
    ln -s /shared_data/heimdall-pth/DINOv3_binary.pth app/ai_pipeline/image/binary/DINOv3/weights/DINOv3_binary.pth && \
    ln -s /shared_data/heimdall-pth/F3Net_binary.pth app/ai_pipeline/image/binary/F3Net/weights/F3Net_binary.pth && \
    ln -s /shared_data/heimdall-pth/UNet_binary.pth app/ai_pipeline/image/binary/UNet/weights/UNet_binary.pth && \
    ln -s /shared_data/heimdall-pth/DINOv3_multi.pth app/ai_pipeline/image/multiclass/DINOv3/weights/DINOv3_multi.pth && \
    ln -s /shared_data/heimdall-pth/F3Net_multi.pth app/ai_pipeline/image/multiclass/F3Net/weights/F3Net_multi.pth && \
    ln -s /shared_data/heimdall-pth/UNet_multi.pth app/ai_pipeline/image/multiclass/UNet/weights/UNet_multi.pth

# 9. Create upload directory
RUN mkdir -p /app/uploads

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]