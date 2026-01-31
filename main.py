from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.auth.model import User  # noqa: F401 - 테이블 등록용
from app.database import get_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행"""
    await init_db()
    yield


app = FastAPI(
    title="Heimdall API",
    description="Heimdall Backend API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {"message": "Heimdall API에 오신 것을 환영합니다"}


@app.get("/health")
async def health_check():
    """서버 상태 확인용 health check"""
    return {"status": "healthy"}


@app.get("/db-health")
async def db_health_check(db: AsyncSession = Depends(get_db)):
    """DB 연결 상태 확인"""
    await db.execute(text("SELECT 1"))
    return {"status": "healthy", "database": "connected"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
