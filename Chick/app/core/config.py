# app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # 讀 .env
    DATABASE_URL: str | None = None
    JWT_SECRET: str = Field(..., description="JWT 簽章密鑰（請放長且隨機的字串）")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 20
    REFRESH_TOKEN_EXPIRE_DAYS: int = 21
    
    GOOGLE_CLIENT_ID: str | None = None  # ✅ 新增

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
