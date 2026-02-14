import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.config import get_db_settings

load_dotenv()

_db = get_db_settings()
engine = create_async_engine(
    _db.DATABASE_URL,
    echo=os.getenv("DEBUG", "false").lower() == "true",
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db() -> AsyncSession:
    """FastAPI 의존성 주입용 DB 세션"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """앱 시작 시 테이블 생성 (개발용)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
