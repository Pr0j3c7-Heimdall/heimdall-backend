from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String
from sqlalchemy.sql import func

from app.database import Base


class RefreshToken(Base):
    __tablename__ = "refresh_token"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
