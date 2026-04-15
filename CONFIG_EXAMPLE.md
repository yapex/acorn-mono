# Acorn 配置指南

## 配置文件位置

```
~/.config/acorn/config.toml
```

符合 XDG Base Directory 规范。

## 快速开始

### 1. 创建配置文件

```bash
mkdir -p ~/.config/acorn
cat > ~/.config/acorn/config.toml << 'EOF'
# Acorn 个人配置

[vi.query]
years = 20
wacc = 0.10
g_terminal = 0.03

[pdf2txt.batch]
output_dir = "./financial_reports"
organize_by_company = true
skip_existing = true
EOF
```

### 2. 验证配置

```bash
acorn vi query 600519
# 自动使用配置的 20 年、10% WACC、3% 永续增长率
```

## 配置项说明

### vi.query - 价值投资查询

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| years | int | 10 | 查询年数 |
| wacc | float | 0.08 | DCF 折现率 |
| g_terminal | float | 0.03 | 永续增长率 |

**示例**：
```toml
[vi.query]
years = 20       # 分析 20 年数据
wacc = 0.10      # 使用 10% 折现率（更保守）
g_terminal = 0.03  # 3% 永续增长
```

### pdf2txt.batch - PDF 批量转换

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| output_dir | Path | null | 输出目录 |
| organize_by_company | bool | false | 按公司组织输出 |
| skip_existing | bool | false | 跳过已转换文件 |

**示例**：
```toml
[pdf2txt.batch]
output_dir = "./financial_reports"  # 输出到指定目录
organize_by_company = true          # 按公司名分类
skip_existing = true                # 避免重复转换
```

## 使用场景

### 场景 1: 保守型投资者

```toml
[vi.query]
years = 20      # 长期分析
wacc = 0.12     # 高折现率（更安全边际）
g_terminal = 0.02  # 低永续增长
```

### 场景 2: 成长型投资者

```toml
[vi.query]
years = 10      # 中期分析
wacc = 0.08     # 标准折现率
g_terminal = 0.05  # 较高永续增长
```

### 场景 3: PDF 管理工作流

```toml
[pdf2txt.batch]
output_dir = "~/Documents/财报库"
organize_by_company = true
skip_existing = true
```

使用：
```bash
# 简化命令，自动使用配置
acorn pdf2txt batch ~/Downloads

# 等价于
acorn pdf2txt batch ~/Downloads \
  -o ~/Documents/财报库 \
  -c \
  -s
```

## 优先级

配置优先级从高到低：

1. **命令行参数** - 临时覆盖
   ```bash
   acorn vi query 600519 --years 5  # 临时使用 5 年
   ```

2. **配置文件** - 个人偏好
   ```toml
   # ~/.config/acorn/config.toml
   [vi.query]
   years = 20
   ```

3. **代码默认值** - 兜底
   ```python
   years: int = 10  # 默认 10 年
   ```

## 配置模板

### 模板 1: 价值投资入门

```toml
# 适合初学者，使用标准假设
[vi.query]
years = 10
wacc = 0.08
g_terminal = 0.03
```

### 模板 2: 保守分析

```toml
# 保守估计，强调安全边际
[vi.query]
years = 20
wacc = 0.12
g_terminal = 0.02
```

### 模板 3: 专业分析师

```toml
# 深度分析，完整工作流
[vi.query]
years = 20
wacc = 0.10
g_terminal = 0.03

[pdf2txt.batch]
output_dir = "./reports"
organize_by_company = true
skip_existing = true
```

## 常见问题

### Q: 配置不生效？

A: 检查配置文件位置：
```bash
# 查看配置路径
python -c "from acorn_core import get_user_config_path; print(get_user_config_path())"

# 检查文件是否存在
ls -la ~/.config/acorn/config.toml
```

### Q: 如何重置配置？

A: 删除或重命名配置文件：
```bash
mv ~/.config/acorn/config.toml ~/.config/acorn/config.toml.backup
```

### Q: 不同项目需要不同配置？

A: 使用命令行参数临时覆盖：
```bash
# 项目 A 使用 20 年
acorn vi query AAPL

# 项目 B 使用 5 年
acorn vi query AAPL --years 5
```

## 备份配置

```bash
# 备份
cp ~/.config/acorn/config.toml ~/.config/acorn/config.toml.backup

# 恢复
cp ~/.config/acorn/config.toml.backup ~/.config/acorn/config.toml
```
