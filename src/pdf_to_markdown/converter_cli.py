"""
Command-line interface for PDF to Markdown conversion.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Tuple

from .converter import PDFToMarkdown


def parse_page_range(page_range_str: str) -> Tuple[int, int]:
    """
    Parse page range string into tuple.
    
    Args:
        page_range_str: String like "1-5", "3", or "10-15"
    
    Returns:
        Tuple of (start_page, end_page)
    
    Raises:
        ValueError: If format is invalid
    """
    if "-" in page_range_str:
        parts = page_range_str.split("-")
        if len(parts) != 2:
            raise ValueError("Page range must be in format 'start-end' or single page number")
        
        start = int(parts[0])
        end = int(parts[1])
        return (start, end)
    else:
        page = int(page_range_str)
        return (page, page)


def build_argument_parser() -> argparse.ArgumentParser:
    """
    Build and configure the argument parser.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description="Extract text from PDF and convert to Markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract entire document
  tomd document.pdf
  
  # Extract to file
  tomd document.pdf -o output.md
  
  # Extract specific page
  tomd document.pdf -p 5
  
  # Extract page range
  tomd document.pdf -p 1-10
  
  # Simple extraction without structure
  tomd document.pdf --simple
        """
    )
    
    parser.add_argument(
        "pdf_file",
        help="Path to the PDF file"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Output markdown file (default: stdout)"
    )
    
    parser.add_argument(
        "-p", "--pages",
        help="Page range to extract (e.g., '1-5' or '3'). Default: all pages"
    )
    
    parser.add_argument(
        "-s", "--simple",
        action="store_true",
        help="Use simple extraction without structure analysis"
    )

    parser.add_argument(
        "--no-emphasis",
        action="store_true",
        help="Disable bold/italic preservation"
    )

    parser.add_argument(
        "--no-tables",
        action="store_true",
        help="Disable table extraction"
    )
    
    return parser


def validate_input_file(pdf_path: Path) -> None:
    """
    Validate that the input PDF file exists.
    
    Args:
        pdf_path: Path to PDF file
    
    Raises:
        SystemExit: If file doesn't exist
    """
    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)
    
    if not pdf_path.is_file():
        print(f"Error: Path is not a file: {pdf_path}", file=sys.stderr)
        sys.exit(1)


def extract_markdown(
    converter: PDFToMarkdown,
    page_range: Optional[Tuple[int, int]],
    simple_mode: bool,
    preserve_emphasis: bool = True,
    extract_tables: bool = True
) -> str:
    """
    Extract markdown from PDF using the converter.
    
    Args:
        converter: PDFToMarkdown instance
        page_range: Optional page range tuple
        simple_mode: Whether to use simple extraction
        preserve_emphasis: Whether to preserve bold/italic
        extract_tables: Whether to extract tables
    
    Returns:
        Markdown-formatted text
    """
    if simple_mode:
        return converter.extract_simple(page_range)
    else:
        return converter.extract_with_structure(page_range, preserve_emphasis, extract_tables)


def write_output(content: str, output_path: Optional[str]) -> None:
    """
    Write content to file or stdout.
    
    Args:
        content: Text content to write
        output_path: Optional output file path. If None, writes to stdout
    """
    if output_path:
        output_file = Path(output_path)
        output_file.write_text(content, encoding="utf-8")
        print(f"Markdown written to: {output_file}")
    else:
        print(content)


def main():
    """Main entry point for the CLI."""
    parser = build_argument_parser()
    args = parser.parse_args()
    
    # Validate input file
    pdf_path = Path(args.pdf_file)
    validate_input_file(pdf_path)
    
    # Parse page range if provided
    page_range = None
    if args.pages:
        try:
            page_range = parse_page_range(args.pages)
        except ValueError as e:
            print(f"Error: Invalid page range - {e}", file=sys.stderr)
            sys.exit(1)
    
    # Process PDF
    try:
        with PDFToMarkdown(args.pdf_file) as converter:
            # Show page info if range specified
            if page_range:
                start, end = page_range
                print(
                    f"Extracting pages {start}-{end} of {converter.total_pages}...",
                    file=sys.stderr
                )
            
            preserve_emphasis = not args.no_emphasis
            extract_tables = not args.no_tables
            markdown_text = extract_markdown(
                converter, 
                page_range, 
                args.simple, 
                preserve_emphasis,
                extract_tables
            )
            write_output(markdown_text, args.output)
            
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error processing PDF: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()