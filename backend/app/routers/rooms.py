from fastapi import APIRouter, HTTPException

from app.game.types import RoomSettings
from app.schemas.room import CreateRoomRequest
from app.services.persistence import save_room_record
from app.websocket.manager import room_manager

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


@router.post("")
async def create_room(request: CreateRoomRequest) -> dict:
    settings = RoomSettings.from_payload(request.settings.model_dump())
    room = room_manager.create_room(settings)
    room.record_id = await save_room_record(room.code, settings)
    return {"roomCode": room.code, "settings": room.settings.to_payload()}


@router.get("/public/available")
async def get_public_room() -> dict:
    room = room_manager.first_public_room()
    if not room:
        raise HTTPException(status_code=404, detail="No public room available")
    return room.public_state()


@router.get("/{room_code}")
async def get_room(room_code: str) -> dict:
    room = room_manager.get_room(room_code)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room.public_state()
