from sqlalchemy import BigInteger, Column, DateTime, String, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"  # 'user'는 MySQL 예약어이므로 users 사용
    __table_args__ = (UniqueConstraint("provider", "provider_sub", name="uq_provider_sub"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    provider = Column(String(50), nullable=False, default="google")
    provider_sub = Column(String(255), nullable=False)
    password = Column(String(255), nullable=True)  # 소셜 로그인 시 NULL
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
