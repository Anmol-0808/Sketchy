from dataclasses import dataclass, field
from enum import StrEnum
from time import time
from uuid import uuid4

from app.game.utils import clamp_int, hint_word, mask_word


class GamePhase(StrEnum):
    LOBBY = "lobby"
    CHOOSING = "choosing"
    DRAWING = "drawing"
    ROUND_END = "round_end"
    GAME_OVER = "game_over"


@dataclass
class RoomSettings:
    max_players: int = 8
    rounds: int = 3
    draw_time: int = 80
    word_count: int = 3
    hints: int = 3
    is_private: bool = True
    categories: list[str] = field(default_factory=list)
    custom_words: list[str] = field(default_factory=list)

    @classmethod
    def from_payload(cls, payload: dict) -> "RoomSettings":
        return cls(
            max_players=clamp_int(int(payload.get("maxPlayers", 8)), 2, 20),
            rounds=clamp_int(int(payload.get("rounds", 3)), 2, 10),
            draw_time=clamp_int(int(payload.get("drawTime", 80)), 15, 240),
            word_count=clamp_int(int(payload.get("wordCount", 3)), 1, 5),
            hints=clamp_int(int(payload.get("hints", 3)), 0, 5),
            is_private=bool(payload.get("isPrivate", True)),
            categories=[str(category).strip().lower() for category in payload.get("categories", []) if str(category).strip()],
            custom_words=[
                str(word).strip().lower()
                for word in payload.get("customWords", [])
                if 2 <= len(str(word).strip()) <= 40
            ][:200],
        )

    def to_payload(self) -> dict:
        return {
            "maxPlayers": self.max_players,
            "rounds": self.rounds,
            "drawTime": self.draw_time,
            "wordCount": self.word_count,
            "hints": self.hints,
            "isPrivate": self.is_private,
            "categories": self.categories,
            "customWords": self.custom_words,
        }


@dataclass
class Player:
    id: str
    name: str
    is_host: bool = False
    score: int = 0
    connected: bool = True
    kicked: bool = False

    @classmethod
    def create(cls, name: str, is_host: bool) -> "Player":
        clean_name = name.strip()[:24] or "Player"
        return cls(id=str(uuid4()), name=clean_name, is_host=is_host)

    def to_payload(self, drawer_id: str | None = None, guessed_ids: set[str] | None = None) -> dict:
        guessed_ids = guessed_ids or set()
        return {
            "id": self.id,
            "name": self.name,
            "score": self.score,
            "isHost": self.is_host,
            "isDrawer": self.id == drawer_id,
            "hasGuessed": self.id in guessed_ids,
            "connected": self.connected,
            "kicked": self.kicked,
        }


@dataclass
class Stroke:
    id: str
    color: str
    size: int
    points: list[dict] = field(default_factory=list)
    mode: str = "draw"

    @classmethod
    def create(cls, payload: dict) -> "Stroke":
        return cls(
            id=str(uuid4()),
            color=str(payload.get("color", "#111827")),
            size=clamp_int(int(payload.get("size", 6)), 1, 36),
            points=[{"x": payload.get("x", 0), "y": payload.get("y", 0)}],
            mode="erase" if payload.get("mode") == "erase" else "draw",
        )

    def to_payload(self) -> dict:
        return {"id": self.id, "color": self.color, "size": self.size, "mode": self.mode, "points": self.points}


@dataclass
class Room:
    code: str
    settings: RoomSettings
    record_id: int | None = None
    players: dict[str, Player] = field(default_factory=dict)
    player_order: list[str] = field(default_factory=list)
    phase: GamePhase = GamePhase.LOBBY
    round_number: int = 0
    turn_index: int = 0
    drawer_id: str | None = None
    current_word: str | None = None
    word_options: list[str] = field(default_factory=list)
    guessed_ids: set[str] = field(default_factory=set)
    strokes: list[Stroke] = field(default_factory=list)
    active_stroke_id: str | None = None
    round_started_at: float | None = None
    last_round_strokes: list[Stroke] = field(default_factory=list)
    turn_token: str = field(default_factory=lambda: str(uuid4()))

    def add_player(self, name: str) -> Player:
        if len(self.players) >= self.settings.max_players:
            raise ValueError("Room is full")
        if self.phase != GamePhase.LOBBY:
            raise ValueError("Game already started")
        candidate_name = name.strip()[:24] or "Player"
        if any(player.name.lower() == candidate_name.lower() for player in self.players.values() if not player.kicked):
            raise ValueError("Name is already taken")
        player = Player.create(name=candidate_name, is_host=not self.has_connected_players())
        if player.is_host:
            for existing_player in self.players.values():
                existing_player.is_host = False
        self.players[player.id] = player
        self.player_order.append(player.id)
        return player

    def remove_player(self, player_id: str) -> None:
        player = self.players.get(player_id)
        if not player:
            return
        player.connected = False
        if player.is_host and self.players:
            connected_players = [player for player in self.players.values() if player.connected and not player.kicked]
            next_player = connected_players[0] if connected_players else None
            if next_player:
                player.is_host = False
                next_player.is_host = True

    def has_connected_players(self) -> bool:
        return any(player.connected and not player.kicked for player in self.players.values())

    def reconnect_player(self, player_id: str) -> Player | None:
        player = self.players.get(player_id)
        if not player or player.kicked:
            return None
        player.connected = True
        if not any(other.connected and other.is_host for other in self.players.values() if other.id != player.id):
            player.is_host = True
        return player

    def reconnect_player_by_name(self, name: str) -> Player | None:
        candidate_name = name.strip()[:24] or "Player"
        for player in self.players.values():
            if player.name.lower() == candidate_name.lower() and not player.connected and not player.kicked:
                return self.reconnect_player(player.id)
        return None

    def kick_player(self, host_id: str, target_id: str) -> Player:
        if not self.players[host_id].is_host:
            raise ValueError("Only host can kick players")
        if host_id == target_id:
            raise ValueError("Host cannot kick themselves")
        target = self.players.get(target_id)
        if not target:
            raise ValueError("Player not found")
        target.kicked = True
        target.connected = False
        self.players.pop(target_id, None)
        self.player_order = [id_ for id_ in self.player_order if id_ != target_id]
        if self.drawer_id == target_id:
            self.drawer_id = None
        return target

    def reset_to_lobby(self) -> None:
        for player in self.players.values():
            player.score = 0
        self.phase = GamePhase.LOBBY
        self.round_number = 0
        self.turn_index = 0
        self.drawer_id = None
        self.current_word = None
        self.word_options.clear()
        self.guessed_ids.clear()
        self.strokes.clear()
        self.active_stroke_id = None
        self.round_started_at = None
        self.turn_token = str(uuid4())

    def players_payload(self) -> list[dict]:
        return [
            self.players[player_id].to_payload(self.drawer_id, self.guessed_ids)
            for player_id in self.player_order
            if player_id in self.players and not self.players[player_id].kicked
        ]

    def public_state(self, viewer_id: str | None = None) -> dict:
        is_drawer = viewer_id == self.drawer_id
        remaining = 0
        elapsed = 0
        if self.phase == GamePhase.DRAWING and self.round_started_at:
            elapsed = max(0, int(time() - self.round_started_at))
            remaining = max(0, int(self.settings.draw_time - elapsed))
        word_hint = None
        if self.current_word:
            if is_drawer:
                word_hint = self.current_word
            elif self.phase == GamePhase.DRAWING:
                word_hint = self.current_hint(elapsed)
            elif self.phase in {GamePhase.ROUND_END, GamePhase.GAME_OVER}:
                word_hint = self.current_word
        return {
            "roomCode": self.code,
            "phase": self.phase,
            "round": self.round_number,
            "totalRounds": self.settings.rounds,
            "drawerId": self.drawer_id,
            "drawerName": self.players[self.drawer_id].name if self.drawer_id in self.players else None,
            "word": self.current_word if is_drawer or self.phase in {GamePhase.ROUND_END, GamePhase.GAME_OVER} else None,
            "wordHint": word_hint,
            "wordLength": len(self.current_word or ""),
            "wordOptions": self.word_options if is_drawer and self.phase == GamePhase.CHOOSING else [],
            "players": self.players_payload(),
            "settings": self.settings.to_payload(),
            "remainingSeconds": remaining,
        }

    def current_hint(self, elapsed: int) -> str:
        if not self.current_word:
            return ""
        if self.settings.hints <= 0:
            return mask_word(self.current_word)
        interval = self.settings.draw_time / (self.settings.hints + 1)
        revealed_count = int(elapsed // interval)
        return hint_word(self.current_word, revealed_count)

    def start_game(self, words: list[str]) -> None:
        if len(self.players) < 2:
            raise ValueError("At least 2 players are required")
        self.phase = GamePhase.CHOOSING
        self.player_order = [id_ for id_ in self.player_order if id_ in self.players]
        self.turn_index = 0
        self.round_number = 1
        self.begin_turn(words)

    def begin_turn(self, words: list[str]) -> None:
        self.phase = GamePhase.CHOOSING
        self.player_order = [id_ for id_ in self.player_order if id_ in self.players and not self.players[id_].kicked]
        self.drawer_id = self.player_order[self.turn_index % len(self.player_order)]
        self.current_word = None
        self.word_options = words
        self.guessed_ids.clear()
        self.strokes.clear()
        self.active_stroke_id = None
        self.round_started_at = None
        self.turn_token = str(uuid4())
        self.round_number = (self.turn_index // len(self.player_order)) + 1

    def choose_word(self, word: str) -> None:
        if self.phase != GamePhase.CHOOSING:
            raise ValueError("Word selection is not active")
        if word not in self.word_options:
            raise ValueError("Choose one of the provided words")
        self.current_word = word
        self.phase = GamePhase.DRAWING
        self.round_started_at = time()

    def add_stroke_start(self, payload: dict) -> Stroke:
        stroke = Stroke.create(payload)
        self.strokes.append(stroke)
        self.active_stroke_id = stroke.id
        return stroke

    def add_stroke_move(self, payload: dict) -> dict:
        if not self.active_stroke_id or not self.strokes:
            raise ValueError("No active stroke")
        point = {"x": payload.get("x", 0), "y": payload.get("y", 0)}
        self.strokes[-1].points.append(point)
        return {"id": self.active_stroke_id, **point}

    def end_stroke(self) -> dict:
        stroke_id = self.active_stroke_id
        self.active_stroke_id = None
        return {"id": stroke_id}

    def undo_stroke(self) -> list[dict]:
        if self.strokes:
            self.strokes.pop()
        return [stroke.to_payload() for stroke in self.strokes]

    def clear_canvas(self) -> None:
        self.strokes.clear()
        self.active_stroke_id = None

    def replay_payload(self) -> list[dict]:
        return [stroke.to_payload() for stroke in self.last_round_strokes]

    def score_correct_guess(self, player_id: str) -> dict:
        if not self.current_word or not self.round_started_at:
            raise ValueError("Round has not started")
        if player_id == self.drawer_id:
            raise ValueError("Drawer cannot guess")
        if player_id in self.guessed_ids:
            raise ValueError("Already guessed")
        remaining = max(0, int(self.settings.draw_time - (time() - self.round_started_at)))
        guesser_points = 100 + remaining * 10
        drawer_points = 50
        self.players[player_id].score += guesser_points
        if self.drawer_id and self.drawer_id in self.players:
            self.players[self.drawer_id].score += drawer_points
        self.guessed_ids.add(player_id)
        return {
            "playerId": player_id,
            "playerName": self.players[player_id].name,
            "points": guesser_points,
            "drawerPoints": drawer_points,
        }

    def all_guessers_done(self) -> bool:
        guessers = [id_ for id_ in self.player_order if id_ != self.drawer_id and id_ in self.players and self.players[id_].connected]
        return bool(guessers) and all(id_ in self.guessed_ids for id_ in guessers)

    def leaderboard(self) -> list[dict]:
        players = sorted(self.players.values(), key=lambda player: player.score, reverse=True)
        return [player.to_payload(self.drawer_id, self.guessed_ids) for player in players]

    def has_next_turn(self) -> bool:
        return self.turn_index + 1 < self.settings.rounds * len(self.player_order)
