"""
Echo Plugin
===========
简单回显插件，将输入的消息原样返回。
"""

from acorn_core.specs import hookimpl


class EchoPlugin:
    """回显插件"""
    
    @property
    def commands(self) -> list[str]:
        return ["echo"]
    
    @hookimpl
    def get_capabilities(self) -> dict:
        return {
            "commands": ["echo"],
            "args": {
                "message": {"type": "string", "required": True, "description": "要回显的消息"}
            }
        }
    
    @hookimpl
    def handle(self, task) -> dict:
        message = task.args.get("message", "")
        return {
            "success": True,
            "data": message
        }


plugin = EchoPlugin()
