"use client";

import { PointerEvent, useCallback, useEffect, useRef } from "react";
import { SocketMessage, Stroke } from "@/types/game";

type Props = {
  canDraw: boolean;
  color: string;
  size: number;
  mode: "draw" | "erase";
  lastEvent: SocketMessage | null;
  send: (type: string, payload?: Record<string, unknown>) => void;
};

const width = 900;
const height = 560;

export function GameCanvas({ canDraw, color, size, mode, lastEvent, send }: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const drawingRef = useRef(false);
  const lastMoveAtRef = useRef(0);

  const clearCanvas = useCallback(() => {
    const context = canvasRef.current?.getContext("2d");
    if (!context) {
      return;
    }
    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, width, height);
  }, []);

  const drawRemote = useCallback((payload: Record<string, unknown>) => {
    const context = canvasRef.current?.getContext("2d");
    if (!context) {
      return;
    }

    if (payload.action === "start") {
      context.beginPath();
      context.lineCap = "round";
      context.lineJoin = "round";
      context.strokeStyle = payload.mode === "erase" ? "#ffffff" : String(payload.color);
      context.lineWidth = Number(payload.size);
      const points = payload.points as Array<{ x: number; y: number }>;
      context.moveTo(points[0].x, points[0].y);
    }

    if (payload.action === "move") {
      context.lineTo(Number(payload.x), Number(payload.y));
      context.stroke();
    }

    if (payload.action === "end") {
      context.closePath();
    }
  }, []);

  const drawStrokes = useCallback((strokes: Stroke[], animated: boolean) => {
    const context = canvasRef.current?.getContext("2d");
    if (!context) {
      return Promise.resolve();
    }

    clearCanvas();
    const run = async () => {
      for (const stroke of strokes) {
        if (stroke.points.length === 0) {
          continue;
        }
        context.beginPath();
        context.lineCap = "round";
        context.lineJoin = "round";
        context.strokeStyle = stroke.mode === "erase" ? "#ffffff" : stroke.color;
        context.lineWidth = stroke.size;
        context.moveTo(stroke.points[0].x, stroke.points[0].y);
        for (const point of stroke.points.slice(1)) {
          context.lineTo(point.x, point.y);
          context.stroke();
          if (animated) {
            await new Promise((resolve) => window.setTimeout(resolve, 10));
          }
        }
        context.closePath();
      }
    };

    return run();
  }, [clearCanvas]);

  useEffect(() => {
    clearCanvas();
  }, [clearCanvas]);

  useEffect(() => {
    if (!lastEvent) {
      return;
    }

    if (lastEvent.type === "canvas_clear") {
      clearCanvas();
    }

    if (lastEvent.type === "canvas_redraw") {
      const payload = lastEvent.payload as { strokes: Stroke[] };
      void drawStrokes(payload.strokes, false);
    }

    if (lastEvent.type === "replay_data") {
      const payload = lastEvent.payload as { strokes: Stroke[] };
      void drawStrokes(payload.strokes, true);
    }

    if (lastEvent.type === "draw_data") {
      drawRemote(lastEvent.payload as Record<string, unknown>);
    }
  }, [clearCanvas, drawRemote, drawStrokes, lastEvent]);

  function pointFromEvent(event: PointerEvent<HTMLCanvasElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    return {
      x: ((event.clientX - rect.left) / rect.width) * width,
      y: ((event.clientY - rect.top) / rect.height) * height,
    };
  }

  function handlePointerDown(event: PointerEvent<HTMLCanvasElement>) {
    if (!canDraw) {
      return;
    }
    drawingRef.current = true;
    lastMoveAtRef.current = 0;
    event.currentTarget.setPointerCapture(event.pointerId);
    send("draw_start", { ...pointFromEvent(event), color, size: mode === "erase" ? Math.max(size, 18) : size, mode });
  }

  function handlePointerMove(event: PointerEvent<HTMLCanvasElement>) {
    if (!canDraw || !drawingRef.current) {
      return;
    }
    const now = performance.now();
    if (now - lastMoveAtRef.current < 16) {
      return;
    }
    lastMoveAtRef.current = now;
    send("draw_move", pointFromEvent(event));
  }

  function handlePointerUp(event: PointerEvent<HTMLCanvasElement>) {
    if (!canDraw || !drawingRef.current) {
      return;
    }
    drawingRef.current = false;
    event.currentTarget.releasePointerCapture(event.pointerId);
    send("draw_end");
  }

  return (
    <canvas
      ref={canvasRef}
      className={canDraw ? "game-canvas can-draw" : "game-canvas"}
      width={width}
      height={height}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
    />
  );
}
