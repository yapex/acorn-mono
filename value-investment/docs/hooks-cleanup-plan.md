# Hooks 清理计划

> 文档目的：识别并清理不再使用或冗余的 Hook 扩展点和文件

## 更新日志

- **2026-03-25**: 删除 `vi_core/cli.py`（冗余的 RPC 包装层）

## 1. 已移除的文件

### 1.1 `vi_core/cli.py` ✅ 已移除

**状态：** 已删除（2026-03-25）

**问题：**
- 冗余的 RPC 包装层：`acorn vi query` → `vi_core/cli.py` → RPC → `acorn-agent` → `vi_core/plugin.py`
- 输出简陋：只是打印 JSON，没有格式化
- 功能完全可通过 Python API 替代

**删除理由：**
1. 增加不必要的复杂性（RPC 调用层）
2. 维护成本高（需要保持与 plugin.py 同步）
3. 用户可以直接使用 Python API

**替代方案：**
```python
from acorn_cli.client import AcornClient
client = AcornClient()
result = client.execute("vi_query", {"symbol": "600519", "items": "revenue,net_profit"})
```

---

## 2. 建议移除的 Hooks

### 2.1 `vi_fetch_historical` ⚠️ 建议移除

**状态：** 从未被调用

**问题：**
- Hook 在 `spec.py` 中定义，但没有任何地方通过 `hook.vi_fetch_historical` 调用
- `fetch_historical` 功能通过 `BaseDataProvider.fetch_historical()` 模板方法实现
- Provider 的 plugin.py 中实现了 `vi_fetch_historical` 但从未被使用

**代码证据：**
```bash
# 没有任何地方调用 hook.vi_fetch_historical
grep -r "hook.vi_fetch_historical" value-investment/  # 无结果
```

**影响分析：**
- ✅ 移除安全：该 hook 从未被调用
- ⚠️ 需要确认：是否有外部插件依赖此 hook

**清理步骤：**
1. 从 `FieldProviderSpec` 移除 `vi_fetch_historical` hook spec
2. 从 Provider plugins 移除 `vi_fetch_historical` 实现（保留 `fetch_historical` 方法）
3. 更新文档说明 OHLCV 数据获取方式

**替代方案：**
- 继续使用 `BaseDataProvider.fetch_historical()` 方法
- 如需通过 hook 调用，可在未来重新添加

---

## 3. 用途有限的 Hooks

### 3.1 `vi_markets` ℹ️ 保留但标注用途

**状态：** 仅用于 status 收集

**问题：**
- 该 hook 用于返回 Provider 支持的市场列表
- 但实际的市场过滤在 `vi_provide_items` 内部通过 `market != "XX"` 判断实现
- `plugin.py` 的 fallback 机制也不使用这个 hook

**当前用途：**
```python
# 仅在 vi_status 中用于收集 providers 列表
for market_result in pm.hook.vi_markets():
    if market_result:
        status["capabilities"]["providers"].extend(market_result)
```

**建议：**
- 保留（用于 status 收集）
- 在文档中标注为"元数据 hook"

---

### 3.2 Calculator 动态管理 Hooks ℹ️ 保留但标注为高级功能

**Hooks：**
- `vi_register_calculator` - 动态注册计算器
- `vi_unregister_calculator` - 卸载计算器
- `vi_reload_calculator` - 重新加载计算器

**状态：** 有实现，主要在测试中使用

**当前用途：**
- `vi_register_calculator` - 在 `plugin.py._register_calculator` 命令中使用
- `vi_unregister_calculator` - 测试中使用
- `vi_reload_calculator` - 测试中使用

**建议：**
- 保留（已有完整实现和测试）
- 在文档中标注为"高级功能，生产环境使用频率低"

---

## 4. 保留的 Hooks（核心功能）

### 3.1 Field Registry
- ✅ `vi_fields` - 字段注册，核心功能

### 3.2 Field Provider（核心）
- ✅ `vi_supported_fields` - 获取 Provider 支持的字段列表
- ✅ `vi_provide_items` - **新架构核心**，统一字段获取接口
- ✅ `vi_fetch_financials` - Fallback 机制使用
- ✅ `vi_fetch_indicators` - Fallback 机制使用
- ✅ `vi_fetch_market` - Fallback 机制使用

### 3.3 Calculator
- ✅ `vi_list_calculators` - 列出计算器
- ✅ `vi_run_calculator` - 运行计算器

### 3.4 Command Handler
- ✅ `vi_commands` - 命令列表
- ✅ `vi_handle` - 命令处理

### 3.5 Status
- ✅ `vi_status` - 状态报告

### 3.6 Evolution
- ✅ `get_evolution_spec` - 进化机制

---

## 5. 清理优先级

| 优先级 | 项目 | 操作 | 风险 | 状态 |
|--------|------|------|------|------|
| ✅ 完成 | `vi_core/cli.py` | 删除 | 无 | 已删除 |
| 🔴 高 | `vi_fetch_historical` | 移除 | 低（从未使用） | 待处理 |
| 🟡 中 | `vi_markets` | 标注用途 | 无 | 待处理 |
| 🟢 低 | Calculator 动态管理 | 标注为高级功能 | 无 | 待处理 |

---

## 6. 执行计划

### Phase 0: ✅ 已完成 - 移除 `vi_core/cli.py`
1. ✅ 从 `pyproject.toml` 注释 entry point
2. ✅ 删除 `cli.py` 文件
3. ✅ 更新 README.md 说明使用 Python API
4. ✅ 更新 vi_core/README.md

### Phase 1: 移除 `vi_fetch_historical`
1. 从 `spec.py` 移除 hook spec
2. 从 Provider plugins 移除实现
3. 更新文档
4. 运行测试确保无影响

### Phase 2: 文档更新
1. 标注 `vi_markets` 为元数据 hook
2. 标注 Calculator 动态管理为高级功能
3. 更新架构文档说明 hook 使用场景

---

## 7. 决策记录

### 2026-03-25

**决策：**
- ✅ 删除 `vi_core/cli.py`（冗余的 RPC 包装层）
- 待处理：移除 `vi_fetch_historical` hook（从未使用）
- 待处理：保留其他 hooks 但标注用途

**理由：**
- 减少 API 表面面积
- 避免混淆（未使用的扩展点）
- 保持向后兼容（fallback hooks 保留）
- 简化架构（减少不必要的 RPC 层）
