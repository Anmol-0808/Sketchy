"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { socketUrl } from "@/lib/api";
import { ChatMessage, GameState, SocketMessage } from "@/types/game";

type HookResult = {
  state: GameState | null;
  playerId: string | null;
  messages: ChatMessage[];
  lastEvent: SocketMessage | null;
  connected: boolean;
  error: string | null;
  send: (type: string, payload?: Record<string, unknown>) => void;
};

export function useGameSocket(roomCode: string, playerName: string | null): HookResult {
  const socketRef = useRef<WebSocket | null>(null);
  const [state, setState] = useState<GameState | null>(null);
  const [playerId, setPlayerId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [lastEvent, setLastEvent] = useState<SocketMessage | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addSystemMessage = useCallback((text: string, kind: ChatMessage["kind"] = "system") => {
    setMessages((current) => [
      ...current.slice(-80),
      { id: crypto.randomUUID(), playerName: "Sketchy", text, kind },
    ]);
  }, []);

  useEffect(() => {
    if (!playerName) {
      return;
    }

    const socket = new WebSocket(socketUrl());
    socketRef.current = socket;
    const sessionKey = `sketchy:${roomCode}:player`;
    const storedSession = window.sessionStorage.getItem(sessionKey);
    const storedPlayer = storedSession ? JSON.parse(storedSession) as { id?: string; name?: string } : null;
    const storedPlayerId = storedPlayer?.name === playerName ? storedPlayer.id : null;

    socket.onopen = () => {
      setError(null);
      setConnected(true);
      socket.send(JSON.stringify({ type: "join_room", payload: { roomCode, playerName, playerId: storedPlayerId } }));
    };

    socket.onclose = () => {
      setConnected(false);
    };

    socket.onerror = () => {
      setError("WebSocket connection failed");
    };

    socket.onmessage = (event) => {
      const message = JSON.parse(event.data) as SocketMessage;
      setLastEvent(message);

      if (message.type === "join_success") {
        const payload = message.payload as { player: { id: string }; room: GameState };
        setPlayerId(payload.player.id);
        window.sessionStorage.setItem(sessionKey, JSON.stringify({ id: payload.player.id, name: playerName }));
        setState(payload.room);
      }

      if (message.type === "game_state") {
        setState(message.payload as GameState);
      }

      if (message.type === "chat_message") {
        const payload = message.payload as { playerName: string; text: string };
        setMessages((current) => [
          ...current.slice(-80),
          { id: crypto.randomUUID(), playerName: payload.playerName, text: payload.text, kind: "chat" },
        ]);
      }

      if (message.type === "guess_result") {
        const payload = message.payload as { playerName: string; points: number };
        addSystemMessage(`${payload.playerName} guessed it and earned ${payload.points} points`, "correct");
      }

      if (message.type === "round_end") {
        const payload = message.payload as { word: string; reason: string };
        addSystemMessage(`Round ended: ${payload.word || "no word selected"}`);
      }

      if (message.type === "game_over") {
        addSystemMessage("Game over. Final leaderboard is ready.");
      }

      if (message.type === "error") {
        const payload = message.payload as { message: string };
        setError(payload.message);
        addSystemMessage(payload.message);
      }

      if (message.type === "kicked") {
        window.sessionStorage.removeItem(sessionKey);
        const payload = message.payload as { message: string };
        setError(payload.message);
        addSystemMessage(payload.message);
      }
    };

    return () => {
      socket.close();
      socketRef.current = null;
    };
  }, [addSystemMessage, playerName, roomCode]);

  const send = useCallback((type: string, payload: Record<string, unknown> = {}) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type, payload }));
    }
  }, []);

  return { state, playerId, messages, lastEvent, connected, error, send };
}
