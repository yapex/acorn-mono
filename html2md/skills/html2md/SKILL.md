---
name: html2md
description: SEC HTML 转 Markdown 转换器 - 将 SEC iXBRL 格式 HTML 转换为可读 Markdown，适合 LLM 分析。触发词：「HTML 转 Markdown」「html2md」「SEC 转换」「20-F 转换」。
---

# html2md - SEC HTML 转 Markdown 转换器

将 SEC iXBRL 格式的 HTML 文件转换为干净的 Markdown 格式，适合人类阅读和 LLM 分析。

**项目位置**: `~/workspace/acorn-mono/html2md/`

**技能位置**: `~/.hermes/skills/html2md/`（软链接）

---

## 快速开始

### 转换单个文件

```bash
# 基本用法
acorn html2md convert filing.html

# 指定输出目录
acorn html2md convert filing.html -o ./outputs_md

# 按公司组织输出
acorn html2md convert TCOM_携程_2024_an.html -c -o ./outputs_md

# 输出纯文本（LLM 优化）
acorn html2md convert filing.html -p

# 跳过已转换文件
acorn html2md convert filing.html -s
```

### 批量转换

```bash
# 转换目录下所有 HTML
acorn html2md batch ./downloads

# 按公司组织 + 跳过已有
acorn html2md batch ./downloads -o ./outputs_md -c -s

# 递归搜索 + 纯文本输出
acorn html2md batch ./downloads -o ./outputs_md -r -p -c
```

---

## 核心功能

### 1. iXBRL 元数据清理

SEC 20-F 文件是 **iXBRL (Inline XBRL)** 格式，包含大量隐藏的财务元数据标签。

**清理内容**:
- `<ix:header>` - XBRL 元数据头
- `<ix:references>` - XBRL 模式引用
- `<ix:resources>` - XBRL 资源定义
- 所有 `<ix:*>` 标签（保留内容）
- `<script>` 和 `<style>` 标签
- HTML 注释

**效果**:
```
原始 HTML: 3.6 MB (3,803,343 字符)
清理后：2.9 MB (移除 25% XBRL 噪声)
Markdown: 857 KB (17,238 行)
```

### 2. 两种输出模式

| 模式 | 参数 | 用途 | 示例 |
|------|------|------|------|
| Markdown | 默认 | 人类阅读 / Obsidian | `TCOM_携程_2024_an.md` |
| Plain Text | `-p` | LLM 分析 | `TCOM_携程_2024_an.txt` |

### 3. 按公司组织输出

自动从文件名提取公司名，创建子目录：

```
outputs_md/
├── 携程/
│   └── TCOM_携程_2024_an.md
├── 腾讯/
│   └── 00700_腾讯控股_2024_an.md
└── 茅台/
    └── 600519_贵州茅台_2024_an.md
```

**文件名格式要求**: `{code}_{company}_{year}_{type}.html`

---

## 转换质量

### 表格保留

财务报表完整转换为 Markdown 表格：

```markdown
| Net revenues    | 18,316 | 20,023 | 20,039 | 44,510 | 53,294 |
| Gross profit    | 14,285 | 15,425 | 15,526 | 36,389 | 43,304 |
| Total assets    | 187,249| 191,859| 191,691| 219,137| 242,581|
```

### 标题层级

完整保留文档结构：

```markdown
# Form 20-F

## TABLE OF CONTENTS

### PART I.

#### Item 1. IDENTITY OF DIRECTORS, SENIOR MANAGEMENT AND ADVISERS

#### Item 3. KEY INFORMATION
```

### 目录

自动生成带锚点的目录，支持跳转。

---

## 完整工作流

### 1. 下载 SEC 财报

```bash
# 使用 financial-downloader 下载
acorn financial-downloader download 0001269238 携程 -m us -y 5 --type 20-F
```

### 2. 转换为 Markdown

```bash
acorn html2md batch ./downloads -o ./outputs_md -c -s
```

### 3. 阅读/分析

```bash
# 查看转换结果
cat ../outputs_md/携程/TCOM_携程_2024_an.md | head -100

# 或用 Obsidian 打开
open ../outputs_md/携程/TCOM_携程_2024_an.md
```

### 4. 完整财报处理流程

```bash
# A 股：下载 + PDF 转 TXT
acorn financial-downloader download 600519 贵州茅台 -m cn -y 10
acorn pdf2txt batch ./downloads -o ./outputs -c -s

# 港股：下载 + PDF 转 TXT
acorn financial-downloader download 00700 腾讯控股 -m hk -y 5
acorn pdf2txt batch ./downloads -o ./outputs -c -s

# 美股：下载 + HTML 转 Markdown
acorn financial-downloader download TCOM Trip.com -m us -y 5 --type 20-F
acorn html2md batch ./downloads -o ./outputs_md -c -s
```

---

## 测试

```bash
# 运行所有测试
uv run pytest tests/ -v

# 运行特定测试
uv run pytest tests/test_converter.py -v
```

**测试结果**: 11 passed

---

## 项目结构

```
html2md/
├── src/html2md/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py              # Typer CLI
│   └── converter.py        # 转换核心
├── tests/
│   ├── __init__.py
│   └── test_converter.py   # 单元测试
├── skills/html2md/         # 本技能
├── pyproject.toml
└── README.md
```

---

## 技术实现

### 1. BeautifulSoup 清理

```python
from bs4 import BeautifulSoup

soup = BeautifulSoup(content, "lxml")

# 移除 XBRL 头
for tag_name in ["ix:header", "ix:references", "ix:resources"]:
    for header in soup.find_all(tag_name):
        header.decompose()

# 展开 ix 标签
for tag in soup.find_all(lambda t: t.name and t.name.startswith("ix:")):
    tag.unwrap()

# 移除脚本和样式
for tag in soup.find_all(["script", "style"]):
    tag.decompose()
```

### 2. html-to-markdown 转换

```python
from html_to_markdown import convert, ConversionOptions

options = ConversionOptions(
    extract_metadata=False,
    heading_style="atx",
    wrap=True,
    wrap_width=120,
)

if plain_text:
    options.output_format = "plain"

result = convert(clean_html, options)
```

### 3. 性能表现

| 文件大小 | 转换时间 |
|---------|---------|
| 3.6 MB HTML | ~1-2 秒 |
| 输出 857 KB MD | |

---

## 常见问题

### Q: 为什么转换后的 Markdown 有很多空白行？

**A**: SEC HTML 本身包含大量格式化空白，转换后会保留结构。可以用以下命令压缩：

```bash
# 移除连续空行
cat filing.md | grep -v '^$' > filing_compact.md
```

### Q: 表格转换不完整怎么办？

**A**: 检查原始 HTML 是否包含复杂的嵌套表格。html-to-markdown 支持标准 Markdown 表格，但极度复杂的表格可能需要手动调整。

### Q: 如何批量转换多个公司的财报？

**A**: 使用 `batch` 命令配合 `-c` 参数：

```bash
uv run python -m html2md batch ./downloads -o ./outputs_md -c -s
```

会自动按公司名组织输出目录。

---

## 相关技能

- `financial-downloader`: 统一财报下载器（A/HK/US）
- `sec-edgar-downloader`: SEC EDGAR 下载工具
- `pdf2txt`: PDF 转 TXT 转换器

---

## Acorn CLI 集成

### 1. 添加 entry-point

编辑 `pyproject.toml`:

```toml
[project.entry-points."acorn.cli.commands"]
html2md = "html2md.cli:app"
```

### 2. 重新安装包

```bash
cd ~/workspace/acorn-mono/html2md
uv sync
```

### 3. 验证注册

```bash
acorn --help  # 应该显示 html2md 命令
acorn html2md --help
```

### 4. 使用 acorn 命令

```bash
# 转换单个文件
acorn html2md convert filing.html -o ./outputs_md -c

# 批量转换
acorn html2md batch ./downloads -o ./outputs_md -c -s
```

---

## 技术选型经验

### 为什么选择 html-to-markdown？

对比了两个库：

| 特性 | html-to-markdown | markdownify |
|------|-----------------|-------------|
| 实现 | Rust 核心 + Python 绑定 | 纯 Python |
| 性能 | **150-280 MB/s** | ~2 MB/s |
| 大文件处理 | ✅ 50ms 处理 10MB | ❌ 5 秒+ |
| 表格支持 | ✅ 结构化提取 | ✅ 标准表格 |
| Plain 模式 | ✅ 内置 | ❌ |

**结论**: SEC 20-F 文件通常 3-10MB，html-to-markdown 快 **100 倍**，必选。

### 为什么需要 BeautifulSoup 预处理？

SEC iXBRL 文件特点：
- 95% 内容是隐藏的 XBRL 元数据
- `<ix:header>`、`<ix:resources>` 等标签包含数千个财务指标
- 直接转换会产生大量噪声

**预处理效果**:
```
原始 HTML:    3.6 MB (含 XBRL 元数据)
清理后 HTML:  2.9 MB (移除 25% 噪声)
Markdown:     857 KB (干净内容)
```

---

## 下一步

1. ✅ 完成核心转换器
2. ✅ 完成 CLI（convert + batch）
3. ✅ 完成测试覆盖（11 tests）
4. ✅ 真实文件验证（携程 20-F）
5. ✅ 集成到 acorn CLI (`acorn html2md`)
6. ⏳ 添加批量下载 + 转换工作流
7. ⏳ 添加 Markdown 后处理（目录优化、表格压缩）
