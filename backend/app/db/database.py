from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def _normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


database_url = _normalize_url(settings.database_url)
engine = create_async_engine(database_url, echo=False) if database_url else None
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False) if engine else None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if AsyncSessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured")
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    if engine is None:
        return
    from app.models import game_result, player_record, room_record, word_record

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    from app.game.word_service import word_service
    from app.services.persistence import load_words, seed_words

    await seed_words(word_service.words)
    word_service.replace_words(await load_words())
