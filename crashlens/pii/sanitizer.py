"""
Sanitizer - Handle reading JSONL files and writing sanitized output
"""

import json
from pathlib import Path
from typing import Optional, List
from .remover import PIIRemover


class FileSanitizer:
    """Sanitize JSONL log files by removing PII."""
    
    def __init__(self, pii_types: Optional[List[str]] = None):
        """Initialize file sanitizer with PII types to remove."""
        self.remover = PIIRemover(pii_types)
    
    def sanitize_jsonl_file(
        self,
        input_file: str,
        output_file: Optional[str] = None,
        dry_run: bool = False
    ) -> dict:
        """
        Sanitize a JSONL file by removing PII.
        
        Args:
            input_file: Path to input JSONL file
            output_file: Path to output file (auto-generated if None)
            dry_run: If True, analyze without creating output file
            
        Returns:
            Dictionary with stats: {
                'input_file': str,
                'output_file': str or None,
                'records_processed': int,
                'pii_stats': dict
            }
        """
        input_path = Path(input_file)
        
        # Validate input file exists
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        # Generate output filename if not provided
        if output_file is None:
            output_file = str(input_path.parent / f"{input_path.stem}_sanitized{input_path.suffix}")
        
        output_path = Path(output_file)
        
        # Reset statistics
        self.remover.reset_stats()
        
        records_processed = 0
        sanitized_records = []
        
        # Read and process input file
        print(f"📖 Reading: {input_file}")
        
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        # Parse JSON line
                        record = json.loads(line)
                        
                        # Remove PII from record
                        sanitized_record = self.remover.remove_pii_from_dict(record, dry_run)
                        sanitized_records.append(sanitized_record)
                        
                        records_processed += 1
                        
                        # Show progress every 100 records
                        if records_processed % 100 == 0:
                            print(f"   Processed {records_processed} records...")
                            
                    except json.JSONDecodeError as e:
                        print(f"⚠️  Warning: Invalid JSON at line {line_num}: {e}")
                        continue
        
        except Exception as e:
            raise RuntimeError(f"Error reading input file: {e}")
        
        # Write sanitized output (unless dry run)
        if not dry_run:
            print(f"💾 Writing: {output_file}")
            
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    for record in sanitized_records:
                        f.write(json.dumps(record) + '\n')
            except Exception as e:
                raise RuntimeError(f"Error writing output file: {e}")
        
        # Get PII removal statistics
        pii_stats = self.remover.get_stats()
        total_pii_removed = sum(pii_stats.values())
        
        return {
            'input_file': str(input_path),
            'output_file': str(output_path) if not dry_run else None,
            'records_processed': records_processed,
            'pii_stats': pii_stats,
            'total_pii_removed': total_pii_removed
        }


class PIISanitizer:
    """Handle file I/O for PII removal operations."""
    
    def __init__(self, pii_types: Optional[List[str]] = None):
        """
        Initialize sanitizer.
        
        Args:
            pii_types: List of PII types to remove. If None, removes all types.
        """
        self.remover = PIIRemover(pii_types)
    
    def sanitize_file(
        self, 
        input_path: Path, 
        output_path: Optional[Path] = None,
        dry_run: bool = False
    ) -> dict:
        """
        Sanitize a JSONL file by removing PII.
        
        Args:
            input_path: Path to input JSONL file
            output_path: Path to output file. If None, generates default name
            dry_run: If True, only analyze without writing output
            
        Returns:
            Dictionary with statistics and output path
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        # Generate output path if not provided
        if output_path is None and not dry_run:
            output_path = self._generate_output_path(input_path)
        
        # Reset statistics
        self.remover.reset_stats()
        
        # Process file
        records_processed = 0
        sanitized_records = []
        
        with open(input_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # Parse JSON line
                    record = json.loads(line)
                    
                    # Remove PII
                    sanitized = self.remover.remove_pii_from_dict(record, dry_run)
                    sanitized_records.append(sanitized)
                    records_processed += 1
                    
                except json.JSONDecodeError as e:
                    print(f"Warning: Skipping invalid JSON at line {line_num}: {e}")
                    continue
        
        # Write output file if not dry run
        if not dry_run and output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                for record in sanitized_records:
                    f.write(json.dumps(record) + '\n')
        
        # Compile results
        stats = self.remover.get_stats()
        total_pii_found = sum(stats.values())
        
        result = {
            'records_processed': records_processed,
            'total_pii_found': total_pii_found,
            'pii_by_type': stats,
            'output_path': str(output_path) if output_path else None,
            'dry_run': dry_run
        }
        
        return result
    
    def _generate_output_path(self, input_path: Path) -> Path:
        """
        Generate output path based on input path.
        
        Args:
            input_path: Original input file path
            
        Returns:
            Generated output path with _sanitized suffix
        """
        stem = input_path.stem
        suffix = input_path.suffix
        parent = input_path.parent
        
        return parent / f"{stem}_sanitized{suffix}"
    
    def get_stats(self) -> dict:
        """Get current statistics."""
        return self.remover.get_stats()
