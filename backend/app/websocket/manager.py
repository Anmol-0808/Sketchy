import asyncio
import random
import string
from time import time

from fastapi import WebSocket

from app.game.types import GamePhase, Room, RoomSettings
from app.game.utils import normalize_guess
from app.game.word_service import word_service
from app.services.persistence import save_game_result, save_player_record


class RoomManager:
    def __init__(self) -> None:
        self.rooms: dict[str, Room] = {}
        self.connections: dict[str, WebSocket] = {}
        self.player_rooms: dict[str, str] = {}
        self.socket_players: dict[WebSocket, str] = {}
        self.round_tasks: dict[str, asyncio.Task] = {}
        self.empty_room_tasks: dict[str, asyncio.Task] = {}

    def create_room(self, settings: RoomSettings) -> Room:
        code = self._make_code()
        room = Room(code=code, settings=settings)
        self.rooms[code] = room
        return room

    def get_room(self, code: str) -> Room | None:
        return self.rooms.get(code.upper())

    def first_public_room(self) -> Room | None:
        for room in self.rooms.values():
            if not room.settings.is_private and room.phase == GamePhase.LOBBY and len(room.players) < room.settings.max_players:
                return room
        return None

    async def join_room(self, websocket: WebSocket, payload: dict) -> None:
        room_code = str(payload.get("roomCode", "")).upper()
        player_name = str(payload.get("playerName", "")).strip()
        reconnect_id = str(payload.get("playerId", "")).strip()
        room = self.get_room(room_code)
        if not room:
            await self.send_error(websocket, "Room not found")
            return
        player = room.reconnect_player(reconnect_id) if reconnect_id else None
        if not player:
            player = room.reconnect_player_by_name(player_name)
        is_reconnect = player is not None
        if not player:
            try:
                player = room.add_player(player_name)
            except ValueError as error:
                await self.send_error(websocket, str(error))
                return
        self.connections[player.id] = websocket
        self.player_rooms[player.id] = room.code
        self.socket_players[websocket] = player.id
        self.cancel_empty_room_cleanup(room.code)
        if not is_reconnect:
            await save_player_record(room, player)
        await self.send_to_player(player.id, "join_success", {"player": player.to_payload(), "room": room.public_state(player.id)})
        await self.broadcast(room.code, "player_joined", {"player": player.to_payload(), "players": room.players_payload()})
        if room.strokes:
            await self.send_to_player(player.id, "canvas_redraw", {"strokes": [stroke.to_payload() for stroke in room.strokes]})
        await self.broadcast_state(room.code)

    async def disconnect(self, websocket: WebSocket) -> None:
        player_id = self.socket_players.pop(websocket, None)
        if not player_id:
            return
        room_code = self.player_rooms.pop(player_id, None)
        self.connections.pop(player_id, None)
        if not room_code or room_code not in self.rooms:
            return
        room = self.rooms[room_code]
        was_drawer = room.drawer_id == player_id and room.phase in {GamePhase.CHOOSING, GamePhase.DRAWING}
        room.remove_player(player_id)
        await self.broadcast(room.code, "player_left", {"playerId": player_id, "players": room.players_payload()})
        if was_drawer:
            await self.end_round(room.code, "drawer_left")
            return
        if room.has_connected_players():
            await self.broadcast_state(room.code)
        else:
            self.schedule_empty_room_cleanup(room.code)

    async def handle_event(self, websocket: WebSocket, message: dict) -> None:
        event_type = message.get("type")
        payload = message.get("payload") or {}
        if event_type == "join_room":
            await self.join_room(websocket, payload)
            return
        player_id = self.socket_players.get(websocket)
        if not player_id:
            await self.send_error(websocket, "Join a room first")
            return
        room = self._room_for_player(player_id)
        if not room:
            await self.send_error(websocket, "Room no longer exists")
            return
        handlers = {
            "start_game": self.start_game,
            "word_chosen": self.choose_word,
            "draw_start": self.draw_start,
            "draw_move": self.draw_move,
            "draw_end": self.draw_end,
            "draw_undo": self.draw_undo,
            "canvas_clear": self.canvas_clear,
            "guess": self.guess,
            "chat": self.chat,
            "kick_player": self.kick_player,
            "restart_game": self.restart_game,
            "request_replay": self.request_replay,
            "request_state": self.request_state,
        }
        handler = handlers.get(str(event_type))
        if not handler:
            await self.send_error(websocket, f"Unknown event: {event_type}")
            return
        await handler(room, player_id, payload)

    async def start_game(self, room: Room, player_id: str, payload: dict) -> None:
        if not room.players[player_id].is_host:
            await self.send_to_player(player_id, "error", {"message": "Only host can start the game"})
            return
        try:
            room.start_game(self.word_choices(room))
        except ValueError as error:
            await self.send_to_player(player_id, "error", {"message": str(error)})
            return
        await self.broadcast(room.code, "canvas_clear", {})
        await self.broadcast_round_start(room)
        await self.broadcast_state(room.code)

    async def choose_word(self, room: Room, player_id: str, payload: dict) -> None:
        if player_id != room.drawer_id:
            await self.send_to_player(player_id, "error", {"message": "Only the drawer can choose the word"})
            return
        try:
            room.choose_word(str(payload.get("word", "")))
        except ValueError as error:
            await self.send_to_player(player_id, "error", {"message": str(error)})
            return
        await self.broadcast(room.code, "word_chosen", {"drawerId": room.drawer_id, "drawTime": room.settings.draw_time})
        await self.broadcast_state(room.code)
        self.round_tasks[room.code] = asyncio.create_task(self.end_round_after_timeout(room.code, room.turn_token))

    async def draw_start(self, room: Room, player_id: str, payload: dict) -> None:
        if not self._can_draw(room, player_id):
            return
        stroke = room.add_stroke_start(payload)
        await self.broadcast(room.code, "draw_data", {"action": "start", **stroke.to_payload()})

    async def draw_move(self, room: Room, player_id: str, payload: dict) -> None:
        if not self._can_draw(room, player_id):
            return
        try:
            point = room.add_stroke_move(payload)
        except ValueError:
            return
        await self.broadcast(room.code, "draw_data", {"action": "move", **point})

    async def draw_end(self, room: Room, player_id: str, payload: dict) -> None:
        if not self._can_draw(room, player_id):
            return
        await self.broadcast(room.code, "draw_data", {"action": "end", **room.end_stroke()})

    async def draw_undo(self, room: Room, player_id: str, payload: dict) -> None:
        if not self._can_draw(room, player_id):
            return
        await self.broadcast(room.code, "canvas_redraw", {"strokes": room.undo_stroke()})

    async def canvas_clear(self, room: Room, player_id: str, payload: dict) -> None:
        if not self._can_draw(room, player_id):
            return
        room.clear_canvas()
        await self.broadcast(room.code, "canvas_clear", {})

    async def guess(self, room: Room, player_id: str, payload: dict) -> None:
        text = str(payload.get("text", ""))
        if not text.strip():
            return
        if room.phase != GamePhase.DRAWING or not room.current_word:
            await self.chat(room, player_id, payload)
            return
        if normalize_guess(text) == normalize_guess(room.current_word):
            try:
                result = room.score_correct_guess(player_id)
            except ValueError as error:
                await self.send_to_player(player_id, "error", {"message": str(error)})
                return
            await self.broadcast(room.code, "guess_result", {"correct": True, **result})
            await self.broadcast_state(room.code)
            if room.all_guessers_done():
                await self.end_round(room.code, "all_guessed")
            return
        await self.chat(room, player_id, payload)

    async def chat(self, room: Room, player_id: str, payload: dict) -> None:
        text = str(payload.get("text", "")).strip()[:180]
        if not text:
            return
        player = room.players[player_id]
        await self.broadcast(room.code, "chat_message", {"playerId": player.id, "playerName": player.name, "text": text})

    async def kick_player(self, room: Room, player_id: str, payload: dict) -> None:
        target_id = str(payload.get("playerId", ""))
        try:
            target = room.kick_player(player_id, target_id)
        except ValueError as error:
            await self.send_to_player(player_id, "error", {"message": str(error)})
            return
        websocket = self.connections.pop(target.id, None)
        self.player_rooms.pop(target.id, None)
        if websocket:
            self.socket_players.pop(websocket, None)
            await websocket.send_json({"type": "kicked", "payload": {"message": "You were removed by the host"}})
            await websocket.close()
        await self.broadcast(room.code, "player_left", {"playerId": target.id, "players": room.players_payload()})
        await self.broadcast_state(room.code)

    async def restart_game(self, room: Room, player_id: str, payload: dict) -> None:
        if not room.players[player_id].is_host:
            await self.send_to_player(player_id, "error", {"message": "Only host can restart the game"})
            return
        task = self.round_tasks.pop(room.code, None)
        if task and not task.done():
            task.cancel()
        room.reset_to_lobby()
        await self.broadcast(room.code, "canvas_clear", {})
        await self.broadcast(room.code, "chat_message", {"playerId": "system", "playerName": "Sketchy", "text": "Game reset to lobby"})
        await self.broadcast_state(room.code)

    async def request_replay(self, room: Room, player_id: str, payload: dict) -> None:
        await self.send_to_player(player_id, "replay_data", {"strokes": room.replay_payload()})

    async def request_state(self, room: Room, player_id: str, payload: dict) -> None:
        await self.send_to_player(player_id, "game_state", room.public_state(player_id))

    async def end_round_after_timeout(self, room_code: str, turn_token: str) -> None:
        while True:
            await asyncio.sleep(1)
            room = self.rooms.get(room_code)
            if not room or room.turn_token != turn_token or room.phase != GamePhase.DRAWING:
                return
            await self.broadcast_state(room_code)
            if room.round_started_at and time() - room.round_started_at >= room.settings.draw_time:
                await self.end_round(room_code, "timeout")
                return

    async def end_round(self, room_code: str, reason: str) -> None:
        room = self.rooms.get(room_code)
        if not room or room.phase not in {GamePhase.DRAWING, GamePhase.CHOOSING}:
            return
        room.phase = GamePhase.ROUND_END
        room.last_round_strokes = list(room.strokes)
        task = self.round_tasks.pop(room.code, None)
        if task and not task.done():
            task.cancel()
        await self.broadcast(
            room.code,
            "round_end",
            {"reason": reason, "word": room.current_word, "leaderboard": room.leaderboard()},
        )
        await self.broadcast_state(room.code)
        asyncio.create_task(self.advance_after_pause(room.code, room.turn_token))

    async def advance_after_pause(self, room_code: str, turn_token: str) -> None:
        await asyncio.sleep(7)
        room = self.rooms.get(room_code)
        if not room or room.turn_token != turn_token:
            return
        if not room.has_next_turn():
            room.phase = GamePhase.GAME_OVER
            winner = room.leaderboard()[0] if room.players else None
            await self.broadcast(room.code, "game_over", {"winner": winner, "leaderboard": room.leaderboard()})
            await self.broadcast_state(room.code)
            await save_game_result(room)
            return
        room.turn_index += 1
        room.begin_turn(self.word_choices(room))
        await self.broadcast(room.code, "canvas_clear", {})
        await self.broadcast_round_start(room)
        await self.broadcast_state(room.code)

    async def broadcast_round_start(self, room: Room) -> None:
        for player_id in list(room.players):
            await self.send_to_player(player_id, "round_start", room.public_state(player_id))

    async def broadcast_state(self, room_code: str) -> None:
        room = self.rooms.get(room_code)
        if not room:
            return
        for player_id in list(room.players):
            await self.send_to_player(player_id, "game_state", room.public_state(player_id))

    async def broadcast(self, room_code: str, event_type: str, payload: dict) -> None:
        room = self.rooms.get(room_code)
        if not room:
            return
        for player_id in list(room.players):
            await self.send_to_player(player_id, event_type, payload)

    async def send_to_player(self, player_id: str, event_type: str, payload: dict) -> None:
        websocket = self.connections.get(player_id)
        if not websocket:
            return
        await websocket.send_json({"type": event_type, "payload": payload})

    async def send_error(self, websocket: WebSocket, message: str) -> None:
        await websocket.send_json({"type": "error", "payload": {"message": message}})

    def schedule_empty_room_cleanup(self, room_code: str) -> None:
        task = self.empty_room_tasks.pop(room_code, None)
        if task and not task.done():
            task.cancel()
        self.empty_room_tasks[room_code] = asyncio.create_task(self.cleanup_empty_room(room_code))

    def cancel_empty_room_cleanup(self, room_code: str) -> None:
        task = self.empty_room_tasks.pop(room_code, None)
        if task and not task.done():
            task.cancel()

    async def cleanup_empty_room(self, room_code: str) -> None:
        await asyncio.sleep(90)
        room = self.rooms.get(room_code)
        if room and not room.has_connected_players():
            self.rooms.pop(room_code, None)
        self.empty_room_tasks.pop(room_code, None)

    def _room_for_player(self, player_id: str) -> Room | None:
        room_code = self.player_rooms.get(player_id)
        return self.rooms.get(room_code or "")

    def _can_draw(self, room: Room, player_id: str) -> bool:
        return room.phase == GamePhase.DRAWING and player_id == room.drawer_id

    def word_choices(self, room: Room) -> list[str]:
        return word_service.choices(
            room.settings.word_count,
            categories=room.settings.categories,
            custom_words=room.settings.custom_words,
        )

    def _make_code(self) -> str:
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = "".join(random.choice(alphabet) for _ in range(6))
            if code not in self.rooms:
                return code


room_manager = RoomManager()
