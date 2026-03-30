# Acorn 🌰

自进化插件系统。基于 pluggy 构建，支持通过事件驱动的自我进化能力。

---

## 🚀 3 分钟上手

### 1. 安装

```bash
git clone https://github.com/yapex/acorn-mono.git
cd acorn-mono

# 方式 1: 使用 uv tool (推荐)
uv tool install -e acorn-cli \
  --with-editable value-investment/vi_cli \
  --with-editable value-investment/vi_core \
  --with-editable value-investment/vi_fields_extension \
  --with-editable value-investment/vi_fields_ifrs \
  --with-editable value-investment/vi_calculators \
  --with-editable value-investment/provider_market_a \
  --with-editable value-investment/provider_market_hk \
  --with-editable value-investment/provider_market_us

# 方式 2: 开发环境
uv sync
```

### 2. 配置 API Token（可选）

```bash
# A 股数据 (Tushare) - 查询 A 股时需要
export TUSHARE_TOKEN="your_token_here"
```

### 3. 启动服务

```bash
acorn-agent
```

服务地址：
- API: `http://localhost:18732`
- Swagger: `http://localhost:18732/docs`

### 4. CLI 命令

```bash
# 查看系统状态（验证安装）
acorn status

# 查询贵州茅台 ROE（最近 5 年）
acorn vi query 600519 --items roe --years 5

# 查询苹果净利润（最近 10 年）
acorn vi query AAPL --items net_profit --years 10

# 查询腾讯 + 计算隐含增长率
acorn vi query 00700 --items operating_cash_flow,market_cap,implied_growth

# 列出所有字段和计算器
acorn vi list

# 按类型筛选
acorn vi list --category calculator

# 列出已安装插件
acorn list
```

### Python Client

```python
from acorn_cli.client import AcornClient

client = AcornClient()

# 查询财务数据
result = client.execute("vi_query", {
    "symbol": "600519",
    "items": "revenue,roe,market_cap",
    "years": 5,
})

# 列出所有字段
result = client.execute("vi_list_fields", {})

# 列出所有计算器
result = client.execute("vi_list_calculators", {})
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
│                     命令行层                              │
│  • acorn (插件管理)                                      │
│  • acorn vi (价值投资查询 - 插件贡献)                     │
│  • acorn-agent (HTTP 服务)                                │
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
│  • vi_fields_* (字段定义)                                │
│  • provider_market_* (数据源)                            │
│  • ...                                                 │
└─────────────────────────────────────────────────────────┘
```

---

## 项目结构

```
acorn-mono/
├── acorn-core/              # 核心框架 (事件总线、进化管理)
├── acorn-cli/               # CLI 工具 + HTTP API 服务
├── acorn-events/            # 事件常量定义
├── value-investment/         # 价值投资领域插件
│   ├── vi_cli/             # CLI 入口 (typer，通过 entry_points 注册)
│   ├── vi_core/            # 核心包 (查询引擎，pluggy 插件)
│   ├── vi_calculators/     # 计算器引擎
│   ├── vi_fields_extension/ # 字段扩展
│   ├── vi_fields_ifrs/     # IFRS 标准字段
│   └── provider_market_*/  # 数据源 (A/港/美股)
└── examples-plugin/         # 示例插件
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

通过 entry_points 注册，重启 CLI 即可自动加载。

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
