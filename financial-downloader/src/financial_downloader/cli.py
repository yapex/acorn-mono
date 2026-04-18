"""Command-line interface for financial-downloader."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .downloaders import CninfoDownloader, HkexDownloader, SecDownloader

app = typer.Typer(
    name="fin-down",
    help="Download financial reports from A-share, HK-share, and US-stock markets",
    add_completion=False,
)
console = Console()


def _get_downloader(market: str, output_dir: Optional[Path] = None):
    """根据市场获取下载器实例。"""
    if market == "cn":
        return CninfoDownloader(output_dir=output_dir)
    elif market == "hk":
        return HkexDownloader(output_dir=output_dir)
    elif market == "us":
        return SecDownloader(output_dir=output_dir)
    else:
        raise ValueError(f"不支持的市场：{market}")


@app.command()
def download(
    code: str = typer.Argument(..., help="股票代码"),
    name: str = typer.Argument(..., help="公司名"),
    market: str = typer.Option(..., "--market", "-m", help="市场：cn, hk, us"),
    years: int = typer.Option(10, "--years", "-y", help="下载最近多少年"),
    year: Optional[int] = typer.Option(None, "--year", help="下载指定年份"),
    doc_type: str = typer.Option("annual", "--type", "-t", help="文档类型"),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="输出目录"),
    skip_existing: bool = typer.Option(True, "--skip-existing/-f", "-s", help="跳过已下载"),
    dry_run: bool = typer.Option(False, "--list", "-l", help="仅列出，不下载"),
) -> None:
    """下载财务报表。"""
    try:
        downloader = _get_downloader(market, output_dir)

        console.print(f"[bold blue]📥 正在下载 {code} ({name}) 的财报...[/bold blue]")
        console.print(f"  市场：{market}")
        console.print(f"  类型：{doc_type}")
        console.print(f"  年份：{year or f'最近{years}年'}")
        console.print(f"  跳过已下载：{'是' if skip_existing else '否'}")

        result = downloader.download(
            code=code,
            name=name,
            years=years,
            year=year,
            doc_type=doc_type,
            dry_run=dry_run,
            skip_existing=skip_existing,
        )

        if result.success:
            console.print("\n[green]✅ 下载完成！[/green]")
            console.print(f"  成功：{len(result.files)} 个文件")
            if result.total_size > 0:
                console.print(f"  总大小：{result.total_size_mb:.2f} MB")
        else:
            console.print("\n[red]❌ 下载失败！[/red]")
            for error in result.errors:
                console.print(f"  • {error}")
            raise typer.Exit(code=1)

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("list-types")
def list_types(
    market: str = typer.Option(..., "--market", "-m", help="市场：cn, hk, us"),
) -> None:
    """列出支持的文档类型。"""
    try:
        downloader = _get_downloader(market)
        types = downloader.get_supported_types()

        console.print(f"[bold]{market.upper()}[/bold] 支持的文档类型:")
        console.print()

        table = Table(title="文档类型")
        table.add_column("类型", style="cyan")
        table.add_column("描述", style="green")

        descriptions = {
            "cn": {"annual": "年度报告", "ipo": "招股说明书", "listing": "上市公告书", "bond": "债券募集说明书"},
            "hk": {"annual": "年报", "esg": "ESG 报告", "financial": "财务报表"},
            "us": {"20-F": "外国发行人年报", "10-K": "美国公司年报", "10-Q": "季度报告", "8-K": "重大事件"},
        }

        for doc_type in types:
            desc = descriptions.get(market, {}).get(doc_type, "")
            table.add_row(doc_type, desc)

        console.print(table)

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def batch(
    config_file: Path = typer.Argument(..., help="批量下载配置文件（YAML）", exists=True),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="输出目录"),
    skip_existing: bool = typer.Option(True, "--skip-existing/-f", "-s", help="跳过已下载"),
    dry_run: bool = typer.Option(False, "--list", "-l", help="仅列出，不下载"),
) -> None:
    """批量下载财报。"""
    try:
        import yaml

        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        downloads = config.get("downloads", [])

        if not downloads:
            console.print("[yellow]⚠️  配置文件中没有下载任务[/yellow]")
            return

        console.print(f"[bold]📋 找到 {len(downloads)} 个下载任务[/bold]\n")

        success_count = 0
        fail_count = 0

        for i, task in enumerate(downloads, 1):
            try:
                downloader = _get_downloader(task.get("market"), output_dir)

                result = downloader.download(
                    code=task.get("code"),
                    name=task.get("name"),
                    years=task.get("years", 10),
                    year=task.get("year"),
                    doc_type=task.get("type", "annual"),
                    dry_run=dry_run,
                    skip_existing=skip_existing,
                )

                if result.success:
                    success_count += 1
                    console.print(f"[green]✓ {task.get('code')}[/green]")
                else:
                    fail_count += 1
                    console.print(f"[red]✗ {task.get('code')}[/red]")

            except Exception as e:
                fail_count += 1
                console.print(f"[red]✗ {task.get('code')} 失败：{e}[/red]")

        console.print("\n[bold]下载摘要:[/bold]")
        console.print(f"  成功：[green]{success_count}[/green]")
        console.print(f"  失败：[red]{fail_count}[/red]")

        if fail_count > 0:
            raise typer.Exit(code=1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def config() -> None:
    """显示当前配置。"""
    console.print("[bold]当前配置:[/bold]\n")
    console.print("  输出目录：~/.workspace/acorn-mono/downloads")
    console.print("  SEC User-Agent: Test Company test@example.com")
    console.print("  默认年份：10")


if __name__ == "__main__":
    app()
