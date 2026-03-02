"""
Command-line interface for PDF slicing.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

from .slicer import PDFSlicer


def parse_page_specification(spec: str) -> List[Tuple[int, int]]:
    """
    Parse page specification string into list of ranges.
    
    Accepts formats:
    - Single page: "5"
    - Range: "1-10"
    - Multiple ranges: "1-5,8,10-15"
    - Mixed: "1,3-5,7,10-12"
    
    Args:
        spec: Page specification string
    
    Returns:
        List of (start_page, end_page) tuples
    
    Raises:
        ValueError: If format is invalid
    """
    ranges = []
    parts = spec.split(',')
    
    for part in parts:
        part = part.strip()
        
        if '-' in part:
            # It's a range
            range_parts = part.split('-')
            if len(range_parts) != 2:
                raise ValueError(
                    f"Invalid range format: '{part}'. Expected 'start-end'"
                )
            
            try:
                start = int(range_parts[0].strip())
                end = int(range_parts[1].strip())
            except ValueError:
                raise ValueError(
                    f"Invalid range: '{part}'. Both start and end must be numbers"
                )
            
            ranges.append((start, end))
        else:
            # It's a single page
            try:
                page = int(part)
                ranges.append((page, page))
            except ValueError:
                raise ValueError(
                    f"Invalid page number: '{part}'. Must be a number"
                )
    
    return ranges


def build_argument_parser() -> argparse.ArgumentParser:
    """
    Build and configure the argument parser.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description="Extract specific pages or ranges from a PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract a single page
  slice-pdf document.pdf 5 -o page5.pdf
  
  # Extract a range
  slice-pdf document.pdf 1-10 -o chapter1.pdf
  
  # Extract multiple pages
  slice-pdf document.pdf 1,5,10 -o selected.pdf
  
  # Extract multiple ranges
  slice-pdf document.pdf 1-5,10-15,20 -o excerpts.pdf
  
  # Complex extraction
  slice-pdf document.pdf 1,3-7,9,15-20 -o mixed.pdf
  
  # Show page count
  slice-pdf document.pdf --info
        """
    )
    
    parser.add_argument(
        "pdf_file",
        help="Path to the PDF file"
    )
    
    parser.add_argument(
        "pages",
        nargs="?",
        help="Page specification (e.g., '5', '1-10', '1-5,8,10-15')"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Output PDF file path (required unless --info is used)"
    )
    
    parser.add_argument(
        "-i", "--info",
        action="store_true",
        help="Show PDF information (page count) and exit"
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


def generate_output_path(input_path: Path, page_spec: str) -> Path:
    """
    Generate a default output path based on input file and page spec.
    
    Args:
        input_path: Input PDF path
        page_spec: Page specification string
    
    Returns:
        Generated output path
    """
    stem = input_path.stem
    suffix = input_path.suffix
    
    # Simplify page spec for filename
    simple_spec = page_spec.replace(',', '_').replace('-', 'to')
    
    return input_path.parent / f"{stem}_pages_{simple_spec}{suffix}"


def show_info(slicer: PDFSlicer, pdf_path: Path) -> None:
    """
    Display information about the PDF.
    
    Args:
        slicer: PDFSlicer instance
        pdf_path: Path to the PDF file
    """
    print(f"PDF: {pdf_path}")
    print(f"Total pages: {slicer.total_pages}")


def slice_pdf(
    slicer: PDFSlicer,
    page_ranges: List[Tuple[int, int]],
    output_path: Path
) -> None:
    """
    Perform the PDF slicing operation.
    
    Args:
        slicer: PDFSlicer instance
        page_ranges: List of page range tuples
        output_path: Output file path
    """
    # Calculate total pages being extracted
    total_extracted = sum(end - start + 1 for start, end in page_ranges)
    
    # Show what we're doing
    if len(page_ranges) == 1:
        start, end = page_ranges[0]
        if start == end:
            print(f"Extracting page {start}...", file=sys.stderr)
        else:
            print(f"Extracting pages {start}-{end}...", file=sys.stderr)
    else:
        print(f"Extracting {total_extracted} pages from {len(page_ranges)} range(s)...", file=sys.stderr)
    
    # Perform the slice
    slicer.slice_to_file(str(output_path), page_ranges)
    
    print(f"Saved to: {output_path}")


def main():
    """Main entry point for the slice CLI."""
    parser = build_argument_parser()
    args = parser.parse_args()
    
    # Validate input file
    pdf_path = Path(args.pdf_file)
    validate_input_file(pdf_path)
    
    try:
        with PDFSlicer(args.pdf_file) as slicer:
            # Handle info mode
            if args.info:
                show_info(slicer, pdf_path)
                return
            
            # Require pages specification for slice mode
            if not args.pages:
                print("Error: Page specification required (or use --info to show PDF info)", file=sys.stderr)
                parser.print_help(sys.stderr)
                sys.exit(1)
            
            # Parse page specification
            try:
                page_ranges = parse_page_specification(args.pages)
            except ValueError as e:
                print(f"Error: Invalid page specification - {e}", file=sys.stderr)
                sys.exit(1)
            
            # Determine output path
            if args.output:
                output_path = Path(args.output)
            else:
                output_path = generate_output_path(pdf_path, args.pages)
                print(f"No output specified, using: {output_path}", file=sys.stderr)
            
            # Check if output exists
            if output_path.exists():
                response = input(f"File {output_path} already exists. Overwrite? [y/N] ")
                if response.lower() not in ('y', 'yes'):
                    print("Cancelled.", file=sys.stderr)
                    sys.exit(0)
            
            # Perform the slice
            slice_pdf(slicer, page_ranges, output_path)
            
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error processing PDF: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()