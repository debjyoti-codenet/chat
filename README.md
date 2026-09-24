# 💬 Realtime Chat Application

A clean, modern, and simple real-time chat application built with **Python (aiohttp + Socket.IO)** and **vanilla HTML/CSS/JavaScript**.

---

## ✨ Features

- **⚡ Real-time Messaging**: Instant message delivery with Socket.IO.
- **↔️ Two-Sided Chat Layout**: 
  - Your own messages always align to the **Right** (indigo gradient bubble with `✓✓`).
  - Other users' messages always align to the **Left** (dark slate card with avatar and name).
- **✍️ Live Typing Indicator**: Real-time `● ● ● Alice is typing...` animated bouncing dots.
- **✏️ Inline Message Editing**: Hover over your message and click `✏️` to edit your text with real-time update and `(edited)` tag.
- **👥 Active Online Members Drawer**: Click the `🟢 X Online` chip in the header to open a slide-out drawer showing active members.
- **📎 Image & Photo Sharing**: 
  - Click `📎` to pick an image.
  - Drag and drop images onto the chat.
  - Paste images directly from clipboard with `Ctrl + V`.
  - Click any image in chat to view it in full-screen lightbox.
- **🗑️ Single Message Delete**: Hover over any message and click the trash icon `🗑️` to delete it.
- **☑️ Multi-Select Delete**: Click **"Select"** in the header, pick multiple messages (or **"Select All"**), and bulk delete.
- **😀 Quick Emoji Bar**: Instant emoji insertion.
- **💾 Session History**: Keeps message history in-memory so new or refreshed tabs see current messages.

---

## 🚀 How to Run

1. **Start the server:**
   ```powershell
   .\.venv\Scripts\python.exe server.py
   ```

2. **Open in your browser:**
   Go to [http://localhost:5000](http://localhost:5000).

> **💡 Multi-User Test**: Open [http://localhost:5000](http://localhost:5000) in two separate browser tabs side-by-side. You will see both users in the Online Members drawer, typing indicators as you type, two-sided messaging, photo sharing, and inline editing!
