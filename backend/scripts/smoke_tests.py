import asyncio
import json
import os
import urllib.error
import urllib.request

import websockets


API_URL = os.getenv("SMOKE_API_URL", "http://127.0.0.1:8124")
WS_URL = API_URL.replace("http", "ws") + "/ws"


class Client:
    def __init__(self, websocket):
        self.websocket = websocket
        self.queue = asyncio.Queue()
        self.task = asyncio.create_task(self.collect())

    async def collect(self):
        async for raw in self.websocket:
            await self.queue.put(json.loads(raw))

    async def send(self, event_type, payload=None):
        await self.websocket.send(json.dumps({"type": event_type, "payload": payload or {}}))

    async def wait_for(self, event_type, timeout=8):
        skipped = []
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            message = await asyncio.wait_for(self.queue.get(), timeout=deadline - loop.time())
            if message["type"] == event_type:
                for skipped_message in skipped:
                    self.queue.put_nowait(skipped_message)
                return message
            skipped.append(message)
        raise TimeoutError(event_type)

    async def close(self):
        self.task.cancel()
        await self.websocket.close()


def post_json(path, payload):
    body = json.dumps(payload).encode()
    request = urllib.request.Request(
        API_URL + path,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return json.loads(urllib.request.urlopen(request, timeout=10).read())


def get_json(path):
    return json.loads(urllib.request.urlopen(API_URL + path, timeout=10).read())


async def connect(room_code, player_name, player_id=None):
    websocket = await websockets.connect(WS_URL)
    client = Client(websocket)
    payload = {"roomCode": room_code, "playerName": player_name}
    if player_id:
        payload["playerId"] = player_id
    await client.send("join_room", payload)
    return client


async def expect_error(client, text):
    message = await client.wait_for("error")
    assert text in message["payload"]["message"], message


async def wait_for_phase(client, phase):
    for _ in range(20):
        message = await client.wait_for("game_state")
        if message["payload"]["phase"] == phase:
            return message
    raise AssertionError(f"missing phase {phase}")


async def test_health_and_public_room():
    assert get_json("/api/health")["status"] == "ok"
    room = post_json(
        "/api/rooms",
        {
            "settings": {
                "maxPlayers": 4,
                "rounds": 2,
                "drawTime": 20,
                "wordCount": 3,
                "hints": 2,
                "isPrivate": False,
                "categories": ["food"],
                "customWords": ["internship win"],
            }
        },
    )
    public_room = get_json("/api/rooms/public/available")
    assert public_room["roomCode"]


async def test_join_limits_and_reconnect():
    room = post_json(
        "/api/rooms",
        {"settings": {"maxPlayers": 3, "rounds": 2, "drawTime": 20, "wordCount": 3, "hints": 2, "isPrivate": True}},
    )
    code = room["roomCode"]

    first = await connect(code, "First")
    first_join = await first.wait_for("join_success")
    first_id = first_join["payload"]["player"]["id"]
    await first.close()

    first_reconnected = await connect(code, "First", first_id)
    reconnected = await first_reconnected.wait_for("join_success")
    assert reconnected["payload"]["player"]["id"] == first_id

    second = await connect(code, "Second")
    await second.wait_for("join_success")
    third = await connect(code, "Third")
    third_join = await third.wait_for("join_success")
    assert len(third_join["payload"]["room"]["players"]) == 3

    fourth = await connect(code, "Fourth")
    await expect_error(fourth, "Room is full")

    await first_reconnected.close()
    await second.close()
    await third.close()
    await fourth.close()


async def test_full_game_flow():
    room = post_json(
        "/api/rooms",
        {
            "settings": {
                "maxPlayers": 4,
                "rounds": 2,
                "drawTime": 20,
                "wordCount": 3,
                "hints": 2,
                "isPrivate": True,
                "categories": ["objects"],
                "customWords": ["codex crown"],
            }
        },
    )
    code = room["roomCode"]
    host = await connect(code, "Host")
    host_join = await host.wait_for("join_success")
    guest = await connect(code, "Guest")
    guest_join = await guest.wait_for("join_success")

    await guest.send("start_game")
    await expect_error(guest, "Only host")

    await host.send("start_game")
    start = await host.wait_for("round_start")
    drawer_id = start["payload"]["drawerId"]
    host_id = host_join["payload"]["player"]["id"]
    guest_id = guest_join["payload"]["player"]["id"]
    drawer = host if drawer_id == host_id else guest
    guesser = guest if drawer_id == host_id else host
    non_drawer = guest if drawer is host else host
    word = start["payload"]["wordOptions"][0]

    await non_drawer.send("word_chosen", {"word": word})
    await expect_error(non_drawer, "Only the drawer")

    await drawer.send("word_chosen", {"word": word})
    await guesser.wait_for("game_state")

    await drawer.send("draw_start", {"x": 8, "y": 8, "color": "#111827", "size": 6, "mode": "draw"})
    draw_start = await guesser.wait_for("draw_data")
    assert draw_start["payload"]["action"] == "start"
    await drawer.send("draw_move", {"x": 18, "y": 18})
    draw_move = await guesser.wait_for("draw_data")
    assert draw_move["payload"]["action"] == "move"
    await drawer.send("draw_end")
    await guesser.wait_for("draw_data")
    await drawer.send("draw_start", {"x": 12, "y": 12, "color": "#111827", "size": 8, "mode": "erase"})
    erase = await guesser.wait_for("draw_data")
    assert erase["payload"]["mode"] == "erase"

    await drawer.send("guess", {"text": word})
    await expect_error(drawer, "Drawer cannot guess")
    await guesser.send("guess", {"text": "wrong guess"})
    chat = await drawer.wait_for("chat_message")
    assert chat["payload"]["text"] == "wrong guess"
    await guesser.send("guess", {"text": word.upper()})
    result = await drawer.wait_for("guess_result")
    assert result["payload"]["correct"] is True
    assert result["payload"]["points"] > 0
    round_end = await drawer.wait_for("round_end")
    assert round_end["payload"]["word"] == word

    await drawer.send("request_replay")
    replay = await drawer.wait_for("replay_data")
    assert len(replay["payload"]["strokes"]) >= 1

    await host.send("restart_game")
    await wait_for_phase(host, "lobby")

    await host.close()
    await guest.close()


async def test_kick():
    room = post_json(
        "/api/rooms",
        {"settings": {"maxPlayers": 4, "rounds": 2, "drawTime": 20, "wordCount": 3, "hints": 2, "isPrivate": True}},
    )
    code = room["roomCode"]
    host = await connect(code, "KickHost")
    await host.wait_for("join_success")
    guest = await connect(code, "KickGuest")
    guest_join = await guest.wait_for("join_success")
    await host.send("kick_player", {"playerId": guest_join["payload"]["player"]["id"]})
    kicked = await guest.wait_for("kicked")
    assert "removed" in kicked["payload"]["message"]
    await host.close()


async def main():
    tests = [
        test_health_and_public_room,
        test_join_limits_and_reconnect,
        test_full_game_flow,
        test_kick,
    ]
    for test in tests:
        await test()
        print(f"passed {test.__name__}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except urllib.error.URLError as error:
        raise SystemExit(f"Backend is not reachable at {API_URL}: {error}") from error
