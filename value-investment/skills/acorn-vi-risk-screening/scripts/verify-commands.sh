#!/bin/bash
# 排雷分析常用搜索命令参考
# 使用方法：复制命令到终端执行

# ========== 第一阶段：基础验证 ==========

# 1. 言行一致验证
# 查找历年承诺
rg "將 | 会 | 計劃 | 预计 | 承诺" outputs/{公司}/*_an.txt --context 3

# 查找研发投入承诺
rg "研發 | 研发" outputs/{公司}/*_an.txt --context 5

# 查找股东回报承诺
rg "股息 | 分紅 | 回購 | 股东回报" outputs/{公司}/*_an.txt --context 5

# 查找资本开支承诺
rg "資本開支 | 资本开支 | 投資計劃" outputs/{公司}/*_an.txt --context 5


# 2. 风险提示验证
# 风险因素
rg "風險因素 | 風險" outputs/{公司}/*_an.txt --context 3

# 诉讼/仲裁
rg "訴訟 | 仲裁 | 法律程序" outputs/{公司}/*_an.txt --context 3

# 担保/抵押
rg "擔保 | 抵押 | pledge | guarantee" outputs/{公司}/*_an.txt --context 3

# 关联交易
rg "關聯交易 | 關聯方 | related party" outputs/{公司}/*_an.txt --context 5


# 3. 数据透明验证
# 搜索附注目录
rg "附註 | 附注" outputs/{公司}/*_an.txt --context 2

# 搜索具体指标披露位置
rg "研發開支 | 投資收益 | 員工成本 | 商譽減值" outputs/{公司}/*_an.txt --context 2


# 4. 坦诚度验证
# 坏消息关键词
rg "下降 | 減少 | 虧損 | 下滑 | decline | loss" outputs/{公司}/*_an.txt --context 3

# 对比不同年份篇幅（手动统计）
# 好年份 vs 差年份的管理层讨论页数


# ========== 第二阶段：量化归因 ==========

# 1. 利润波动归因
# 搜索利润相关
rg "利潤 | 盈利 | net profit" outputs/{公司}/*_an.txt --context 5

# 搜索投资收益
rg "投資收益 | 投資虧損 | fair value" outputs/{公司}/*_an.txt --context 5

# 搜索减值
rg "減值 | impairment" outputs/{公司}/*_an.txt --context 5

# 搜索一次性项目
rg "一次性 | 非經常 | 處置" outputs/{公司}/*_an.txt --context 5


# 2. ROE 下降归因
# 搜索权益回报
rg "權益回報|ROE|return on equity" outputs/{公司}/*_an.txt --context 5

# 搜索股东权益
rg "股東權益 | 權益總額 | shareholders' equity" outputs/{公司}/*_an.txt --context 3


# 3. 现金流异常归因
# 搜索现金流
rg "現金流 | cash flow | 經營活動" outputs/{公司}/*_an.txt --context 5

# 搜索应收账款
rg "應收賬款 | 应收账款" outputs/{公司}/*_an.txt --context 3

# 搜索存货
rg "存貨 | 存货 | inventory" outputs/{公司}/*_an.txt --context 3


# ========== 定量数据获取 ==========

# 获取核心财务指标
acorn vi query {股票代码} --items net_profit,total_revenue,operating_cash_flow,roe --years 10

# 获取资产负债指标
acorn vi query {股票代码} --items total_assets,total_liabilities,cash_and_equivalents --years 10

# 获取费用指标
acorn vi query {股票代码} --items operating_expenses,interest_expense --years 10

# 获取周转率指标
acorn vi query {股票代码} --items accounts_receivable,inventory,goodwill --years 10


# ========== 使用示例 ==========

# 腾讯控股排雷分析
# 1. 获取定量数据
acorn vi query 00700 --items net_profit,total_revenue,operating_cash_flow,roe --years 10

# 2. 转换财报（如未转换）
acorn pdf2txt convert downloads/00700_腾讯控股_2024_an.pdf -o outputs/ -c -s

# 3. 搜索管理层承诺
rg "將 | 会 | 計劃" outputs/腾讯控股/*_an.txt --context 3

# 4. 搜索利润波动原因
rg "利潤 | 盈利 | 投資收益" outputs/腾讯控股/*2024*.txt --context 5

# 5. 搜索风险因素
rg "風險" outputs/腾讯控股/*2024*.txt --context 3
