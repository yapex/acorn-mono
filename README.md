# Acorn 🌰

自进化插件系统。基于 pluggy 构建，支持通过事件驱动的自我进化能力。

## 快速开始

### 安装

```bash
git clone https://github.com/yapex/acorn-mono.git
cd acorn-mono
uv sync
```

### 查询股票数据

```bash
# 查询贵州茅台 ROE
acorn vi query 600519 --fields roe --years 5

# 查询苹果净利润
acorn vi query AAPL --fields net_profit --years 10

# 查询腾讯 + 计算隐含增长率
acorn vi query 00700 --fields operating_cash_flow,market_cap --calculators implied_growth

# 列出可用字段
acorn vi list-fields

# 列出可用计算器
acorn vi list-calculators
```

### 查看系统状态

```bash
acorn status
```

---

## 项目结构

```
acorn-mono/
├── acorn-core/              # 核心框架 (事件总线、进化管理)
├── acorn-cli/               # CLI 工具 + HTTP API 服务
├── acorn-events/            # 事件常量定义
├── value-investment/         # 价值投资领域插件
│   ├── vi_core/            # 核心包 (查询引擎)
│   ├── vi_calculators/     # 计算器引擎
│   ├── vi_fields_extension/ # 字段扩展
│   ├── vi_fields_ifrs/     # IFRS 标准字段
│   └── provider_market_*/  # 数据源 (A/港/美股)
└── examples-plugin/         # 示例插件
```

---

## 架构

```
┌─────────────────────────────────────────────────────────┐
│                      用户 / LLM                          │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                     acorn-cli                            │
│  • CLI 命令 (typer)                                     │
│  • HTTP API (FastAPI)                                  │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                     acorn-core                           │
│  • Acorn Kernel (插件管理)                              │
│  • EvoManager (进化管理)                                 │
│  • EventBus (事件总线)                                  │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                      插件层                              │
│  • vi_core (查询引擎)                                   │
│  • vi_calculators (计算器)                              │
│  • providers (数据源)                                    │
│  • ...                                                 │
└─────────────────────────────────────────────────────────┘
```

---

## 扩展开发

### 贡献计算器

创建 `calculators/calc_xxx.py`：

```python
REQUIRED_FIELDS = ["operating_cash_flow", "net_profit"]

def calculate(data, config):
    ocf = data["operating_cash_flow"]
    np_ = data["net_profit"]
    return ocf / np_.replace(0, float('nan'))
```

重启 CLI 即可自动加载。

### 贡献字段

通过 pluggy hook 注册：

```python
# my_fields/__init__.py
@pluggy.HookimplMarker("value_investment")
def vi_fields():
    return {
        "source": "my_fields",
        "fields": {
            "my_custom_field": "自定义字段",
        }
    }
```

### 贡献数据源

实现 Provider hook：

```python
class MyProvider:
    @pluggy.HookimplMarker("value_investment")
    def vi_markets(self):
        return ["A", "HK", "US"]

    @pluggy.HookimplMarker("value_investment")
    def vi_supported_fields(self):
        return ["roe", "net_profit", ...]

    @pluggy.HookimplMarker("value_investment")
    def vi_fetch_financials(self, symbol, fields, end_year, years):
        # 获取并返回财务数据
        return pd.DataFrame(...)
```

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [docs/evolution_architecture.md](docs/evolution_architecture.md) | 演化系统架构设计 |
| [acorn-cli/README.md](acorn-cli/README.md) | CLI 使用文档 |
| [value-investment/](value-investment/) | 价值投资插件详情 |

---

## CLI 命令

| 命令 | 说明 |
|------|------|
| `acorn status` | 查看系统状态 |
| `acorn list` | 列出已安装插件 |
| `acorn install <pkg>` | 安装插件 |
| `acorn vi query <symbol>` | 查询股票数据 |
| `acorn vi list-fields` | 列出可用字段 |
| `acorn vi list-calculators` | 列出可用计算器 |

## HTTP API

服务启动后访问：

- API: `http://localhost:18732`
- Swagger: `http://localhost:18732/docs`

```bash
# 启动服务
acorn-agent

# HTTP 请求
curl -X POST http://localhost:18732/execute \
  -H "Content-Type: application/json" \
  -d '{"command": "vi_query", "args": {"symbol": "600519", "fields": "roe"}}'
```
