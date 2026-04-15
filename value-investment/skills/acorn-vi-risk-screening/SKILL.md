---
name: acorn-vi-risk-screening
description: 企业财务排雷系统 — 定量排雷（C01-C10+P0-P2）+ 定性验证（言行一致 + 坦诚度）+ 量化归因。触发词：「排雷」「财务排雷」「排险」「排优」「风险筛查」「造假检测」。
---

# 企业财务排雷系统 🔍

**定位**：排雷工具，不是选股工具。排除有问题的公司，不保证没问题的公司就是好公司。

**数据来源**（仅两个）：
1. **定量**：`acorn vi query` API
2. **定性**：pdf2txt 转换的财报原文

**❌ 禁止**：联网搜索、记忆数据、主观猜测、外部知识填充

---

## 快速开始

```bash
# Step 1: 获取定量数据
acorn vi query {股票代码} \
  --items net_profit,total_revenue,operating_cash_flow,total_assets,total_liabilities,\
cash_and_equivalents,interest_bearing_debt,current_assets,current_liabilities,\
interest_expense,capital_expenditure,inventory,accounts_receivable,roe,goodwill \
  --years 10

# Step 2: 转换财报（如未转换）
acorn pdf2txt convert {PDF 文件} -o outputs/ -c -s

# Step 3: 搜索财报原文
rg "关键词" outputs/{公司}/*{年份}*.txt --context 5
```

---

## 十段检查清单

### [ ] 第一段：核心数据展示
输出 5-10 年核心财务指标。详见 [references/segments/01-core-data.md](references/segments/01-core-data.md)

### [ ] 第二段：偿债能力（排险）
检查：现金比率/速动比率/流动比率 + 资产负债率/净负债率/利息保障倍数 + 现金流覆盖
详见 [references/segments/02-solvency.md](references/segments/02-solvency.md)

### [ ] 第三段：组合信号（排雷）— C01-C10
捕捉：现金流与利润背离、存货/应收与营收背离、货币资金虚增等造假模式
详见 [references/segments/03-combined-signals.md](references/segments/03-combined-signals.md)

### [ ] 第四段：单字段极值（排雷）— P0/P1/P2
捕捉：应收账款超标、存货超标、毛利率突变等极端信号
详见 [references/segments/04-extreme-values.md](references/segments/04-extreme-values.md)

### [ ] 第五段：长期价值（排优）
评分：增长性 (25%) + 稳定性 (35%) + 可理解性 (20%) + 穿越周期 (20%)
详见 [references/segments/05-long-term-value.md](references/segments/05-long-term-value.md)

### [ ] 第六段：时间序列分析
逐年追踪核心指标，标记连续异常年份
详见 [references/segments/06-time-series.md](references/segments/06-time-series.md)

### [ ] 第七段：特殊项目 + 定性验证
检查：审计意见、股东回报、资本开支、减值拨备 + **言行一致验证** + **管理层坦诚度**
详见 [references/segments/07-special-items.md](references/segments/07-special-items.md)
新增：[references/phase1-checklist.md](references/phase1-checklist.md)

### [ ] 第八段：综合判定 ❌ 依赖前置
基于 2-7 段结果，输出六维风险判定 + **量化归因分析**
详见 [references/segments/08-verdict.md](references/segments/08-verdict.md)
新增：[references/phase2-attribution.md](references/phase2-attribution.md)

### [ ] 第九段：结论与建议 ❌ 依赖前置
整体判定 + 核心优势 + 风险点 + 数据缺失清单
详见 [references/segments/09-conclusion.md](references/segments/09-conclusion.md)

### [ ] 第十段：局限性说明
数据年限 | 数据完整性 | 行业特殊性 + 数据缺失清单
详见 [references/segments/10-limitations.md](references/segments/10-limitations.md)

---

## 新增增强功能

### 第一阶段：基础验证（第七段增强）

| 验证维度 | 检查内容 | 通过标准 |
|----------|----------|----------|
| 言行一致 | 承诺 vs 执行 | 兑现率≥70% |
| 风险提示 | 重大风险披露 | 覆盖主要风险 |
| 数据透明 | 关键指标披露 | ≥70% 单独披露 |
| 坦诚度 | 坏消息披露 + 归因清晰 | 评分≥0.6 |

详见 [references/phase1-checklist.md](references/phase1-checklist.md)

### 第二阶段：量化归因（第八段增强）

**五步法**：
```
1. 量化异常 → 2. 识别原因 → 3. 原文摘录 → 4. 量化验证 → 5. 归因分析
```

**核心公式**：
```
异常变化总额 = 原因 1 贡献 + 原因 2 贡献 + ... + 无法解释部分
贡献比例 = 贡献额 / 变化总额 × 100%
```

详见 [references/phase2-attribution.md](references/phase2-attribution.md)

---

## 快速判定规则

```
1. 造假风险 🔴？ → 是 → ❌ 直接排除
2. 生存风险 🔴？ → 是 → ❌ 直接排除
3. 造假✅ + 生存✅ + 价值≥80？ → 是 → 🟢 适合长期持有
4. 造假✅ + 生存✅ + 价值 60-79？ → 是 → 🟡 可关注
5. 其他 → ⚠️ 不适合长期持有
```

---

## 核心原则

> 每一个异常都要找到管理层解释，每一个解释都要用数据验证，无法验证的部分要明确标注比例。

**AI 角色**：研究助理（搜集、整理、验证、量化归因）  
**用户角色**：决策者（审核、判断、决策）
