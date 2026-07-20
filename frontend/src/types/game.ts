export type GamePhase = "lobby" | "choosing" | "drawing" | "round_end" | "game_over";

export type RoomSettings = {
  maxPlayers: number;
  rounds: number;
  drawTime: number;
  wordCount: number;
  hints: number;
  isPrivate: boolean;
  categories: string[];
  customWords: string[];
};

export type Player = {
  id: string;
  name: string;
  score: number;
  isHost: boolean;
  isDrawer: boolean;
  hasGuessed: boolean;
  connected: boolean;
  kicked: boolean;
};

export type GameState = {
  roomCode: string;
  phase: GamePhase;
  round: number;
  totalRounds: number;
  drawerId: string | null;
  drawerName: string | null;
  word: string | null;
  wordHint: string | null;
  wordLength: number;
  wordOptions: string[];
  players: Player[];
  settings: RoomSettings;
  remainingSeconds: number;
};

export type ChatMessage = {
  id: string;
  playerName: string;
  text: string;
  kind: "chat" | "system" | "correct";
};

export type Stroke = {
  id: string;
  color: string;
  size: number;
  mode: "draw" | "erase";
  points: Array<{ x: number; y: number }>;
};

export type SocketMessage<T = unknown> = {
  type: string;
  payload: T;
};
