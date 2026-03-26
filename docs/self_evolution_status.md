# 自进化系统实现状态报告

## 概述

Acorn 系统设计了自进化能力，能够自动检测能力缺失并触发扩展流程。本文档记录当前实现状态和测试结果。

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     用户查询请求                              │
│              (如: acorn vi query 00700 --items total_shares) │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    vi_core Plugin                            │
│  1. 解析请求字段 (requested_fields)                          │
│  2. 获取标准字段列表 (standard_fields)                        │
│  3. 获取 Provider 支持字段 (provider_fields)                  │
│  4. 检测缺失字段:                                             │
│     - unsupported: 请求了但不是标准字段                       │
│     - unfilled: 是标准字段但 Provider 不支持                  │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
┌─────────────────────────┐      ┌─────────────────────────────┐
│   字段可用，正常查询      │      │   字段缺失，触发事件          │
│                         │      │                             │
│   返回财务数据           │      │   EVO_CAPABILITY_MISSING    │
│                         │      │   事件发布到 EventBus        │
└─────────────────────────┘      └─────────────────────────────┘
                                              │
                                              ▼
                              ┌───────────────────────────────┐
                              │      EvoManager Plugin         │
                              │  订阅 EVO_CAPABILITY_MISSING   │
                              │  记录能力缺失到内存队列         │
                              └───────────────────────────────┘
```

## 当前实现状态

### ✅ 已实现功能

1. **字段定义系统**
   - 标准字段定义在 `vi_fields_extension.standard_fields`
   - 共 118 个标准字段，包括 `total_shares` (总股本)
   - 字段分类：财务数据、指标数据、市场数据

2. **Provider 系统**
   - A 股 Provider: `provider_market_a` (支持 84 个字段)
   - 港股 Provider: `provider_market_hk` (支持约 70+ 字段)
   - 美股 Provider: `provider_market_us`

3. **能力缺失检测**
   - 代码位置: `vi_core/plugin.py::_query()` 方法
   - 检测逻辑:
     ```python
     unsupported = requested_fields - standard_fields  # 非标准字段
     unfilled = requested_fields & (standard_fields - provider_fields)  # 标准但无Provider支持
     ```

4. **事件发布机制**
   - 事件类型: `AcornEvents.EVO_CAPABILITY_MISSING`
   - 事件内容: capability_type, name, context

5. **EvoManager 订阅处理**
   - 位置: `acorn_core/plugins/evo_manager.py`
   - 功能: 接收事件并记录到 `capability_missing` 队列
   - 提供 `capabilities` 命令查看缺失记录

### ❌ 发现的问题

#### 问题 1: Provider 字段聚合导致无法检测缺失

**现象**: 查询港股 `total_shares` 时，系统没有记录能力缺失。

**原因**: 
- `provider_fields` 是**所有** Provider 支持字段的并集
- A 股 Provider 支持 `total_shares`，所以该字段被认为"有 Provider 支持"
- 但实际上港股 Provider 不支持此字段

**代码位置**: `vi_core/plugin.py:458-461`
```python
provider_fields: set[str] = set()
for result in self._get_plugin_manager().hook.vi_supported_fields():
    if result:
        provider_fields.update(result)  # 合并所有 Provider 的字段
```

**影响**: 
- 无法准确检测某个市场的字段缺失
- 自我进化触发条件失效

#### 问题 2: 字段缺失后没有触发进化流程

**现象**: 即使检测到 `unfilled` 字段，也没有后续动作。

**代码分析**: 
- 当前只发布了事件，但没有自动触发扩展流程
- 需要实现: 事件监听 → 生成扩展 Prompt → 调用 LLM → 创建补丁

#### 问题 3: 港股 Provider 缺少 `total_shares` 映射

**现象**: AKShare 港股 API 可能提供总股本数据，但未在 `FIELD_MAPPINGS` 中映射。

**需要**: 检查 AKShare API 并添加字段映射。

## 测试记录

### 测试 1: 查询缺失字段

```bash
$ acorn vi query 00700 --items total_shares --years 1
```

**结果**: 
- 返回成功，但数据为空
- 没有触发能力缺失记录
- `capability_missing: 0 条记录`

**分析**: 由于问题 1，系统认为 `total_shares` 有 Provider 支持（A 股 Provider），所以不认为是缺失字段。

### 测试 2: 检查 Provider 字段覆盖

```python
标准字段总数: 118
total_shares 是标准字段: True

Provider 支持字段总数: 115  (所有 Provider 的并集)
total_shares 在 provider 中: True  (因为 A 股 Provider 支持)

实际港股 Provider 支持: False  (但代码没有按市场过滤)
```

## 修复建议

### 方案 1: 按市场过滤 Provider 字段 (推荐)

修改 `vi_core/plugin.py` 中的字段检测逻辑：

```python
# 当前: 获取所有 Provider 的字段并集
provider_fields: set[str] = set()
for result in self._get_plugin_manager().hook.vi_supported_fields():
    if result:
        provider_fields.update(result)

# 修复: 只获取目标市场的 Provider 字段
market = self._infer_market(symbol)
provider_fields: set[str] = set()
for result in self._get_plugin_manager().hook.vi_provide_items(
    items=list(standard_fields),  # 请求所有标准字段
    symbol=symbol,
    market=market,
    end_year=end_year,
    years=0,  # 只检查支持性，不获取数据
):
    if result is not None:
        provider_fields.update(result.columns)
```

### 方案 2: 添加市场感知字段检测

为每个 Provider 添加市场标识：

```python
# 在检测缺失时，检查该市场的 Provider 是否支持
market = self._infer_market(symbol)
market_provider_fields = set()
for plugin in pm.get_plugins():
    if hasattr(plugin, 'vi_markets'):
        markets = plugin.vi_markets()
        if market in markets and hasattr(plugin, 'vi_supported_fields'):
            market_provider_fields.update(plugin.vi_supported_fields())

unfilled = requested_fields & (standard_fields - market_provider_fields)
```

### 方案 3: 实现自动扩展流程

1. **事件监听**: EvoManager 订阅 `EVO_CAPABILITY_MISSING`
2. **生成 Prompt**: 根据缺失字段类型生成扩展 Prompt
3. **调用 LLM**: 使用 Prompt 调用 AI 生成代码
4. **沙箱验证**: 验证生成的代码
5. **自动注册**: 将新字段/计算器注册到系统

## 下一步行动

1. **修复字段检测逻辑** (优先级: 高)
   - 修改 `vi_core/plugin.py` 中的 Provider 字段获取逻辑
   - 确保按市场过滤，准确检测缺失字段

2. **补充港股字段映射** (优先级: 中)
   - 检查 AKShare 港股 API 文档
   - 添加 `total_shares` 等缺失字段的映射

3. **实现自动扩展流程** (优先级: 中)
   - 完善 EvoManager 的事件处理
   - 实现 Prompt 生成和 LLM 调用
   - 添加沙箱验证和自动注册

4. **编写测试用例** (优先级: 高)
   - 测试字段缺失检测
   - 测试事件发布和订阅
   - 测试自动扩展流程

## 相关文件

- `value-investment/vi_core/src/vi_core/plugin.py` - 核心查询逻辑
- `value-investment/vi_core/src/vi_core/evolution.py` - 进化相关功能
- `acorn-core/src/acorn_core/plugins/evo_manager.py` - 进化管理器
- `value-investment/provider_market_hk/src/provider_market_hk/provider.py` - 港股数据源
- `value-investment/vi_fields_extension/src/vi_fields_extension/standard_fields.py` - 标准字段定义

---

**文档版本**: 2024-03-25
**测试环境**: acorn-mono 项目本地环境
**Python 版本**: 3.12
