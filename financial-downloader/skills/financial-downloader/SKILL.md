---
name: financial-downloader
description: 统一财报下载器 - 支持 A 股/港股/美股财报下载，TDD 开发，实测验证。触发词：「下载财报」「财报下载器」「financial-downloader」。
---

# Financial Downloader 统一财报下载器

从 A 股/港股/美股市场下载上市公司财报，统一输出到 `~/workspace/acorn-mono/downloads/`。

**项目位置**: `~/workspace/acorn-mono/financial-downloader/`

**技能位置**: `~/.hermes/skills/financial-downloader/`（软链接）

---

## 快速开始

### 下载 A 股财报

```bash
# 下载茅台最近 10 年年报
acorn financial-downloader download 600519 贵州茅台 -m cn -y 10

# 下载指定年份
acorn financial-downloader download 600519 贵州茅台 -m cn --year 2024

# 下载招股书
acorn financial-downloader download 300750 宁德时代 -m cn --type ipo
```

### 下载港股财报

```bash
# 下载腾讯最近 5 年年报
acorn financial-downloader download 00700 腾讯控股 -m hk -y 5

# 下载 ESG 报告
acorn financial-downloader download 00700 腾讯控股 -m hk --type esg -y 5
```

### 下载美股财报

```bash
# 下载携程最近 2 年 20-F
acorn financial-downloader download TCOM Trip.com -m us -y 2 --type 20-F

# 下载苹果 10-K
acorn financial-downloader download AAPL Apple -m us -y 5 --type 10-K
```

### 批量下载

```bash
# 创建配置文件 stocks.yaml
acorn financial-downloader batch stocks.yaml -s  # -s 跳过已下载
```

### 查看支持的文档类型

```bash
acorn financial-downloader list-types -m cn
acorn financial-downloader list-types -m hk
acorn financial-downloader list-types -m us
```

---

## 支持的文档类型

| 市场 | 类型 | 说明 |
|------|------|------|
| **A 股 (cn)** | annual | 年度报告 |
| | ipo | 招股说明书 |
| | listing | 上市公告书 |
| | bond | 债券募集说明书 |
| **港股 (hk)** | annual | 年报 |
| | esg | ESG 报告 |
| | financial | 财务报表 |
| **美股 (us)** | 20-F | 外国发行人年报 |
| | 10-K | 美国公司年报 |
| | 10-Q | 季度报告 |
| | 8-K | 重大事件 |

---

## 文件名格式

统一格式：`{code}_{name}_{year}_{type}.{ext}`

示例：
- `600519_贵州茅台_2024_an.pdf` (A 股)
- `00700_腾讯控股_2024_an.pdf` (港股)
- `TCOM_Trip.com_2024_20F.html` (美股)

---

## 核心实现要点

### 1. A 股下载器 (CninfoDownloader)

**关键点**:
- 使用 `scrapling` 处理反爬
- PDF URL 使用 `static.cninfo.com.cn` 域名
- 设置正确的 Referer 头
- 正则提取年份：`r'(20\d{2})\s*年'`

```python
# URL 修复
pdf_url = f"https://static.cninfo.com.cn/{adjunct_url}"  # 不是 www.cninfo.com.cn

# Referer 头
headers = {
    'Referer': f'https://www.cninfo.com.cn/new/disclosure/stock?stockCode={code}&orgId={org_id}',
    'X-Requested-With': 'XMLHttpRequest'
}
```

### 2. 港股下载器 (HkexDownloader)

**关键点**:
- 通过 `prefix.do` 获取 stockId
- 使用 `t1code=40000` 筛选财务报告类
- 排除 ESG 和中期报告
- 年份验证：财报年份 < 当前年份

```python
# 筛选年报
if any(kw in title for kw in ["ESG", "環境", "中期"]):
    continue
if not any(kw in title for kw in ["年報", "年报", "Annual Report"]):
    continue
```

### 3. 美股下载器 (SecDownloader)

**关键点**:
- 使用 `sec-edgar-downloader` 库
- 固定 `download_details=True` 下载 HTML
- 从 accession number 提取年份：`0001193125-25-078429` → `25` → `2025` → 财报年份 `2024`
- 保留原始扩展名 `.html`

```python
# 年份提取
year_part = accession_num.split('-')[1][:2]  # '25'
filing_year = 2000 + int(year_part)  # 2025
doc_year = filing_year - 1  # 2024 (财报年份)

# 保留扩展名
ext = html_file.suffix.lstrip('.')  # 'html' not '.html'
```

---

## 测试

```bash
# 运行所有测试
uv run pytest tests/ -v

# 运行特定测试
uv run pytest tests/test_cninfo.py -v
uv run pytest tests/test_hkex.py -v
uv run pytest tests/test_sec.py -v
```

**测试结果**: 60 passed, 7 skipped

---

## 常见问题

### Q: A 股下载失败，返回 404

**A**: 检查 PDF URL 是否使用 `static.cninfo.com.cn` 而不是 `www.cninfo.com.cn`

### Q: 美股下载连接超时

**A**: 
1. SEC 有速率限制（10 req/s），库已内置节流
2. 网络问题，稍后重试
3. 使用 CIK 而不是 ticker 可跳过 ticker-to-CIK 查找

### Q: 年份提取错误

**A**: 
- A 股：从标题提取，使用正则 `r'(20\d{2})\s*年'`
- 港股：从标题提取，验证 < 当前年份
- 美股：从 accession number 第二部分提取

### Q: 港股第二上市公司没有年报

**A**: 在港交所第二上市的公司（如携程 09961、阿里巴巴 09988）**不发布完整年报**，只发布业绩公告。完整年报需从主要上市地（如 SEC）获取。

---

## 配置

编辑 `~/.config/financial-downloader/config.toml`:

```toml
[financial_downloader]
output_dir = "/Users/yapex/workspace/acorn-mono/downloads"
sec_user_agent = "YourCompany your@email.com"
cninfo_years_default = 10
hkex_years_default = 10
sec_years_default = 10
```

---

## 项目结构

```
financial-downloader/
├── src/financial_downloader/
│   ├── downloaders/
│   │   ├── base.py            # 抽象基类
│   │   ├── cninfo.py          # A 股下载器
│   │   ├── hkex.py            # 港股下载器
│   │   └── sec.py             # 美股下载器
│   ├── cli.py                 # Typer CLI
│   └── config.py              # 配置管理
├── tests/
│   ├── test_base.py
│   ├── test_cninfo.py
│   ├── test_hkex.py
│   ├── test_sec.py
│   └── test_cli.py
├── skills/financial-downloader/  # 本技能
├── pyproject.toml
└── docs/plans/PROGRESS.md
```

---

## 实测验证

### A 股（茅台）
```
✅ 9 份年报 (2016-2024)
总大小：24.94 MB
```

### 港股（腾讯）
```
✅ 4 份年报 (2022-2025)
总大小：20.37 MB
```

### 美股（携程）
```
✅ 2 份 20-F (2023-2024)
总大小：7.29 MB
```

---

## 踩坑经验

### 1. URL 域名修复

**问题**: 使用 `www.cninfo.com.cn` 下载 PDF 返回 404

**修复**: 使用 `static.cninfo.com.cn`
```python
# 错误
pdf_url = f"{CNINFO_BASE_URL}/{adjunct_url}"

# 正确
pdf_url = f"https://static.cninfo.com.cn/{adjunct_url}"
```

### 2. Referer 头修复

**问题**: API 请求返回空文档

**修复**: 设置正确的 Referer 头
```python
headers = {
    'Referer': f'https://www.cninfo.com.cn/new/disclosure/stock?stockCode={stock_code}&orgId={org_id}',
    'X-Requested-With': 'XMLHttpRequest'
}
```

### 3. 年份提取修复

**问题**: 标题中"年"字重复（如"2024 年年年度报告"）导致匹配失败

**修复**: 使用正则表达式
```python
# 错误
for year in range(2015, current_year + 1):
    if f"{year}年" in clean_title:
        return year

# 正确
import re
match = re.search(r'(20\d{2})\s*年', clean_title)
if match:
    year = int(match.group(1))
    if 2015 <= year <= current_year:
        return year
```

### 4. scrapling 配置

**问题**: scrapling 需要额外依赖

**修复**: 安装完整依赖
```bash
uv add scrapling playwright browserforge
```

---

## 相关技能

- `acorn-value-investment`: 用 `acorn vi` 查询财务数据进行估值分析
- `earnings-call-transcript`: 查找财报电话会议记录
- `html2md`: SEC HTML 转 Markdown 流程
- `pdf2txt`: PDF 转 TXT 转换器

---

## 下一步

1. ✅ 完成核心下载器（A/HK/US）
2. ✅ 完成统一 CLI
3. ✅ 完成测试覆盖
4. ✅ 真实下载验证
5. ✅ 集成到 acorn CLI (`acorn financial-downloader`)
6. ⏳ 添加 PDF 转换功能
7. ⏳ 添加财报数据分析
