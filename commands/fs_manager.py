"""
Safe File System Manager
Handles file operations with safety controls and path restrictions
"""

import asyncio
import os
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.safety import SafetyManager, SafePathManager

logger = logging.getLogger(__name__)

class FileSystemManager:
    """Manages file system operations with safety controls."""
    
    def __init__(self, safety_manager: SafetyManager):
        self.safety_manager = safety_manager
        self.safe_path_manager = SafePathManager()
    
    async def read_file(self, file_path: str, dry_run: bool = False) -> Dict[str, Any]:
        """Read file contents with safety checks."""
        try:
            path = Path(file_path).resolve()
            
            if dry_run:
                return {
                    'success': True,
                    'message': f'[DRY RUN] Would read file: {path}',
                    'content': ''
                }
            
            # Check if path is safe
            if not self.safe_path_manager.is_safe_path(str(path)):
                confirmation = await self.safety_manager.confirm_action(
                    'read_file', str(path),
                    f'Read file outside safe directories: {path}'
                )
                
                if not confirmation['allowed']:
                    return {
                        'success': False,
                        'message': 'File read cancelled - outside safe paths'
                    }
            
            # Check file size
            if path.stat().st_size > 5 * 1024 * 1024:  # 5MB
                confirmation = await self.safety_manager.confirm_action(
                    'read_large_file', str(path),
                    f'Read large file ({path.stat().st_size / 1024 / 1024:.1f}MB): {path}'
                )
                
                if not confirmation['allowed']:
                    return {
                        'success': False,
                        'message': 'Large file read cancelled'
                    }
            
            # Read file
            content = path.read_text(encoding='utf-8', errors='replace')
            
            return {
                'success': True,
                'message': f'Read file: {path}',
                'content': content,
                'size': path.stat().st_size
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to read file: {e}',
                'error': str(e)
            }
    
    async def write_file(self, file_path: str, content: str, dry_run: bool = False) -> Dict[str, Any]:
        """Write file with safety checks."""
        try:
            path = Path(file_path).resolve()
            
            if dry_run:
                return {
                    'success': True,
                    'message': f'[DRY RUN] Would write to file: {path}',
                    'content_length': len(content)
                }
            
            # Safety checks
            if not self.safe_path_manager.is_safe_path(str(path)):
                confirmation = await self.safety_manager.confirm_action(
                    'write_file', str(path),
                    f'Write file outside safe directories: {path}'
                )
                
                if not confirmation['allowed']:
                    return {
                        'success': False,
                        'message': 'File write cancelled - outside safe paths'
                    }
            
            # Create backup if file exists
            if path.exists():
                backup_path = path.with_suffix(path.suffix + '.backup')
                shutil.copy2(path, backup_path)
            
            # Write file
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
            
            return {
                'success': True,
                'message': f'Wrote file: {path}',
                'size': len(content.encode('utf-8'))
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to write file: {e}',
                'error': str(e)
            }
    
    def _resolve_directory_path(self, directory: str) -> str:
        """Resolve common directory names to actual Windows paths."""
        directory_lower = directory.lower().strip()
        
        # Windows desktop paths
        if directory_lower in ['desktop', 'the desktop', 'my desktop']:
            # Try different common desktop locations
            possible_desktops = [
                Path.home() / "Desktop",
                Path.home() / "OneDrive" / "Desktop",
                os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')
            ]
            
            for desktop_path in possible_desktops:
                if Path(desktop_path).exists():
                    return str(desktop_path)
            
            # Fallback to first option if none exist
            return str(possible_desktops[0])
        
        # Other common directory mappings
        directory_mappings = {
            'documents': str(Path.home() / "Documents"),
            'downloads': str(Path.home() / "Downloads"),
            'pictures': str(Path.home() / "Pictures"),
            'videos': str(Path.home() / "Videos"),
            'music': str(Path.home() / "Music"),
            'home': str(Path.home()),
            'current': os.getcwd(),
            'current directory': os.getcwd(),
            '.': os.getcwd(),
            '': os.getcwd()
        }
        
        return directory_mappings.get(directory_lower, directory)
    
    async def list_files(self, directory: str = ".", dry_run: bool = False) -> Dict[str, Any]:
        """List files in directory."""
        try:
            # Resolve directory path
            resolved_directory = self._resolve_directory_path(directory)
            
            path = Path(resolved_directory).resolve()
            
            if dry_run:
                return {
                    'success': True,
                    'message': f'[DRY RUN] Would list files in: {path}',
                    'files': []
                }
            
            files = []
            for item in path.iterdir():
                files.append({
                    'name': item.name,
                    'path': str(item),
                    'type': 'directory' if item.is_dir() else 'file',
                    'size': item.stat().st_size if item.is_file() else 0
                })
            
            return {
                'success': True,
                'message': f'Listed {len(files)} items in {path}',
                'files': files,
                'directory': str(path)
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to list files: {e}',
                'error': str(e)
            }
    
    async def find_file(self, pattern: str, directory: str = ".", dry_run: bool = False) -> Dict[str, Any]:
        """Find files matching pattern."""
        try:
            if directory == "" or directory == ".":
                directory = os.getcwd()
            
            path = Path(directory).resolve()
            
            if dry_run:
                return {
                    'success': True,
                    'message': f'[DRY RUN] Would search for "{pattern}" in: {path}',
                    'matches': []
                }
            
            matches = []
            for item in path.rglob(f"*{pattern}*"):
                matches.append({
                    'name': item.name,
                    'path': str(item),
                    'type': 'directory' if item.is_dir() else 'file'
                })
            
            return {
                'success': True,
                'message': f'Found {len(matches)} matches for "{pattern}"',
                'matches': matches,
                'pattern': pattern
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to find files: {e}',
                'error': str(e)
            }
