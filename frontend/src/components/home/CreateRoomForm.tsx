"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createRoom } from "@/lib/api";
import { RoomSettings } from "@/types/game";

const defaultSettings: RoomSettings = {
  maxPlayers: 8,
  rounds: 3,
  drawTime: 80,
  wordCount: 3,
  hints: 3,
  isPrivate: true,
  categories: [],
  customWords: [],
};

const categories = ["animals", "food", "objects", "places", "actions"];

export function CreateRoomForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [settings, setSettings] = useState(defaultSettings);
  const [customWordsText, setCustomWordsText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError("Enter your player name first");
      return;
    }

    setBusy(true);
    try {
      const customWords = customWordsText
        .split(/[\n,]/)
        .map((word) => word.trim())
        .filter(Boolean);
      const room = await createRoom({ ...settings, customWords });
      router.push(`/room/${room.roomCode}?name=${encodeURIComponent(name.trim())}`);
    } catch {
      setError("Backend is not reachable. Start FastAPI and try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="form-page-shell">
      <section className="form-brand">
        <Link href="/">Sketchy</Link>
      </section>

      <div className="home-actions form-page-actions">
        <form className="setup-panel form-page-panel" onSubmit={handleCreate}>
          <div className="panel-title">
            <p className="eyebrow">Private room</p>
            <h2>Create Game</h2>
          </div>
          <label>
            Player name
            <input value={name} onChange={(event) => setName(event.target.value)} maxLength={24} />
          </label>

          <div className="settings-grid">
            <label>
              Players
              <input
                type="number"
                min={2}
                max={20}
                value={settings.maxPlayers}
                onChange={(event) => setSettings({ ...settings, maxPlayers: Number(event.target.value) })}
              />
            </label>
            <label>
              Rounds
              <input
                type="number"
                min={2}
                max={10}
                value={settings.rounds}
                onChange={(event) => setSettings({ ...settings, rounds: Number(event.target.value) })}
              />
            </label>
            <label>
              Draw time
              <input
                type="number"
                min={15}
                max={240}
                value={settings.drawTime}
                onChange={(event) => setSettings({ ...settings, drawTime: Number(event.target.value) })}
              />
            </label>
            <label>
              Words
              <input
                type="number"
                min={1}
                max={5}
                value={settings.wordCount}
                onChange={(event) => setSettings({ ...settings, wordCount: Number(event.target.value) })}
              />
            </label>
            <label>
              Hints
              <input
                type="number"
                min={0}
                max={5}
                value={settings.hints}
                onChange={(event) => setSettings({ ...settings, hints: Number(event.target.value) })}
              />
            </label>
          </div>

          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={settings.isPrivate}
              onChange={(event) => setSettings({ ...settings, isPrivate: event.target.checked })}
            />
            Private invite room
          </label>

          <div className="category-picker">
            {categories.map((category) => (
              <button
                className={settings.categories.includes(category) ? "category-chip selected" : "category-chip"}
                key={category}
                type="button"
                onClick={() => {
                  const selected = settings.categories.includes(category)
                    ? settings.categories.filter((item) => item !== category)
                    : [...settings.categories, category];
                  setSettings({ ...settings, categories: selected });
                }}
              >
                {category}
              </button>
            ))}
          </div>

          <label>
            Custom words
            <textarea
              value={customWordsText}
              onChange={(event) => setCustomWordsText(event.target.value)}
              placeholder="Separate words with commas or new lines"
              rows={4}
            />
          </label>

          <button className="primary-button" disabled={busy}>
            {busy ? "Creating..." : "Create Room"}
          </button>
          <Link className="back-link" href="/">
            Back
          </Link>
        </form>

        {error && <p className="error-text">{error}</p>}
      </div>
    </main>
  );
}
