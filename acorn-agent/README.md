# acorn-agent

持久化 Agent 服务，通过 Unix Socket 与 acorn-core 通信。

## 安装

```bash
uv pip install -e acorn-agent
```

## 启动服务

```bash
# 前台运行
acorn-agent

# 或后台运行
nohup acorn-agent > /tmp/acorn-agent.log 2>&1 &
```

## 客户端使用

```python
from acorn_agent import AcornClient

client = AcornClient()

# 方式 1: execute
result = client.execute("echo", {"message": "hello"})
print(result)  # {"success": true, "data": "hello"}

# 方式 2: 快捷调用
result = client("echo", message="hello")
print(result)  # {"success": true, "data": "hello"}
```

## 停止服务

```bash
pkill acorn-agent
```
