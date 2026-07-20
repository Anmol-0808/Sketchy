from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket.manager import room_manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_json()
            await room_manager.handle_event(websocket, message)
    except WebSocketDisconnect:
        await room_manager.disconnect(websocket)
