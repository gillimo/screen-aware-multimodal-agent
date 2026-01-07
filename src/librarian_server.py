"""
Librarian Server - Claude-backed assistant for when local model is stuck.
Runs as a separate process, listens on socket for help requests.

Usage:
    python -m src.librarian_server
"""
from __future__ import annotations

import base64
import json
import os
import socket
import struct
import threading
from pathlib import Path
from typing import Any, Dict, Optional

# Try to import anthropic
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    print("Warning: anthropic not installed. Run: pip install anthropic")

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

# Server config
HOST = os.getenv("LIBRARIAN_HOST", "127.0.0.1")
PORT = int(os.getenv("LIBRARIAN_PORT", 6000))
MAX_MSG_BYTES = 2 * 1024 * 1024  # 2MB for screenshots


class LibrarianServer:
    """Socket server that answers game assistance requests using Claude."""

    def __init__(self, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port
        self.client: Optional[anthropic.Anthropic] = None
        self.running = False
        self.config = self._load_config()
        self._init_client()

    def _load_config(self) -> dict:
        """Load config with model preferences."""
        config_path = DATA_DIR / "claude_config.json"
        defaults = {
            "vision_model": "claude-sonnet-4-20250514",
            "text_model": "claude-3-5-haiku-20241022",
            "max_tokens": 300,
        }
        if config_path.exists():
            try:
                loaded = json.loads(config_path.read_text())
                defaults.update(loaded)
            except Exception:
                pass
        return defaults

    def _init_client(self):
        if not HAS_ANTHROPIC:
            return
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            config_path = DATA_DIR / "claude_config.json"
            if config_path.exists():
                try:
                    config = json.loads(config_path.read_text())
                    # Support api_key_env to read from env var specified in config
                    env_var = config.get("api_key_env")
                    if env_var:
                        api_key = os.environ.get(env_var)
                    # Fallback to direct api_key (not recommended)
                    if not api_key:
                        api_key = config.get("api_key")
                except Exception:
                    pass
        if api_key:
            self.client = anthropic.Anthropic(api_key=api_key)
            print("Claude API initialized")
        else:
            print("Warning: No ANTHROPIC_API_KEY found. Set environment variable or update data/claude_config.json")

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming request and return response."""
        req_type = request.get("type", "")
        request_id = request.get("request_id", "")

        if req_type == "ping":
            return {"status": "success", "request_id": request_id}

        if req_type == "game_assist":
            return self._handle_game_assist(request)

        if req_type == "cloud_query":
            return self._handle_cloud_query(request)

        return {"status": "error", "message": f"Unknown request type: {req_type}"}

    def _handle_game_assist(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle game assistance request with optional screenshot."""
        if not self.client:
            return {"status": "error", "message": "Claude not configured"}

        question = request.get("question", "What should I do?")
        context = request.get("context", {})
        screenshot_b64 = request.get("screenshot_b64")

        prompt = f"""You are helping navigate OSRS Tutorial Island.

Current context:
- Phase: {context.get('phase', 'unknown')}
- Tutorial hint: "{context.get('tutorial_hint', 'none')}"
- Hover text: "{context.get('hover_text', 'none')}"
- Attempts so far: {context.get('repeat_count', 0)}

Question: {question}

Look at the screenshot and identify:
1. Where is the flashing yellow arrow pointing (if visible)?
2. What specific thing should be clicked to progress?
3. Give approximate x,y coordinates (image is ~1140x710 pixels)

Respond ONLY with valid JSON:
{{
    "action": "click",
    "target": {{"x": number, "y": number}},
    "target_description": "what to click",
    "reasoning": "brief explanation",
    "confidence": 0.0-1.0
}}"""

        try:
            messages_content = []

            if screenshot_b64:
                messages_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": screenshot_b64,
                    },
                })

            messages_content.append({
                "type": "text",
                "text": prompt,
            })

            model = self.config.get("vision_model", "claude-sonnet-4-20250514")
            max_tokens = self.config.get("max_tokens", 300)
            response = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": messages_content}],
            )

            text = response.content[0].text
            # Extract JSON
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                answer = json.loads(text[start:end])
                return {
                    "status": "success",
                    "request_id": request.get("request_id"),
                    "answer": answer,
                }

            return {"status": "error", "message": "Could not parse response"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _handle_cloud_query(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle direct cloud query."""
        if not self.client:
            return {"status": "error", "message": "Claude not configured"}

        prompt = request.get("prompt", "")
        try:
            model = self.config.get("text_model", "claude-3-5-haiku-20241022")
            max_tokens = self.config.get("max_tokens", 300)
            response = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return {
                "status": "success",
                "request_id": request.get("request_id"),
                "answer": response.content[0].text,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def handle_client(self, conn: socket.socket, addr):
        """Handle a single client connection."""
        try:
            while True:
                # Read message length (4 bytes)
                len_bytes = conn.recv(4)
                if not len_bytes:
                    break

                msg_len = struct.unpack("!I", len_bytes)[0]
                if msg_len > MAX_MSG_BYTES:
                    break

                # Read message
                msg_bytes = b""
                while len(msg_bytes) < msg_len:
                    chunk = conn.recv(msg_len - len(msg_bytes))
                    if not chunk:
                        break
                    msg_bytes += chunk

                request = json.loads(msg_bytes.decode("utf-8"))
                print(f"Request from {addr}: {request.get('type')}")

                # Process and respond
                response = self.handle_request(request)
                resp_json = json.dumps(response).encode("utf-8")
                conn.sendall(struct.pack("!I", len(resp_json)) + resp_json)

        except Exception as e:
            print(f"Client error: {e}")
        finally:
            conn.close()

    def run(self):
        """Start the server."""
        self.running = True
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(5)

        print(f"Librarian listening on {self.host}:{self.port}")
        print("Ready to assist with game decisions")

        try:
            while self.running:
                conn, addr = server.accept()
                thread = threading.Thread(target=self.handle_client, args=(conn, addr))
                thread.daemon = True
                thread.start()
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            server.close()


def main():
    server = LibrarianServer()
    server.run()


if __name__ == "__main__":
    main()
