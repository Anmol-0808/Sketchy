"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { findPublicRoom } from "@/lib/api";

export function JoinRoomForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleJoinPublic() {
    setError(null);
    if (!name.trim()) {
      setError("Enter your player name first");
      return;
    }
    try {
      const room = await findPublicRoom();
      router.push(`/room/${room.roomCode}?name=${encodeURIComponent(name.trim())}`);
    } catch {
      setError("No public room is waiting. Create one instead.");
    }
  }

  function handleJoin(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!name.trim() || !joinCode.trim()) {
      setError("Enter your name and room code");
      return;
    }
    router.push(`/room/${joinCode.trim().toUpperCase()}?name=${encodeURIComponent(name.trim())}`);
  }

  return (
    <main className="form-page-shell">
      <section className="form-brand">
        <Link href="/">Sketchy</Link>
      </section>

      <div className="form-page-actions join-page-actions">
        <form className="join-panel form-page-panel" onSubmit={handleJoin}>
          <div className="panel-title">
            <p className="eyebrow">Quick play</p>
            <h2>Join Game</h2>
          </div>
          <label>
            Player name
            <input value={name} onChange={(event) => setName(event.target.value)} maxLength={24} />
          </label>
          <label>
            Room code
            <input value={joinCode} onChange={(event) => setJoinCode(event.target.value)} maxLength={8} />
          </label>
          <button className="primary-button">Join Room</button>
          <button className="secondary-button" type="button" onClick={handleJoinPublic}>
            Join Public Room
          </button>
          <Link className="back-link" href="/">
            Back
          </Link>
          {error && <p className="error-text">{error}</p>}
        </form>
      </div>
    </main>
  );
}
