"""PDF to TXT CLI - Convert financial report PDFs to TXT format."""

from pathlib import Path
from typing import Optional

import typer
from loguru import logger

from .extractor import PdfExtractor
from acorn_core import AcornConfig  # type: ignore[import]

# Typer app - will be registered as acorn.cli.commands entry point
app = typer.Typer(
    name="pdf2txt",
    help="Convert financial report PDFs to readable TXT format",
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
    pdf_file: Path = typer.Argument(..., help="PDF file to convert"),
    output_dir: Optional[Path] = typer.Option(
        None,
        "-o",
        "--output-dir",
        help="Output directory (default: same as input PDF)",
    ),
    organize_by_company: bool = typer.Option(
        False,
        "--organize-by-company",
        "-c",
        help="Organize output by company name (e.g., output/贵州茅台/xxx.txt). "
             "Requires filename format: <code>_<name>_<year>_an.pdf",
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
    """Convert a PDF file to TXT format.

    Examples:
        acorn pdf2txt convert report.pdf
        acorn pdf2txt convert report.pdf -o ./output
        acorn pdf2txt convert 600519_贵州茅台_2023_an.pdf -c -o ./outputs
        acorn pdf2txt convert report.pdf -s  # Skip if already converted
        acorn pdf2txt convert /path/to/annual_report.pdf -v
    """
    _setup_logger(verbose)

    try:
        extractor = PdfExtractor(
            output_dir=output_dir,
            organize_by_company=organize_by_company,
            skip_existing=skip_existing,
            force=force,
        )
        output_path = extractor.extract(pdf_file)
        typer.echo(f"✅ Converted: {pdf_file} → {output_path}")
    except FileNotFoundError as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)
    except ValueError as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)
    except ImportError as e:
        typer.echo(f"❌ Error: {e}", err=True)
        typer.echo("💡 Install extractous: pip install extractous", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Unexpected error: {e}", err=True)
        raise typer.Exit(1)


@app.command("batch")
def batch_convert(
    input_dir: Path = typer.Argument(..., help="Directory containing PDF files"),
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
        help="Organize output by company name (e.g., output/贵州茅台/xxx.txt)",
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
        help="Search recursively for PDF files",
    ),
    verbose: bool = typer.Option(
        False,
        "-v",
        "--verbose",
        help="Enable verbose output",
    ),
) -> None:
    """Convert all PDF files in a directory to TXT format.

    Examples:
        acorn pdf2txt batch ./downloads
        acorn pdf2txt batch ./downloads -o ./outputs -c
        acorn pdf2txt batch ./downloads -o ./outputs -c -s  # Skip already converted
        acorn pdf2txt batch ./downloads -o ./outputs -c -r
    """
    _setup_logger(verbose)

    # Load config and use CLI args if provided, otherwise use config defaults
    config = AcornConfig.load()
    
    # Use command-line args if provided, otherwise use config defaults
    final_output_dir = output_dir if output_dir is not None else config.pdf2txt_batch.output_dir
    final_organize = organize_by_company if organize_by_company is not None else config.pdf2txt_batch.organize_by_company
    final_skip = skip_existing if skip_existing is not None else config.pdf2txt_batch.skip_existing

    if not input_dir.exists():
        typer.echo(f"❌ Error: Directory not found: {input_dir}", err=True)
        raise typer.Exit(1)

    if not input_dir.is_dir():
        typer.echo(f"❌ Error: Not a directory: {input_dir}", err=True)
        raise typer.Exit(1)

    # Find PDF files
    pattern = "**/*.pdf" if recursive else "*.pdf"
    pdf_files = list(input_dir.glob(pattern))

    if not pdf_files:
        typer.echo(f"⚠️  No PDF files found in: {input_dir}")
        return

    typer.echo(f"📁 Found {len(pdf_files)} PDF file(s)")

    # Convert each file
    converted_count = 0
    skipped_count = 0
    fail_count = 0

    for pdf_file in pdf_files:
        try:
            extractor = PdfExtractor(
                output_dir=final_output_dir,
                organize_by_company=final_organize,
                skip_existing=final_skip,
                force=force,
            )
            
            # Check if should skip before converting
            was_skipped = False
            if final_skip and not force:
                from .extractor import should_skip_conversion
                if should_skip_conversion(pdf_file, extractor):
                    output_path = extractor._get_output_path(pdf_file)
                    was_skipped = True
            
            if was_skipped:
                try:
                    rel_path = output_path.relative_to(output_dir or Path.cwd())
                except ValueError:
                    rel_path = output_path
                typer.echo(f"  ⏭️  {pdf_file.name} → {rel_path} (skipped)")
                skipped_count += 1
            else:
                output_path = extractor.extract(pdf_file)
                try:
                    rel_path = output_path.relative_to(output_dir or Path.cwd())
                except ValueError:
                    rel_path = output_path
                typer.echo(f"  ✅ {pdf_file.name} → {rel_path}")
                converted_count += 1
        except Exception as e:
            typer.echo(f"  ❌ {pdf_file.name}: {e}", err=True)
            fail_count += 1

    # Summary
    typer.echo(f"\n📊 Summary: {converted_count} converted, {skipped_count} skipped, {fail_count} failed")

    if fail_count > 0:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
