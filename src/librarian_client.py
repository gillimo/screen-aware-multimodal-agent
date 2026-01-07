"""Lightweight socket client for Claude-backed librarian assistance."""
from __future__ import annotations

import json
import os
import socket
import struct
import uuid
from typing import Any, Dict, Optional, Tuple

# Configuration
LIBRARIAN_HOST = os.getenv("LIBRARIAN_HOST", "127.0.0.1")
LIBRARIAN_PORT = int(os.getenv("LIBRARIAN_PORT", 6000))
LIBRARIAN_TIMEOUT_S = int(os.getenv("LIBRARIAN_TIMEOUT_S", 15))
MAX_MSG_BYTES = 1024 * 1024  # 1MB


class LibrarianClient:
    """
    Minimal client for querying the librarian when local model is stuck.
    """

    def __init__(self, address: Tuple[str, int] = None) -> None:
        self.address = address or (LIBRARIAN_HOST, LIBRARIAN_PORT)
        self._conn: Optional[socket.socket] = None

    def _connect(self) -> bool:
        if self._conn:
            return True
        try:
            self._conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._conn.settimeout(LIBRARIAN_TIMEOUT_S)
            self._conn.connect(self.address)
            return True
        except Exception as e:
            print(f"Librarian connection failed: {e}")
            self._conn = None
            return False

    def _send_receive(self, message: Dict[str, Any]) -> Dict[str, Any]:
        if not self._connect():
            return {"status": "error", "message": "Connection failed"}

        try:
            message["request_id"] = str(uuid.uuid4())
            msg_json = json.dumps(message).encode("utf-8")
            if len(msg_json) > MAX_MSG_BYTES:
                return {"status": "error", "message": "Payload too large"}

            # Send: 4-byte length + JSON
            self._conn.sendall(struct.pack("!I", len(msg_json)) + msg_json)

            # Receive: 4-byte length + JSON
            resp_len_bytes = self._conn.recv(4)
            if not resp_len_bytes:
                raise ConnectionError("Connection closed")

            resp_len = struct.unpack("!I", resp_len_bytes)[0]
            response_bytes = b""
            while len(response_bytes) < resp_len:
                chunk = self._conn.recv(resp_len - len(response_bytes))
                if not chunk:
                    raise ConnectionError("Connection closed during response")
                response_bytes += chunk

            return json.loads(response_bytes.decode("utf-8"))

        except Exception as e:
            print(f"Librarian communication error: {e}")
            self.close()
            return {"status": "error", "message": str(e)}

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def ask_for_help(
        self,
        question: str,
        screenshot_b64: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Ask librarian for help with a game decision.

        Args:
            question: What we need help with
            screenshot_b64: Base64 encoded screenshot (optional)
            context: Additional context (tutorial_hint, hover_text, phase, etc.)

        Returns:
            {"status": "success", "answer": {...}} or {"status": "error", ...}
        """
        message = {
            "type": "game_assist",
            "question": question,
            "context": context or {},
        }
        if screenshot_b64:
            message["screenshot_b64"] = screenshot_b64

        return self._send_receive(message)

    def query_cloud(self, prompt: str) -> Dict[str, Any]:
        """Direct cloud query for complex reasoning."""
        return self._send_receive({
            "type": "cloud_query",
            "prompt": prompt,
        })

    def is_available(self) -> bool:
        """Check if librarian is available."""
        try:
            result = self._send_receive({"type": "ping"})
            return result.get("status") == "success"
        except Exception:
            return False


# Singleton instance
_client: Optional[LibrarianClient] = None


def get_client() -> LibrarianClient:
    global _client
    if _client is None:
        _client = LibrarianClient()
    return _client


def ask_librarian(
    question: str,
    screenshot_b64: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Convenience function to ask librarian for help.
    Returns None if librarian unavailable.
    """
    client = get_client()
    result = client.ask_for_help(question, screenshot_b64, context)
    if result.get("status") == "success":
        return result.get("answer")
    return None
