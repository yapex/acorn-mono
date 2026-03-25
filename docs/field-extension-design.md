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

### 2.4 现有设计的问题

| 问题 | 说明 |
|------|------|
| **错误使用 pluggy** | 手动循环调用 `for result in pm.hook...`，而不是直接调用 `results = pm.hook...` |
| **Provider 被动等待** | 不是主动回答"我能提供什么"，而是等待系统分发任务 |
| **预设 hook 名** | 不是询问"谁能获取"，而是预设了数据类型（financials/indicators/market） |
| **非询问式调用** | 直接分发到特定 hook，不会询问"谁能获取" |
| **市场未解耦** | Provider 依赖 `MARKET_CODE`，但 hook 调用时未传入市场参数过滤 |

### 2.5 现有代码中的错误用法

```python
# 现有代码（错误）
for result in self._pm.hook.vi_fetch_indicators(
    symbol=symbol,
    fields=request_indicators,
    end_year=end_year,
    years=self.years,
):
    if result is not None and not result.empty:
        dfs.append(result)

# 正确用法
results = self._pm.hook.vi_fetch_indicators(
    symbol=symbol,
    fields=request_indicators,
    end_year=end_year,
    years=self.years,
)
for result in results:
    if result is not None and not result.empty:
        dfs.append(result)
```

**注意**：虽然 `for result in pm.hook...` 也能工作，但这不是 pluggy 的正确用法。pluggy 会返回一个迭代器，直接遍历这个迭代器即可，不需要手动分发给每个 Provider。

---

## 3. 核心问题：pluggy 的正确使用方式

### 3.1 pluggy 的本质

**pluggy 的核心能力是自动广播**：调用一个 hook 时，pluggy 会自动分发给所有实现了该 hook 的插件。

```python
# 正确：直接调用，pluggy 自动分发给所有实现了 hook 的插件
results = pm.hook.vi_provide_items(items=[...], symbol="00700", market="HK")
# results 是一个迭代器，包含所有插件的返回值

# 错误：手动循环（我们现有的用法）
for result in pm.hook.vi_fetch_indicators(...):  # ❌ 这是错误的用法
    if result:
        dfs.append(result)
```

### 3.2 pluggy 的工作原理

```
pm.hook.vi_provide_items(items=[...], symbol="00700", market="HK")
         │
         │ pluggy 自动执行
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│Plugin A│ │Plugin B│
│        │ │        │
│return  │ │return  │
│[]      │ │[result]│
└───┬────┘ └───┬────┘
    │          │
    └────┬─────┘
         │
         ▼
    results 迭代器
    [[], [result], ...]
```

### 3.3 正确的 pluggy 协作方式

**现有设计（错误）**：
```python
# 手动循环每个 Provider
for result in self._pm.hook.vi_fetch_indicators(...):
    if result:
        dfs.append(result)
```

**正确设计（协作式）**：
```python
# 直接调用，pluggy 自动广播给所有实现了 hook 的插件
results = self._pm.hook.vi_provide_items(
    items=items,
    symbol=symbol,
    market=market,
)
# pluggy 返回所有插件的返回值

# 合并结果
all_items = []
for sublist in results:
    if sublist:
        all_items.extend(sublist)
```

### 3.4 与现有代码的对比

| 方面 | 现有设计（错误） | 正确设计 |
|------|------------------|----------|
| 调用方式 | 手动循环 `for result in pm.hook...` | 直接调用 `results = pm.hook...` |
| 分发方式 | 需要手动遍历 | pluggy 自动广播 |
| 返回值 | 需要手动收集 | pluggy 自动收集所有返回值 |

---

## 4. 实现方案

### 4.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Query Flow                                      │
│                                                                      │
│  User Query: [net_profit, total_shares, roe, implied_growth]        │
│  Symbol: 00700, Market: HK                                           │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  pluggy 广播: vi_provide_items(items, symbol, market)         │  │
│  │                                                               │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │  │
│  │  │ Tushare     │  │ AKShare    │  │ YFinance   │          │  │
│  │  │ (A 股)      │  │ (A/HK/US)  │  │ (HK/US)   │          │  │
│  │  │             │  │             │  │            │          │  │
│  │  │ supports:   │  │ supports:   │  │ supports:  │          │  │
│  │  │  market=HK?│  │  market=HK? │  │  market=HK? │          │  │
│  │  │  → No ❌   │  │  → Yes ✅   │  │  → Yes ✅  │          │  │
│  │  │             │  │             │  │            │          │  │
│  │  │ return []   │  │ return:     │  │ return:    │          │  │
│  │  │             │  │  net_profit │  │  total_shares │        │  │
│  │  │             │  │  roe       │  │            │          │  │
│  │  └─────────────┘  └──────┬─────┘  └──────┬─────┘          │  │
│  └────────────────────────────┼───────────────┼────────────────┘  │
│                               │               │                   │
│                               └───────┬───────┘                   │
│                                       ▼                           │
│                          ┌─────────────────────┐                 │
│                          │  合并结果           │                 │
│                          │  - net_profit ✅   │                 │
│                          │  - total_shares ✅ │                 │
│                          │  - roe ✅         │                 │
│                          │  - implied_growth ❌ (Calculator) │    │
│                          └──────────┬──────────┘                │
│                                     │                            │
│                                     ▼                            │
│                          ┌─────────────────────┐                 │
│                          │  Calculator Engine  │                 │
│                          │  (implied_growth)  │                 │
│                          └──────────┬──────────┘                │
│                                     │                            │
│                                     ▼                            │
│                          ┌─────────────────────┐                 │
│                          │  最终结果            │                 │
│                          │  {所有字段: 值}     │                 │
│                          └─────────────────────┘                 │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 核心组件

#### 4.2.1 ItemResult

```python
@dataclass
class ItemResult:
    """Provider 返回的单个 item 结果"""
    item: str                    # item 名称
    value: Any                  # 字段值
    source: str                 # 来源：provider 名称
    year: int = None            # 年份（可选）
```

#### 4.2.2 Provider 接口

```python
class FieldProvider:
    """字段提供者接口"""
    
    name: str = ""              # Provider 名称
    supported_markets: list = []  # 支持的市场列表
    FIELD_MAPPINGS: dict = {}   # 字段映射
    
    def supports(self, item: str, market: str) -> bool:
        """是否支持此 item + 市场组合"""
        return (
            market in self.supported_markets and
            self._can_provide(item)
        )
    
    def _can_provide(self, item: str) -> bool:
        """是否能够提供此 item（检查映射）"""
        raise NotImplementedError
    
    def fetch(self, item: str, symbol: str, market: str) -> Any:
        """获取 item 的值"""
        raise NotImplementedError
    
    def provide_items(
        self, 
        items: list[str], 
        symbol: str, 
        market: str
    ) -> list[ItemResult]:
        """
        协作式接口：返回我能提供的 items
        
        核心方法！pluggy 会调用此方法。
        """
        # 1. 先检查市场
        if market not in self.supported_markets:
            return []  # 不支持此市场，返回空
        
        # 2. 筛选我能提供的 items
        available = []
        for item in items:
            if self._can_provide(item):
                available.append(item)
        
        if not available:
            return []
        
        # 3. 尝试获取
        results = []
        for item in available:
            value = self.fetch(item, symbol, market)
            if value is not None:
                results.append(ItemResult(
                    item=item,
                    value=value,
                    source=self.name,
                ))
        
        return results
```

#### 4.2.3 pluggy Hook 定义

```python
class FieldSystemSpec:
    """字段系统的 pluggy 规范"""
    
    @vi_hookspec(firstresult=False)
    def vi_provide_items(
        self,
        items: list[str],
        symbol: str,
        market: str,
    ) -> list[ItemResult]:
        """
        协作式接口：谁能提供这些 items？
        
        pluggy 会分发给所有实现了此 hook 的插件，
        每个 Provider 返回自己能提供的 items。
        
        Args:
            items: 要查询的 items 列表
            symbol: 股票代码
            market: 市场代码 (A/HK/US)
        
        Returns:
            各个 Provider 返回的 ItemResult 列表的列表
            [[result, ...], [result, ...], ...]
        """
        return []
```

#### 4.2.4 Provider 实现示例

**AKShareProvider（HK市场）**：

```python
class AKShareProvider(FieldProvider):
    """AKShare Provider"""
    
    name = "akshare"
    supported_markets = ["A", "HK", "US"]
    
    FIELD_MAPPINGS = {
        # HK
        "net_profit": "净利润",
        "total_revenue": "营业总收入",
        "roe": "股东权益回报率(%)",
        # ...
    }
    
    def _can_provide(self, item: str) -> bool:
        """检查我能提供此 item"""
        return item in self.FIELD_MAPPINGS
    
    def fetch(self, item: str, symbol: str, market: str) -> Any:
        """获取数据"""
        native_field = self.FIELD_MAPPINGS.get(item)
        if not native_field:
            return None
        
        try:
            # 调用 AKShare API
            df = ak.stock_hk_financial_indicator_em(symbol=symbol)
            if df is not None and native_field in df.columns:
                return df[native_field].iloc[0]
        except Exception as e:
            logging.warning(f"AKShare fetch failed: {e}")
        
        return None
    
    @vi_hookimpl
    def vi_provide_items(
        self,
        items: list[str],
        symbol: str,
        market: str,
    ) -> list[ItemResult]:
        """
        协作式接口实现
        
        关键点：
        1. 先检查市场 - 如果不支持，直接返回 []
        2. 只返回我能成功获取的
        3. 失败的不返回，让其他 Provider 尝试
        """
        # 市场过滤 - 关键！
        if market not in self.supported_markets:
            return []
        
        # 筛选我能提供的 items
        available = [item for item in items if self._can_provide(item)]
        if not available:
            return []
        
        # 尝试获取
        results = []
        for item in available:
            value = self.fetch(item, symbol, market)
            if value is not None:
                results.append(ItemResult(
                    item=item,
                    value=value,
                    source=self.name,
                ))
        
        return results
```

**YFinanceProvider**：

```python
class YFinanceProvider(FieldProvider):
    """YFinance Provider"""
    
    name = "yfinance"
    supported_markets = ["HK", "US"]  # 不支持 A 股
    
    FIELD_MAPPINGS = {
        "total_shares": "sharesOutstanding",
        "circ_shares": "floatShares",
        "market_cap": "marketCap",
    }
    
    @vi_hookimpl
    def vi_provide_items(self, items, symbol, market) -> list[ItemResult]:
        # 市场过滤
        if market not in self.supported_markets:
            return []
        
        available = [item for item in items if self._can_provide(item)]
        results = []
        
        for item in available:
            value = self._fetch(item, symbol)
            if value is not None:
                results.append(ItemResult(item=item, value=value, source=self.name))
        
        return results
```

#### 4.2.5 系统合并结果

```python
class FieldSystem:
    """字段系统"""
    
    def query(
        self,
        items: list[str],
        symbol: str,
        market: str,
    ) -> QueryResult:
        """
        查询多个 items
        
        通过 pluggy 广播给所有 Provider，
        收集返回，合并结果。
        """
        # 1. 广播询问 - pluggy 自动分发给所有实现了 hook 的插件
        all_results = self._pm.hook.vi_provide_items(
            items=items,
            symbol=symbol,
            market=market,
        )
        # pluggy 返回的是迭代器，包含所有插件的返回值
        # 需要 flatten: [[results], [results], ...] -> [results, results, ...]
        flat_results = []
        for sublist in all_results:
            if sublist:
                flat_results.extend(sublist)
        
        # 2. 合并结果
        merged = {}
        for result in flat_results:
            if result.item not in merged:
                merged[result.item] = result
        
        # 3. 检查缺失的 items
        provided = set(merged.keys())
        missing = [item for item in items if item not in provided]
        
        # 4. 处理 Calculator items
        # （Calculator 不通过 vi_provide_items 获取，
        #    而是在获取到 Field 数据后单独计算）
        
        return QueryResult(
            data={item: r.value for item, r in merged.items()},
            provided=list(provided),
            missing=missing,
        )
```

---

## 5. 与 Calculator 的协作

### 5.1 ItemSource 区分

```python
class ItemSource(Enum):
    FIELD = "field"        # 从 Provider 获取
    CALCULATOR = "calculator"  # 从 Calculator 计算
```

### 5.2 查询流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Query Flow                                      │
│                                                                      │
│  User Query: [net_profit, total_shares, roe, implied_growth]        │
│               │                                                      │
│               ▼                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Step 1: 区分 Field 和 Calculator                            │  │
│  │                                                           │  │
│  │  Field Items: [net_profit, total_shares, roe]              │  │
│  │  Calculator Items: [implied_growth]                        │  │
│  └───────────────────────────────────────────────────────────────┘  │
│               │                                                      │
│               ▼                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Step 2: 通过 pluggy 获取 Field Items                        │  │
│  │                                                           │  │
│  │  vi_provide_items([net_profit, total_shares, roe], ...)    │  │
│  │      │                                                     │  │
│  │      ├─ Tushare: [] (不支持 HK)                           │  │
│  │      ├─ AKShare: [net_profit, roe]                       │  │
│  │      └─ YFinance: [total_shares]                          │  │
│  │                                                           │  │
│  │  Result: {net_profit: x, total_shares: y, roe: z}         │  │
│  └───────────────────────────────────────────────────────────────┘  │
│               │                                                      │
│               ▼                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Step 3: 运行 Calculator                                    │  │
│  │                                                           │  │
│  │  implied_growth.calculate(                                  │  │
│  │      data={net_profit: x, total_shares: y, roe: z}         │  │
│  │  )                                                         │  │
│  │                                                           │  │
│  │  Result: {implied_growth: w}                              │  │
│  └───────────────────────────────────────────────────────────────┘  │
│               │                                                      │
│               ▼                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Step 4: 合并结果                                          │  │
│  │                                                           │  │
│  │  Final: {                                                   │  │
│  │    net_profit: x,                                          │  │
│  │    total_shares: y,                                       │  │
│  │    roe: z,                                                 │  │
│  │    implied_growth: w,                                      │  │
│  │  }                                                         │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.3 协作式设计的关键点

1. **市场过滤在 Provider 内部**：每个 Provider 检查 `market in self.supported_markets`
2. **Provider 主动回答**：返回我能提供的，不是被动等待调用
3. **失败返回空**：获取失败时返回 `[]`，让其他 Provider 尝试
4. **pluggy 收集所有返回**：系统合并所有 Provider 的回答

---

## 6. 动态扩展机制

### 6.1 触发条件

当 `missing` 列表不为空时，触发扩展：

```python
if missing:
    # 问 LLM："谁能帮我获取这些 items？"
    return QueryResult(
        data=merged,
        provided=list(provided),
        missing=missing,
        needs_extension=True,
        extension_spec=generate_extension_spec(missing, market),
    )
```

### 6.2 扩展规范

```python
def generate_extension_spec(missing: list[str], market: str) -> str:
    return f"""
## 字段扩展规范

### 缺失的 Items
{format_list(missing)}

### 市场
{market}

### 数据源能力
- Tushare: A 股
- AKShare: A/HK/US
- YFinance: HK/US

### 需要做的
在 Provider 的 `FIELD_MAPPINGS` 中添加映射：

```python
# {provider}_provider.py

FIELD_MAPPINGS = {{
    # 添加缺失字段的映射
    "{field}": "{native_field}",
}}
```

### 完成后
重新运行查询，系统将自动使用新映射。
"""
```

---

## 7. LLM 推理机制

### 7.1 触发条件

当所有 Provider 都无法获取，且系统也没有扩展规范时，触发 LLM 推理。

### 7.2 推理上下文

```python
def generate_inference_context(
    missing: list[str],
    symbol: str,
    market: str,
    provided_data: dict,
) -> str:
    return f"""
## 字段 LLM 推理规范

### 目标
获取字段：{format_list(missing)}

### 上下文
- 股票代码: {symbol}
- 市场: {market}
- 已有数据: {provided_data}

### 推理原则

1. **优先公开披露数据**
   - 从财报、年报、招股书获取
   - 从权威金融网站获取

2. **跨源验证**
   - 尝试至少 2 种不同的推理方法
   - 比较结果，偏差超过 5% 需要复查

3. **合理推导**
   - 可用公式: total_shares = market_cap / price
   - 可用公式: total_shares = net_profit / eps

4. **留有余地**
   - 实在无法获取时返回 None
   - 提供置信度评估
"""
```

---

## 8. 与现有架构融合

### 8.1 渐进迁移

| 阶段 | 内容 |
|------|------|
| Phase 1 | 新增 `vi_provide_items` hook，与现有 hook 并存 |
| Phase 2 | Provider 实现新 hook |
| Phase 3 | 迁移现有 hook 调用到新方式 |
| Phase 4 | 移除旧 hook |

### 8.2 兼容性

```python
class AKShareProvider:
    """同时支持新旧两种 hook"""
    
    # 旧 hook（兼容）
    @vi_hookimpl
    def vi_fetch_indicators(self, symbol, fields, end_year, years):
        ...
    
    # 新 hook（协作式）
    @vi_hookimpl
    def vi_provide_items(self, items, symbol, market):
        ...
```

---

## 9. 设计原则

| 原则 | 说明 |
|------|------|
| **pluggy 广播** | 利用 pluggy 的广播能力，让 Provider 主动回答 |
| **市场过滤** | Provider 内部检查市场，不响应不支持的市场 |
| **协作式** | Provider 返回我能提供的，不是被动等待调用 |
| **失败返回空** | 获取失败时返回 `[]`，让其他 Provider 尝试 |
| **渐进迁移** | 新旧 hook 并存，逐步迁移 |

---

## 10. 待办事项

- [ ] 新增 `vi_provide_items` hook
- [ ] Provider 实现新 hook
- [ ] 实现结果合并逻辑
- [ ] 实现动态扩展机制
- [ ] 实现 LLM 推理接口
- [ ] 迁移现有 hook 到新方式
- [ ] 编写单元测试
- [ ] 编写集成测试
