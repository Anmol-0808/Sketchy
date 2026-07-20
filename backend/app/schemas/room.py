from pydantic import BaseModel, Field


class RoomSettingsPayload(BaseModel):
    maxPlayers: int = Field(default=8, ge=2, le=20)
    rounds: int = Field(default=3, ge=2, le=10)
    drawTime: int = Field(default=80, ge=15, le=240)
    wordCount: int = Field(default=3, ge=1, le=5)
    hints: int = Field(default=3, ge=0, le=5)
    isPrivate: bool = True
    categories: list[str] = Field(default_factory=list)
    customWords: list[str] = Field(default_factory=list, max_length=200)


class CreateRoomRequest(BaseModel):
    settings: RoomSettingsPayload = Field(default_factory=RoomSettingsPayload)


class CreateRoomResponse(BaseModel):
    roomCode: str
    settings: RoomSettingsPayload
