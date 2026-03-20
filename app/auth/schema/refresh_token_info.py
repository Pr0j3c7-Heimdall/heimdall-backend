"""리프레시 토큰 조회 결과 (DB/Redis 공통)"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RefreshTokenInfo:
    """find_valid_by_token 반환용 (user_id만 필요)"""

    user_id: int
