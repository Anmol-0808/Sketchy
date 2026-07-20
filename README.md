# Sketchy

Sketchy is a skribbl.io-inspired multiplayer drawing and guessing game built with Next.js, TypeScript, FastAPI, WebSockets, and PostgreSQL.

## Features

- Create a room with configurable player count, rounds, draw time, and word choices.
- Join a room with a code or shared link.
- Create private invite rooms or public rooms.
- Join the first available public lobby.
- Lobby with player list and host start control.
- Host kick controls in the lobby.
- Turn-based drawer rotation.
- Drawer word selection.
- Real-time canvas stroke sync through WebSockets.
- Chat-style guessing with server-side word matching.
- Timed letter hints for guessers.
- Time-based scoring and drawer bonus points.
- Pen, eraser, color palette, brush size, undo, clear canvas, and last-round replay.
- Custom words and category-based word pools.
- Round result, final leaderboard, play again, and home actions.
- Reconnect support for active games using local player session storage.
- Responsive mobile layout for Android browser testing.
- 1000-word default word list.
- PostgreSQL persistence for rooms, players, seeded words, and final game results when `DATABASE_URL` is configured.

## Architecture

The frontend owns rendering and user interaction. The backend owns game truth: room membership, current drawer, selected word, score calculation, timers, and broadcasts.

PostgreSQL is used for persistent records. Live game state stays in FastAPI memory because drawing events and timers need fast WebSocket updates.

```text
frontend/
  Next.js UI, canvas, socket hook, room screens

backend/
  FastAPI APIs, WebSocket event router, room manager, game classes, PostgreSQL models
```

## Local Setup

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm.cmd install
copy .env.example .env.local
npm.cmd run dev
```

Open `http://localhost:3000`.

## Smoke Tests

Start a backend on a test port:

```bash
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8124
```

Run the WebSocket smoke suite in another terminal:

```bash
cd backend
.venv\Scripts\python.exe scripts\smoke_tests.py
```

The suite checks public rooms, multi-client joins, max-player limits, reconnect, host-only start, word choice, drawing sync, guessing, scoring, replay, restart, and kick.

## PostgreSQL

Create a PostgreSQL database named `sketchy`, then update `backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/sketchy
```

The backend creates the required tables on startup.

## Deployment

Recommended setup:

```text
Frontend: Vercel
Backend: Render or Railway
Database: Supabase, Neon, Render PostgreSQL, or Railway PostgreSQL
```

Frontend environment:

```env
NEXT_PUBLIC_API_URL=https://your-backend-url
```

Backend environment:

```env
FRONTEND_ORIGIN=https://your-frontend-url
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database
```

Backend start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## WebSocket Message Shape

```json
{
  "type": "draw_move",
  "payload": {
    "x": 120,
    "y": 80
  }
}
```

Important events:

```text
join_room
player_joined
player_left
start_game
round_start
word_chosen
game_state
draw_start
draw_move
draw_end
draw_data
draw_undo
canvas_clear
canvas_redraw
replay_data
guess
guess_result
chat_message
kick_player
restart_game
round_end
game_over
```
