# Sketchy

Sketchy is a full-stack skribbl.io-inspired multiplayer drawing and guessing game. Players create or join rooms, one player draws a selected word, the others guess in real time, and scores update across rounds until a winner is shown.

## Live URL

```text
Frontend: add after deployment
Backend: add after deployment
```

## Tech Stack

```text
Frontend: Next.js, React, TypeScript
Canvas: HTML5 Canvas API
Backend: FastAPI, Python
Real time: FastAPI WebSockets
Database: PostgreSQL with SQLAlchemy async models
Word source: JSON seed list plus optional PostgreSQL words
```

## Core Flow

```text
Home -> Create Room / Join Room -> Lobby -> Word Selection -> Drawing Round -> Round Result -> Next Round -> Final Leaderboard
```

## Must-Have Requirements From The PDF

| Requirement | Status |
| --- | --- |
| Create room with configurable settings | Done |
| Join room through code or invite link | Done |
| Lobby with player list | Done |
| Host starts the game | Done |
| Turn-based rounds with one drawer | Done |
| Drawer chooses from word options | Done |
| Guessers see hidden word/hints | Done |
| Real-time drawing sync | Done |
| Guess input and answer checking | Done |
| Scoring and leaderboard | Done |
| Game end with winner | Done |
| WebSockets for drawing, guessing, chat, and game state | Done |
| Basic drawing tools: pen, colors, brush size, undo, clear | Done |
| README with setup and architecture | Done |

## Should-Have Requirements

| Requirement | Status |
| --- | --- |
| Hints / revealed letters | Done |
| Chat / guess stream | Done |
| Draw time countdown | Done |
| Private rooms with invite links | Done |
| Public rooms | Done |

## Bonus Features

| Bonus Idea From PDF | Status |
| --- | --- |
| OOP backend structure with Room, Player, game logic classes | Implemented |
| Room settings: max players, rounds, draw time, word count, hints | Implemented |
| Word categories | Implemented |
| Custom word list | Implemented |
| Eraser | Implemented |
| Host kick | Implemented |
| Replay last round drawing | Implemented |
| Avatars | Partially implemented with colored letter avatars |
| Spectator mode | Not implemented |
| Votekick | Not implemented |
| Ban/report moderation | Not implemented |
| Multiple languages | Not implemented |
| Word modes: normal/hidden/combination | Partially implemented with hidden word and hints |

## Room Settings

Hosts can configure:

```text
max players: 2-20
rounds: 2-10
draw time: 15-240 seconds
word choices: 1-5
hints: 0-5
private/public room
word categories
custom words
```

## WebSocket Architecture

All real-time messages use one JSON shape:

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
guess
guess_result
chat
chat_message
round_end
game_over
kick_player
restart_game
request_replay
replay_data
kicked
request_state
```

Room creation is handled through REST instead of WebSocket:

```text
POST /api/rooms
```

This keeps room creation simple, while gameplay stays fully real time through WebSockets.

## Canvas Sync

The app does not send canvas images. It sends stroke data:

```json
{
  "x": 120,
  "y": 80,
  "color": "#111827",
  "size": 6,
  "mode": "draw"
}
```

The backend validates that the sender is the current drawer, stores the current round strokes in memory, and broadcasts `draw_data` to all room clients. Every browser then redraws the same stroke locally on its own HTML5 canvas.

## Scoring

Correct guesses use time-based scoring:

```text
guesser_points = 100 + remaining_seconds * 10
drawer_points = 50 per correct guess
```

Rules:

```text
drawer cannot guess
each guesser scores once per round
correct guesses are announced without revealing the word
wrong guesses appear as chat messages
matching is case-insensitive and trims spaces
```

## Project Structure

```text
backend/
  app/
    core/
    db/
    game/
    models/
    routers/
    schemas/
    services/
    websocket/
  data/
  scripts/

frontend/
  src/
    app/
    components/
    hooks/
    lib/
    types/
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

Open:

```text
http://localhost:3000
```

## PostgreSQL

Create a PostgreSQL database named `sketchy`, then update `backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/sketchy
```

The backend creates the required tables on startup.

PostgreSQL stores:

```text
rooms
players
words
game results
final scores
```

Live game state stays in backend memory for fast WebSocket updates:

```text
active sockets
current drawer
current word
timer
current round strokes
guessed players
```

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

The suite checks:

```text
public rooms
multi-client joins
max-player limits
reconnect
host-only start
word choice
drawing sync
guessing
scoring
replay
restart
kick
```

## Deployment Plan

Recommended:

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

Important deployment note:

```text
Run the backend as one instance / one worker for this internship version.
Live room state is stored in memory, so multiple backend replicas can split players across different room states.
```

## Validation Status

Latest local checks:

```text
backend compile: passed
frontend lint: passed
frontend production build: passed
WebSocket smoke suite: passed
words.json: 1000 unique words
```
