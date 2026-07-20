import { RoomSettings } from "@/types/game";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export function socketUrl() {
  return API_URL.replace(/^http/, "ws") + "/ws";
}

export async function createRoom(settings: RoomSettings) {
  const response = await fetch(`${API_URL}/api/rooms`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ settings }),
  });

  if (!response.ok) {
    throw new Error("Could not create room");
  }

  return response.json() as Promise<{ roomCode: string; settings: RoomSettings }>;
}

export async function findPublicRoom() {
  const response = await fetch(`${API_URL}/api/rooms/public/available`);

  if (!response.ok) {
    throw new Error("No public room available");
  }

  return response.json() as Promise<{ roomCode: string }>;
}
