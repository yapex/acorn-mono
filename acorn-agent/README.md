# Acorn Agent

Persistent agent service for acorn-core with Unix Socket RPC interface.

## Quick Start

```bash
# Start the agent server (runs in foreground)
acorn-agent

# Or run via uv
uv run acorn-agent
```

## RPC Interface

The agent listens on Unix Socket at `~/.acorn/agent.sock`. Send JSON commands via `socat`:

```bash
echo '{"command": "<cmd>", "args": {}}' | socat - UNIX-CONNECT:~/.acorn/agent.sock
```

## Available Commands

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
}' | socat - UNIX-CONNECT:~/.acorn/agent.sock
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
# List all fields
echo '{"command": "vi_list_fields", "args": {}}' | socat - UNIX-CONNECT:~/.acorn/agent.sock

# Filter by source
echo '{"command": "vi_list_fields", "args": {"source": "ifrs"}}' | socat - UNIX-CONNECT:~/.acorn/agent.sock

# Filter by prefix
echo '{"command": "vi_list_fields", "args": {"prefix": "roe"}}' | socat - UNIX-CONNECT:~/.acorn/agent.sock
```

#### `vi_list_calculators` - List Available Calculators

```bash
echo '{"command": "vi_list_calculators", "args": {}}' | socat - UNIX-CONNECT:~/.acorn/agent.sock
```

**Available Calculators:**

| Calculator | Required Fields | Description |
|------------|-----------------|-------------|
| `implied_growth` | `operating_cash_flow`, `market_cap` | DCF implied growth rate |

### Built-in Commands

#### `health` - Check Server Status

```bash
echo '{"command": "health", "args": {}}' | socat - UNIX-CONNECT:~/.acorn/agent.sock
```

#### `list_commands` - List All Available Commands

```bash
echo '{"command": "list_commands", "args": {}}' | socat - UNIX-CONNECT:~/.acorn/agent.sock
```

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
# 1. List available fields for analysis
echo '{"command": "vi_list_fields", "args": {"prefix": "roe"}}' | socat - UNIX-CONNECT:~/.acorn/agent.sock

# 2. Query key metrics for 10 years
echo '{"command": "vi_query", "args": {"symbol": "600519", "fields": "roe,gross_margin,net_profit_margin,current_ratio", "years": 10}}' | socat - UNIX-CONNECT:~/.acorn/agent.sock

# 3. Calculate implied growth rate
echo '{"command": "vi_query", "args": {"symbol": "600519", "fields": "operating_cash_flow,market_cap", "calculators": "implied_growth", "calculator_config": {"implied_growth": {"wacc": 0.08}}}}' | socat - UNIX-CONNECT:~/.acorn/agent.sock
```

### Screen Stocks

```bash
# Query multiple stocks
for symbol in 600519 000001 600036; do
  echo "=== $symbol ==="
  echo "{\"command\": \"vi_query\", \"args\": {\"symbol\": \"$symbol\", \"fields\": \"roe,gross_margin\", \"years\": 5}}" | socat - UNIX-CONNECT:~/.acorn/agent.sock
done
```
