# Value Investment Plugin - MVP 计划

> 最小可运行原型

## 目标

验证 pluggy 插件框架能跑通：
1. **Provider 插件**：获取财务数据
2. **Calculator 插件**：计算衍生指标
3. **CLI/HTTP**：命令行和 HTTP 调用

## 验收标准

### 1. Provider 框架验证

```bash
v-invest query 600519 -r "market_cap" -y 5
```

返回 A 股贵州茅台的市值数据。

### 2. Calculator 框架验证

```bash
v-invest query 600519 -r "implied_growth" -y 5
```

完整流程：
1. Provider 获取 `operating_cash_flow`, `market_cap`, `capital_expenditure`
2. Calculator (`calc_implied_growth`) 计算
3. 返回 `implied_growth` 结果

## MVP 组件

| 组件 | 路径 | 说明 |
|------|------|------|
| 核心包 | `vi_core/` | Field Registry, spec, Calculator Registry, Query Engine |
| Provider | `provider_tushare/` | TushareProvider |
| Calculator | `calculators/calc_implied_growth/` | 隐含增长率计算器 |
| CLI | `vi_cli/` | v-invest query 命令 |

## MVP 不包含

- 运行时注册 Calculator
- 多 Provider 降级
- 缓存管理
- 错误处理 + 警告
- 多种输出格式
- 其他 Provider (akshare, yfinance)
- 其他 Calculator

## 实现步骤

### Step 1: 项目结构

```
value-investment-plugin/
├── pyproject.toml          # uv workspace
├── vi_core/
├── provider_tushare/
├── calculators/
│   └── calc_implied_growth/
├── vi_cli/
└── tests/
```

### Step 2: vi_core

- [ ] `field_registry.py` - 复用原 fields.py
- [ ] `spec.py` - pluggy Hook 规范
- [ ] `calculator_registry.py` - Calculator 注册
- [ ] `calculator_loader.py` - 文件扫描加载
- [ ] `query_engine.py` - 查询引擎

### Step 3: provider_tushare

- [ ] TushareProvider 插件
- [ ] 获取基础财务字段

### Step 4: calc_implied_growth

- [ ] Calculator 插件规范
- [ ] 隐含增长率计算

### Step 5: vi_cli

- [ ] typer CLI
- [ ] v-invest query 命令
- [ ] AcornClient 调用

### Step 6: acorn-agent 集成

- [ ] 注册 query 命令
- [ ] 验证 RPC 调用

## 依赖

- pluggy
- typer
- pandas
- tushare
