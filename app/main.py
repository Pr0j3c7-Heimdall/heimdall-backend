from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from app.user.model import User  # noqa: F401 - 테이블 등록용
from app.image.model import Image  # noqa: F401 - 테이블 등록용
from app.detection.image.model.image_final_detection_results import ImageFinalDetectionResult  # noqa: F401 - 테이블 등록용
from app.detection.image.model.image_binary_detection_results import ImageBinaryDetectionResult  # noqa: F401 - 테이블 등록용
from app.detection.image.model.image_multiclass_detection_results import ImageMulticlassDetectionResult  # noqa: F401 - 테이블 등록용
from app.detection.image.model.image_c2pa_analysis_results import ImageC2paAnalysisResult  # noqa: F401 - 테이블 등록용
from app.audio.model import Audio  # noqa: F401 - 테이블 등록용
from app.detection.audio.model.audio_final_detection_results import AudioFinalDetectionResult  # noqa: F401 - 테이블 등록용
from app.detection.audio.model.audio_model_detection_results import AudioModelDetectionResult  # noqa: F401 - 테이블 등록용

from app.auth.router import router as auth_router
from app.user.router import router as user_router
from app.image import base_router as image_base_router
from app.audio import base_router as audio_base_router
from app.detection import router as detection_router

from app.common.exception import register_exception_handlers
from app.common.schema import SuccessResponse
from redis.asyncio import from_url

from app.config import get_auth_settings, get_cors_settings, get_image_settings, get_redis_settings
from app.database import get_db, init_db
from app.redis_client import clear_redis, get_redis, set_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행"""
    get_auth_settings()  # fail-fast: 환경 변수 검증
    await init_db()

    redis_settings = get_redis_settings()
    redis_client = from_url(redis_settings.REDIS_URL, decode_responses=True)
    set_redis(redis_client)

    yield

    await redis_client.aclose()
    clear_redis()


app = FastAPI(
    title="Heimdall API",
    description="Heimdall Backend API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,  # 아래에서 직접 제공 (_openapi_url_for 주석 참고)
    redoc_url=None,
    openapi_url="/api/v1/openapi.json",
)


def _openapi_url_for(request: Request) -> str:
    """docs 페이지가 참조할 openapi.json 주소를 접속 경로에 맞춰 결정한다.

    프론트엔드의 next.config.mjs rewrite가 '/api/:path*'를 'backend:8000/:path*'로
    넘기면서 경로에서 /api를 한 번 벗겨낸다. 그래서 도메인으로 접속한 경우에는
    브라우저가 /api가 하나 더 붙은 주소를 요청해야 백엔드의 /api/v1/openapi.json에
    도달한다. 반대로 포트로 직접 붙은 경우(localhost:8000)에는 rewrite가 없으므로
    접두사를 붙이면 안 된다. 고정값으로 두면 둘 중 한쪽이 반드시 404가 난다.

    TODO: 백엔드를 api 서브도메인으로 분리해 rewrite가 사라지면 이 분기는 제거할 것.
    """
    host = request.headers.get("host", "").split(":")[0]
    prefix = "" if host in ("localhost", "127.0.0.1") else "/api"
    return f"{prefix}/api/v1/openapi.json"


@app.get("/api/v1/docs", include_in_schema=False)
async def swagger_ui_html(request: Request):
    """Swagger UI (내장 docs_url 대체)"""
    return get_swagger_ui_html(
        openapi_url=_openapi_url_for(request),
        title=f"{app.title} - Swagger UI",
    )


@app.get("/api/v1/redoc", include_in_schema=False)
async def redoc_html(request: Request):
    """ReDoc (내장 redoc_url 대체)"""
    return get_redoc_html(
        openapi_url=_openapi_url_for(request),
        title=f"{app.title} - ReDoc",
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

# 정적 파일 서빙 (업로드된 이미지 제공용)
image_settings = get_image_settings()
app.mount("/uploads", StaticFiles(directory=image_settings.UPLOAD_DIR), name="uploads")

app.include_router(auth_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
app.include_router(image_base_router, prefix="/api/v1")
app.include_router(audio_base_router, prefix="/api/v1")
app.include_router(detection_router, prefix="/api/v1")

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


@app.get("/redis-health", response_model=SuccessResponse)
async def redis_health_check():
    """Redis 연결 상태 확인"""
    try:
        redis = get_redis()
        await redis.ping()
        return SuccessResponse(data={"status": "healthy", "redis": "connected"})
    except (RedisConnectionError, RedisTimeoutError) as e:
        raise HTTPException(
            status_code=503,
            detail=f"Redis unavailable: {type(e).__name__}: {e!s}",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )