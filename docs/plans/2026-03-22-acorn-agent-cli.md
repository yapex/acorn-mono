# Acorn Agent CLI 规划

## 概述

为 acorn-agent 添加 client CLI，复用 vi-cli 的设计模式。

## 命令设计

```
# 启动 server（默认行为，无子命令时）
acorn-agent

# Client 模式（有子命令时）
acorn-agent query <symbol> [-r <fields>] [-y <years>] [-c <calculators>] [--format <format>]
acorn-agent list-fields [--source <source>] [--prefix <prefix>]
acorn-agent list-calculators
acorn-agent call <command> --args '<json>'  # 底层调试
```

## 子命令详情

### `query` - 查询财务数据

```bash
acorn-agent query <symbol> [-r <fields>] [-y <years>] [-c <calculators>] [--format <format>]

# 示例
acorn-agent query AAPL -r market_cap,operating_cash_flow -y 10
acorn-agent query 00700 -r all -c implied_growth --wacc 0.08
acorn-agent query 600519 --format json
```

选项：
- `-r, --fields`: 字段列表，逗号分隔，默认 `all`
- `-y, --years`: 年数，默认 10
- `-c, --calculators`: 计算器列表
- `--wacc`: DCF 折现率，默认 0.08
- `--g-terminal`: 永续增长率，默认 0.03
- `--format`: 输出格式 `table` | `json`，默认 `table`

### `list-fields` - 列出可用字段

```bash
acorn-agent list-fields [--source <source>] [--prefix <prefix>]
```

### `list-calculators` - 列出可用计算器

```bash
acorn-agent list-calculators
```

### `call` - 底层 RPC 调用（调试用）

```bash
acorn-agent call vi_query --args '{"symbol": "AAPL", "fields": "market_cap"}'
```

## 实现要点

1. **复用 vi-cli 代码**
   - 输出格式化逻辑 `_format_output`, `_format_value`
   - typer 框架

2. **client 调用方式**
   - 通过 `AcornClient` 调用 Unix Socket
   - 检测 server 是否运行，给出提示

3. **server 启动逻辑**
   - 无子命令时启动 server（兼容现有行为）

## 文件改动

```
acorn-agent/
├── src/acorn_agent/
│   ├── cli.py          # 重写，添加子命令
│   ├── client.py       # 现有，无需改动
│   └── formatter.py    # 新增，输出格式化（从 vi-cli 复用）
└── pyproject.toml      # 添加 typer, tabulate 依赖
```

## 依赖

```toml
[project.dependencies]
typer = ">=0.9"
tabulate = ">=0.9"
```

## 任务清单

- [ ] 创建 `formatter.py`（从 vi-cli 复用 `_format_output`, `_format_value`）
- [ ] 重写 `cli.py`（添加 typer 子命令）
- [ ] 更新 `pyproject.toml`（添加依赖）
- [ ] 测试各子命令
