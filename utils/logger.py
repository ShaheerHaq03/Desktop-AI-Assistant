"""
History Logger - Manages interaction history with rotation and size limits
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class HistoryLogger:
    """Logs user interactions and system responses with rotation."""
    
    def __init__(self, log_dir: str = None, max_size_mb: int = 5, max_files: int = 5):
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            self.log_dir = Path.home() / ".agent_desktop_ai" / "logs"
        
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.log_dir / "history.json"
        self.error_file = self.log_dir / "errors.json"
        
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_files = max_files
        
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup Python logging configuration."""
        log_file = self.log_dir / "agent.log"
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Create file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(formatter)
        
        # Get root logger and add handlers
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Add new handlers
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
    
    def log_interaction(self, user_input: str, intent: Dict[str, Any], result: Dict[str, Any]):
        """Log a complete user interaction."""
        try:
            entry = {
                'timestamp': time.time(),
                'datetime': datetime.now().isoformat(),
                'user_input': user_input,
                'intent': intent,
                'result': result,
                'success': result.get('success', False)
            }
            
            self._append_to_file(self.history_file, entry)
            self._rotate_if_needed(self.history_file)
            
            logger.info(f"Logged interaction: {intent.get('intent', 'unknown')} - {'SUCCESS' if entry['success'] else 'FAILED'}")
            
        except Exception as e:
            logger.error(f"Failed to log interaction: {e}")
    
    def log_error(self, error_message: str, context: Dict[str, Any] = None):
        """Log an error with optional context."""
        try:
            entry = {
                'timestamp': time.time(),
                'datetime': datetime.now().isoformat(),
                'error': error_message,
                'context': context or {}
            }
            
            self._append_to_file(self.error_file, entry)
            self._rotate_if_needed(self.error_file)
            
            logger.error(f"Logged error: {error_message}")
            
        except Exception as e:
            logger.error(f"Failed to log error: {e}")
    
    def _append_to_file(self, file_path: Path, entry: Dict[str, Any]):
        """Append entry to JSON file."""
        entries = []
        
        # Load existing entries
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    entries = json.load(f)
            except (json.JSONDecodeError, IOError):
                entries = []
        
        # Add new entry
        entries.append(entry)
        
        # Keep only last 1000 entries to prevent unbounded growth
        entries = entries[-1000:]
        
        # Save back to file
        with open(file_path, 'w') as f:
            json.dump(entries, f, indent=2, default=str)
    
    def _rotate_if_needed(self, file_path: Path):
        """Rotate log file if it exceeds size limit."""
        try:
            if not file_path.exists():
                return
            
            file_size = file_path.stat().st_size
            
            if file_size > self.max_size_bytes:
                logger.info(f"Rotating log file: {file_path}")
                
                # Create rotated filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                rotated_name = f"{file_path.stem}_{timestamp}.json"
                rotated_path = file_path.parent / rotated_name
                
                # Move current file to rotated name
                file_path.rename(rotated_path)
                
                # Clean up old rotated files
                self._cleanup_old_files(file_path)
                
        except Exception as e:
            logger.error(f"Failed to rotate log file: {e}")
    
    def _cleanup_old_files(self, base_file: Path):
        """Remove old rotated log files beyond max_files limit."""
        try:
            pattern = f"{base_file.stem}_*.json"
            rotated_files = list(base_file.parent.glob(pattern))
            
            # Sort by modification time (oldest first)
            rotated_files.sort(key=lambda f: f.stat().st_mtime)
            
            # Remove excess files
            while len(rotated_files) > self.max_files:
                old_file = rotated_files.pop(0)
                old_file.unlink()
                logger.info(f"Removed old log file: {old_file}")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old log files: {e}")
    
    def get_recent_interactions(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent user interactions."""
        try:
            if not self.history_file.exists():
                return []
            
            with open(self.history_file, 'r') as f:
                entries = json.load(f)
            
            return entries[-count:]
            
        except Exception as e:
            logger.error(f"Failed to get recent interactions: {e}")
            return []
    
    def get_recent_errors(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent errors."""
        try:
            if not self.error_file.exists():
                return []
            
            with open(self.error_file, 'r') as f:
                entries = json.load(f)
            
            return entries[-count:]
            
        except Exception as e:
            logger.error(f"Failed to get recent errors: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get usage statistics."""
        try:
            stats = {
                'total_interactions': 0,
                'successful_interactions': 0,
                'failed_interactions': 0,
                'total_errors': 0,
                'most_used_intents': {},
                'recent_activity': []
            }
            
            # Process history file
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
                
                stats['total_interactions'] = len(history)
                
                for entry in history:
                    if entry.get('success'):
                        stats['successful_interactions'] += 1
                    else:
                        stats['failed_interactions'] += 1
                    
                    intent_type = entry.get('intent', {}).get('intent', 'unknown')
                    stats['most_used_intents'][intent_type] = stats['most_used_intents'].get(intent_type, 0) + 1
                
                # Get recent activity (last 24 hours)
                current_time = time.time()
                one_day_ago = current_time - (24 * 60 * 60)
                
                stats['recent_activity'] = [
                    entry for entry in history
                    if entry.get('timestamp', 0) > one_day_ago
                ]
            
            # Process error file
            if self.error_file.exists():
                with open(self.error_file, 'r') as f:
                    errors = json.load(f)
                
                stats['total_errors'] = len(errors)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {'error': str(e)}
    
    def clear_history(self):
        """Clear all history files."""
        try:
            files_to_clear = [self.history_file, self.error_file]
            
            for file_path in files_to_clear:
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Cleared history file: {file_path}")
            
            # Also clear rotated files
            for pattern in ["history_*.json", "errors_*.json"]:
                for old_file in self.log_dir.glob(pattern):
                    old_file.unlink()
                    logger.info(f"Removed old file: {old_file}")
                    
        except Exception as e:
            logger.error(f"Failed to clear history: {e}")
    
    def export_history(self, output_file: str = None) -> str:
        """Export history to a file."""
        try:
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"agent_history_export_{timestamp}.json"
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'statistics': self.get_statistics(),
                'history': self.get_recent_interactions(1000),
                'errors': self.get_recent_errors(100)
            }
            
            output_path = Path(output_file)
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Exported history to: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to export history: {e}")
            return ""
