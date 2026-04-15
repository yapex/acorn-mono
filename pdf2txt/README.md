# pdf2txt

Convert financial report PDFs to readable TXT format using Extractous.

## Supported Report Types

| Type | Suffix | Example | Description |
|------|--------|---------|-------------|
| annual | `an` | `00700_腾讯控股_2024_an.pdf` | Annual report (年报) |
| esg | `es` | `00700_腾讯控股_2024_es.pdf` | ESG/Sustainability report (环境、社会及管治报告) |
| interim | `H1` | `00700_腾讯控股_2024_H1.pdf` | Interim/Half-year report (中期报告) |
| financial | `fs` | `00700_腾讯控股_2024_fs.pdf` | Financial statements (财务报表) |
| circular | `ci` | `00700_腾讯控股_2024_ci.pdf` | Circular (通函) |
| prospectus | `ip` | `00700_腾讯控股_2018_ip.pdf` | Prospectus (招股书) |

## Installation

As part of the acorn-mono workspace:

```bash
uv pip install -e pdf2txt
```

## Usage

### Single PDF Conversion

```bash
# Convert a single PDF file
acorn pdf2txt convert annual_report_2024.pdf

# Specify output directory
acorn pdf2txt convert annual_report_2024.pdf -o ./output

# Verbose mode
acorn pdf2txt convert annual_report_2024.pdf -v
```

### Batch Conversion

```bash
# Convert all PDFs in a directory
acorn pdf2txt batch ./reports

# Recursive search
acorn pdf2txt batch ./reports -r -o ./txt_output

# Skip already converted files
acorn pdf2txt batch ./reports -c -s

# Force re-conversion
acorn pdf2txt batch ./reports -c -f
```

## API Usage

```python
from pdf2txt import PdfExtractor
from pathlib import Path

# Single file conversion
extractor = PdfExtractor()
output_path = extractor.extract("report.pdf")

# With custom output directory
extractor = PdfExtractor(output_dir=Path("./output"))
output_path = extractor.extract("report.pdf")

# Skip already converted files
extractor = PdfExtractor(skip_existing=True)
output_path = extractor.extract("report.pdf")  # Skips if output exists

# Force re-conversion
extractor = PdfExtractor(force=True)
output_path = extractor.extract("report.pdf")  # Always converts

# Parse report metadata
from pdf2txt.extractor import parse_company_name, parse_report_type, parse_year

pdf_path = Path("00700_腾讯控股_2024_es.pdf")
company = parse_company_name(pdf_path)  # "腾讯控股"
report_type = parse_report_type(pdf_path)  # "esg"
year = parse_year(pdf_path)  # "2024"
```

## Output Organization

When using `--organize-by-company` (`-c`), output files are organized by company name:

```
outputs/
├── 腾讯控股/
│   ├── 00700_腾讯控股_2024_an.txt
│   ├── 00700_腾讯控股_2024_es.txt
│   └── 00700_腾讯控股_2024_H1.txt
├── 贵州茅台/
│   └── 600519_贵州茅台_2023_an.txt
└── 携程集团/
    └── 09961_携程集团_2023_an.txt
```

## Architecture

```
pdf2txt/
├── src/pdf2txt/
│   ├── __init__.py      # Package exports
│   ├── extractor.py     # PDF extraction logic (Extractous wrapper)
│   └── cli.py           # CLI commands (convert, batch)
├── tests/
│   ├── test_extractor.py
│   └── test_cli.py
├── pyproject.toml
└── README.md
```

## Future Enhancements

### Content Simplification (Planned)

The next phase will add content simplification capabilities to remove formulaic content from financial reports:

- Remove standard disclaimers and legal text
- Filter out repetitive boilerplate sections
- Extract key financial highlights
- Preserve meaningful narrative sections

Example (future API):

```python
from pdf2txt import PdfExtractor, ContentSimplifier

extractor = PdfExtractor()
txt_path = extractor.extract("report.pdf")

simplifier = ContentSimplifier()
simplified_path = simplifier.simplify(txt_path)
```

## Dependencies

- **extractous**: PDF to text conversion
- **typer**: CLI framework
- **loguru**: Logging
- **acorn-cli**: Acorn plugin integration

## Development

```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=pdf2txt

# Lint
uv run ruff check pdf2txt
```
