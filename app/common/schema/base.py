"""공통 Base Model - API 요청/응답용"""

from pydantic import BaseModel, ConfigDict


class CamelModel(BaseModel):
    """camelCase 자동 매핑 (alias 허용, populate_by_name)"""

    model_config = ConfigDict(populate_by_name=True)
