"""
Client for acorn-agent RPC
"""
from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from typing import Any, Optional


# Default socket path in user directory
DEFAULT_SOCKET_PATH = Path.home() / ".acorn" / "agent.sock"


class AcornClient:
    """Unix Socket RPC Client"""

    def __init__(self, socket_path: Optional[str] = None) -> None:
        self.socket_path = socket_path or os.environ.get(
            "ACORN_AGENT_SOCKET",
            str(DEFAULT_SOCKET_PATH)
        )

    def execute(self, command: str, args: Optional[dict[str, Any]] = None) -> dict:
        """Execute a command via RPC"""
        if args is None:
            args = {}

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(self.socket_path)
            request = json.dumps({"command": command, "args": args})
            sock.sendall(request.encode())

            # Read all response data (may span multiple recv calls)
            chunks = []
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
            response = b"".join(chunks)
            return json.loads(response.decode())
        finally:
            sock.close()

    def __call__(self, command: str, **kwargs: Any) -> dict:
        """Shortcut: client("echo", message="hello")"""
        return self.execute(command, kwargs)
