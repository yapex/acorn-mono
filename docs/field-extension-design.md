# 字段扩展架构设计文档

## 1. 背景说明

### 1.1 需求场景

在实际使用中，用户会询问系统能否获取特定字段：

```
"能查询总股本吗？"
"港股的市净率能获取吗？"
"美股公司的每股收益怎么查？"
```

系统需要能够：

1. **快速判断**：当前系统是否支持该字段
2. **智能获取**：从合适的数据源获取数据
3. **动态扩展**：如果不支持，能够让 LLM 动态添加能力
4. **推理能力**：当所有数据源都无法获取时，能够通过 LLM 联网搜索或推导

### 1.2 多数据源现状

当前系统有多个数据源，各有特点：

| 数据源 | 支持市场 | 稳定性 | 数据覆盖 | 说明 |
|--------|----------|--------|----------|------|
| **Tushare** | A 股 | 高 | 完整 | 需要 API Token，A 股数据最权威，但只开通了 A 股权限 |
| **AKShare** | A/HK/US | 低 | 完整 | 网页抓取，数据全面，但可能因反爬策略变化失效 |
| **YFinance** | HK/US | 高 | 部分 | Yahoo Finance，稳定，但数据量少、年份不全 |

#### 路由策略

根据数据源能力和稳定性，制定以下路由规则：

| 市场 | 优先级 1 | 优先级 2 | 说明 |
|------|----------|----------|------|
| **A (A股)** | Tushare | - | 只开通了 A 股数据，官方数据源优先 |
| **HK (港股)** | AKShare | YFinance | AKShare 数据全但不稳定，YFinance 稳定但数据有限 |
| **US (美股)** | AKShare | YFinance | 同港股 |

### 1.3 当前痛点

| 问题 | 说明 | 影响 |
|------|------|------|
| **多数据源异构** | A 股用 Tushare，港股/美股用 AKShare/YFinance，字段名、格式、单位都不同 | 用户感知复杂 |
| **数据源不稳定** | AKShare 依赖网页抓取，可能因反爬策略变化失效 | 数据获取失败 |
| **映射缺失** | 数据源有数据但我们没有配置映射，导致无法获取 | 明明数据存在却用不了 |
| **缺乏推理能力** | 当数据源无法获取时，没有 fallback 机制 | 用户无法获得数据 |

### 1.4 失败场景分析

用户查询字段时，可能的失败场景：

```
场景 A：数据源有数据，但系统没有配置映射
  → 需要：动态扩展映射

场景 B：数据源有数据，但暂时获取失败（网络、反爬）
  → 需要：重试、降级到其他数据源

场景 C：数据源本身不提供这个字段
  → 需要：LLM 联网搜索或推导
```

这三种场景的处理逻辑不同，需要在架构中体现。

### 1.5 类比 Calculator

现有的 Calculator 机制是一个很好的参考：

```
Calculator 工作流程：
1. 发现所有 calc_*.py
2. 检查 required_fields 是否满足
3. 调用 calculate() 执行计算
4. 如果 Calculator 不存在，返回 evolution_spec 规范
5. LLM 根据规范创建新的 Calculator
```

字段获取可以类比设计。

### 1.6 设计目标

1. **声明式能力**：Provider 通过声明表明自己能提供哪些字段
2. **智能路由**：根据市场、数据源优先级自动选择
3. **故障恢复**：自动重试、降级、交叉验证
4. **LLM 驱动**：当传统方式失败时，通过规范让 LLM 推理获取
5. **动态扩展**：像 Calculator 一样，支持运行时添加新字段能力

---

## 2. 现有架构分析

### 2.1 BaseDataProvider 模板基类

现有的 Provider 继承自 `BaseDataProvider`，采用 Template Method 模式：

```python
class BaseDataProvider(ABC):
    """Provider 模板基类"""
    
    MARKET_CODE: str = ""
    FIELD_MAPPINGS: dict[str, dict[str, str]] = {
        "balance_sheet": {},
        "income_statement": {},
        "indicators": {},
        "market": {},
    }
    
    def fetch_financials(self, symbol, fields, end_year, years) -> pd.DataFrame | None:
        """模板方法：缓存 → 获取 → 映射 → 去重 → 过滤"""
        df = self._fetch_all_financials(...)
        df = self._apply_mapping(df)
        return self._filter_to_mapped_fields(df, fields)
```

### 2.2 现有 Provider 示例

**HKProvider**（`provider_market_hk`）：

```python
class HKProvider(BaseDataProvider):
    MARKET_CODE = "HK"
    
    FIELD_MAPPINGS = {
        "balance_sheet": {
            "股本": StandardFields.share_capital,
        },
        "indicators": {
            "营业总收入": StandardFields.total_revenue,
            "净利润": StandardFields.net_profit,
        },
    }
```

### 2.3 pluggy Hook 规范

```python
class FieldProviderSpec:
    @vi_hookspec
    def vi_fetch_financials(self, symbol, fields, end_year, years) -> pd.DataFrame | None:
        """获取财务报表数据"""
        return None
    
    @vi_hookspec
    def vi_fetch_indicators(self, symbol, fields, end_year, years) -> pd.DataFrame | None:
        """获取财务指标"""
        return None
```

---

## 3. MVP 方案设计

### 3.1 核心决策

**保持 Market-Based 设计**，只做最小改动：

1. **新增 `vi_provide_items` hook**：让 Provider 主动协作
2. **Provider 内部市场过滤**：不响应不支持的市场
3. **QueryEngine 合并结果**：收集所有 Provider 返回

### 3.2 整体流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                         查询流程 (Query Flow)                        │
│                                                                      │
│  用户查询: [net_profit, total_shares, roe, implied_growth]          │
│  股票代码: 00700, 市场: HK                                           │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Step 1: 预检 (Prechecker)                                    │  │
│  │                                                               │  │
│  │  - 检查 items 是否存在于 ItemRegistry                         │  │
│  │  - 区分 Field items 和 Calculator items                       │  │
│  │  - 检查 Field 是否被 Provider 支持                            │  │
│  │  - 检查 Calculator 依赖是否满足                               │  │
│  │                                                               │  │
│  │  结果:                                                        │  │
│  │    Field items: [net_profit, total_shares, roe]              │  │
│  │    Calculator items: [implied_growth]                        │  │
│  │    不可用: []                                                │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                       │
│                              ▼                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Step 2: 获取 Field 数据 (vi_provide_items)                   │  │
│  │                                                               │  │
│  │  pluggy 广播: vi_provide_items(                               │  │
│  │      items=[net_profit, total_shares, roe],                  │  │
│  │      symbol="00700",                                         │  │
│  │      market="HK"                                             │  │
│  │  )                                                           │  │
│  │                                                               │  │
│  │      ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │  │
│  │      │ Tushare     │  │ AKShare    │  │ YFinance   │      │  │
│  │      │ Provider    │  │ Provider   │  │ Provider   │      │  │
│  │      │ (A 股)      │  │ (HK)       │  │ (HK/US)   │      │  │
│  │      │             │  │             │  │            │      │  │
│  │      │ market==HK? │  │ market==HK? │  │ market==HK? │      │  │
│  │      │ → No ❌     │  │ → Yes ✅   │  │ → Yes ✅  │      │  │
│  │      │ return None │  │             │  │            │      │  │
│  │      │             │  │ 检查字段:   │  │ 检查字段:   │      │  │
│  │      │             │  │ - net_profit│  │ - net_profit│      │  │
│  │      │             │  │   ✅ 支持   │  │   ❌ 不支持│      │  │
│  │      │             │  │ - total_shares│  - total_shares│    │  │
│  │      │             │  │   ❌ 不支持 │  │   ✅ 支持  │      │  │
│  │      │             │  │ - roe       │  │ - roe      │      │  │
│  │      │             │  │   ✅ 支持   │  │   ❌ 不支持│      │  │
│  │      │             │  │             │  │            │      │  │
│  │      │             │  │ 获取数据    │  │ 获取数据   │      │  │
│  │      │             │  │ return DF   │  │ return DF  │      │  │
│  │      └─────────────┘  └──────┬─────┘  └──────┬─────┘      │  │
│  │                              │               │              │  │
│  │                              └───────┬───────┘              │  │
│  │                                      ▼                      │  │
│  │                          ┌─────────────────────┐            │  │
│  │                          │  QueryEngine 合并   │            │  │
│  │                          │                     │            │  │
│  │                          │  - net_profit:      │            │  │
│  │                          │    AKShare ✅      │            │  │
│  │                          │  - total_shares:    │            │  │
│  │                          │    YFinance ✅     │            │  │
│  │                          │  - roe:             │            │  │
│  │                          │    AKShare ✅      │            │  │
│  │                          │                     │            │  │
│  │                          │  结果: {            │            │  │
│  │                          │    net_profit: x,  │            │  │
│  │                          │    total_shares: y,│            │  │
│  │                          │    roe: z          │            │  │
│  │                          │  }                 │            │  │
│  │                          └──────────┬──────────┘            │  │
│  └─────────────────────────────────────┼───────────────────────┘  │
│                                        │                          │
│                                        ▼                          │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Step 3: 运行 Calculator                                      │  │
│  │                                                               │  │
│  │  implied_growth.calculate(                                    │  │
│  │      data={net_profit: x, total_shares: y, roe: z}           │  │
│  │  )                                                           │  │
│  │                                                               │  │
│  │  结果: {implied_growth: w}                                   │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                       │
│                              ▼                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Step 4: 返回最终结果                                         │  │
│  │                                                               │  │
│  │  QueryResult:                                                 │  │
│  │    success: True                                             │  │
│  │    data: {                                                   │  │
│  │      net_profit: x,                                          │  │
│  │      total_shares: y,                                       │  │
│  │      roe: z,                                                 │  │
│  │      implied_growth: w,                                      │  │
│  │    }                                                         │  │
│  │    available: [net_profit, total_shares, roe, implied_growth]│  │
│  │    unavailable: []                                           │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 扩展机制流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                      动态扩展流程 (Extension Flow)                   │
│                                                                      │
│  场景: 用户查询 "hk_dividend_yield"，但系统不支持                    │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Step 1: 预检发现缺失                                         │  │
│  │                                                               │  │
│  │  Prechecker.check("00700", ["hk_dividend_yield"])            │  │
│  │                                                               │  │
│  │  结果:                                                        │  │
│  │    available: []                                             │  │
│  │    issues: [{                                                 │  │
│  │      item: "hk_dividend_yield",                              │  │
│  │      severity: ERROR,                                        │  │
│  │      reason: "当前市场不支持",                                │  │
│  │      source: FIELD                                           │  │
│  │    }]                                                        │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                       │
│                              ▼                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Step 2: 发布 Evolution 事件                                  │  │
│  │                                                               │  │
│  │  publish_capability_missing(                                  │  │
│  │      item="hk_dividend_yield",                               │  │
│  │      capability_type=FIELD,                                  │  │
│  │      reason=FIELD_UNFILLED,                                  │  │
│  │      context={symbol: "00700", market: "HK"}                 │  │
│  │  )                                                           │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                       │
│                              ▼                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Step 3: 生成扩展规范                                         │  │
│  │                                                               │  │
│  │  evolution_spec = generate_extension_spec(                    │  │
│  │      missing=["hk_dividend_yield"],                          │  │
│  │      market="HK"                                             │  │
│  │  )                                                           │  │
│  │                                                               │  │
│  │  生成规范:                                                    │  │
│  │  ─────────────────────────────────────────────────────────   │  │
│  │  ## 字段扩展规范                                              │  │
│  │                                                               │  │
│  │  缺失字段: hk_dividend_yield                                  │  │
│  │  市场: HK                                                     │  │
│  │                                                               │  │
│  │  HKProvider 的 FIELD_MAPPINGS 中缺少此字段映射。              │  │
│  │                                                               │  │
│  │  请在以下位置添加映射:                                        │  │
│  │  - provider_market_hk/src/provider_market_hk/provider.py     │  │
│  │                                                               │  │
│  │  AKShare 可能提供的原始字段:                                  │  │
│  │  - "股息率TTM(%)"                                            │  │
│  │  - "派息比率(%)"                                             │  │
│  │                                                               │  │
│  │  示例:                                                        │  │
│  │  FIELD_MAPPINGS = {                                          │  │
│  │      "indicators": {                                         │  │
│  │          "股息率TTM(%)": StandardFields.hk_dividend_yield,   │  │
│  │      }                                                       │  │
│  │  }                                                           │  │
│  │  ─────────────────────────────────────────────────────────   │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                       │
│                              ▼                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Step 4: LLM 处理扩展规范                                     │  │
│  │                                                               │  │
│  │  LLM 收到 evolution_spec，执行:                               │  │
│  │                                                               │  │
│  │  1. 查找 AKShare 文档，确认 "股息率TTM(%)" 字段存在           │  │
│  │  2. 修改 provider.py，添加映射                                │  │
│  │  3. 重新加载 Provider                                         │  │
│  │                                                               │  │
│  │  修改后代码:                                                  │  │
│  │  FIELD_MAPPINGS = {                                          │  │
│  │      "indicators": {                                         │  │
│  │          "股东权益回报率(%)": StandardFields.roe,             │  │
│  │          "股息率TTM(%)": StandardFields.hk_dividend_yield,   │  │
│  │          # ... 其他映射                                       │  │
│  │      }                                                       │  │
│  │  }                                                           │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                       │
│                              ▼                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Step 5: 重新查询                                             │  │
│  │                                                               │  │
│  │  用户再次查询 "hk_dividend_yield":                            │  │
│  │                                                               │  │
│  │  Prechecker.check("00700", ["hk_dividend_yield"])            │  │
│  │  → 现在 available: ["hk_dividend_yield"] ✅                  │  │
│  │                                                               │  │
│  │  vi_provide_items(...)                                       │  │
│  │  → AKShareProvider 返回数据 ✅                               │  │
│  │                                                               │  │
│  │  最终结果: {hk_dividend_yield: 3.5}                          │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. 核心改动

### 4.1 新增 Hook

```python
# vi_core/spec.py

class FieldProviderSpec:
    """Hook spec for VI field providers"""
    
    # ... 现有 hooks ...
    
    @vi_hookspec
    def vi_provide_items(
        self,
        items: list[str],
        symbol: str,
        market: str,
    ) -> pd.DataFrame | None:
        """Provider 返回它能提供的 items 数据
        
        Args:
            items: 请求的字段列表
            symbol: 股票代码
            market: 市场代码 (A/HK/US)
        
        Returns:
            DataFrame with columns: fiscal_year, [requested fields...]
            或 None 如果不支持此市场/字段
        """
        return None
```

### 4.2 Provider 实现

```python
# provider_market_hk/plugin.py

class ProviderHKPlugin:
    @vi_hookimpl
    def vi_provide_items(
        self,
        items: list[str],
        symbol: str,
        market: str,
    ) -> pd.DataFrame | None:
        """HKProvider 实现 vi_provide_items"""
        # 市场过滤
        if market != "HK":
            return None
        
        provider = _get_provider()
        
        # 筛选 Provider 能提供的字段
        supported = provider.get_supported_fields()
        available = set(items) & supported
        
        if not available:
            return None
        
        # 分类获取（复用现有逻辑）
        dfs = []
        
        # 获取财务数据
        financial_fields = available & get_financial_fields()
        if financial_fields:
            df = provider.fetch_financials(symbol, financial_fields, ...)
            if df is not None:
                dfs.append(df)
        
        # 获取指标数据
        indicator_fields = available & get_indicator_fields()
        if indicator_fields:
            df = provider.fetch_indicators(symbol, indicator_fields, ...)
            if df is not None:
                dfs.append(df)
        
        # 合并并返回
        return merge_dataframes(dfs)
```

### 4.3 QueryEngine 修改

```python
# vi_core/query.py

class QueryEngine:
    def _fetch_data(self, symbol: str, items: list[str]) -> dict[str, Any]:
        """获取数据 - 使用 vi_provide_items"""
        if not self._pm or not items:
            return {}
        
        # 从 symbol 推断 market
        market = self._infer_market(symbol)
        
        # 广播给所有 Provider
        results = self._pm.hook.vi_provide_items(
            items=items,
            symbol=symbol,
            market=market,
        )
        
        # 合并所有 Provider 返回的 DataFrames
        dfs = [r for r in results if r is not None and not r.empty]
        merged_df = self._merge_dfs(dfs)
        
        return self._df_to_result_dict(merged_df)
```

---

## 5. 与 Calculator 的协作

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Field + Calculator 协作                        │
│                                                                      │
│  用户查询: [roe, net_profit, implied_growth]                        │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  ItemRegistry 定义                                            │  │
│  │                                                               │  │
│  │  roe:           ItemSource.FIELD                              │  │
│  │  net_profit:    ItemSource.FIELD                              │  │
│  │  implied_growth: ItemSource.CALCULATOR                        │  │
│  │                 requires: [roe, net_profit]                  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                       │
│                              ▼                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Step 1: 获取 Field 数据                                      │  │
│  │                                                               │  │
│  │  vi_provide_items([roe, net_profit], symbol, market)         │  │
│  │                                                               │  │
│  │  结果: {roe: {2023: 0.15, 2022: 0.14},                        │  │
│  │          net_profit: {2023: 1000, 2022: 900}}                │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                       │
│                              ▼                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Step 2: 运行 Calculator                                      │  │
│  │                                                               │  │
│  │  检查依赖: roe ✅, net_profit ✅                             │  │
│  │                                                               │  │
│  │  vi_run_calculator(                                           │  │
│  │      name="implied_growth",                                  │  │
│  │      data={roe: ..., net_profit: ...},                       │  │
│  │      config={}                                               │  │
│  │  )                                                           │  │
│  │                                                               │  │
│  │  结果: {implied_growth: {2023: 0.08, 2022: 0.07}}            │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                       │
│                              ▼                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Step 3: 合并结果                                             │  │
│  │                                                               │  │
│  │  最终结果:                                                    │  │
│  │  {                                                           │  │
│  │    roe: {2023: 0.15, 2022: 0.14},                            │  │
│  │    net_profit: {2023: 1000, 2022: 900},                      │  │
│  │    implied_growth: {2023: 0.08, 2022: 0.07}                  │  │
│  │  }                                                           │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. 设计原则

| 原则 | 说明 |
|------|------|
| **保持 Market-Based** | 不切换到 Source-Based，避免大规模重构 |
| **最小改动** | 只添加 `vi_provide_items` hook，复用现有逻辑 |
| **Provider 协作** | 让 Provider 主动回答"我能提供什么" |
| **市场过滤在 Provider** | 每个 Provider 检查 `market == self.MARKET_CODE` |
| **失败返回 None** | 获取失败时返回 None，让 QueryEngine 处理 |

---

## 7. 待办事项

- [x] 在 `spec.py` 中添加 `vi_provide_items` hook
- [x] 各 Provider 实现 `vi_provide_items` 方法
- [x] 修改 `QueryEngine._fetch_data` 使用新 hook
- [x] 测试验证
