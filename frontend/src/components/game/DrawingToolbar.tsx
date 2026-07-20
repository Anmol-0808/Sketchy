type Props = {
  color: string;
  size: number;
  mode: "draw" | "erase";
  canDraw: boolean;
  onColorChange: (color: string) => void;
  onSizeChange: (size: number) => void;
  onModeChange: (mode: "draw" | "erase") => void;
  onUndo: () => void;
  onClear: () => void;
};

const colors = ["#111827", "#ef4444", "#f97316", "#facc15", "#22c55e", "#06b6d4", "#3b82f6", "#a855f7", "#ec4899", "#ffffff"];

export function DrawingToolbar({ color, size, mode, canDraw, onColorChange, onSizeChange, onModeChange, onUndo, onClear }: Props) {
  return (
    <div className="drawing-toolbar" aria-disabled={!canDraw}>
      <div className="mode-toggle">
        <button className={mode === "draw" ? "tool-button active" : "tool-button"} onClick={() => onModeChange("draw")} disabled={!canDraw}>
          Pen
        </button>
        <button className={mode === "erase" ? "tool-button active" : "tool-button"} onClick={() => onModeChange("erase")} disabled={!canDraw}>
          Eraser
        </button>
      </div>
      <div className="swatches">
        {colors.map((item) => (
          <button
            className={item === color ? "swatch selected" : "swatch"}
            key={item}
            style={{ background: item }}
            title={item === "#ffffff" ? "White" : item}
            onClick={() => {
              onModeChange("draw");
              onColorChange(item);
            }}
            disabled={!canDraw}
          />
        ))}
      </div>
      <label className="brush-control">
        <span>Size</span>
        <input
          type="range"
          min={2}
          max={28}
          value={size}
          onChange={(event) => onSizeChange(Number(event.target.value))}
          disabled={!canDraw}
        />
      </label>
      <button className="tool-button" onClick={onUndo} disabled={!canDraw} title="Undo last stroke">
        Undo
      </button>
      <button className="tool-button" onClick={onClear} disabled={!canDraw} title="Clear canvas">
        Clear
      </button>
    </div>
  );
}
