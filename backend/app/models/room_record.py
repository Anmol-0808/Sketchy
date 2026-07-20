from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class RoomRecord(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    is_private: Mapped[bool] = mapped_column(Boolean, default=True)
    max_players: Mapped[int] = mapped_column(Integer, default=8)
    rounds: Mapped[int] = mapped_column(Integer, default=3)
    draw_time: Mapped[int] = mapped_column(Integer, default=80)
    word_count: Mapped[int] = mapped_column(Integer, default=3)
    hints: Mapped[int] = mapped_column(Integer, default=3)
    categories: Mapped[list] = mapped_column(JSON, default=list)
    custom_words: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    players = relationship("PlayerRecord", back_populates="room")
