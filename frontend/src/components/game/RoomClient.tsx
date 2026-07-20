"use client";

import { FormEvent, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ChatPanel } from "@/components/game/ChatPanel";
import { DrawingToolbar } from "@/components/game/DrawingToolbar";
import { GameCanvas } from "@/components/game/GameCanvas";
import { GameHeader } from "@/components/game/GameHeader";
import { PlayerList } from "@/components/game/PlayerList";
import { WordChooser } from "@/components/game/WordChooser";
import { useGameSocket } from "@/hooks/useGameSocket";
import { Player } from "@/types/game";

type Props = {
  roomCode: string;
};

export function RoomClient({ roomCode }: Props) {
  const searchParams = useSearchParams();
  const initialName = searchParams.get("name");
  const [pendingName, setPendingName] = useState(initialName ?? "");
  const [playerName, setPlayerName] = useState(initialName);
  const [color, setColor] = useState("#111827");
  const [size, setSize] = useState(6);
  const [mode, setMode] = useState<"draw" | "erase">("draw");
  const [inviteCopied, setInviteCopied] = useState(false);
  const { state, playerId, messages, lastEvent, connected, error, send } = useGameSocket(roomCode, playerName);

  const currentPlayer = useMemo(
    () => state?.players.find((player) => player.id === playerId) ?? null,
    [playerId, state?.players],
  );

  const isDrawer = Boolean(playerId && state?.drawerId === playerId);
  const canDraw = isDrawer && state?.phase === "drawing";
  const winner = [...(state?.players ?? [])].sort((first, second) => second.score - first.score)[0];
  const canStart = Boolean(currentPlayer?.isHost && (state?.players.length ?? 0) >= 2);

  function handleNameSubmit(event: FormEvent) {
    event.preventDefault();
    if (pendingName.trim()) {
      setPlayerName(pendingName.trim());
    }
  }

  async function copyInviteLink() {
    const inviteUrl = `${window.location.origin}/room/${roomCode}`;
    await navigator.clipboard.writeText(inviteUrl);
    setInviteCopied(true);
    window.setTimeout(() => setInviteCopied(false), 1800);
  }

  if (!playerName) {
    return (
      <main className="join-gate">
        <form className="setup-panel" onSubmit={handleNameSubmit}>
          <h1>Join {roomCode}</h1>
          <label>
            Player name
            <input value={pendingName} onChange={(event) => setPendingName(event.target.value)} maxLength={24} />
          </label>
          <button className="primary-button">Enter Room</button>
        </form>
      </main>
    );
  }

  if (!state) {
    return (
      <main className="loading-room">
        <h1>Joining {roomCode}</h1>
        <p>{connected ? "Syncing room state..." : "Opening WebSocket connection..."}</p>
        {error && <p className="error-text">{error}</p>}
      </main>
    );
  }

  return (
    <main className="game-shell">
      <GameHeader state={state} />

      <section className="game-layout">
        <PlayerList
          players={state.players}
          currentPlayerId={playerId}
          canModerate={Boolean(currentPlayer?.isHost && state.phase === "lobby")}
          onKick={(targetId) => send("kick_player", { playerId: targetId })}
        />

        <section className="canvas-column">
          {state.phase === "lobby" && (
            <div className="lobby-banner">
              <div>
                <p className="eyebrow">Room {state.roomCode}</p>
                <h1>Waiting for players</h1>
                <p>Share this code with a friend. The game needs at least two players before the host starts.</p>
                <div className="room-settings">
                  <span>{state.settings.maxPlayers} players</span>
                  <span>{state.settings.rounds} rounds</span>
                  <span>{state.settings.drawTime}s draw time</span>
                  <span>{state.settings.wordCount} word choices</span>
                  <span>{state.settings.hints} hints</span>
                  <span>{state.settings.categories.length ? state.settings.categories.join(", ") : "all categories"}</span>
                  {state.settings.customWords.length > 0 && <span>{state.settings.customWords.length} custom words</span>}
                </div>
              </div>
              <div className="lobby-actions">
                <button className="secondary-button" onClick={copyInviteLink}>
                  {inviteCopied ? "Link Copied" : "Copy Link"}
                </button>
                {currentPlayer?.isHost && (
                  <button className="primary-button" onClick={() => send("start_game")} disabled={!canStart}>
                    {canStart ? "Start Game" : "Need 2 Players"}
                  </button>
                )}
              </div>
            </div>
          )}

          {state.phase === "choosing" && (
            <WordChooser
              options={state.wordOptions}
              isDrawer={isDrawer}
              drawerName={state.drawerName}
              onChoose={(word) => send("word_chosen", { word })}
            />
          )}

          {state.phase === "round_end" && (
            <div className="round-result">
              <div>
                <h2>Word was {state.word}</h2>
                <p>Next round starts in a moment.</p>
              </div>
              <button className="secondary-button" onClick={() => send("request_replay")}>
                Replay Drawing
              </button>
            </div>
          )}

          {state.phase === "game_over" && (
            <FinalLeaderboard
              winnerName={winner?.name || "Winner"}
              players={state.players}
              canRestart={Boolean(currentPlayer?.isHost)}
              onRestart={() => send("restart_game")}
            />
          )}

          <GameCanvas canDraw={canDraw} color={color} size={size} mode={mode} lastEvent={lastEvent} send={send} />
          <DrawingToolbar
            color={color}
            size={size}
            mode={mode}
            canDraw={canDraw}
            onColorChange={setColor}
            onSizeChange={setSize}
            onModeChange={setMode}
            onUndo={() => send("draw_undo")}
            onClear={() => send("canvas_clear")}
          />
        </section>

        <ChatPanel messages={messages} phase={state.phase} isDrawer={isDrawer} onSend={(text) => send("guess", { text })} />
      </section>

      {error && <p className="floating-error">{error}</p>}
    </main>
  );
}

function FinalLeaderboard({
  winnerName,
  players,
  canRestart,
  onRestart,
}: {
  winnerName: string;
  players: Player[];
  canRestart: boolean;
  onRestart: () => void;
}) {
  const rankedPlayers = [...players].sort((first, second) => second.score - first.score);

  return (
    <div className="final-board">
      <div>
        <p className="eyebrow">Game over</p>
        <h2>{winnerName} wins</h2>
      </div>
      <div className="final-ranks">
        {rankedPlayers.map((player, index) => (
          <div className="final-rank" key={player.id}>
            <span>#{index + 1}</span>
            <strong>{player.name}</strong>
            <b>{player.score}</b>
          </div>
        ))}
      </div>
      <div className="final-actions">
        {canRestart && (
          <button className="primary-button" onClick={onRestart}>
            Play Again
          </button>
        )}
        <Link className="secondary-button link-button" href="/">
          Home
        </Link>
      </div>
    </div>
  );
}
