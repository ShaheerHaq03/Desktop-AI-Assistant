"""
Task Router - Routes parsed intents to appropriate command handlers
Implements safety checks and dry-run functionality
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime

from .safety import SafetyManager, CapabilityManager
from commands.open_apps import AppLauncher
from commands.fs_manager import FileSystemManager
from commands.process_manager import ProcessManager
from commands.window_control import WindowController

logger = logging.getLogger(__name__)

class TaskRouter:
    """Routes intents to appropriate handlers with safety controls."""
    
    def __init__(self, safety_manager: SafetyManager, 
                 capability_manager: CapabilityManager, 
                 dry_run: bool = True):
        self.safety_manager = safety_manager
        self.capability_manager = capability_manager
        self.dry_run = dry_run
        
        # Initialize command handlers
        self.app_launcher = AppLauncher()
        self.fs_manager = FileSystemManager(safety_manager)
        self.process_manager = ProcessManager(safety_manager)
        self.window_controller = WindowController()
        
        # Map intents to handlers
        self.intent_handlers = {
            'open_app': self._handle_open_app,
            'close_app': self._handle_close_app,
            'switch_app': self._handle_switch_app,
            'read_file': self._handle_read_file,
            'write_file': self._handle_write_file,
            'list_files': self._handle_list_files,
            'find_file': self._handle_find_file,
            'run_command': self._handle_run_command,
            'kill_process': self._handle_kill_process,
            'list_processes': self._handle_list_processes,
            'search_web': self._handle_search_web,
            'open_url': self._handle_open_url,
            'get_time': self._handle_get_time,
            'get_system_info': self._handle_get_system_info,
            'focus_window': self._handle_focus_window,
            'click_at': self._handle_click_at,
            'type_text': self._handle_type_text,
            'screenshot': self._handle_screenshot,
            'help': self._handle_help,
            'ask_for_clarification': self._handle_clarification,
            'exit': self._handle_exit
        }
        
        # Map intents to required capabilities
        self.intent_capabilities = {
            'open_app': 'window_control',
            'close_app': 'process_control',
            'switch_app': 'window_control',
            'read_file': 'fs',
            'write_file': 'fs',
            'list_files': 'fs',
            'find_file': 'fs',
            'run_command': 'run_shell',
            'kill_process': 'process_control',
            'list_processes': 'process_control',
            'search_web': 'browser_control',
            'open_url': 'browser_control',
            'get_time': None,  # No special capability required
            'get_system_info': 'system_info',
            'focus_window': 'window_control',
            'click_at': 'window_control',
            'type_text': 'window_control',
            'screenshot': 'screenshot',
            'help': None,
            'ask_for_clarification': None,
            'exit': None
        }
    
    async def execute(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an intent with safety checks."""
        start_time = time.time()
        
        try:
            # Validate intent structure
            if not self._validate_intent(intent):
                return {
                    'success': False,
                    'message': 'Invalid intent structure',
                    'error': 'Missing required fields',
                    'execution_time': time.time() - start_time
                }
            
            intent_type = intent['intent']
            target = intent['target']
            options = intent.get('options', {})
            
            # Check if capability is required and enabled
            required_capability = self.intent_capabilities.get(intent_type)
            if required_capability and not self.capability_manager.is_enabled(required_capability):
                return {
                    'success': False,
                    'message': f'Capability "{required_capability}" is not enabled',
                    'error': f'Intent "{intent_type}" requires capability "{required_capability}"',
                    'execution_time': time.time() - start_time
                }
            
            # Apply dry run override - always set the current mode
            options['dry_run'] = self.dry_run
            
            # Check if handler exists
            handler = self.intent_handlers.get(intent_type)
            if not handler:
                return {
                    'success': False,
                    'message': f'Unknown intent: {intent_type}',
                    'error': f'No handler for intent "{intent_type}"',
                    'execution_time': time.time() - start_time
                }
            
            # Execute the handler
            logger.info(f"Executing intent: {intent_type} with target: {target}")
            result = await handler(target, options)
            
            # Add execution metadata
            result['execution_time'] = time.time() - start_time
            result['timestamp'] = datetime.now().isoformat()
            result['intent_type'] = intent_type
            result['dry_run'] = options.get('dry_run', False)
            
            return result
            
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return {
                'success': False,
                'message': 'Task execution failed',
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    def _validate_intent(self, intent: Dict[str, Any]) -> bool:
        """Validate intent structure."""
        required_fields = ['intent', 'target', 'options']
        return all(field in intent for field in required_fields)
    
    # Intent handlers
    
    async def _handle_open_app(self, target: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Handle app opening intent."""
        try:
            result = await self.app_launcher.open_app(target, dry_run=options.get('dry_run', False))
            return {
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'details': result
            }
        except Exception as e:
            return {'success': False, 'message': f'Failed to open app: {e}'}
    
    async def _handle_close_app(self, target: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Handle app closing intent."""
        try:
            # This requires process control capability
            if options.get('dry_run', False):
                return {
                    'success': True,
                    'message': f'[DRY RUN] Would close app: {target}',
                    'action': 'close_app'
                }
            
            # Get confirmation for potentially disruptive action
            confirmation = await self.safety_manager.confirm_action(
                'close_app', target, 
                f'Close application "{target}" - this may lose unsaved work'
            )
            
            if not confirmation['allowed']:
                return {
                    'success': False,
                    'message': 'Action cancelled by user',
                    'reason': 'User denied permission'
                }
            
            result = await self.process_manager.kill_process_by_name(target)
            return {
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'details': result
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Failed to close app: {e}'}
    
    async def _handle_switch_app(self, target: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Handle app switching intent."""
        try:
            result = await self.window_controller.focus_window(target, dry_run=options.get('dry_run', False))
            return {
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'details': result
            }
        except Exception as e:
            return {'success': False, 'message': f'Failed to switch app: {e}'}
    
    async def _handle_read_file(self, target: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file reading intent."""
        try:
            result = await self.fs_manager.read_file(target, dry_run=options.get('dry_run', False))
            return {
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'content': result.get('content', ''),
                'details': result
            }
        except Exception as e:
            return {'success': False, 'message': f'Failed to read file: {e}'}
    
    async def _handle_write_file(self, target: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file writing intent."""
        try:
            content = options.get('content', '')
            if not content:
                return {
                    'success': False,
                    'message': 'No content specified for file write operation'
                }
            
            result = await self.fs_manager.write_file(
                target, content, dry_run=options.get('dry_run', False)
            )
            return {
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'details': result
            }
        except Exception as e:
            return {'success': False, 'message': f'Failed to write file: {e}'}
    
    async def _handle_list_files(self, target: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file listing intent."""
        try:
            result = await self.fs_manager.list_files(target, dry_run=options.get('dry_run', False))
            return {
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'files': result.get('files', []),
                'details': result
            }
        except Exception as e:
            return {'success': False, 'message': f'Failed to list files: {e}'}
    
    async def _handle_find_file(self, target: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file finding intent."""
        try:
            result = await self.fs_manager.find_file(target, dry_run=options.get('dry_run', False))
            return {
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'matches': result.get('matches', []),
                'details': result
            }
        except Exception as e:
            return {'success': False, 'message': f'Failed to find file: {e}'}
    
    async def _handle_run_command(self, target: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Handle shell command execution intent."""
        try:
            if options.get('dry_run', False):
                return {
                    'success': True,
                    'message': f'[DRY RUN] Would execute command: {target}',
                    'action': 'run_command'
                }
            
            # Shell commands require explicit confirmation
            confirmation = await self.safety_manager.confirm_action(
                'run_command', target,
                f'Execute shell command: {target} - This could potentially harm your system',
                requires_password=True
            )
            
            if not confirmation['allowed']:
                return {
                    'success': False,
                    'message': 'Command execution cancelled by user',
                    'reason': 'User denied permission'
                }
            
            # Execute command (implementation would go here)
            return {
                'success': True,
                'message': f'Command executed: {target}',
                'output': '[Command execution not implemented in demo]'
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Failed to execute command: {e}'}
    
    async def _handle_kill_process(self, target: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Handle process termination intent."""
        try:
            if options.get('dry_run', False):
                return {
                    'success': True,
                    'message': f'[DRY RUN] Would kill process: {target}',
                    'action': 'kill_process'
                }
            
            result = await self.process_manager.kill_process_by_name(target)
            return {
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'details': result
            }
        except Exception as e:
            return {'success': False, 'message': f'Failed to kill process: {e}'}
    
    async def _handle_list_processes(self, target: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Handle process listing intent."""
        try:
            result = await self.process_manager.list_processes(filter_name=target if target else None)
            return {
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'processes': result.get('processes', []),
                'details': result
            }
        except Exception as e:
            return {'success': False, 'message': f'Failed to list processes: {e}'}
    
    async def _handle_search_web(self, target: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Handle web search intent."""
        try:
            import webbrowser
            
            if options.get('dry_run', False):
                return {
                    'success': True,
                    'message': f'[DRY RUN] Would search web for: {target}',
                    'action': 'search_web'
                }
            
            search_url = f"https://www.google.com/search?q={target.replace(' ', '+')}"
            webbrowser.open(search_url)
            
            return {
                'success': True,
                'message': f'Opened web search for: {target}',
                'url': search_url
            }
        except Exception as e:
            return {'success': False, 'message': f'Failed to search web: {e}'}
    
    async def _handle_open_url(self, target: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Handle URL opening intent."""
        try:
            import webbrowser
            
            if options.get('dry_run', False):
                return {
                    'success': True,
                    'message': f'[DRY RUN] Would open URL: {target}',
                    'action': 'open_url'
                }
            
            webbrowser.open(target)
            return {
                'success': True,
                'message': f'Opened URL: {target}',
                'url': target
            }
        except Exception as e:
            return {'success': False, 'message': f'Failed to open URL: {e}'}
    
    async def _handle_get_time(self, target: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Handle time query intent."""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return {
                'success': True,
                'message': f'Current time: {current_time}',
                'time': current_time
            }
        except Exception as e:
            return {'success': False, 'message': f'Failed to get time: {e}'}
    
    async def _handle_get_system_info(self, target: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system info query intent."""
        try:
            import psutil
            import platform
            
            info = {
                'os': platform.system(),
                'os_version': platform.version(),
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent if platform.system() != 'Windows' else psutil.disk_usage('C:').percent
            }
            
            message = f"System: {info['os']} | CPU: {info['cpu_percent']}% | Memory: {info['memory_percent']}% | Disk: {info['disk_usage']}%"
            
            return {
                'success': True,
                'message': message,
                'system_info': info
            }
        except Exception as e:
            return {'success': False, 'message': f'Failed to get system info: {e}'}
    
    async def _handle_focus_window(self, target: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Handle window focusing intent."""
        try:
            result = await self.window_controller.focus_window(target, dry_run=options.get('dry_run', False))
            return {
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'details': result
            }
        except Exception as e:
            return {'success': False, 'message': f'Failed to focus window: {e}'}
    
    async def _handle_click_at(self, target: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Handle click at coordinates intent."""
        try:
            x = options.get('x', 0)
            y = options.get('y', 0)
            
            if x == 0 and y == 0 and target:
                # Try to parse coordinates from target
                try:
                    coords = target.split(',')
                    x = int(coords[0].strip())
                    y = int(coords[1].strip())
                except:
                    return {
                        'success': False,
                        'message': 'Invalid coordinates specified'
                    }
            
            result = await self.window_controller.click_at(x, y, dry_run=options.get('dry_run', False))
            return {
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'details': result
            }
        except Exception as e:
            return {'success': False, 'message': f'Failed to click: {e}'}
    
    async def _handle_type_text(self, target: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Handle text typing intent."""
        try:
            result = await self.window_controller.type_text(target, dry_run=options.get('dry_run', False))
            return {
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'details': result
            }
        except Exception as e:
            return {'success': False, 'message': f'Failed to type text: {e}'}
    
    async def _handle_screenshot(self, target: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Handle screenshot intent."""
        try:
            result = await self.window_controller.take_screenshot(target, dry_run=options.get('dry_run', False))
            return {
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'details': result
            }
        except Exception as e:
            return {'success': False, 'message': f'Failed to take screenshot: {e}'}
    
    async def _handle_help(self, target: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Handle help request intent."""
        help_text = """
Agent Desktop AI Extended - Available Commands:

🔧 Application Control:
- "open chrome" - Launch applications
- "close notepad" - Close applications  
- "switch to firefox" - Focus windows

📁 File Operations:
- "read file.txt" - Read file contents
- "list files in documents" - List directory
- "find readme" - Search for files

💻 System Operations:  
- "what time is it" - Get current time
- "show system status" - System information
- "list processes" - Show running processes

🌐 Web & URLs:
- "search for python tutorials" - Web search
- "open https://example.com" - Open URLs

🎮 GUI Control:
- "click at 100, 200" - Click coordinates
- "type hello world" - Type text
- "take screenshot" - Capture screen

⚙️ Settings:
- Toggle capabilities in the sidebar
- Enable/disable dry run mode
- View safety settings

Type your commands naturally - the AI will understand!
        """
        
        return {
            'success': True,
            'message': help_text.strip(),
            'help': True
        }
    
    async def _handle_clarification(self, target: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Handle clarification request intent."""
        message = options.get('message', "I didn't understand that command. Please rephrase or type 'help' for available commands.")
        
        return {
            'success': True,
            'message': message,
            'clarification': True
        }
    
    async def _handle_exit(self, target: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Handle exit intent."""
        return {
            'success': True,
            'message': 'Goodbye! Thanks for using Agent Desktop AI Extended.',
            'exit': True
        }
