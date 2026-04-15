# 统一配置方案设计

## 现状问题

目前各个子项目的 CLI 默认值都硬编码在代码中：
- `pdf2txt`: `organize_by_company=False`, `skip_existing=False`
- `vi_cli`: `years=10`, `wacc=0.08`, `g_terminal=0.03`

**问题**：
1. 用户每次都要输入相同的参数
2. 不同用户有不同的偏好（如有人默认看 5 年，有人看 10 年）
3. 修改默认值需要改代码

---

## 设计方案

### 方案 A: 分层配置（推荐）

```
┌─────────────────────────────────────────┐
│  命令行参数 (最高优先级)                  │
│  acorn vi query 600519 --years 20       │
└─────────────────────────────────────────┘
              ↓ 覆盖
┌─────────────────────────────────────────┐
│  用户配置文件 ~/.acorn/config.toml      │
│  [vi.query]                             │
│  years = 20                             │
│  wacc = 0.10                            │
└─────────────────────────────────────────┘
              ↓ 覆盖
┌─────────────────────────────────────────┐
│  项目配置 pyproject.toml                │
│  [tool.acorn.vi.query]                  │
│  years = 10                             │
└─────────────────────────────────────────┘
              ↓ 覆盖
┌─────────────────────────────────────────┐
│  代码默认值 (最低优先级)                 │
│  years: int = 10                        │
└─────────────────────────────────────────┘
```

**优点**：
- 灵活：个人偏好、项目配置、临时覆盖互不冲突
- 向后兼容：没有配置时用代码默认值
- 清晰：优先级明确

---

### 配置文件格式

#### 1. 全局配置 `~/.acorn/config.toml`

```toml
# 全局默认配置

[vi.query]
years = 20
wacc = 0.10
g_terminal = 0.03

[pdf2txt.batch]
output_dir = "./outputs"
organize_by_company = true
skip_existing = true
```

#### 2. 项目配置 `.acorn.toml` (项目根目录)

```toml
# 项目特定配置

[vi.query]
years = 10  # 本项目默认看 10 年

[pdf2txt.batch]
output_dir = "./financial_reports/txt"
```

---

## 实现架构

### 配置加载器

```python
# acorn-core/src/acorn_core/config.py

from pathlib import Path
import tomllib
from dataclasses import dataclass, field

@dataclass
class ViQueryConfig:
    years: int = 10
    wacc: float = 0.08
    g_terminal: float = 0.03

@dataclass
class Pdf2txtBatchConfig:
    output_dir: Path | None = None
    organize_by_company: bool = False
    skip_existing: bool = False

@dataclass
class AcornConfig:
    vi_query: ViQueryConfig = field(default_factory=ViQueryConfig)
    pdf2txt_batch: Pdf2txtBatchConfig = field(default_factory=Pdf2txtBatchConfig)
    
    @classmethod
    def load(cls) -> "AcornConfig":
        """加载配置，按优先级合并"""
        config = cls()
        
        # 1. 加载项目配置
        project_config = Path.cwd() / ".acorn.toml"
        if project_config.exists():
            config._merge_from_file(project_config)
        
        # 2. 加载用户配置 (覆盖项目配置)
        user_config = Path.home() / ".acorn" / "config.toml"
        if user_config.exists():
            config._merge_from_file(user_config)
        
        return config
    
    def _merge_from_file(self, path: Path):
        """从 TOML 文件合并配置"""
        with open(path, "rb") as f:
            data = tomllib.load(f)
        
        if "vi" in data and "query" in data["vi"]:
            for key, value in data["vi"]["query"].items():
                setattr(self.vi_query, key, value)
        
        if "pdf2txt" in data and "batch" in data["pdf2txt"]:
            for key, value in data["pdf2txt"]["batch"].items():
                setattr(self.pdf2txt_batch, key, value)
```

### CLI 集成

```python
# vi_cli/src/vi_cli/cli.py

from acorn_core.config import AcornConfig

@app.command("query")
def query(
    symbol: str = typer.Argument(..., help="股票代码"),
    years: int | None = typer.Option(None, "-y", "--years", help="查询年数"),
    wacc: float | None = typer.Option(None, "--wacc", help="WACC"),
    g_terminal: float | None = typer.Option(None, "--g-terminal", help="永续增长率"),
) -> None:
    """查询股票财务数据"""
    # 加载配置
    config = AcornConfig.load()
    
    # 使用配置默认值，但命令行参数优先
    final_years = years if years is not None else config.vi_query.years
    final_wacc = wacc if wacc is not None else config.vi_query.wacc
    final_g_terminal = g_terminal if g_terminal is not None else config.vi_query.g_terminal
    
    # 使用 final_* 参数执行查询
    ...
```

---

## 使用示例

### 场景 1: 个人偏好配置

**用户 A** 喜欢长期分析（20 年）：
```bash
# 首次设置
cat > ~/.acorn/config.toml << EOF
[vi.query]
years = 20
wacc = 0.10
EOF

# 之后命令简化
acorn vi query 600519  # 自动使用 20 年，10% WACC
```

**用户 B** 喜欢短期分析（5 年）：
```bash
cat > ~/.acorn/config.toml << EOF
[vi.query]
years = 5
EOF

acorn vi query 00700  # 自动使用 5 年
```

### 场景 2: 临时覆盖

```bash
# 使用配置的默认值（20 年）
acorn vi query 600519

# 临时改为 10 年
acorn vi query 600519 --years 10

# 临时指定所有参数
acorn vi query 600519 --years 10 --wacc 0.12 --g-terminal 0.04
```

### 场景 3: pdf2txt 工作流优化

```bash
# 配置默认行为
cat > ~/.acorn/config.toml << EOF
[pdf2txt.batch]
output_dir = "./financial_reports"
organize_by_company = true
skip_existing = true
EOF

# 简化命令
acorn pdf2txt batch ./downloads
# 等价于：
# acorn pdf2txt batch ./downloads -o ./financial_reports -c -s
```

---

## 实施步骤

### Phase 1: 配置加载器 (1-2 天)
- [ ] 创建 `acorn_core/config.py`
- [ ] 实现 TOML 配置加载
- [ ] 实现优先级合并逻辑
- [ ] 编写单元测试

### Phase 2: vi_cli 集成 (1 天)
- [ ] 修改 `vi_cli/cli.py` 使用配置
- [ ] 参数改为 `Optional` 类型
- [ ] 更新文档

### Phase 3: pdf2txt 集成 (半天)
- [ ] 修改 `pdf2txt/cli.py` 使用配置
- [ ] 测试配置生效

### Phase 4: 配置管理命令 (可选)
```bash
acorn config get vi.query.years      # 查看配置
acorn config set vi.query.years 20   # 设置配置
acorn config list                    # 列出所有配置
```

---

## 配置项清单

### vi.query
| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| years | int | 10 | 查询年数 |
| wacc | float | 0.08 | DCF 折现率 |
| g_terminal | float | 0.03 | 永续增长率 |

### pdf2txt.batch
| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| output_dir | Path | null | 输出目录 |
| organize_by_company | bool | false | 按公司组织 |
| skip_existing | bool | false | 跳过已存在 |

---

## 向后兼容

- **无配置时**：使用代码默认值，与当前行为一致
- **部分配置时**：未配置的项使用代码默认值
- **命令行参数**：始终优先于配置文件

---

## 扩展性

未来可以轻松添加：
- 环境变量支持：`ACORN_VI_QUERY_YEARS=20`
- 远程配置：团队共享配置
- 配置模板：`acorn config init --template value-investment`
