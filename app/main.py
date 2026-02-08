from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.model import RefreshToken, User  # noqa: F401 - 테이블 등록용
from app.auth.router import router as auth_router
from app.common.exception import register_exception_handlers
from app.common.schema import SuccessResponse
from app.config import get_auth_settings, get_cors_settings
from app.database import get_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행"""
    get_auth_settings()  # fail-fast: 환경 변수 검증
    await init_db()
    yield


app = FastAPI(
    title="Heimdall API",
    description="Heimdall Backend API",
    version="0.1.0",
    lifespan=lifespan,
)
cors = get_cors_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_exception_handlers(app)
app.include_router(auth_router, prefix="/api/v1")


@app.get("/", response_model=SuccessResponse)
async def root():
    """루트 엔드포인트"""
    return SuccessResponse(data={"message": "Heimdall API에 오신 것을 환영합니다"})


@app.get("/health", response_model=SuccessResponse)
async def health_check():
    """서버 상태 확인용 health check"""
    return SuccessResponse(data={"status": "healthy"})


@app.get("/db-health", response_model=SuccessResponse)
async def db_health_check(db: AsyncSession = Depends(get_db)):
    """DB 연결 상태 확인"""
    await db.execute(text("SELECT 1"))
    return SuccessResponse(data={"status": "healthy", "database": "connected"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
