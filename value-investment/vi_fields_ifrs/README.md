# vi_fields_ifrs

IFRS（国际财务报告准则）标准字段定义插件。

## 职责

- 提供 IFRS 标准的财务字段定义
- 通过 Pluggy Hook 贡献字段到 vi_core

## 架构

```
vi_fields_ifrs
├── plugin.py          # Pluggy 插件实现
└── (依赖 vi_fields_extension)
```

## 字段列表

### 资产负债表 (Balance Sheet)

| 字段名 | 描述 |
|--------|------|
| total_assets | 资产总计 |
| total_liabilities | 负债合计 |
| total_equity | 所有者权益合计 |
| current_assets | 流动资产 |
| current_liabilities | 流动负债 |
| cash_and_equivalents | 货币资金 |
| inventory | 存货 |
| accounts_receivable | 应收账款 |
| accounts_payable | 应付账款 |
| fixed_assets | 固定资产 |
| prepayment | 预付款项 |
| adv_receipts | 预收款项 |
| contract_assets | 合同资产 |
| contract_liab | 合同负债 |

### 利润表 (Income Statement)

| 字段名 | 描述 |
|--------|------|
| total_revenue | 营业总收入 |
| net_profit | 净利润 |
| operating_profit | 营业利润 |
| operating_cost | 营业成本 |

### 现金流量表 (Cash Flow)

| 字段名 | 描述 |
|--------|------|
| operating_cash_flow | 经营活动现金流量净额 |
| investing_cash_flow | 投资活动现金流量净额 |
| financing_cash_flow | 筹资活动现金流量净额 |
| capital_expenditure | 资本支出 |

### 财务比率 (Ratios)

| 字段名 | 描述 |
|--------|------|
| roe | 净资产收益率 (ROE) |
| roa | 资产收益率 (ROA) |
| gross_margin | 毛利率 |
| net_profit_margin | 净利率 |
| current_ratio | 流动比率 |
| quick_ratio | 速动比率 |
| debt_ratio | 资产负债率 |
| asset_turnover | 资产周转率 |
| receivable_turnover | 应收账款周转率 |

### 市场数据 (Market)

| 字段名 | 描述 |
|--------|------|
| market_cap | 总市值 |
| pe_ratio | 市盈率 (P/E) |
| pb_ratio | 市净率 (P/B) |
| basic_eps | 基本每股收益 |
| diluted_eps | 稀释每股收益 |
| book_value_per_share | 每股净资产 |

## 插件实现

```python
# plugin.py
class ViFieldsIfrsPlugin:
    @vi_hookimpl
    def vi_fields(self):
        return {
            "source": "ifrs",
            "fields": IFRS_FIELD_DESCRIPTIONS,
            "description": "International Financial Reporting Standards fields",
        }
```

## Entry Point

```toml
[project.entry-points."value_investment.fields"]
ifrs = "vi_fields_ifrs.plugin:plugin"
```

## 开发规范

1. **字段定义来源**：所有字段定义在 `vi_fields_extension.standard_fields.py`
2. **不要在此添加新字段**：新增字段应修改 `vi_fields_extension`
3. **此插件只负责贡献**：将 IFRS 字段通过 Hook 暴露给 vi_core

## 相关文档

- [字段扩展开发](../vi_fields_extension/README.md)
