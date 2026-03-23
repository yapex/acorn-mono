"""
Unix Socket RPC Server for acorn-core
"""
from __future__ import annotations

import json
import socket
import threading
from pathlib import Path
from typing import Any, Optional

from acorn_core import Acorn, Task  # type: ignore[import]

# Default socket path in user directory
DEFAULT_SOCKET_PATH = Path.home() / ".acorn" / "agent.sock"


class AcornServer:
    """Unix Socket RPC Server"""

    def __init__(self, socket_path: Optional[str] = None) -> None:
        self.socket_path = socket_path or str(DEFAULT_SOCKET_PATH)
        self.acorn = Acorn()
        self.acorn.load_plugins()
        self._running = False

    def start(self) -> None:
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

    def stop(self) -> None:
        """Stop the server"""
        self._running = False
        Path(self.socket_path).unlink(missing_ok=True)

    def _handle_connection(self, conn: socket.socket) -> None:
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

    def _execute(self, request: dict[str, Any]) -> dict[str, Any]:
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
            plugins_info = []
            for name, plugin in self.acorn.list_plugins():
                plugin_info = {"name": name}
                # 如果插件有 get_health_info 方法，获取详细信息
                if hasattr(plugin, "get_health_info"):
                    try:
                        detailed = plugin.get_health_info()
                        if detailed:
                            plugin_info["details"] = detailed
                    except Exception as e:
                        plugin_info["error"] = str(e)
                plugins_info.append(plugin_info)

            return {
                "success": True,
                "data": {
                    "status": "ok",
                    "plugins": plugins_info
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


def main() -> int:
    """Server entry point"""
    import signal

    server = AcornServer()

    def handle_signal(signum, frame):
        print("\nShutting down...")
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    server.start()
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main())
