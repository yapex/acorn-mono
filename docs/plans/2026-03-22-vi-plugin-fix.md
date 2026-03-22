# acorn-agent VI 插件修复计划

> **Goal:** 修复 acorn-agent 启动后能自动加载所有必需的 VI 插件，并能成功查询苹果和腾讯的隐含增长率

## 问题诊断结果

### 问题 1: vi_fields_ifrs 返回格式错误 ✓ 已修复
- **期望:** `{field_name: {description: ...}}`
- **实际:** `{field_name: description_str}`
- **状态:** 已修复

### 问题 2: HK/US Provider entry point 配置错误
- **文件:** `provider_market_hk/pyproject.toml`, `provider_market_us/pyproject.toml`
- **问题:** entry point 值格式错误 `provider_market_hk:plugin` 应为 `provider_market_hk.plugin:plugin`

### 问题 3: `_df_to_serializable_dict` 无法处理 year 作为 index.name
- **文件:** `vi_core/plugin.py`
- **问题:** 函数只检查 `df.columns` 中的日期列，但 `_merge_dfs` 将 year 作为 `df.index.name` 设置
- **症状:** 查询返回 `fields_fetched: []`

### 问题 4: HK/US Provider 缺少 market_cap 字段映射
- **问题:** HK Provider 有 `hk_market_cap`，US Provider 缺少市值字段
- **implied_growth 计算器需要:** `market_cap` 和 `operating_cash_flow`

---

## 修复任务

### Task 1: 修复 HK Provider entry point 配置

**文件:** `value-investment-plugin/provider_market_hk/pyproject.toml`

**Step 1: 检查当前配置**
```bash
grep -A 3 "value_investment.providers" value-investment-plugin/provider_market_hk/pyproject.toml
```

**Step 2: 修复 entry point**
```toml
[project.entry-points."value_investment.providers"]
provider_market_hk = "provider_market_hk.plugin:plugin"
```

**Step 3: 验证修复**
```bash
uv pip install -e ./value-investment-plugin/provider_market_hk
python -c "from importlib.metadata import entry_points; eps = entry_points(group='value_investment.providers'); print([e.value for e in eps if e.name == 'provider_market_hk'])"
```

---

### Task 2: 修复 US Provider entry point 配置

**文件:** `value-investment-plugin/provider_market_us/pyproject.toml`

**Step 1: 检查当前配置**
```bash
grep -A 3 "value_investment.providers" value-investment-plugin/provider_market_us/pyproject.toml
```

**Step 2: 修复 entry point**
```toml
[project.entry-points."value_investment.providers"]
provider_market_us = "provider_market_us.plugin:plugin"
```

**Step 3: 验证修复**
```bash
uv pip install -e ./value-investment-plugin/provider_market_us
python -c "from importlib.metadata import entry_points; eps = entry_points(group='value_investment.providers'); print([e.value for e in eps if e.name == 'provider_market_us'])"
```

---

### Task 3: 修复 `_df_to_serializable_dict` 函数

**文件:** `value-investment-plugin/vi_core/src/vi_core/plugin.py`

**问题根源:**
- `_merge_dfs` 将 year 设置为 `df.index.name`（不是 column）
- `_df_to_serializable_dict` 只检查 `df.columns` 中的日期列

**Step 1: 添加测试**
```python
def test_df_to_serializable_with_index_name():
    """测试 year 作为 index.name 的 DataFrame"""
    df = pd.DataFrame({
        'operating_cash_flow': [9.246369e+10, 6.659325e+10],
        'market_cap': [1.809530e+08, 1.809530e+08],
    })
    df.index.name = 'year'
    
    result = _df_to_serializable_dict(df)
    assert 'operating_cash_flow' in result
    assert 'market_cap' in result
    assert 2024 in result['operating_cash_flow'] or 2023 in result['operating_cash_flow']
```

**Step 2: 修复函数**
```python
def _df_to_serializable_dict(df: pd.DataFrame | None) -> dict[str, dict[int, Any]]:
    if df is None or df.empty:
        return {}
    
    result: dict[str, dict[int, Any]] = {}
    
    # Identify date column
    date_columns = ["end_date", "report_date", "date", "trade_date", "year", "REPORT_DATE"]
    actual_date_col = None
    
    # 首先检查 df.index.name 是否是日期列
    if df.index.name and df.index.name in date_columns:
        actual_date_col = df.index.name
    
    # 然后检查 df.columns
    if actual_date_col is None:
        for col in date_columns:
            if col in df.columns:
                actual_date_col = col
                break
    
    if actual_date_col is None:
        return {}
    
    # 获取年份
    try:
        if actual_date_col == "year" and df.index.name == "year":
            years = df.index.astype(int)
        elif actual_date_col == "year":
            years = df[actual_date_col].astype(int)
        else:
            dates = pd.to_datetime(df[actual_date_col], format="mixed")
            years = dates.dt.year
    except Exception:
        return {}
    
    # 处理数据列
    for col in df.columns:
        if col == actual_date_col:
            continue
        
        col_data: dict[int, Any] = {}
        for year, val in zip(years, df[col]):
            if pd.isna(val):
                continue
            if hasattr(val, 'item'):
                col_data[int(year)] = val.item()
            elif isinstance(val, float):
                col_data[int(year)] = float(val)
            elif isinstance(val, int):
                col_data[int(year)] = int(val)
            else:
                col_data[int(year)] = val
        
        if col_data:
            result[col] = col_data
    
    return result
```

**Step 3: 运行测试验证**
```bash
cd value-investment-plugin/vi_core
uv run pytest tests/ -v -k "serializable"
```

---

### Task 4: HK/US Provider 添加 market_cap 字段映射

**方案 A: 在 Provider 中添加 market_cap → market_cap 映射**

**文件:** `provider_market_hk/src/provider_market_hk/provider.py`

在 `FIELD_MAPPINGS["market"]` 中添加:
```python
"market": {
    "总市值(港元)": StandardFields.market_cap,  # 添加这一行
    "港股市值(港元)": StandardFields.hk_market_cap,
    # ...
}
```

**方案 B: 创建统一的 implied_growth_hk/implied_growth_us 计算器**

注册支持 `hk_market_cap` / `us_market_cap` 的计算器。

**推荐方案 A**，因为更简单且与 A 股保持一致。

---

### Task 5: 端到端验证测试

**Step 1: 重启 agent**
```bash
cd /Users/yapex/workspace/acorn-mono
./stop-agent.sh && ./start-agent.sh
sleep 3
```

**Step 2: 测试查询 A 股（茅台）**
```python
from acorn_agent.client import AcornClient
client = AcornClient()
result = client.execute('vi_query', {
    'symbol': '600519',
    'fields': 'operating_cash_flow,market_cap',
    'years': 5,
})
assert result['success']
assert 'operating_cash_flow' in result['data']['data']
assert 'market_cap' in result['data']['data']
```

**Step 3: 测试查询苹果 (AAPL)**
```python
result = client.execute('vi_query', {
    'symbol': 'AAPL',
    'fields': 'operating_cash_flow,market_cap',
    'years': 5,
})
assert result['success']
```

**Step 4: 测试查询腾讯 (00700)**
```python
result = client.execute('vi_query', {
    'symbol': '00700',
    'fields': 'operating_cash_flow,hk_market_cap',
    'years': 5,
})
assert result['success']
```

**Step 5: 测试隐含增长率计算**
```python
# 注册支持 hk_market_cap 的计算器
client.execute('vi_register_calculator', {
    "name": "implied_growth_hk",
    "required_fields": ["operating_cash_flow", "hk_market_cap"],
    "code": """..."""
})

# 查询并计算
result = client.execute('vi_query', {
    'symbol': '00700',
    'fields': 'operating_cash_flow,hk_market_cap',
    'calculators': 'implied_growth_hk',
    'calculator_config': {'implied_growth_hk': {'wacc': 0.08, 'g_terminal': 0.03}},
})
print(result['data']['data'].get('implied_growth_hk'))
```

---

## 执行顺序

1. Task 1: 修复 HK Provider entry point
2. Task 2: 修复 US Provider entry point  
3. Task 3: 修复 `_df_to_serializable_dict`
4. Task 4: 添加 market_cap 字段映射
5. Task 5: 端到端验证
