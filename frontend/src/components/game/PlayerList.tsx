import { Player } from "@/types/game";

type Props = {
  players: Player[];
  currentPlayerId: string | null;
  canModerate: boolean;
  onKick: (playerId: string) => void;
};

export function PlayerList({ players, currentPlayerId, canModerate, onKick }: Props) {
  const rankedPlayers = [...players].sort((first, second) => second.score - first.score);

  return (
    <aside className="side-panel player-panel">
      <h2>Scoreboard</h2>
      <div className="player-list">
        {rankedPlayers.map((player, index) => {
          const isCurrentPlayer = player.id === currentPlayerId;
          const rowClassName = ["player-row", player.isDrawer ? "drawing-player" : "", isCurrentPlayer ? "current-player" : ""]
            .filter(Boolean)
            .join(" ");

          return (
            <div className={rowClassName} key={player.id}>
              <div className={`avatar avatar-${index % 6}`}>{player.name.slice(0, 1).toUpperCase()}</div>
              <div className="player-meta">
                <span>
                  #{index + 1} {player.name}
                </span>
                <small>{!player.connected ? "Disconnected" : player.isDrawer ? "Drawing now" : player.hasGuessed ? "Guessed" : "Guessing"}</small>
                <div className="player-tags">
                  {isCurrentPlayer && <em>You</em>}
                  {player.isHost && <em>Host</em>}
                  {player.isDrawer && <em>Drawer</em>}
                </div>
              </div>
              <strong>{player.score.toLocaleString()}</strong>
              {canModerate && player.id !== currentPlayerId && (
                <button className="kick-button" onClick={() => onKick(player.id)} title={`Kick ${player.name}`}>
                  Kick
                </button>
              )}
            </div>
          );
        })}
      </div>
    </aside>
  );
}
