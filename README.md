# PDF to Markdown Converter & Slicer

A comprehensive Python toolkit for working with PDF files, including text extraction with Markdown conversion and page slicing capabilities.

## Features

### PDF to Markdown Converter

- **Semantic Structure Detection**: Automatically identifies headings, lists, and paragraphs based on font size and styling
- **Emphasis Preservation**: Maintains **bold** and *italic* formatting in the output
- **Page Range Selection**: Extract specific pages or page ranges instead of entire documents
- **Multi-paragraph List Support**: Keeps continuation paragraphs grouped with their list items
- **Nested Lists**: Handles numbered lists (1., 2., 3.) and lettered sub-lists (a., b., c.)
- **Blockquote Detection**: Recognizes italicized blocks as quotations
- **Two Extraction Modes**:
  - **Structured**: Analyzes PDF formatting to create proper Markdown structure
  - **Simple**: Plain text extraction without formatting analysis
- **Context Manager Support**: Proper resource management with Python's `with` statement

### PDF Slicer

- **Extract Single Pages**: Pull out individual pages from a PDF
- **Extract Page Ranges**: Get consecutive page sequences
- **Multiple Ranges**: Extract non-contiguous sections in one operation
- **Flexible Syntax**: Supports complex page specifications like `1-5,8,10-15,20`
- **Auto-naming**: Generates sensible output filenames automatically
- **Info Mode**: Quick page count lookup

## Installation

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager

### Install with uv
```bash
# Clone or navigate to the project directory
cd pdf-to-markdown

# Install the package in development mode
uv pip install -e .
```

This will:
- Install all required dependencies (PyMuPDF)
- Make the `tomd` and `slice-pdf` commands available globally
- Allow you to edit the source code with changes reflected immediately

## Usage

### PDF to Markdown Converter

#### Command Line Interface
```bash
# Extract entire document to stdout
tomd document.pdf

# Extract to a file
tomd document.pdf -o output.md

# Extract a specific page
tomd document.pdf -p 5

# Extract a page range
tomd document.pdf -p 1-10 -o chapter1.md

# Disable emphasis preservation (no bold/italic)
tomd document.pdf --no-emphasis -o plain.md

# Use simple extraction (no structure analysis)
tomd document.pdf --simple

# Combine options
tomd document.pdf -p 15-25 --simple -o appendix.md
```

#### Command Options
```
positional arguments:
  pdf_file                Path to the PDF file

options:
  -h, --help              Show help message and exit
  -o, --output OUTPUT     Output markdown file (default: stdout)
  -p, --pages PAGES       Page range to extract (e.g., '1-5' or '3')
                          Default: all pages
  -s, --simple            Use simple extraction without structure analysis
  --no-emphasis           Disable bold/italic preservation
```

#### Python API
```python
from pdf_to_markdown import PDFToMarkdown

# Using context manager (recommended)
with PDFToMarkdown("document.pdf") as converter:
    # Extract entire document with structure
    markdown = converter.extract_with_structure()
    
    # Extract specific pages with emphasis
    markdown = converter.extract_with_structure(
        page_range=(1, 5),
        preserve_emphasis=True
    )
    
    # Extract without emphasis preservation
    markdown = converter.extract_with_structure(
        page_range=(10, 15),
        preserve_emphasis=False
    )
    
    # Simple extraction
    text = converter.extract_simple(page_range=(10, 15))
    
    # Check total pages
    print(f"Document has {converter.total_pages} pages")

# Manual resource management
converter = PDFToMarkdown("document.pdf")
try:
    markdown = converter.extract_with_structure()
finally:
    converter.close()
```

### PDF Slicer

#### Command Line Interface
```bash
# Show PDF information (page count)
slice-pdf document.pdf --info

# Extract a single page
slice-pdf document.pdf 5 -o page5.pdf

# Extract a range
slice-pdf document.pdf 1-10 -o chapter1.pdf

# Extract multiple specific pages
slice-pdf document.pdf 1,5,10,15 -o selected_pages.pdf

# Extract multiple ranges
slice-pdf document.pdf 1-5,10-15,20-25 -o excerpts.pdf

# Complex mixed extraction
slice-pdf document.pdf 1,3-7,9,15-20,25 -o mixed.pdf

# Auto-generate output filename
slice-pdf document.pdf 1-10
# Creates: document_pages_1to10.pdf
```

#### Command Options
```
positional arguments:
  pdf_file              Path to the PDF file
  pages                 Page specification (e.g., '5', '1-10', '1-5,8,10-15')

options:
  -h, --help            Show help message and exit
  -o, --output OUTPUT   Output PDF file path
  -i, --info            Show PDF information (page count) and exit
```

#### Python API
```python
from pdf_to_markdown import PDFSlicer

# Using context manager (recommended)
with PDFSlicer("document.pdf") as slicer:
    # Check total pages
    print(f"Total pages: {slicer.total_pages}")
    
    # Extract single page
    slicer.slice_to_file("page5.pdf", [(5, 5)])
    
    # Extract range
    slicer.slice_to_file("chapter1.pdf", [(1, 10)])
    
    # Extract multiple ranges
    slicer.slice_to_file(
        "excerpts.pdf",
        [(1, 5), (10, 15), (20, 25)]
    )

# Manual resource management
slicer = PDFSlicer("document.pdf")
try:
    slicer.slice_to_file("output.pdf", [(1, 10)])
finally:
    slicer.close()
```

## How It Works

### PDF to Markdown: Structured Extraction

The structured extraction mode analyzes PDF text formatting to infer semantic meaning:

1. **Font Size Analysis**: Larger fonts are interpreted as headings
   - Size > 18pt → `# Heading 1` (Title)
   - Size > 16pt → `# Heading 1`
   - Size > 14pt → `## Heading 2`
   - Size > 12pt (bold) → `### Heading 3`

2. **Bold/Italic Detection**: Preserves text emphasis
   - Bold text → `**bold**`
   - Italic text → `*italic*`
   - Both → `***bold italic***`

3. **List Detection**: Recognizes various list formats
   - Numbered lists: `1.`, `2.`, `3.`
   - Lettered sub-lists: `a.`, `b.`, `c.` (indented)
   - Bullet points: `•`, `◦`, `-`, `*`, `·`

4. **Multi-paragraph Lists**: Keeps continuation paragraphs with their list items

5. **Blockquote Detection**: Fully italicized paragraphs become `> quotes`

6. **Paragraph Preservation**: Regular text is formatted as standard paragraphs

### PDF to Markdown: Simple Extraction

Simple mode extracts raw text without analyzing structure, useful for:
- Scanned documents
- PDFs with complex or inconsistent formatting
- When you just need the plain text content

### PDF Slicer: Page Extraction

The slicer creates new PDF files containing only the specified pages:

1. **Validates** all page ranges against document length
2. **Extracts** pages in the order specified
3. **Combines** multiple ranges into a single output file
4. **Preserves** all original PDF formatting, fonts, and images

## Project Structure
```
pdf-to-markdown/
├── pyproject.toml              # Project configuration and dependencies
├── README.md                   # This file
└── src/
    └── pdf_to_markdown/
        ├── __init__.py         # Package initialization
        ├── converter.py        # PDFToMarkdown class
        ├── cli.py              # tomd command-line interface
        ├── slicer.py           # PDFSlicer class
        └── slice_cli.py        # slice-pdf command-line interface
```

## Examples

### Converting Technical Documentation
```bash
# Extract just the API reference section (pages 45-89)
tomd technical_manual.pdf -p 45-89 -o api_reference.md

# Get the introduction without formatting
tomd technical_manual.pdf -p 1-10 --simple -o intro.md
```

### Extracting Adventure Guide Sections
```bash
# Convert the adventure writing guide
tomd Adventure_Design_Guide.pdf -o design_guide.md

# Extract just page 1 (the core principles)
tomd Adventure_Design_Guide.pdf -p 1 -o core_principles.md
```

### Creating Study Materials
```bash
# Extract chapters as separate PDFs first
slice-pdf textbook.pdf 1-25 -o chapter1.pdf
slice-pdf textbook.pdf 26-50 -o chapter2.pdf

# Then convert to markdown
tomd chapter1.pdf -o chapter1_notes.md
tomd chapter2.pdf -o chapter2_notes.md
```

### Combining Tools
```bash
# Extract relevant pages, then convert to markdown
slice-pdf large_document.pdf 5,10-15,20,25-30 -o excerpts.pdf
tomd excerpts.pdf -o excerpts.md
```

### Batch Processing
```bash
# Convert all PDFs in a directory
for pdf in *.pdf; do
    tomd "$pdf" -o "${pdf%.pdf}.md"
done

# Extract first page of all PDFs
for pdf in *.pdf; do
    slice-pdf "$pdf" 1 -o "${pdf%.pdf}_page1.pdf"
done
```

### Working with Large Documents
```bash
# Check page count first
slice-pdf thesis.pdf --info

# Extract table of contents
slice-pdf thesis.pdf 1-5 -o toc.pdf

# Extract individual chapters
slice-pdf thesis.pdf 10-35 -o chapter1.pdf
slice-pdf thesis.pdf 36-67 -o chapter2.pdf
slice-pdf thesis.pdf 68-92 -o chapter3.pdf

# Convert chapters to markdown
tomd chapter1.pdf -o chapter1.md
tomd chapter2.pdf -o chapter2.md
tomd chapter3.pdf -o chapter3.md
```

## Limitations

### PDF to Markdown

- **Best Results**: Well-structured PDFs with clear formatting
- **Scanned PDFs**: Use simple mode or consider OCR preprocessing
- **Complex Layouts**: Multi-column layouts may not convert perfectly
- **Tables**: Basic table structure might be lost (rendered as text)
- **Images**: Currently only extracts text, not images or graphics
- **Fonts**: Requires font information to be embedded in PDF for best structure detection

### PDF Slicer

- **Page Integrity**: Extracts complete pages only (cannot crop or split pages)
- **File Size**: Output PDFs maintain original quality, which may result in large files
- **Annotations**: Preserves annotations only if they're on the extracted pages

## Troubleshooting

### "PDF file not found" Error

Ensure the file path is correct and the file exists:
```bash
ls -la document.pdf
tomd "$(pwd)/document.pdf"
```

### Page Range Errors
```bash
# Check total pages first
slice-pdf document.pdf --info
# Output: Total pages: 50

# Then use valid range
tomd document.pdf -p 1-50
slice-pdf document.pdf 1-50 -o complete.pdf
```

### Poor Structure Detection

Try simple mode if structured extraction produces poor results:
```bash
tomd document.pdf --simple -o output.md
```

### Emphasis Formatting Issues

If bold/italic markers clutter the output:
```bash
tomd document.pdf --no-emphasis -o plain.md
```

### Complex Page Specifications

Test your page specification with the slicer first:
```bash
# See what you're getting
slice-pdf document.pdf 1-5,10,15-20 --info
```

## Dependencies

- **PyMuPDF (fitz)**: PDF parsing, text extraction, and manipulation
  - Robust, fast, and provides detailed text positioning and styling data
  - Handles complex PDF structures
  - Supports PDF creation and modification

## Development

### Running Without Installation
```bash
# Run tomd directly
uv run src/pdf_to_markdown/cli.py document.pdf

# Run slice-pdf directly
uv run src/pdf_to_markdown/slice_cli.py document.pdf 1-10
```

### Running Tests
```bash
# Add pytest to dependencies first
uv add --dev pytest

# Run tests (when test suite is added)
uv run pytest
```

### Making Changes

Since the package is installed in editable mode (`-e`), any changes to the source files will be immediately available when running `tomd` or `slice-pdf`.

### Code Structure

- **converter.py**: Core text extraction and Markdown conversion logic
- **cli.py**: Command-line interface for tomd
- **slicer.py**: Core PDF page extraction logic
- **slice_cli.py**: Command-line interface for slice-pdf
- ****init__.py**: Package exports and version info

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Author

Dan - Software Consultant specializing in full-stack development

## Acknowledgments

- PyMuPDF team for the excellent PDF library
- D&D Adventure Design Guide for inspiring document structure detection improvements

## Version History

- **0.1.0** (2024): Initial release
  - Core PDF to Markdown conversion
  - Page range selection for conversion
  - Structured and simple extraction modes
  - Bold/italic emphasis preservation
  - Multi-paragraph list support
  - Nested list detection
  - Blockquote recognition
  - PDF slicing tool with flexible page specifications
  - CLI interfaces for both tools
  - Python API for programmatic access

## Roadmap

Future enhancements under consideration:

- [ ] Table extraction and conversion to Markdown tables
- [ ] Image extraction and embedding
- [ ] OCR support for scanned documents
- [ ] PDF merging capabilities (combine multiple PDFs)
- [ ] Batch conversion with wildcard support
- [ ] Configuration file support for default options
- [ ] Progress bars for large documents
- [ ] PDF metadata editing
- [ ] Bookmark/TOC extraction