#!/usr/bin/env python3
"""Analyze content patterns in converted financial reports."""

from pathlib import Path
import re

def analyze_file(txt_path: Path) -> dict:
    """Analyze a single TXT file."""
    content = txt_path.read_text(encoding="utf-8")
    lines = content.split("\n")

    stats = {
        "total_lines": len(lines),
        "empty_lines": 0,
        "page_number_lines": 0,
        "short_lines": 0,  # < 10 chars
        "company_header_lines": 0,
        "toc_lines": 0,
        "legal_lines": 0,
    }

    in_toc = False
    in_legal = False
    toc_keywords = ["目录", "目錄", "Contents", "目 錄"]
    legal_keywords = ["重要提示", "董事會", "监事会", "保证年度报告", "虚假记载", "前瞻性陈述"]

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Empty lines
        if not stripped:
            stats["empty_lines"] += 1

        # Page numbers (e.g., "1 / 143")
        if re.match(r"^\d+\s*/\s*\d+$", stripped):
            stats["page_number_lines"] += 1

        # Short lines (< 10 chars, often headers/footers)
        if len(stripped) < 10 and stripped:
            stats["short_lines"] += 1

        # TOC section
        if any(kw in stripped for kw in toc_keywords):
            in_toc = True
        if in_toc and ("第" in stripped or "章" in stripped or "节" in stripped):
            stats["toc_lines"] += 1
        if in_toc and len(stripped) > 50:
            in_toc = False

        # Legal section
        if any(kw in stripped for kw in legal_keywords):
            in_legal = True
        if in_legal:
            stats["legal_lines"] += 1
            if i > 0 and not lines[i-1].strip():
                in_legal = False

    stats["content_lines"] = (
        stats["total_lines"]
        - stats["empty_lines"]
        - stats["page_number_lines"]
        - stats["toc_lines"]
    )

    return stats


def main():
    outputs_dir = Path("outputs")

    print("="*80)
    print("财报内容分析报告")
    print("="*80)
    print()

    all_stats = []

    for company_dir in sorted(outputs_dir.iterdir()):
        if not company_dir.is_dir():
            continue

        company_name = company_dir.name
        print(f"\n📊 {company_name}")
        print("-"*60)

        for txt_file in sorted(company_dir.glob("*.txt")):
            stats = analyze_file(txt_file)
            stats["filename"] = txt_file.name
            stats["company"] = company_name
            all_stats.append(stats)

            # Calculate reduction percentages
            empty_pct = stats["empty_lines"] / stats["total_lines"] * 100
            page_pct = stats["page_number_lines"] / stats["total_lines"] * 100
            toc_pct = stats["toc_lines"] / stats["total_lines"] * 100

            # Estimated reduction (removing empty + page numbers + TOC)
            removable = stats["empty_lines"] + stats["page_number_lines"] + stats["toc_lines"]
            reduction_pct = removable / stats["total_lines"] * 100

            print(f"\n  {txt_file.stem}:")
            print(f"    总行数：{stats['total_lines']:,}")
            print(f"    空行：{stats['empty_lines']:,} ({empty_pct:.1f}%)")
            print(f"    页码：{stats['page_number_lines']:,} ({page_pct:.1f}%)")
            print(f"    目录：{stats['toc_lines']:,} ({toc_pct:.1f}%)")
            print(f"    内容行：{stats['content_lines']:,}")
            print("    ━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f"    可精简：{removable:,} 行 ({reduction_pct:.1f}%)")
            print(f"    精简后：{stats['total_lines'] - removable:,} 行")

    # Summary
    print("\n" + "="*80)
    print("📈 汇总统计")
    print("="*80)

    total_lines = sum(s["total_lines"] for s in all_stats)
    total_empty = sum(s["empty_lines"] for s in all_stats)
    total_page = sum(s["page_number_lines"] for s in all_stats)
    total_toc = sum(s["toc_lines"] for s in all_stats)
    total_content = sum(s["content_lines"] for s in all_stats)

    print(f"\n  总行数：{total_lines:,}")
    print(f"  空行：{total_empty:,} ({total_empty/total_lines*100:.1f}%)")
    print(f"  页码：{total_page:,} ({total_page/total_lines*100:.1f}%)")
    print(f"  目录：{total_toc:,} ({total_toc/total_lines*100:.1f}%)")
    print(f"  内容行：{total_content:,} ({total_content/total_lines*100:.1f}%)")

    removable = total_empty + total_page + total_toc
    print(f"\n  {'='*50}")
    print("  基础精简（空行 + 页码 + 目录）:")
    print(f"    可删除：{removable:,} 行 ({removable/total_lines*100:.1f}%)")
    print(f"    保留：{total_lines - removable:,} 行 ({(total_lines-removable)/total_lines*100:.1f}%)")

    # Add legal section estimate (保守估计 10%)
    legal_estimate = int(total_content * 0.10)
    total_removable = removable + legal_estimate
    print("\n  进阶精简（+ 法律声明/重要提示 ~10%）:")
    print(f"    可删除：{total_removable:,} 行 ({total_removable/total_lines*100:.1f}%)")
    print(f"    保留：{total_lines - total_removable:,} 行 ({(total_lines-total_removable)/total_lines*100:.1f}%)")

    print(f"\n  {'='*50}")
    print("  📌 预期压缩率：40-55%")
    print("     - 保守估计（仅基础精简）：~35-40%")
    print("     - 激进估计（+ 法律声明）：~50-55%")
    print()


if __name__ == "__main__":
    main()
