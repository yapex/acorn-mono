"""
Client for acorn-agent RPC
"""

import json
import os
import socket
from pathlib import Path
from typing import Any


# Default socket path in user directory
DEFAULT_SOCKET_PATH = Path.home() / ".acorn" / "agent.sock"


class AcornClient:
    """Unix Socket RPC Client"""

    def __init__(self, socket_path: str | None = None):
        self.socket_path = socket_path or os.environ.get(
            "ACORN_AGENT_SOCKET",
            str(DEFAULT_SOCKET_PATH)
        )

    def execute(self, command: str, args: dict[str, Any] | None = None) -> dict:
        """Execute a command via RPC"""
        if args is None:
            args = {}

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(self.socket_path)
            request = json.dumps({"command": command, "args": args})
            sock.sendall(request.encode())

            response = sock.recv(4096)
            return json.loads(response.decode())
        finally:
            sock.close()

    def __call__(self, command: str, **kwargs) -> dict:
        """Shortcut: client("echo", message="hello")"""
        return self.execute(command, kwargs)
