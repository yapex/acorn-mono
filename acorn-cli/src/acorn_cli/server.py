"""
FastAPI Server for acorn-core
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from acorn_core import Acorn, Task  # type: ignore[import]

# 创建 FastAPI 应用
app = FastAPI(title="Acorn Agent", version="0.1.0")

# 全局 Acorn 实例
acorn = Acorn()
acorn.load_plugins()


# 请求/响应模型
class ExecuteRequest(BaseModel):
    command: str
    args: dict[str, Any] = {}


class ExecuteResponse(BaseModel):
    success: bool
    data: Any = None
    error: dict | None = None


class HealthResponse(BaseModel):
    healthy: bool
    version: str = "0.1.0"


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """健康检查"""
    return HealthResponse(healthy=True, version="0.1.0")


@app.get("/status")
def get_status() -> dict[str, Any]:
    """获取系统状态"""
    status_info = {
        "status": "ok",
        "plugins": [],
    }

    for name, plugin in acorn.list_plugins():
        plugin_info = {"name": name}

        if hasattr(plugin, "vi_status"):
            try:
                plugin_status = plugin.vi_status()
                if plugin_status:
                    plugin_info.update(plugin_status)
            except Exception as e:
                plugin_info["error"] = str(e)
                plugin_info["status"] = "error"
        else:
            plugin_info["status"] = "no vi_status hook"

        status_info["plugins"].append(plugin_info)

    return {"success": True, "data": status_info}


@app.get("/commands")
def list_commands() -> dict[str, Any]:
    """列出可用命令"""
    capabilities = acorn.list_capabilities()
    return {"success": True, "data": {"commands": capabilities}}


@app.post("/execute", response_model=ExecuteResponse)
def execute(request: ExecuteRequest) -> ExecuteResponse:
    """执行命令"""
    if not request.command:
        raise HTTPException(status_code=400, detail="command is required")

    task = Task(command=request.command, args=request.args)
    response = acorn.execute(task)

    if response.success:
        return ExecuteResponse(success=True, data=response.data)
    else:
        error = response.error
        return ExecuteResponse(
            success=False,
            error={
                "code": error.code if error else "UNKNOWN",
                "message": error.message if error else "Unknown error",
            },
        )


def is_port_in_use(port: int) -> bool:
    """检查端口是否已被占用"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


@app.on_event("startup")
def on_startup():
    """服务启动时的回调"""
    import sys
    print("", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("🌰 Acorn 服务已启动", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("  HTTP API:    http://127.0.0.1:18732", file=sys.stderr)
    print("  Swagger UI:  http://127.0.0.1:18732/docs", file=sys.stderr)
    print("  健康检查:    http://127.0.0.1:18732/health", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("", file=sys.stderr)


def main() -> int:
    """Server entry point"""
    import uvicorn

    port = 18732

    if is_port_in_use(port):
        print(f"端口 {port} 已被占用，服务已在运行")
        return 1

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
