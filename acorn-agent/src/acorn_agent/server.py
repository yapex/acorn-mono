"""
Unix Socket RPC Server for acorn-core
"""

import json
import socket
import threading
from pathlib import Path

from acorn_core import Acorn, Task


# Default socket path in user directory
DEFAULT_SOCKET_PATH = Path.home() / ".acorn" / "agent.sock"


class AcornServer:
    """Unix Socket RPC Server"""

    def __init__(self, socket_path: str | None = None):
        self.socket_path = socket_path or str(DEFAULT_SOCKET_PATH)
        self.acorn = Acorn()
        self.acorn.load_plugins()
        self._running = False

    def start(self):
        """Start the server (blocking)"""
        # Create directory if needed
        Path(self.socket_path).parent.mkdir(parents=True, exist_ok=True)

        # Remove existing socket file
        Path(self.socket_path).unlink(missing_ok=True)

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(self.socket_path)
        server.listen(5)

        self._running = True
        print(f"acorn-agent listening on {self.socket_path}")

        while self._running:
            try:
                conn, _ = server.accept()
                threading.Thread(target=self._handle_connection, args=(conn,), daemon=True).start()
            except Exception as e:
                if self._running:
                    print(f"Error: {e}")

    def stop(self):
        """Stop the server"""
        self._running = False
        Path(self.socket_path).unlink(missing_ok=True)

    def _handle_connection(self, conn):
        """Handle a single client connection"""
        try:
            data = conn.recv(4096)
            if not data:
                return

            request = json.loads(data.decode())
            response = self._execute(request)
            conn.sendall(json.dumps(response).encode())
        except Exception as e:
            error_response = {
                "success": False,
                "error": {"code": "SERVER_ERROR", "message": str(e)}
            }
            try:
                conn.sendall(json.dumps(error_response).encode())
            except Exception:
                pass
        finally:
            conn.close()

    def _execute(self, request: dict) -> dict:
        """Execute a command"""
        command = request.get("command")
        args = request.get("args", {})

        if not command:
            return {
                "success": False,
                "error": {"code": "INVALID_REQUEST", "message": "command is required"}
            }

        # Built-in health check
        if command == "health":
            return {
                "success": True,
                "data": {
                    "status": "ok",
                    "plugins": [name for name, _ in self.acorn.list_plugins()]
                }
            }

        # Built-in command list
        if command == "list_commands":
            capabilities = self.acorn.list_capabilities()
            return {
                "success": True,
                "data": {"commands": capabilities}
            }

        task = Task(command=command, args=args)
        response = self.acorn.execute(task)

        if response.success:
            return {"success": True, "data": response.data}
        else:
            error = response.error
            return {
                "success": False,
                "error": {
                    "code": error.code if error else "UNKNOWN",
                    "message": error.message if error else "Unknown error"
                }
            }
