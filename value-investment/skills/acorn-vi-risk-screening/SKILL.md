---
name: acorn-vi-risk-screening
description: 企业财务排雷系统 — 排雷（造假）+ 排险（生存）+ 排优（长期价值）三位一体分析。触发词：「排雷」「财务排雷」「排险」「排优」「风险筛查」「造假检测」「排雷手册」「排雷书册」。
---

# 企业财务排雷系统 🔍

**定位**：排雷工具，不是选股工具。排除有问题的公司，不保证没问题的公司就是好公司。
**原则**：定量为主（≥90%），定性为辅；基于历史数据，不做预测。

---

## ⚠️ 强制数据溯源规则

**严禁用自身知识或估算数据填充报告。所有数字必须来自真实数据源。**

| 规则 | 说明 |
|------|------|
| 禁止估算 | 不得用"大约"、"约XX亿"、"行业平均"等模糊数据 |
| 禁止记忆数据 | 不得使用模型训练数据中的财务数字 |
| 禁止推理数据 | 不得用趋势推断或比率反推出来的数字 |
| 数据缺失处理 | 缺失数据必须标注 🟡，不得自行填补 |

---

## 📋 各市场数据限制一览

### A股（Tushare）

| 字段 | 数据限制 | 替代方案 |
|------|---------|---------|
| accounts_receivable | 仅覆盖 2022-2024，2016-2021 为 N/A | 手动查阅年报 |
| audit_opinion | 不提供 | 手动查阅年报「审计意见」章节 |
| related_party_transactions | 不提供 | 手动查阅年报「关联交易」章节 |
| goodwill_impairment | 不提供 | 手动查阅年报「商誉减值」章节 |

### 港股（AKShare）

| 字段 | 数据限制 | 替代方案 |
|------|---------|---------|
| interest_expense | 无单独字段，仅有「融资成本」(finance_cost) | 已映射融资成本→interest_expense，使用时注明 |
| related_party_transactions | 部分公司（如腾讯）不单独披露关联方数据 | 手动查阅年报「关联交易」章节 |
| goodwill_impairment | 无单独字段，仅有综合「减值及拨备」 | 手动查阅年报「商誉减值」章节 |
| audit_opinion | 不提供 | 手动查阅年报「审计师报告」章节 |
| roe | 部分公司仅有近3-5年数据 | 使用 net_profit / total_equity 手动计算 |
| capital_expenditure | 部分年份可能为空（公司未披露） | 手动查阅年报「资本开支」章节 |

### 美股（AKShare/东方财富）

| 字段 | 数据限制 | 替代方案 |
|------|---------|---------|
| interest_expense | 不提供 | 手动查阅年报「合并财务报告」附注 |
| interest_income | ✅ 提供 | 已映射到 interest_income |
| related_party_transactions | ❌ 不提供 | 手动查阅年报「关联交易」章节 |
| goodwill | ✅ 提供 | 已映射到 goodwill |
| goodwill_impairment | ⚠️ 无单独字段，仅有综合「减值及拨备」 | 手动查阅年报「商誉减值」章节 |
| prepayments | ❌ 不提供 | 手动查阅年报「预付款」附注 |
| construction_in_progress | ❌ 不提供（有物业厂房及设备） | 可用 PP&E 代替 |
| audit_opinion | ❌ 不提供 | 手动查阅年报「审计师报告」章节 |

**注**：美股财报结构与A股/港股不同，利息支出通常不单独披露。

---

## 🚀 Quick Start

### Step 1: 获取数据

```bash
acorn vi query {股票代码} \
  --items net_profit,total_revenue,total_assets,total_equity,operating_cash_flow,gross_profit,operating_profit,total_liabilities,cash_and_equivalents,interest_bearing_debt,current_assets,current_liabilities,interest_expense,capital_expenditure,inventory,accounts_receivable,roe,goodwill,construction_in_progress \
  --years 10
```

> 报错 `[ERROR] unknown error` → 去掉部分字段逐批尝试 | 全部报错 → 停止生成报告

### Step 2: 创建报告文件

路径：`~/Documents/Obsidian/yapex_ob/股票分析/{公司名}/排雷报告-{日期}.md`

### Step 3: 执行分析

按顺序完成十段，详见下方检查清单和 `references/segments/` 目录。

---

## ⚡ 并行执行优化（可选）

第 2-7 段互相独立，可以：

| 模式 | 说明 |
|------|------|
| 串行 | 一段完成后执行下一段（简单可靠） |
| 并行 | 用子 Agent 同时执行多段 |

**并行示例**：
1. 主 Agent 获取核心数据（第一段）
2. 主 Agent 启动子 Agent：
   - Agent A：偿债能力 + 特殊项目（2 + 7）
   - Agent B：造假检测（组合信号 + 极值）（3 + 4）
   - Agent C：长期价值 + 时间序列（5 + 6）
3. 主 Agent 汇总结果，执行综合判定 + 结论（8 + 9）

---

## 十段检查清单

### [ ] 第一段：核心数据展示
输出5-10年核心财务指标。详见 [01-core-data.md](references/segments/01-core-data.md)

### [ ] 第二段：偿债能力（排险）
检查：现金比率/速动比率/流动比率 + 资产负债率/净负债率/利息保障倍数 + 现金流覆盖
详见 [02-solvency.md](references/segments/02-solvency.md)

### [ ] 第三段：组合信号（排雷）— C01-C10
捕捉：现金流与利润背离、存货/应收与营收背离、货币资金虚增等造假模式
详见 [03-combined-signals.md](references/segments/03-combined-signals.md)

### [ ] 第四段：单字段极值（排雷）— P0/P1/P2
捕捉：应收账款超标、存货超标、毛利率突变等极端信号
详见 [04-extreme-values.md](references/segments/04-extreme-values.md)

### [ ] 第五段：长期价值（排优）
评分：增长性(25%) + 稳定性(35%) + 可理解性(20%) + 穿越周期(20%)
详见 [05-long-term-value.md](references/segments/05-long-term-value.md)

### [ ] 第六段：时间序列分析
逐年追踪核心指标，标记连续异常年份
详见 [06-time-series.md](references/segments/06-time-series.md)

### [ ] 第七段：特殊项目
检查：审计意见、股东回报、资本开支、减值拨备
详见 [07-special-items.md](references/segments/07-special-items.md)

### [ ] 第八段：综合判定 ❌ 依赖前置
基于 2-7 段结果，输出六维风险判定
详见 [08-verdict.md](references/segments/08-verdict.md)

### [ ] 第九段：结论与建议 ❌ 依赖前置
整体判定 + 核心优势 + 风险点 + 数据缺失清单
详见 [09-conclusion.md](references/segments/09-conclusion.md)

### [ ] 第十段：局限性说明
数据年限 | 数据完整性 | 行业特殊性 + 数据缺失清单
详见 [10-limitations.md](references/segments/10-limitations.md)

---

## 快速判定规则

```
1. 造假风险 🔴？ → 是 → ❌ 直接排除
2. 生存风险 🔴？ → 是 → ❌ 直接排除
3. 造假✅ + 生存✅ + 价值≥80？ → 是 → 🟢 适合长期持有
4. 造假✅ + 生存✅ + 价值60-79？ → 是 → 🟡 可关注
5. 其他 → ⚠️ 不适合长期持有
```

---

## ⚠️ 服务健康检查

```bash
# 检查服务状态
/Users/yapex/workspace/acorn-mono/.venv/bin/acorn status

# 预期：✅ vi 插件已加载 + 🌰 服务已启动
```

**重启服务**：
```bash
pkill -f acorn-agent
cd /Users/yapex/workspace/acorn-mono && .venv/bin/acorn status
```

---

## 详细参考

```
references/
├── segments/
│   ├── 01-core-data.md         # 第一段：核心数据展示
│   ├── 02-solvency.md          # 第二段：偿债能力分析
│   ├── 03-combined-signals.md  # 第三段：组合信号排查
│   ├── 04-extreme-values.md    # 第四段：单字段极值排查
│   ├── 05-long-term-value.md   # 第五段：长期价值分析
│   ├── 06-time-series.md       # 第六段：时间序列分析
│   ├── 07-special-items.md     # 第七段：特殊项目分析
│   ├── 08-verdict.md           # 第八段：综合判定
│   ├── 09-conclusion.md        # 第九段：结论与建议
│   └── 10-limitations.md       # 第十段：局限性说明
```

每段文件包含：需要的数据/计算公式 → 展示样例 → 核查结果 → 输出格式
