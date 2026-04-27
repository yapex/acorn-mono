# PE 历史估值百分位 — 设计方案

> 日期: 2026-04-15
> 状态: 实施中

## 目标

新增 `pe_percentile` calculator，计算当前 PE 在历史每日数据中的百分位分布。

PE = 当日不复权收盘价 / 最新可获得的年度基本 EPS（`basic_eps`）。

## 核心设计

### DAILY_FIELDS 机制

Calculator 声明两种数据需求：

```python
REQUIRED_FIELDS = ["basic_eps"]   # 年度粒度 → 框架通过 vi_provide_items 获取
DAILY_FIELDS = ["close"]          # 每日粒度  → 框架通过 vi_fetch_historical 获取
```

**框架自动将两种数据统一注入 `data` dict**，`calculate` 签名不变：

```python
def calculate(data):
    eps_series = data["basic_eps"]   # pd.Series(index=fiscal_year)
    close_df = data["close"]         # pd.DataFrame(date, close)
```

这样所有旧 calculator 零改动。

### 数据流

```
_query:
  ① 解析 items → 分离 fields + calculators
  ② 收集所有依赖:
     - required_fields → 年度数据需求
     - daily_fields   → 每日数据需求
  ③ 按粒度获取:
     - 年度通道: vi_provide_items(fields) → merged_df
     - 每日通道: vi_fetch_historical(symbol, adjust="") → daily_data
  ④ _run_calculators(data, ...):
     - data = {**annual_series_dict, **daily_data}
     - calculator 只管从 data 取
```

### EPS 可用规则

`fiscal_year=N` 的 EPS，从 `N+1` 年 1 月 1 日起视为可用。

拉长到 10 年，发布日期差异对百分位影响很小。

## 改动范围

### 新增文件

| 文件 | 说明 |
|------|------|
| `calculators/calc_pe_percentile.py` | PE 百分位 calculator |
| `tests/test_calc_pe_percentile.py` | Calculator 纯逻辑测试 |
| `tests/test_query_daily_fields.py` | Query 层集成测试 |
| `vi_calculators/tests/test_daily_fields_loader.py` | Loader 层测试 |

### 修改文件（3 个）

| 文件 | 改动 |
|------|------|
| `vi_calculators/__init__.py` | ① loader 收集 `DAILY_FIELDS` 属性<br>② `vi_list_calculators` hook spec 新增 `daily_fields`<br>③ `vi_run_calculator` 将 daily data 注入 `data` |
| `vi_core/plugin.py` | ① `_query` 收集 `daily_fields` 并获取每日数据<br>② `_run_calculators` 接收 daily_data 并合并到 data<br>③ 修复多指标返回格式的处理 |

### 不变

- hookspec（`DAILY_FIELDS` 不是新 hook，只是 loader 属性）
- Provider 层（`vi_fetch_historical` 已存在）
- `StandardFields`（复用 `basic_eps`）
- 所有旧 calculator（`calculate(data)` 签名不变）

## 测试计划

### 1. Calculator 纯逻辑测试 (test_calc_pe_percentile.py)

- Spec 声明正确：REQUIRED_FIELDS, DAILY_FIELDS, FORMAT_TYPES
- 基本计算：3 年 EPS + 6 个交易日 → 验证 PE 序列和百分位
- EPS 可用规则：fiscal_year=N 从 N+1 年起可用
- 边界值：最低百分位、最高百分位
- 异常处理：空数据、负 EPS、零价格、NaN

### 2. Loader 层测试 (test_daily_fields_loader.py)

- `load_calculators_from_path` 收集 `DAILY_FIELDS`
- `get_all_calculators` 包含 `daily_fields`
- `vi_list_calculators` hook 暴露 `daily_fields`

### 3. Query 集成测试 (test_query_daily_fields.py)

- Mock Provider 提供年度 EPS + 每日价格
- `_query` 自动获取 daily data 并注入 calculator
- 端到端：`_query("pe_percentile")` 返回完整结果

## 实施步骤

1. ✅ Calculator 纯逻辑 + 测试（已完成，15 个测试通过）
2. ✅ Loader 收集 DAILY_FIELDS + 测试（已完成，4 个测试通过）
3. 🔄 改造数据注入方式：daily data → `data` dict（而非 config）
4. 🔄 Query 层集成 + 测试
5. 全量回归测试
