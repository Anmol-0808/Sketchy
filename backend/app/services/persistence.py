from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.game.types import Player, Room, RoomSettings
from app.models.game_result import GameResult
from app.models.player_record import PlayerRecord
from app.models.room_record import RoomRecord
from app.models.word_record import WordRecord


async def save_room_record(code: str, settings: RoomSettings) -> int | None:
    if AsyncSessionLocal is None:
        return None

    async with AsyncSessionLocal() as session:
        record = RoomRecord(
            code=code,
            is_private=settings.is_private,
            max_players=settings.max_players,
            rounds=settings.rounds,
            draw_time=settings.draw_time,
            word_count=settings.word_count,
            hints=settings.hints,
            categories=settings.categories,
            custom_words=settings.custom_words,
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record.id


async def save_player_record(room: Room, player: Player) -> None:
    if AsyncSessionLocal is None or room.record_id is None:
        return

    async with AsyncSessionLocal() as session:
        session.add(
            PlayerRecord(
                room_id=room.record_id,
                name=player.name,
                score=player.score,
                is_host=player.is_host,
            )
        )
        await session.commit()


async def save_game_result(room: Room) -> None:
    if AsyncSessionLocal is None or room.record_id is None or not room.players:
        return

    leaderboard = room.leaderboard()
    winner = leaderboard[0]
    async with AsyncSessionLocal() as session:
        for player in room.players.values():
            result = await session.execute(
                select(PlayerRecord).where(PlayerRecord.room_id == room.record_id, PlayerRecord.name == player.name)
            )
            record = result.scalar_one_or_none()
            if record:
                record.score = player.score

        session.add(
            GameResult(
                room_id=room.record_id,
                winner_name=winner["name"],
                final_scores={"players": leaderboard},
            )
        )
        await session.commit()


async def seed_words(words: list[str]) -> None:
    if AsyncSessionLocal is None:
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(WordRecord.id).limit(1))
        if result.scalar_one_or_none() is not None:
            return
        session.add_all([WordRecord(text=word, category="general") for word in words])
        await session.commit()


async def load_words() -> list[str]:
    if AsyncSessionLocal is None:
        return []

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(WordRecord.text))
        return list(result.scalars().all())
