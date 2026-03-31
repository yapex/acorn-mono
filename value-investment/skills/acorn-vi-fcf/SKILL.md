---
name: acorn-vi-fcf
description: Calculate Free Cash Flow (FCF) for HK and US markets. Use when user wants to compute FCF = Operating Cash Flow - Capital Expenditure.
---

# Acorn VI FCF

Calculate Free Cash Flow (FCF) for HK and US markets.

## Formula

```
FCF = 经营活动现金流量净额 - 资本支出
FCF = operating_cash_flow - capital_expenditure
```

## Market Coverage

| Market | Method | Notes |
|--------|--------|-------|
| A | Tushare 原始指标 `fcff`/`fcfe` | 不需要计算器 |
| HK | 计算器 `calc_free_cash_flow` | ✅ |
| US | 计算器 `calc_free_cash_flow` | ✅ |

## Usage

```bash
# HK
acorn vi query 00700 -i free_cash_flow --years 10

# US
acorn vi query AAPL -i free_cash_flow --years 10

# A (直接用 Tushare 原始指标)
acorn vi query 600519 -i free_cash_flow_to_firm --years 10
```
