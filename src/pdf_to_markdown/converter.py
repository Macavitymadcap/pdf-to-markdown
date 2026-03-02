# src/pdf_to_markdown/converter.py
"""
PDF to Markdown converter with table extraction and improved header detection.
"""

from pathlib import Path
from typing import Optional, List, Tuple, Dict
import fitz  # PyMuPDF
import re


class PDFToMarkdown:
    """Converts PDF documents to Markdown format with structure preservation."""
    
    # Ligature replacement map
    LIGATURES = {
        '\ufb00': 'ff',
        '\ufb01': 'fi',
        '\ufb02': 'fl',
        '\ufb03': 'ffi',
        '\ufb04': 'ffl',
        '\ufb05': 'ft',
        '\ufb06': 'st',
        # Additional common ligatures
        'ﬀ': 'ff',
        'ﬁ': 'fi',
        'ﬂ': 'fl',
        'ﬃ': 'ffi',
        'ﬄ': 'ffl',
    }
    
    def __init__(self, pdf_path: str):
        """
        Initialize the converter with a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
        """
        self.pdf_path = Path(pdf_path)
        self.doc = fitz.open(pdf_path)
        self.total_pages = len(self.doc)
    
    def _fix_ligatures(self, text: str) -> str:
        """
        Replace ligatures with their component characters.
        
        Args:
            text: Text potentially containing ligatures
        
        Returns:
            Text with ligatures replaced
        """
        for ligature, replacement in self.LIGATURES.items():
            text = text.replace(ligature, replacement)
        return text
    
    def extract_with_structure(
        self, 
        page_range: Optional[Tuple[int, int]] = None,
        preserve_emphasis: bool = True,
        extract_tables: bool = True
    ) -> str:
        """
        Extract text with semantic structure preservation.
        
        Args:
            page_range: Optional tuple of (start_page, end_page) (1-indexed, inclusive)
            preserve_emphasis: Whether to preserve bold/italic formatting
            extract_tables: Whether to extract tables
        
        Returns:
            Markdown-formatted text
        """
        start_page, end_page = self._validate_page_range(page_range)
        markdown_output = []
        
        # Track context across blocks
        prev_block_type = None
        current_list_item = []
        
        for page_num in range(start_page, end_page + 1):
            page = self.doc[page_num - 1]
            
            # Try to extract tables first if enabled
            tables = []
            table_bboxes = []
            if extract_tables:
                tables = self._extract_tables_pymupdf(page)
                table_bboxes = [t['bbox'] for t in tables if t.get('bbox')]
            
            # Get regular text blocks
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if block["type"] == 0:  # Text block
                    bbox = block.get("bbox", [0, 0, 0, 0])
                    
                    # Skip blocks that overlap with tables
                    if self._bbox_overlaps_tables(bbox, table_bboxes):
                        continue
                    
                    block_info = self._analyze_block(block, preserve_emphasis)
                    
                    if not block_info:
                        continue
                    
                    # Handle multi-paragraph list items
                    if prev_block_type and prev_block_type.startswith("list_"):
                        if block_info["type"] == "paragraph" and block_info.get("indent", 0) > 50:
                            current_list_item.append("  " + block_info["text"])
                            continue
                        elif current_list_item:
                            markdown_output.append("\n".join(current_list_item))
                            current_list_item = []
                    
                    # Process the block
                    if block_info["type"].startswith("list_"):
                        current_list_item = [block_info["text"]]
                        prev_block_type = block_info["type"]
                    else:
                        markdown_output.append(block_info["text"])
                        prev_block_type = block_info["type"]
            
            # Flush any remaining list item
            if current_list_item:
                markdown_output.append("\n".join(current_list_item))
                current_list_item = []
            
            # Add extracted tables
            for table in tables:
                markdown_output.append(table['markdown'])
            
            # Add page break except after last page
            if page_num < end_page:
                markdown_output.append("\n---\n")
        
        return "\n\n".join(markdown_output)
    
    def _extract_tables_pymupdf(self, page) -> List[Dict]:
        """
        Extract tables from a page using PyMuPDF's table detection.
        
        Args:
            page: PyMuPDF page object
        
        Returns:
            List of dictionaries with 'markdown' and 'bbox' keys
        """
        tables = []
        
        try:
            # PyMuPDF 1.23+ has find_tables method
            if hasattr(page, 'find_tables'):
                table_finder = page.find_tables()
                
                for table in table_finder.tables:
                    # Extract table data
                    markdown_table = self._table_to_markdown(table)
                    
                    if markdown_table:
                        tables.append({
                            'markdown': markdown_table,
                            'bbox': table.bbox
                        })
            else:
                # Fallback: Use heuristic detection for older PyMuPDF
                tables = self._detect_tables_heuristic(page)
        
        except Exception as e:
            # If extraction fails, try heuristic
            try:
                tables = self._detect_tables_heuristic(page)
            except:
                pass
        
        return tables
    
    def _table_to_markdown(self, table) -> Optional[str]:
        """
        Convert a PyMuPDF table object to Markdown.
        
        Args:
            table: PyMuPDF table object
        
        Returns:
            Markdown-formatted table string or None
        """
        try:
            # Extract table data
            data = table.extract()
            
            if not data or len(data) < 2:  # Need at least header + 1 row
                return None
            
            # Fix ligatures in all cells
            data = [[self._fix_ligatures(str(cell)) if cell else '' for cell in row] for row in data]
            
            # Assume first row is header
            headers = [str(cell).strip() for cell in data[0]]
            
            # Build header row
            header_row = " | ".join(headers)
            separator = " | ".join(["---"] * len(headers))
            
            # Build data rows
            rows = []
            for row in data[1:]:
                # Ensure row has same number of columns as header
                while len(row) < len(headers):
                    row.append('')
                
                row_data = " | ".join([str(cell).strip() for cell in row[:len(headers)]])
                rows.append(row_data)
            
            # Combine into table
            table_lines = [header_row, separator] + rows
            
            return "\n".join(table_lines)
        
        except Exception as e:
            return None
    
    def _detect_tables_heuristic(self, page) -> List[Dict]:
        """
        Heuristic table detection based on text alignment patterns.
        
        Args:
            page: PyMuPDF page object
        
        Returns:
            List of table dictionaries
        """
        tables = []
        
        try:
            # Get all text with positions
            blocks = page.get_text("dict")["blocks"]
            
            # Group lines by Y position (rows)
            rows = {}
            for block in blocks:
                if block["type"] != 0:  # Skip non-text blocks
                    continue
                
                for line in block.get("lines", []):
                    y = round(line["bbox"][1], 0)  # Use top Y coordinate
                    
                    if y not in rows:
                        rows[y] = []
                    
                    # Extract spans with positions
                    for span in line.get("spans", []):
                        text = span["text"].strip()
                        if text:
                            rows[y].append({
                                'text': text,
                                'x': span["bbox"][0],
                                'y': y,
                                'width': span["bbox"][2] - span["bbox"][0]
                            })
            
            # Look for table patterns
            sorted_y = sorted(rows.keys())
            
            if len(sorted_y) < 3:  # Need at least 3 rows for a table
                return tables
            
            # Check for regular spacing
            y_diffs = [sorted_y[i+1] - sorted_y[i] for i in range(len(sorted_y)-1)]
            avg_spacing = sum(y_diffs) / len(y_diffs) if y_diffs else 0
            
            # If spacing is relatively consistent, might be a table
            if avg_spacing > 0:
                # Try to identify column positions
                all_x_positions = set()
                for y in sorted_y:
                    for item in rows[y]:
                        all_x_positions.add(round(item['x'], -1))  # Round to nearest 10
                
                # If we have consistent X positions across multiple rows, likely a table
                if len(all_x_positions) >= 2:  # At least 2 columns
                    # Build table from rows
                    table_data = self._build_table_from_rows(rows, sorted_y, all_x_positions)
                    
                    if table_data and len(table_data) > 2:  # Need header + data rows
                        markdown_table = self._format_detected_table(table_data)
                        if markdown_table:
                            tables.append({
                                'markdown': markdown_table,
                                'bbox': None
                            })
        
        except Exception as e:
            pass
        
        return tables
    
    def _build_table_from_rows(self, rows, sorted_y, x_positions):
        """
        Build table structure from detected rows and column positions.
        
        Args:
            rows: Dictionary mapping Y coordinates to text items
            sorted_y: Sorted list of Y coordinates
            x_positions: Set of detected X column positions
        
        Returns:
            List of lists representing table rows
        """
        # Sort X positions to define column order
        sorted_x = sorted(x_positions)
        
        # Define column boundaries (midpoints between X positions)
        col_boundaries = []
        for i in range(len(sorted_x)):
            if i == 0:
                col_boundaries.append((0, (sorted_x[0] + sorted_x[1]) / 2 if len(sorted_x) > 1 else float('inf')))
            elif i == len(sorted_x) - 1:
                col_boundaries.append(((sorted_x[i-1] + sorted_x[i]) / 2, float('inf')))
            else:
                col_boundaries.append(((sorted_x[i-1] + sorted_x[i]) / 2, (sorted_x[i] + sorted_x[i+1]) / 2))
        
        # Build table
        table_data = []
        
        for y in sorted_y[:20]:  # Limit to first 20 rows to avoid false positives
            row_data = [''] * len(col_boundaries)
            
            for item in rows[y]:
                # Find which column this text belongs to
                for col_idx, (start_x, end_x) in enumerate(col_boundaries):
                    if start_x <= item['x'] < end_x:
                        if row_data[col_idx]:
                            row_data[col_idx] += ' ' + item['text']
                        else:
                            row_data[col_idx] = item['text']
                        break
            
            # Only include rows that have data
            if any(cell.strip() for cell in row_data):
                table_data.append([cell.strip() for cell in row_data])
        
        return table_data
    
    def _format_detected_table(self, table_data):
        """
        Format detected table data as Markdown.
        
        Args:
            table_data: List of lists representing table rows
        
        Returns:
            Markdown table string or None
        """
        if not table_data or len(table_data) < 2:
            return None
        
        # Fix ligatures in all cells
        table_data = [[self._fix_ligatures(cell) for cell in row] for row in table_data]
        
        # Ensure all rows have the same number of columns
        max_cols = max(len(row) for row in table_data)
        table_data = [row + [''] * (max_cols - len(row)) for row in table_data]
        
        # First row is header
        headers = table_data[0]
        
        # Build markdown table
        header_row = " | ".join(headers)
        separator = " | ".join(["---"] * len(headers))
        
        data_rows = []
        for row in table_data[1:]:
            row_text = " | ".join(row[:len(headers)])
            data_rows.append(row_text)
        
        table_lines = [header_row, separator] + data_rows
        
        return "\n".join(table_lines)
    
    def _bbox_overlaps_tables(
        self, 
        bbox: Tuple[float, float, float, float],
        table_bboxes: List[Tuple[float, float, float, float]]
    ) -> bool:
        """
        Check if a bounding box overlaps with any table bounding box.
        
        Args:
            bbox: Block bounding box (x0, y0, x1, y1)
            table_bboxes: List of table bounding boxes
        
        Returns:
            True if there's significant overlap
        """
        if not table_bboxes:
            return False
        
        x0, y0, x1, y1 = bbox
        block_area = (x1 - x0) * (y1 - y0)
        
        for tx0, ty0, tx1, ty1 in table_bboxes:
            # Calculate intersection
            ix0 = max(x0, tx0)
            iy0 = max(y0, ty0)
            ix1 = min(x1, tx1)
            iy1 = min(y1, ty1)
            
            if ix0 < ix1 and iy0 < iy1:
                intersection_area = (ix1 - ix0) * (iy1 - iy0)
                
                # If more than 50% of block overlaps with table, consider it part of table
                if intersection_area > block_area * 0.5:
                    return True
        
        return False
    
    def extract_simple(
        self, 
        page_range: Optional[Tuple[int, int]] = None
    ) -> str:
        """
        Simple text extraction without structure analysis.
        
        Args:
            page_range: Optional tuple of (start_page, end_page) (1-indexed, inclusive)
        
        Returns:
            Plain text content
        """
        start_page, end_page = self._validate_page_range(page_range)
        text_parts = []
        
        for page_num in range(start_page, end_page + 1):
            page = self.doc[page_num - 1]
            text = page.get_text()
            text = self._fix_ligatures(text)
            text_parts.append(text)
        
        return "\n\n".join(text_parts)
    
    def _validate_page_range(
        self, 
        page_range: Optional[Tuple[int, int]]
    ) -> Tuple[int, int]:
        """
        Validate and normalize page range.
        
        Args:
            page_range: Optional tuple of (start_page, end_page) (1-indexed)
        
        Returns:
            Validated (start_page, end_page) tuple
        
        Raises:
            ValueError: If page range is invalid
        """
        if page_range is None:
            return (1, self.total_pages)
        
        start_page, end_page = page_range
        
        if start_page < 1:
            raise ValueError(f"Start page must be >= 1, got {start_page}")
        
        if end_page > self.total_pages:
            raise ValueError(
                f"End page {end_page} exceeds document length ({self.total_pages})"
            )
        
        if start_page > end_page:
            raise ValueError(
                f"Start page ({start_page}) cannot be greater than end page ({end_page})"
            )
        
        return (start_page, end_page)
    
    def _analyze_block(
        self, 
        block: dict, 
        preserve_emphasis: bool = True
    ) -> Optional[dict]:
        """
        Analyze a text block and return structured information.
        
        Args:
            block: PyMuPDF text block dictionary
            preserve_emphasis: Whether to preserve bold/italic formatting
        
        Returns:
            Dictionary with 'type', 'text', 'indent' keys, or None if empty
        """
        lines = block.get("lines", [])
        if not lines:
            return None
        
        # Get block positioning
        bbox = block.get("bbox", [0, 0, 0, 0])
        indent = bbox[0] if bbox else 0
        
        # Build the text with emphasis preserved
        text_parts = []
        
        for line in lines:
            line_text = self._process_line_with_emphasis(line, preserve_emphasis)
            if line_text.strip():
                text_parts.append(line_text)
        
        if not text_parts:
            return None
        
        full_text = " ".join(text_parts)
        full_text = self._fix_ligatures(full_text)
        
        # Determine block type
        block_type = self._classify_block(full_text, lines, indent)
        
        # Format the text based on type
        formatted_text = self._format_block(full_text, block_type)
        
        return {
            "type": block_type,
            "text": formatted_text,
            "indent": indent
        }
    
    def _process_line_with_emphasis(
        self, 
        line: dict, 
        preserve_emphasis: bool
    ) -> str:
        """
        Process a line and preserve emphasis (bold/italic) formatting.
        
        Args:
            line: PyMuPDF line dictionary
            preserve_emphasis: Whether to preserve formatting
        
        Returns:
            Text with markdown emphasis
        """
        if not preserve_emphasis:
            return "".join(span["text"] for span in line.get("spans", []))
        
        result = []
        spans = line.get("spans", [])
        
        for i, span in enumerate(spans):
            text = span["text"]
            flags = span.get("flags", 0)
            
            # Check for bold (bit 4) and italic (bit 1)
            is_bold = bool(flags & (1 << 4))
            is_italic = bool(flags & (1 << 1))
            
            # Also check font name for more accurate detection
            font = span.get("font", "").lower()
            if "bold" in font or "heavy" in font or "black" in font:
                is_bold = True
            if "italic" in font or "oblique" in font:
                is_italic = True
            
            # Don't mark single spaces as bold/italic
            if text.strip() == "":
                result.append(text)
                continue
            
            # Apply markdown formatting
            if is_bold and is_italic:
                text = f"***{text}***"
            elif is_bold:
                text = f"**{text}**"
            elif is_italic:
                text = f"*{text}*"
            
            result.append(text)
        
        return "".join(result)
    
    def _classify_block(
        self, 
        text: str, 
        lines: List[dict], 
        indent: float
    ) -> str:
        """
        Classify a block of text by its type with improved header detection.
        
        Args:
            text: The text content
            lines: Line dictionaries from PyMuPDF
            indent: Left indent position
        
        Returns:
            Block type string
        """
        # Get font characteristics
        total_size = 0
        span_count = 0
        bold_count = 0
        italic_count = 0
        
        for line in lines:
            for span in line.get("spans", []):
                size = span.get("size", 12)
                total_size += size
                span_count += 1
                
                flags = span.get("flags", 0)
                font = span.get("font", "").lower()
                
                # Check bold
                if (flags & (1 << 4)) or "bold" in font or "heavy" in font or "black" in font:
                    bold_count += 1
                
                # Check italic
                if (flags & (1 << 1)) or "italic" in font or "oblique" in font:
                    italic_count += 1
        
        if span_count == 0:
            return "paragraph"
        
        avg_size = total_size / span_count
        bold_ratio = bold_count / span_count
        italic_ratio = italic_count / span_count
        
        is_mostly_bold = bold_ratio > 0.7  # At least 70% of spans are bold
        is_mostly_italic = italic_ratio > 0.7
        is_all_caps = text.isupper() and len(text) > 3
        
        # Clean text for pattern matching (remove markdown formatting)
        clean_text = re.sub(r'\*\*\*?(.*?)\*\*\*?', r'\1', text)
        
        # ENHANCED HEADER DETECTION
        
        # Level 1: Large ALL CAPS titles
        if is_all_caps and len(clean_text) < 150:
            if avg_size > 16 or (avg_size > 12 and is_mostly_bold):
                return "heading1"
        
        # Level 2: Bold section headers
        if is_mostly_bold and len(clean_text) < 150:
            if avg_size > 12:
                return "heading2"
            elif avg_size > 10:
                return "heading3"
        
        # Detect specific header patterns (case-insensitive)
        header_patterns = [
            (r'^(TIER|LEVEL)\s+\d+', 'heading2'),
            (r'^(STEP|PART|CHAPTER)\s+\d+', 'heading3'),
            (r'^[A-Z][A-Z\s&]{4,}$', 'heading2'),  # ALL CAPS HEADERS
        ]
        
        for pattern, header_type in header_patterns:
            if re.match(pattern, clean_text, re.IGNORECASE):
                return header_type
        
        # Check for numbered lists (1., 2., 3., etc.)
        if re.match(r'^\d+[\.\)]\s', clean_text):
            return "list_numbered"
        
        # Check for lettered lists (a., b., c., etc.)
        if re.match(r'^[a-z][\.\)]\s', clean_text, re.IGNORECASE):
            return "list_lettered"
        
        # Check for bullet points
        bullet_chars = ["•", "◦", "○", "▪", "‣", "⁃", "→", "–", "—", "●"]
        if any(clean_text.startswith(char) for char in bullet_chars):
            return "list_bullet"
        
        # Check for markdown-style bullets
        if re.match(r'^[-*+]\s', clean_text):
            return "list_bullet"
        
        # Check for block quote (mostly italic, substantial text)
        if is_mostly_italic and len(clean_text) > 50:
            return "blockquote"
        
        # Default to paragraph
        return "paragraph"
    
    def _format_block(self, text: str, block_type: str) -> str:
        """
        Format text based on its block type.
        
        Args:
            text: The text content
            block_type: Type of block
        
        Returns:
            Markdown-formatted text
        """
        # Remove existing markdown formatting from headers to avoid double-marking
        if block_type.startswith("heading"):
            # Remove bold/italic markers but keep the text
            text = re.sub(r'\*\*\*([^\*]+)\*\*\*', r'\1', text)
            text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
            text = re.sub(r'\*([^\*]+)\*', r'\1', text)
        
        if block_type == "heading1":
            return f"# {text}"
        
        elif block_type == "heading2":
            return f"## {text}"
        
        elif block_type == "heading3":
            return f"### {text}"
        
        elif block_type == "list_numbered":
            return text
        
        elif block_type == "list_lettered":
            return f"   {text}"
        
        elif block_type == "list_bullet":
            # Normalize all bullets to markdown style
            bullet_chars = ["•", "◦", "○", "▪", "‣", "⁃", "→", "–", "—", "●"]
            for char in bullet_chars:
                if text.startswith(char):
                    clean_text = text[len(char):].strip()
                    return f"- {clean_text}"
            clean_text = re.sub(r'^[-*+]\s*', '', text)
            return f"- {clean_text}"
        
        elif block_type == "blockquote":
            return f"> {text}"
        
        else:  # paragraph
            return text
    
    def close(self):
        """Close the PDF document and free resources."""
        self.doc.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures document is closed."""
        self.close()