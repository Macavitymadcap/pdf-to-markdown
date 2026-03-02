"""
PDF slicing tool for extracting specific pages or ranges.
"""

from pathlib import Path
from typing import Optional, Tuple, List
import fitz  # PyMuPDF


class PDFSlicer:
    """Extract specific pages or ranges from a PDF document."""
    
    def __init__(self, pdf_path: str):
        """
        Initialize the slicer with a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
        """
        self.pdf_path = Path(pdf_path)
        self.doc = fitz.open(pdf_path)
        self.total_pages = len(self.doc)
    
    def slice_to_file(
        self,
        output_path: str,
        page_ranges: List[Tuple[int, int]]
    ) -> None:
        """
        Extract pages and save to a new PDF file.
        
        Args:
            output_path: Path for the output PDF file
            page_ranges: List of (start_page, end_page) tuples (1-indexed, inclusive)
        
        Raises:
            ValueError: If any page range is invalid
        """
        # Validate all ranges first
        validated_ranges = [self._validate_page_range(r) for r in page_ranges]
        
        # Create a new PDF document
        output_doc = fitz.open()
        
        # Insert pages from each range
        for start_page, end_page in validated_ranges:
            output_doc.insert_pdf(
                self.doc,
                from_page=start_page - 1,  # Convert to 0-indexed
                to_page=end_page - 1,      # Convert to 0-indexed
                start_at=-1                 # Append to end
            )
        
        # Save the output
        output_doc.save(output_path)
        output_doc.close()
    
    def get_page_count(self) -> int:
        """
        Get the total number of pages in the PDF.
        
        Returns:
            Total page count
        """
        return self.total_pages
    
    def _validate_page_range(
        self,
        page_range: Tuple[int, int]
    ) -> Tuple[int, int]:
        """
        Validate and normalize page range.
        
        Args:
            page_range: Tuple of (start_page, end_page) (1-indexed)
        
        Returns:
            Validated (start_page, end_page) tuple
        
        Raises:
            ValueError: If page range is invalid
        """
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
    
    def close(self):
        """Close the PDF document and free resources."""
        self.doc.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures document is closed."""
        self.close()