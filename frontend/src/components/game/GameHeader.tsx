"use client";

import { useEffect, useState } from "react";
import { GameState } from "@/types/game";

type Props = {
  state: GameState;
};

export function GameHeader({ state }: Props) {
  const displayWord = getDisplayWord(state);
  const roundText = state.phase === "lobby" ? "Lobby" : `${state.round || 0}/${state.totalRounds}`;
  const timerText = getTimerText(state);

  return (
    <header className="game-header">
      <div className="header-brand">
        <span>Sketchy</span>
      </div>
      <div>
        <span className="header-label">Round</span>
        <strong>{roundText}</strong>
      </div>
      <div className="word-display">{displayWord}</div>
      <div>
        <span className="header-label">Timer</span>
        <strong>{timerText}</strong>
      </div>
    </header>
  );
}

function getDisplayWord(state: GameState) {
  if (state.phase === "lobby") {
    return "Waiting for players";
  }
  if (state.phase === "choosing") {
    return state.drawerName ? `${state.drawerName} is choosing` : "Choosing word";
  }
  return state.wordHint || state.word || "_ ".repeat(state.wordLength || 5).trim();
}

function getTimerText(state: GameState) {
  if (state.phase === "lobby") {
    return "Ready";
  }
  if (state.phase === "choosing") {
    return "Pick";
  }
  if (state.phase === "drawing") {
    return <><Countdown key={`${state.round}-${state.drawerId}-${state.remainingSeconds}`} seconds={state.remainingSeconds} />s</>;
  }
  if (state.phase === "game_over") {
    return "Done";
  }
  return "Next";
}

function Countdown({ seconds }: { seconds: number }) {
  const [value, setValue] = useState(seconds);

  useEffect(() => {
    const id = window.setInterval(() => setValue((current) => Math.max(0, current - 1)), 1000);
    return () => window.clearInterval(id);
  }, []);

  return value;
}
