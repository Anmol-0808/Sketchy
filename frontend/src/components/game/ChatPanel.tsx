"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { ChatMessage, GamePhase } from "@/types/game";

type Props = {
  messages: ChatMessage[];
  phase: GamePhase;
  isDrawer: boolean;
  onSend: (text: string) => void;
};

export function ChatPanel({ messages, phase, isDrawer, onSend }: Props) {
  const [text, setText] = useState("");
  const listRef = useRef<HTMLDivElement | null>(null);
  const disabled = phase !== "drawing" || isDrawer;
  const title = isDrawer ? "Chat" : "Guesses";

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [messages]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!text.trim()) {
      return;
    }
    onSend(text);
    setText("");
  }

  return (
    <aside className="side-panel chat-panel">
      <h2>{title}</h2>
      <div className="message-list" ref={listRef}>
        {messages.length === 0 && (
          <div className="empty-chat">
            {phase === "lobby" ? "Guesses will appear here once the round begins." : "No messages yet."}
          </div>
        )}
        {messages.map((message) => (
          <div className={`message ${message.kind}`} key={message.id}>
            <strong>{message.playerName}</strong>
            <span>{message.text}</span>
          </div>
        ))}
      </div>
      <form className="guess-form" onSubmit={handleSubmit}>
        <input
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder={disabled ? "Waiting for guessers" : "Type your guess"}
          disabled={disabled}
          maxLength={180}
        />
        <button disabled={disabled}>Send</button>
      </form>
    </aside>
  );
}
