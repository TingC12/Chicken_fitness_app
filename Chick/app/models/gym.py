# path: app/models/gym.py
from sqlalchemy import Integer, String, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class Gym(Base):
    __tablename__ = "gyms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # 經緯度（用 Float 最簡單；想要更精準可改 DECIMAL）
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)

    # 半徑（公尺）
    radius_m: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
