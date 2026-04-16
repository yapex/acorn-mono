"""HTML to Markdown CLI - Convert SEC HTML filings to Markdown format."""

from pathlib import Path
from typing import Optional

import typer
from loguru import logger

from .converter import HtmlConverter

# Load config if available, otherwise use defaults
try:
    from acorn_core import AcornConfig  # type: ignore[import]
    HAS_ACORN = True
except ImportError:
    HAS_ACORN = False

# Typer app - will be registered as acorn.cli.commands entry point
app = typer.Typer(
    name="html2md",
    help="Convert SEC HTML filings to readable Markdown format",
)


def _setup_logger(verbose: bool = False) -> None:
    """Setup logger based on verbosity."""
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(
        lambda msg: typer.echo(msg, err=True),
        level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>",
    )


@app.command("convert")
def convert(
    html_file: Path = typer.Argument(..., help="HTML file to convert"),
    output_dir: Optional[Path] = typer.Option(
        None,
        "-o",
        "--output-dir",
        help="Output directory (default: same as input HTML)",
    ),
    organize_by_company: bool = typer.Option(
        False,
        "--organize-by-company",
        "-c",
        help="Organize output by company name (e.g., output/携程/xxx.md). "
             "Requires filename format: <code>_<name>_<year>_<type>.html",
    ),
    plain_text: bool = typer.Option(
        False,
        "--plain-text",
        "-p",
        help="Output plain text instead of Markdown (optimized for LLM)",
    ),
    skip_existing: bool = typer.Option(
        False,
        "--skip-existing",
        "-s",
        help="Skip conversion if output file already exists",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force conversion even if output file exists (overrides --skip-existing)",
    ),
    verbose: bool = typer.Option(
        False,
        "-v",
        "--verbose",
        help="Enable verbose output",
    ),
) -> None:
    """Convert an HTML file to Markdown format.

    Examples:
        acorn html2md convert filing.html
        acorn html2md convert filing.html -o ./output
        acorn html2md convert TCOM_携程_2024_an.html -c -o ./outputs_md
        acorn html2md convert filing.html -p  # Plain text for LLM
        acorn html2md convert filing.html -s  # Skip if already converted
    """
    _setup_logger(verbose)

    try:
        converter = HtmlConverter(
            output_dir=output_dir,
            organize_by_company=organize_by_company,
            skip_existing=skip_existing,
            force=force,
            plain_text=plain_text,
        )
        output_path = converter.convert(html_file)
        ext = "txt" if plain_text else "md"
        typer.echo(f"✅ Converted: {html_file} → {output_path}")
    except FileNotFoundError as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)
    except ValueError as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Unexpected error: {e}", err=True)
        raise typer.Exit(1)


@app.command("batch")
def batch_convert(
    input_dir: Path = typer.Argument(..., help="Directory containing HTML files"),
    output_dir: Optional[Path] = typer.Option(
        None,
        "-o",
        "--output-dir",
        help="Output directory (default: same as input directory or config)",
    ),
    organize_by_company: bool | None = typer.Option(
        None,
        "--organize-by-company",
        "-c",
        help="Organize output by company name (e.g., output/携程/xxx.md)",
    ),
    plain_text: bool = typer.Option(
        False,
        "--plain-text",
        "-p",
        help="Output plain text instead of Markdown",
    ),
    skip_existing: bool | None = typer.Option(
        None,
        "--skip-existing",
        "-s",
        help="Skip conversion if output file already exists",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force conversion even if output file exists",
    ),
    recursive: bool = typer.Option(
        False,
        "-r",
        "--recursive",
        help="Search recursively for HTML files",
    ),
    verbose: bool = typer.Option(
        False,
        "-v",
        "--verbose",
        help="Enable verbose output",
    ),
) -> None:
    """Convert all HTML files in a directory to Markdown format.

    Examples:
        acorn html2md batch ./downloads
        acorn html2md batch ./downloads -o ./outputs_md -c
        acorn html2md batch ./downloads -o ./outputs_md -c -s
        acorn html2md batch ./downloads -o ./outputs_md -p -c  # Plain text
    """
    _setup_logger(verbose)

    # Load config and use CLI args if provided, otherwise use config defaults
    if HAS_ACORN:
        config = AcornConfig.load()
        # Use command-line args if provided, otherwise use config defaults
        final_output_dir = output_dir if output_dir is not None else config.html2md_batch.output_dir
        final_organize = organize_by_company if organize_by_company is not None else config.html2md_batch.organize_by_company
        final_skip = skip_existing if skip_existing is not None else config.html2md_batch.skip_existing
    else:
        # Default values when acorn_core is not available
        final_output_dir = output_dir
        final_organize = organize_by_company or False
        final_skip = skip_existing or False

    if not input_dir.exists():
        typer.echo(f"❌ Error: Directory not found: {input_dir}", err=True)
        raise typer.Exit(1)

    if not input_dir.is_dir():
        typer.echo(f"❌ Error: Not a directory: {input_dir}", err=True)
        raise typer.Exit(1)

    # Find HTML files (only SEC .html files, not .htm)
    pattern = "**/*.html" if recursive else "*.html"
    html_files = list(input_dir.glob(pattern))

    if not html_files:
        typer.echo(f"⚠️  No HTML files found in: {input_dir}")
        return

    typer.echo(f"📁 Found {len(html_files)} HTML file(s)")

    # Convert each file
    converted_count = 0
    skipped_count = 0
    fail_count = 0

    for html_file in html_files:
        try:
            converter = HtmlConverter(
                output_dir=final_output_dir,
                organize_by_company=final_organize,
                skip_existing=final_skip,
                force=force,
                plain_text=plain_text,
            )

            # Check if should skip before converting
            was_skipped = False
            if final_skip and not force:
                output_path = converter._get_output_path(html_file)
                if output_path.exists():
                    was_skipped = True

            ext = "txt" if plain_text else "md"
            if was_skipped:
                try:
                    rel_path = output_path.relative_to(output_dir or Path.cwd())
                except ValueError:
                    rel_path = output_path
                typer.echo(f"  ⏭️  {html_file.name} → {rel_path} (skipped)")
                skipped_count += 1
            else:
                output_path = converter.convert(html_file)
                try:
                    rel_path = output_path.relative_to(output_dir or Path.cwd())
                except ValueError:
                    rel_path = output_path
                typer.echo(f"  ✅ {html_file.name} → {rel_path}")
                converted_count += 1
        except Exception as e:
            typer.echo(f"  ❌ {html_file.name}: {e}", err=True)
            fail_count += 1

    # Summary
    typer.echo(f"\n📊 Summary: {converted_count} converted, {skipped_count} skipped, {fail_count} failed")

    if fail_count > 0:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
