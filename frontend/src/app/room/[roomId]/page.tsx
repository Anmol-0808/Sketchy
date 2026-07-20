import { RoomClient } from "@/components/game/RoomClient";

type Props = {
  params: Promise<{ roomId: string }>;
};

export default async function RoomPage({ params }: Props) {
  const { roomId } = await params;
  return <RoomClient roomCode={roomId.toUpperCase()} />;
}
