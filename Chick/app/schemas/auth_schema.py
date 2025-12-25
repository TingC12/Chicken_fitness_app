# app/schemas/auth_schema.py
from typing import Optional, Literal
from pydantic import BaseModel, Field

# ===== 請求模型 =====
class GuestLoginRequest(BaseModel):
    """
    遊客登入請求：
    - device_id 可選：若前端還沒有就留空，後端可生成並回傳
    - platform 必填：限制在 android / ios / web
    - app_version 必填：建議 x.y.z 格式（此處不強制），方便後端統計
    - device_model / os_version 可選：用於除錯與統計
    """
    device_id: Optional[str] = Field(
        default=None,
        max_length=64,
        description="裝置識別；若無則可不傳，由後端生成後回傳"
    )
    platform: Literal["android", "ios", "web"] = Field(
        description="平台"
    )
    app_version: str = Field(
        min_length=1,
        max_length=32,
        description="App 版本（例如 1.0.0）"
    )
    device_model: Optional[str] = Field(default=None, max_length=64)
    os_version: Optional[str]   = Field(default=None, max_length=64)


# ===== 成功回應模型 =====
class GuestLoginResponse(BaseModel):
    """
    遊客登入回應：
    - 若後端有生成新的 device_id，也會回傳 device_id 讓前端保存
    - *_expires_in 均為秒數
    """
    user_id: int
    access_token: str
    access_token_expires_in: int
    refresh_token: str
    refresh_token_expires_in: int
    is_guest: bool = True
    device_id: Optional[str] = None


# ===== 錯誤回應模型（所有 auth 端點共用）=====
class ErrorResponse(BaseModel):
    error_code: str
    message: str
    retry_after_seconds: Optional[int] = None

# === Refresh Token ===
class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10, description="客戶端持有的 RT 明文")

class RefreshResponse(BaseModel):
    access_token: str
    access_token_expires_in: int
    # 旋轉更新：一併發新 RT
    refresh_token: str
    refresh_token_expires_in: int
