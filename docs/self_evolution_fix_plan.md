# 自进化系统修复计划

## 问题总结

当前系统无法正确检测字段缺失，导致自我进化能力无法触发。

根本原因：**Provider 字段检测没有按市场过滤**，将所有 Provider 的字段取并集，导致某个市场的缺失字段被其他市场的 Provider "掩盖"。

## 修复步骤

### Step 1: 修复字段检测逻辑 (30分钟)

**文件**: `value-investment/vi_core/src/vi_core/plugin.py`

**修改点**: `_query()` 方法中 Provider 字段的获取逻辑

**当前代码** (约 458-461 行):
```python
# 获取 Provider 支持的字段
provider_fields: set[str] = set()
for result in self._get_plugin_manager().hook.vi_supported_fields():
    if result:
        provider_fields.update(result)
```

**修复方案**:
```python
# 获取目标市场的 Provider 支持的字段
market = self._infer_market(symbol)
market_provider_fields: set[str] = set()

for plugin in self._get_plugin_manager().get_plugins():
    # 检查插件是否支持目标市场
    if hasattr(plugin, 'vi_markets'):
        supported_markets = plugin.vi_markets()
        if market not in supported_markets:
            continue
    
    # 获取该插件支持的字段
    if hasattr(plugin, 'vi_supported_fields'):
        fields = plugin.vi_supported_fields()
        if fields:
            market_provider_fields.update(fields)

provider_fields = market_provider_fields
```

### Step 2: 验证修复 (15分钟)

**测试命令**:
```bash
# 重启服务
pkill -f acorn-agent
nohup .venv/bin/python -m acorn_cli.server > /tmp/acorn-server.log 2>&1 &

# 测试查询缺失字段
.venv/bin/python -c "
from acorn_cli.client import AcornClient
client = AcornClient()

# 查询港股 total_shares (当前缺失)
result = client.execute('vi_query', {
    'symbol': '00700',
    'items': 'total_shares',
    'years': 1
})
print('Query result:', result)

# 检查是否记录了能力缺失
import time
time.sleep(1)
status = client.execute('capabilities', {})
print('Status:', status)
"
```

**预期结果**:
- `capability_missing` 应该显示 `total_shares` 被记录为缺失字段
- 事件 `EVO_CAPABILITY_MISSING` 被正确发布

### Step 3: 补充港股字段 (可选，1小时)

**文件**: `value-investment/provider_market_hk/src/provider_market_hk/provider.py`

**任务**:
1. 检查 AKShare 港股 API 是否提供 `total_shares` (总股本) 数据
2. 在 `FIELD_MAPPINGS["market"]` 中添加映射
3. 测试数据获取

**示例**:
```python
"market": {
    # ... 现有映射
    "总股本": StandardFields.total_shares,  # 如果 AKShare 提供
}
```

### Step 4: 实现自动扩展流程 (2-3小时)

**文件**: 
- `acorn-core/src/acorn_core/plugins/evo_manager.py`
- 新增: `value-investment/vi_core/src/vi_core/auto_extend.py`

**功能**:
1. EvoManager 监听到 `EVO_CAPABILITY_MISSING` 事件
2. 根据缺失类型生成 Prompt
3. 调用 LLM 生成扩展代码
4. 沙箱验证代码
5. 自动注册新字段/计算器

**Prompt 模板示例**:
```python
FIELD_EXTENSION_PROMPT = """
用户请求查询字段 '{field_name}'，但当前系统不支持。

请创建一个新的字段扩展，要求：
1. 字段名: {field_name}
2. 描述: {description}
3. 数据源: 使用 AKShare 获取港股数据
4. 输出格式: 返回 pd.DataFrame，包含 fiscal_year 和 {field_name} 列

代码模板:
```python
import akshare as ak
import pandas as pd

def fetch_{field_name}(symbol: str, years: int = 10) -> pd.DataFrame:
    # 使用 AKShare API 获取数据
    # ...
    return df
```
"""
```

## 验证清单

- [ ] 查询港股 `total_shares` 时，`capability_missing` 正确记录
- [ ] 查询 A 股存在的字段时，不触发缺失记录
- [ ] 事件 `EVO_CAPABILITY_MISSING` 被正确发布到 EventBus
- [ ] EvoManager 正确接收并存储缺失记录
- [ ] `acorn status` 或 `capabilities` 命令显示缺失记录

## 相关命令

```bash
# 启动服务
nohup .venv/bin/python -m acorn_cli.server > /tmp/acorn-server.log 2>&1 &

# 查询测试
.venv/bin/python -c "
from acorn_cli.client import AcornClient
client = AcornClient()
result = client.execute('vi_query', {'symbol': '00700', 'items': 'total_shares', 'years': 1})
print(result)
"

# 检查状态
.venv/bin/python -c "
from acorn_cli.client import AcornClient
client = AcornClient()
print(client.execute('capabilities', {}))
"

# 查看服务日志
tail -f /tmp/acorn-server.log
```

---

**创建时间**: 2024-03-25
**预计总耗时**: 3-4 小时
