from fastapi import FastAPI

app = FastAPI(
    title="Heimdall API",
    description="Heimdall Backend API",
    version="0.1.0",
)


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {"message": "Heimdall API에 오신 것을 환영합니다"}


@app.get("/health")
async def health_check():
    """서버 상태 확인용 health check"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
