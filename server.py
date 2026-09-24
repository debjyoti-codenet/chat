import os
import re
import uuid
from datetime import datetime
from aiohttp import web
import socketio

# Initialize Socket.IO server with CORS enabled for all origins
sio = socketio.AsyncServer(async_mode="aiohttp", cors_allowed_origins="*")
app = web.Application()
sio.attach(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# In-memory message store for live session
message_history = []
MAX_HISTORY = 100

# Server-side limits (the browser UI already enforces these, but a raw
# socket client can skip the browser entirely, so they must be re-checked
# here too).
MAX_TEXT_LEN = 2000
MAX_IMAGE_DATA_URL_LEN = 7_000_000  # ~5MB image, base64-inflated, plus headroom
IMAGE_DATA_URL_RE = re.compile(r"^data:image/(png|jpe?g|gif|webp);base64,")

# Online users tracking: sid -> {"username": str, "avatarColor": str, "clientId": str}
online_users = {}


def _valid_image(image):
    if not isinstance(image, str):
        return False
    if len(image) > MAX_IMAGE_DATA_URL_LEN:
        return False
    return bool(IMAGE_DATA_URL_RE.match(image))


async def broadcast_online_users():
    """Broadcast the updated list of online members to all connected clients."""
    user_list = [
        {
            "sid": s,
            "username": u.get("username", "Anonymous"),
            "avatarColor": u.get("avatarColor", "#6366f1"),
            "clientId": u.get("clientId", s),
        }
        for s, u in online_users.items()
    ]
    await sio.emit("online_users_updated", {"users": user_list, "count": len(user_list)})


# Serve index.html directly on root URL
async def index(request):
    return web.FileResponse(os.path.join(BASE_DIR, "index.html"))


# Serve socket.io.min.js locally (fast, zero external dependency, 100% offline)
async def socket_io_js(request):
    js_path = os.path.join(BASE_DIR, "socket.io.min.js")
    if os.path.exists(js_path):
        return web.FileResponse(js_path)
    return web.Response(status=404, text="socket.io.min.js not found")


app.router.add_get("/", index)
app.router.add_get("/socket.io.min.js", socket_io_js)


# Socket.IO Event Handlers
@sio.event
async def connect(sid, environ):
    print(f"[+] Client connected: {sid}")
    online_users[sid] = {
        "username": "User",
        "avatarColor": "#6366f1",
        "clientId": sid,
    }
    # Send message history to the newly connected client
    if message_history:
        await sio.emit("history", message_history, to=sid)
    await broadcast_online_users()


@sio.event
async def update_profile(sid, data):
    """Handle user profile updates (username, avatar color, clientId)."""
    if sid in online_users and isinstance(data, dict):
        username = str(data.get("username", "")).strip()[:18] or "User"
        avatar_color = str(data.get("avatarColor", "#6366f1"))[:32]
        client_id = str(data.get("clientId", sid))[:128]
        online_users[sid] = {
            "username": username,
            "avatarColor": avatar_color,
            "clientId": client_id,
        }
        await broadcast_online_users()


@sio.event
async def disconnect(sid):
    print(f"[-] Client disconnected: {sid}")
    online_users.pop(sid, None)
    await broadcast_online_users()


@sio.event
async def typing(sid, data):
    """Broadcast typing indicator to other clients."""
    if not isinstance(data, dict):
        return
    is_typing = bool(data.get("isTyping", False))
    username = str(data.get("username", "Someone")).strip()[:18]
    client_id = str(data.get("clientId", sid))[:128]

    await sio.emit(
        "user_typing",
        {"username": username, "isTyping": is_typing, "clientId": client_id},
        skip_sid=sid,
    )


@sio.event
async def chat_message(sid, data):
    """Handle chat messages with text and optional image attachments."""
    global message_history
    if not isinstance(data, dict):
        return

    text = str(data.get("text", "")).strip()[:MAX_TEXT_LEN]
    image = data.get("image")  # base64 image data URL (optional)
    username = str(data.get("username", "Anonymous")).strip()[:18] or "Anonymous"
    avatar_color = str(data.get("avatarColor", "#6366f1"))[:32]
    client_id = str(data.get("clientId", sid))[:128]

    # Reject anything that isn't a genuine, size-bounded image data URL. This
    # matters because a raw socket client (not just the browser UI) can send
    # arbitrary "image" content, bypassing the browser's own 5MB/type checks.
    if image is not None and not _valid_image(image):
        image = None

    if not text and not image:
        return

    payload = {
        "msgId": str(uuid.uuid4()),
        "clientId": client_id,
        "senderId": sid,
        "username": username,
        "text": text,
        "image": image,
        "avatarColor": avatar_color,
        "time": datetime.now().strftime("%I:%M %p"),
        "isEdited": False,
    }

    message_history.append(payload)
    if len(message_history) > MAX_HISTORY:
        message_history.pop(0)

    log_content = text if text else "[Image]"
    print(f"[{payload['username']}]: {log_content} (ID: {payload['msgId'][:8]})")
    await sio.emit("chat_message", payload)


@sio.event
async def edit_message(sid, data):
    """Handle editing an existing message."""
    global message_history
    if not isinstance(data, dict):
        return

    msg_id = data.get("msgId")
    new_text = str(data.get("newText", "")).strip()[:MAX_TEXT_LEN]
    if not msg_id or not new_text:
        return

    for msg in message_history:
        if msg.get("msgId") == msg_id:
            msg["text"] = new_text
            msg["isEdited"] = True
            print(f"[*] Message edited: {msg_id[:8]} -> {new_text}")
            await sio.emit(
                "message_edited",
                {"msgId": msg_id, "newText": new_text, "isEdited": True},
            )
            break


@sio.event
async def delete_messages(sid, data):
    """Handle single and multi-select message deletions."""
    global message_history

    if isinstance(data, dict):
        raw_ids = data.get("msgIds") or ([data.get("msgId")] if data.get("msgId") else [])
    elif isinstance(data, list):
        raw_ids = data
    elif isinstance(data, str):
        raw_ids = [data]
    else:
        raw_ids = []

    target_ids = {str(i) for i in raw_ids if i}
    if not target_ids:
        return

    initial_len = len(message_history)
    message_history = [m for m in message_history if m.get("msgId") not in target_ids]
    deleted_count = initial_len - len(message_history)

    print(f"[-] Deleted {len(target_ids)} message(s) ({deleted_count} removed from history)")
    await sio.emit("messages_deleted", {"msgIds": list(target_ids)})


if __name__ == "__main__":
    port = 5000
    print(f"=== Chat Server running at: http://localhost:{port} ===")
    print(f"=== Also accessible at:     http://127.0.0.1:{port} ===")
    print("=" * 48)
    web.run_app(app, host="0.0.0.0", port=port)