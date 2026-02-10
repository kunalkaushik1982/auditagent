"""
Annotator Engine for Word Documents.
File: backend/app/core/annotator.py

This module handles the injection of inline audits/comments into Word documents.
"""

import logging
import os
from typing import List, Dict, Any
from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.shared import RGBColor

logger = logging.getLogger(__name__)

class Annotator:
    """
    Handles the annotation of Word documents with audit findings.
    """
    
    def __init__(self):
        pass
        
    def annotate_document(self, original_path: str, findings: List[Dict[str, Any]]) -> str:
        """
        Open document, inject findings as highlights/comments, and save as new file.
        
        Args:
            original_path: Path to the original .docx file
            findings: List of finding dictionaries (must contain 'quote', 'description', 'severity')
            
        Returns:
            Path to the annotated document
        """
        if not os.path.exists(original_path):
            raise FileNotFoundError(f"Document not found: {original_path}")
            
        try:
            doc = Document(original_path)
            logger.info(f"Opened document for annotation: {original_path}")
            
            annotated_count = 0
            
            for finding in findings:
                quote = finding.get('quote')
                
                # If no quote or quote is "N/A", skip inline annotation (it will be in the report)
                if not quote or len(quote) < 5 or "N/A" in quote:
                    continue
                    
                # Search and Highlight
                if self._highlight_text(doc, quote, finding):
                    annotated_count += 1
            
            # Save properly
            base, ext = os.path.splitext(original_path)
            output_path = f"{base}_annotated{ext}"
            doc.save(output_path)
            
            logger.info(f"Saved annotated document: {output_path} ({annotated_count} annotations)")
            return output_path
            
        except Exception as e:
            logger.error(f"Error annotating document: {e}", exc_info=True)
            raise

    def _highlight_text(self, doc, quote: str, finding: Dict[str, Any]) -> bool:
        """
        Search for quote in document and highlight it.
        Returns True if found and highlighted.
        """
        # Clean quotes (sometimes AI adds quotes around the text)
        clean_quote = quote.strip('"').strip("'").strip()
        
        for paragraph in doc.paragraphs:
            if clean_quote in paragraph.text:
                # Found the paragraph! 
                # Identifying exact run is hard, so for MVP we append a comment 
                # to the paragraph text directly in a distinct format.
                
                # 1. Add visual highlight to the paragraph (or try to find run)
                # For MVP: We will append the finding to the end of the paragraph in [RED]
                
                run = paragraph.add_run(f"\n[AUDIT {finding.get('finding_type', 'issue').upper()}: {finding.get('description', '')}]")
                run.bold = True
                
                # Color code based on severity/type
                severity = finding.get('severity', 'medium').lower()
                if severity == 'critical':
                    run.font.highlight_color = WD_COLOR_INDEX.RED
                    run.font.color.rgb = RGBColor(255, 255, 255)
                elif severity == 'high':
                    run.font.highlight_color = WD_COLOR_INDEX.DARK_RED
                    run.font.color.rgb = RGBColor(255, 255, 255)
                elif severity == 'medium':
                    run.font.highlight_color = WD_COLOR_INDEX.YELLOW
                else:
                    run.font.highlight_color = WD_COLOR_INDEX.BRIGHT_GREEN
                
                return True
                
        return False
