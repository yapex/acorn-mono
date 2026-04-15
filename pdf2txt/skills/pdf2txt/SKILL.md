---
name: pdf2txt
description: Convert financial report PDFs to readable TXT format. Use when user wants to convert PDF files to text, process financial reports, or mentions PDF conversion.
---

# pdf2txt - Financial Report PDF Converter

## Quick Start

Convert a single PDF:
```bash
acorn pdf2txt convert report.pdf
```

Batch convert with organization:
```bash
acorn pdf2txt batch ./downloads -o ./outputs -c -s
```

## Workflows

### Convert Single PDF
1. Run: `acorn pdf2txt convert <file.pdf>`
2. Output: `<file>.txt` in same directory
3. Optional: `-o <dir>` specify output directory

### Batch Convert Reports
1. Organize PDFs in a directory
2. Run: `acorn pdf2txt batch ./pdfs -o ./txt -c -s`
   - `-c`: Organize by company name
   - `-s`: Skip already converted files
3. Output structure:
   ```
   outputs/
   ├── 贵州茅台/
   │   └── 600519_贵州茅台_2023_an.txt
   └── 腾讯控股/
       └── 00700_腾讯控股_2024_an.txt
   ```

### Configure Defaults
Create `~/.config/acorn/config.toml`:
```toml
[pdf2txt.batch]
output_dir = "./outputs"
organize_by_company = true
skip_existing = true
```

## Supported Report Types

| Type | Suffix | Example |
|------|--------|---------|
| Annual | `an` | `600519_贵州茅台_2023_an.pdf` |
| ESG | `es` | `00700_腾讯控股_2024_es.pdf` |
| Interim | `H1` | `00700_腾讯控股_2024_H1.pdf` |
| Financial | `fs` | `00700_腾讯控股_2024_fs.pdf` |
| Circular | `ci` | `00700_腾讯控股_2024_ci.pdf` |
| Prospectus | `ip` | `00700_腾讯控股_2018_ip.pdf` |

## Common Commands

```bash
# Convert with verbose output
acorn pdf2txt convert report.pdf -v

# Batch with company organization
acorn pdf2txt batch ./downloads -c

# Skip already converted
acorn pdf2txt batch ./downloads -s

# Force re-conversion
acorn pdf2txt batch ./downloads -f

# Recursive search
acorn pdf2txt batch ./downloads -r
```

## Configuration

See [CONFIG_EXAMPLE.md](../../../CONFIG_EXAMPLE.md) for detailed configuration options.

Example `~/.config/acorn/config.toml`:
```toml
[pdf2txt.batch]
output_dir = "./financial_reports"
organize_by_company = true
skip_existing = true
```
