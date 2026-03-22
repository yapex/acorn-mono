# Acorn Agent

Persistent agent service for acorn-core with Unix Socket RPC interface.

## Quick Start

### Using CLI (Recommended)

CLI commands automatically start the server if not running:

```bash
# Query stock data (auto-starts server if needed)
acorn-agent query 600519 -r roe,gross_margin -y 10

# List available fields
acorn-agent list-fields --source ifrs

# List calculators
acorn-agent list-calculators

# Raw RPC call (for debugging)
acorn-agent call health --args '{}'
```

### Start Server Manually

```bash
# Start the agent server (runs in foreground)
acorn-agent

# Or run via uv
uv run acorn-agent
```

## CLI Commands

### `query` - Query Financial Data

```bash
acorn-agent query <symbol> [options]

# Examples
acorn-agent query 600519 -r roe,gross_margin -y 10
acorn-agent query 600519 -r all -c implied_growth --wacc 0.08
acorn-agent query 600519 --format json
```

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--fields` | `-r` | `all` | Comma-separated fields |
| `--years` | `-y` | `10` | Number of years |
| `--calculators` | `-c` | | Comma-separated calculators |
| `--wacc` | | `0.08` | WACC for DCF calculations |
| `--g-terminal` | | `0.03` | Terminal growth rate |
| `--format` | | `table` | Output format: `table`, `json` |

### `list-fields` - List Available Fields

```bash
acorn-agent list-fields [--source <source>] [--prefix <prefix>]

# Examples
acorn-agent list-fields
acorn-agent list-fields --source ifrs
acorn-agent list-fields --prefix roe
```

### `list-calculators` - List Available Calculators

```bash
acorn-agent list-calculators
```

### `call` - Raw RPC Call (Debugging)

```bash
acorn-agent call <command> --args '<json>'

# Examples
acorn-agent call health --args '{}'
acorn-agent call vi_query --args '{"symbol": "600519", "fields": "roe"}'
```

## RPC Interface

The agent listens on Unix Socket at `~/.acorn/agent.sock`. Send JSON commands via `nc` (netcat):

```bash
echo '{"command": "<cmd>", "args": {}}' | nc -U ~/.acorn/agent.sock
```

## Available Commands

### Built-in Commands

#### `health` - Check Server Status

Returns server status and loaded plugins:

```bash
echo '{"command": "health", "args": {}}' | nc -U ~/.acorn/agent.sock
```

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "ok",
    "plugins": [
      {
        "name": "vi_core",
        "details": {
          "sub_plugins": ["provider_market_a", "ifrs", "extension", "vi_calculators"],
          "entry_point_groups": ["value_investment.fields", "value_investment.providers", "value_investment.calculators"]
        }
      },
      {"name": "evo_manager"},
      {"name": "vi"}
    ]
  }
}
```

#### `list_commands` - List All Available Commands

```bash
echo '{"command": "list_commands", "args": {}}' | nc -U ~/.acorn/agent.sock
```

### VI Commands (Value Investment)

#### `vi_query` - Query Financial Data

```bash
echo '{
  "command": "vi_query",
  "args": {
    "symbol": "600519",
    "fields": "roe,gross_margin,net_profit_margin",
    "years": 10,
    "calculators": "implied_growth",
    "calculator_config": {
      "implied_growth": {"wacc": 0.08, "g_terminal": 0.03, "n_years": 10}
    }
  }
}' | nc -U ~/.acorn/agent.sock
```

**Arguments:**

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `symbol` | string | **required** | Stock code (e.g. `600519`, `000001`) |
| `fields` | string | `"all"` | Comma-separated fields or `"all"` |
| `years` | integer | `10` | Number of years to fetch |
| `calculators` | string | `""` | Comma-separated calculator names |
| `calculator_config` | object | `{}` | Calculator-specific config |

**Popular Fields:**

| Field | Description |
|-------|-------------|
| `roe` | Return on Equity (%) |
| `roa` | Return on Assets (%) |
| `gross_margin` | Gross Profit Margin (%) |
| `net_profit_margin` | Net Profit Margin (%) |
| `current_ratio` | Current Ratio |
| `pe_ratio` | P/E Ratio |
| `pb_ratio` | P/B Ratio |
| `market_cap` | Market Capitalization |
| `operating_cash_flow` | Operating Cash Flow |
| `revenue_yoy` | Revenue Year-over-Year Growth (%) |
| `net_profit_yoy` | Net Profit YoY Growth (%) |

#### `vi_list_fields` - List Available Fields

```bash
echo '{"command": "vi_list_fields", "args": {}}' | nc -U ~/.acorn/agent.sock
echo '{"command": "vi_list_fields", "args": {"source": "ifrs"}}' | nc -U ~/.acorn/agent.sock
echo '{"command": "vi_list_fields", "args": {"prefix": "roe"}}' | nc -U ~/.acorn/agent.sock
```

#### `vi_list_calculators` - List Available Calculators

```bash
echo '{"command": "vi_list_calculators", "args": {}}' | nc -U ~/.acorn/agent.sock
```

#### `vi_register_calculator` - Register a Calculator Dynamically

```bash
echo '{
  "command": "vi_register_calculator",
  "args": {
    "name": "roe_score",
    "required_fields": ["roe"],
    "code": "import pandas as pd\n\ndef calculate(results, config):\n    roe = results.get(\"roe\", {})\n    if roe.empty:\n        return pd.Series(dtype=float)\n    latest_year = max(roe.index)\n    latest_roe = roe.loc[latest_year]\n    return pd.Series({latest_year: round(latest_roe / 10, 2)})",
    "description": "ROE Score = ROE / 10"
  }
}' | nc -U ~/.acorn/agent.sock
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | string | **yes** | Calculator name |
| `code` | string | **yes** | Python code with `calculate(results, config)` function |
| `required_fields` | array | **yes** | List of required field names |
| `description` | string | no | Calculator description |
| `namespace` | string | `"dynamic"` | Namespace: `builtin`, `user`, `dynamic` |

## Plugin Architecture

```
acorn-core [yapex.acorn.plugins]
├── vi_core
│   ├── [value_investment.fields]
│   │   ├── ifrs - IFRS standard fields
│   │   └── extension - Extended/custom fields
│   ├── [value_investment.providers]
│   │   ├── provider_market_a - A-share market (Tushare)
│   │   ├── provider_market_hk - HK market
│   │   └── provider_market_us - US market
│   └── [value_investment.calculators]
│       └── vi_calculators - Calculator loader
├── evo_manager - Evolution manager
└── vi - Agent built-in plugin
```

### Calculator Namespaces

| Namespace | Source | Trust Level |
|-----------|--------|-------------|
| `builtin` | `value-investment-plugin/calculators/` | Trusted |
| `user` | `~/.value_investment/calculators/` | User-defined |
| `dynamic` | Runtime registration (default) | Unverified |

## Response Format

**Success:**
```json
{
  "success": true,
  "data": { ... }
}
```

**Error:**
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Error description"
  }
}
```

## Python Client

```python
from acorn_agent.client import AcornClient

client = AcornClient()

# Query stock data
result = client.execute('vi_query', {
    'symbol': '600519',
    'fields': 'roe,gross_margin',
    'years': 10,
})

if result['success']:
    data = result['data']
    print(data['fields_fetched'])
    print(data['data']['roe'])
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TUSHARE_TOKEN` | (required) | Tushare API token for China stock data |
| `ACORN_AGENT_SOCKET` | `~/.acorn/agent.sock` | Unix socket path |

## Example Workflows

### Analyze a Stock

```bash
# Using CLI
acorn-agent query 600519 -r roe,gross_margin,net_profit_margin -y 10

# With calculator
acorn-agent query 600519 -r operating_cash_flow,market_cap -c implied_growth --wacc 0.08
```

### Screen Multiple Stocks

```bash
for symbol in 600519 000001 600036; do
  echo "=== $symbol ==="
  acorn-agent query $symbol -r roe,gross_margin -y 5
done
```

### Register and Use Custom Calculator

```bash
# 1. Register
acorn-agent call vi_register_calculator --args '{"name": "roe_score", "required_fields": ["roe"], "code": "import pandas as pd\n\ndef calculate(results, config):\n    roe = results.get(\"roe\", {})\n    if roe.empty:\n        return pd.Series(dtype=float)\n    latest_year = max(roe.index)\n    latest_roe = roe.loc[latest_year]\n    return pd.Series({latest_year: round(latest_roe / 10, 2)})"}'

# 2. Use
acorn-agent query 600519 -r roe -c roe_score
```
