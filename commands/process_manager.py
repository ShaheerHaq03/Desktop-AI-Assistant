"""
Safe Process Manager
Handles process listing and termination with safety controls
"""

import asyncio
import logging
from typing import Dict, Any, List
import psutil

from core.safety import SafetyManager

logger = logging.getLogger(__name__)

class ProcessManager:
    """Manages process operations with safety controls."""
    
    def __init__(self, safety_manager: SafetyManager):
        self.safety_manager = safety_manager
        
        # Critical processes that should never be killed
        self.protected_processes = {
            'system', 'kernel', 'init', 'systemd', 'csrss.exe', 'wininit.exe',
            'winlogon.exe', 'lsass.exe', 'services.exe', 'svchost.exe'
        }
    
    async def list_processes(self, filter_name: str = None) -> Dict[str, Any]:
        """List running processes."""
        try:
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
                try:
                    proc_info = proc.info
                    
                    # Filter by name if specified
                    if filter_name and filter_name.lower() not in proc_info['name'].lower():
                        continue
                    
                    processes.append({
                        'pid': proc_info['pid'],
                        'name': proc_info['name'],
                        'cpu_percent': proc_info['cpu_percent'] or 0,
                        'memory_mb': proc_info['memory_info'].rss / 1024 / 1024 if proc_info['memory_info'] else 0
                    })
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by CPU usage
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            
            return {
                'success': True,
                'message': f'Found {len(processes)} processes',
                'processes': processes[:20],  # Limit to top 20
                'total_count': len(processes)
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to list processes: {e}',
                'error': str(e)
            }
    
    async def kill_process_by_name(self, name: str) -> Dict[str, Any]:
        """Kill process by name with safety checks."""
        try:
            name_lower = name.lower()
            
            # Check if process is protected
            if any(protected in name_lower for protected in self.protected_processes):
                return {
                    'success': False,
                    'message': f'Cannot kill protected system process: {name}',
                    'reason': 'protected_process'
                }
            
            # Find matching processes
            matching_procs = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if name_lower in proc.info['name'].lower():
                        matching_procs.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if not matching_procs:
                return {
                    'success': False,
                    'message': f'No processes found matching: {name}',
                    'reason': 'not_found'
                }
            
            # Get user confirmation
            proc_names = [p.info['name'] for p in matching_procs]
            confirmation = await self.safety_manager.confirm_action(
                'kill_process', name,
                f'Kill {len(matching_procs)} process(es): {", ".join(proc_names)}'
            )
            
            if not confirmation['allowed']:
                return {
                    'success': False,
                    'message': 'Process termination cancelled by user',
                    'reason': 'user_cancelled'
                }
            
            # Terminate processes
            killed_count = 0
            errors = []
            
            for proc in matching_procs:
                try:
                    proc.terminate()
                    killed_count += 1
                except Exception as e:
                    errors.append(str(e))
            
            # Wait for termination
            await asyncio.sleep(2)
            
            # Force kill if still running
            for proc in matching_procs:
                try:
                    if proc.is_running():
                        proc.kill()
                except:
                    pass
            
            result = {
                'success': killed_count > 0,
                'message': f'Terminated {killed_count} process(es)',
                'killed_count': killed_count,
                'process_names': proc_names
            }
            
            if errors:
                result['errors'] = errors
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to kill process: {e}',
                'error': str(e)
            }
    
    async def get_system_resources(self) -> Dict[str, Any]:
        """Get system resource usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'success': True,
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / 1024 / 1024 / 1024,
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / 1024 / 1024 / 1024
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to get system resources: {e}',
                'error': str(e)
            }
