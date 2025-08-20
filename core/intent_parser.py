"""
Intent Parser - Converts natural language to structured intent JSON
Handles language detection, translation, and intent classification
"""

import json
import re
import logging
from typing import Dict, Any, Optional
import asyncio

from .llm_client import OllamaClient, MockLLMClient

logger = logging.getLogger(__name__)

class IntentParser:
    """Parses natural language input into structured intent objects."""
    
    # Standard intent schema
    INTENT_SCHEMA = {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": [
                    "open_app", "close_app", "switch_app",
                    "read_file", "write_file", "list_files", "find_file",
                    "run_command", "kill_process", "list_processes",
                    "search_web", "open_url", "bookmark_url",
                    "play_media", "pause_media", "control_volume",
                    "get_time", "get_weather", "get_system_info",
                    "focus_window", "click_at", "type_text", "screenshot",
                    "ask_for_clarification", "help", "exit"
                ]
            },
            "target": {"type": "string"},
            "options": {"type": "object"}
        },
        "required": ["intent", "target", "options"]
    }
    
    # Common phrases and their intent mappings
    INTENT_PATTERNS = {
        # Application control
        r'\b(open|start|launch)\b.*\b(app|application|program)\b': 'open_app',
        r'\b(close|exit|quit)\b.*\b(app|application|program)\b': 'close_app',
        r'\bswitch to\b': 'switch_app',
        
        # File operations
        r'\b(read|open|show|display)\b.*\bfile\b': 'read_file',
        r'\b(write|create|save)\b.*\bfile\b': 'write_file',
        r'\b(list|show)\b.*\b(files|directory|folder)\b': 'list_files',
        r'\b(find|search)\b.*\bfile\b': 'find_file',
        
        # System operations
        r'\b(run|execute)\b.*\b(command|script)\b': 'run_command',
        r'\b(kill|stop|end)\b.*\bprocess\b': 'kill_process',
        r'\blist.*\bprocess': 'list_processes',
        r'\bsystem\b.*\b(info|status|stats)\b': 'get_system_info',
        
        # Web operations
        r'\b(search|google)\b': 'search_web',
        r'\bopen.*\b(url|website|link)\b': 'open_url',
        
        # Window/GUI control
        r'\bfocus.*\bwindow\b': 'focus_window',
        r'\bclick\b.*\bat\b': 'click_at',
        r'\btype\b.*\btext\b': 'type_text',
        r'\btake.*\bscreenshot\b': 'screenshot',
        
        # Time/info queries
        r'\b(what|current)\b.*\btime\b': 'get_time',
        r'\b(weather|temperature)\b': 'get_weather',
        
        # Media control
        r'\bplay\b.*\b(music|video|media)\b': 'play_media',
        r'\b(pause|stop)\b.*\b(music|video|media)\b': 'pause_media',
        r'\b(volume|sound)\b': 'control_volume',
        
        # Help and clarification
        r'\b(help|how|what can)\b': 'help',
        r'\b(exit|goodbye|bye)\b': 'exit'
    }
    
    def __init__(self, llm_client: Optional[OllamaClient] = None):
        self.llm_client = llm_client or OllamaClient()
        self._fallback_client = MockLLMClient()
        
    async def detect_language(self, text: str) -> str:
        """Detect the language of input text."""
        # Simple heuristic-based language detection
        # In a real implementation, you might use a proper language detection library
        
        # Common non-English patterns
        patterns = {
            'es': [r'¿', r'ñ', r'á|é|í|ó|ú', r'\bel\b|\bla\b|\bde\b|\ben\b'],
            'fr': [r'ç', r'à|é|è|ê|ë|î|ï|ô|ù|û|ü|ÿ', r'\ble\b|\bla\b|\bde\b|\bet\b'],
            'de': [r'ä|ö|ü|ß', r'\bder\b|\bdie\b|\bdas\b|\bund\b'],
            'it': [r'\bil\b|\bla\b|\bdi\b|\be\b|\bche\b'],
            'pt': [r'ã|õ', r'\bo\b|\ba\b|\bde\b|\bem\b'],
        }
        
        text_lower = text.lower()
        
        for lang, lang_patterns in patterns.items():
            score = sum(1 for pattern in lang_patterns if re.search(pattern, text_lower))
            if score >= 2:
                return lang
        
        return 'en'  # Default to English
    
    async def translate_to_english(self, text: str, source_lang: str) -> str:
        """Translate text to English if needed."""
        if source_lang == 'en':
            return text
        
        # Use LLM for translation
        prompt = f"""
Translate the following {source_lang} text to English. 
Provide only the English translation, no explanations:

{text}
"""
        
        try:
            # Try with real LLM first
            if await self.llm_client.is_available():
                translation = await self.llm_client.generate(prompt)
                if translation:
                    return translation
        except Exception as e:
            logger.warning(f"Translation failed: {e}")
        
        # Fallback to original text
        return text
    
    def _pattern_based_intent(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract intent using pattern matching as fallback."""
        text_lower = text.lower().strip()
        
        for pattern, intent in self.INTENT_PATTERNS.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                return self._build_intent_from_pattern(intent, text, pattern)
        
        return None
    
    def _build_intent_from_pattern(self, intent: str, text: str, pattern: str) -> Dict[str, Any]:
        """Build intent object from pattern match."""
        text_lower = text.lower()
        
        # Extract target based on intent type
        target = ""
        options = {"dry_run": True, "language": "en"}
        
        if intent == "open_app":
            # Extract app name after "open/start/launch"
            match = re.search(r'\b(open|start|launch)\s+(.*?)(?:\s+(app|application|program))?$', text_lower)
            if match:
                target = match.group(2).strip()
        
        elif intent == "read_file":
            # Extract file path/name
            match = re.search(r'\b(read|open|show|display)\s+(.*?)(?:\s+file)?$', text_lower)
            if match:
                target = match.group(2).strip()
        
        elif intent == "list_files":
            # Extract directory from "list files in <directory>"
            match = re.search(r'\b(list|show)\s+(?:files\s+)?(?:in\s+)?(.*?)(?:\s+(files|directory|folder))?$', text_lower)
            if match:
                potential_dir = match.group(2).strip()
                # Remove common words that aren't directory names
                potential_dir = re.sub(r'\b(files|in|the|directory|folder)\b', '', potential_dir).strip()
                if potential_dir:
                    target = potential_dir
                else:
                    target = "."
        
        elif intent == "search_web":
            # Extract search query
            match = re.search(r'\b(search|google)\s+(?:for\s+)?(.*)', text_lower)
            if match:
                target = match.group(2).strip()
        
        elif intent == "run_command":
            # Extract command
            match = re.search(r'\b(run|execute)\s+(.*?)(?:\s+(command|script))?$', text_lower)
            if match:
                target = match.group(2).strip()
                options["requires_confirmation"] = True
        
        elif intent == "type_text":
            # Extract text to type
            match = re.search(r'\btype\s+(.*)', text_lower)
            if match:
                target = match.group(1).strip()
        
        elif intent == "click_at":
            # Extract coordinates if present
            coord_match = re.search(r'(\d+)[,\s]+(\d+)', text)
            if coord_match:
                options["x"] = int(coord_match.group(1))
                options["y"] = int(coord_match.group(2))
        
        # If we couldn't extract a target, use the original text
        if not target:
            target = text.strip()
        
        return {
            "intent": intent,
            "target": target,
            "options": options
        }
    
    async def parse(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse natural language text into structured intent."""
        if not text or not text.strip():
            return None
        
        try:
            # Detect language
            language = await self.detect_language(text)
            logger.info(f"Detected language: {language}")
            
            # Translate to English if needed
            english_text = await self.translate_to_english(text, language)
            
            # Try LLM-based parsing first
            llm_intent = await self._llm_based_parse(english_text)
            if llm_intent:
                llm_intent["options"]["original_language"] = language
                llm_intent["options"]["original_text"] = text
                return llm_intent
            
            # Fallback to pattern-based parsing
            logger.info("Falling back to pattern-based intent parsing")
            pattern_intent = self._pattern_based_intent(english_text)
            if pattern_intent:
                pattern_intent["options"]["original_language"] = language
                pattern_intent["options"]["original_text"] = text
                return pattern_intent
            
            # Default fallback - ask for clarification
            return {
                "intent": "ask_for_clarification",
                "target": "",
                "options": {
                    "message": f"I'm not sure what you want me to do with: '{text}'",
                    "original_language": language,
                    "original_text": text,
                    "dry_run": True
                }
            }
        
        except Exception as e:
            logger.error(f"Intent parsing failed: {e}")
            return {
                "intent": "ask_for_clarification",
                "target": "",
                "options": {
                    "message": f"Error parsing intent: {str(e)}",
                    "dry_run": True
                }
            }
    
    async def _llm_based_parse(self, text: str) -> Optional[Dict[str, Any]]:
        """Use LLM to parse intent with structured output."""
        
        prompt = f"""
You are an AI assistant that converts natural language commands into structured JSON intents for a desktop automation system.

Analyze this user command and convert it to a JSON intent object:
"{text}"

Available intents:
- open_app: Launch applications (target: app name)
- close_app: Close applications (target: app name)  
- read_file: Read/display file contents (target: file path)
- write_file: Create/write files (target: file path, options.content: text)
- list_files: List directory contents (target: directory path)
- run_command: Execute system commands (target: command)
- get_time: Get current time
- get_system_info: Show system information
- search_web: Search the internet (target: search query)
- focus_window: Focus a window (target: window name)
- type_text: Type text (target: text to type)
- click_at: Click at coordinates (options.x, options.y)
- help: Show help information
- ask_for_clarification: When intent is unclear

Examples:
"open chrome" -> {{"intent": "open_app", "target": "chrome", "options": {{"dry_run": true}}}}
"what time is it" -> {{"intent": "get_time", "target": "", "options": {{"dry_run": true}}}}
"list files in documents" -> {{"intent": "list_files", "target": "documents", "options": {{"dry_run": true}}}}

Respond with ONLY the JSON object:
"""
        
        try:
            # Try with real LLM first
            if await self.llm_client.is_available():
                result = await self.llm_client.generate_structured(prompt, self.INTENT_SCHEMA)
                if result and self._validate_intent(result):
                    return result
        except Exception as e:
            logger.warning(f"LLM-based parsing failed: {e}")
        
        return None
    
    def _validate_intent(self, intent: Dict[str, Any]) -> bool:
        """Validate that the intent object has required fields."""
        required_fields = ["intent", "target", "options"]
        
        for field in required_fields:
            if field not in intent:
                logger.warning(f"Missing required field: {field}")
                return False
        
        # Validate intent type
        valid_intents = self.INTENT_SCHEMA["properties"]["intent"]["enum"]
        if intent["intent"] not in valid_intents:
            logger.warning(f"Invalid intent type: {intent['intent']}")
            return False
        
        # Ensure options is a dict
        if not isinstance(intent["options"], dict):
            intent["options"] = {}
        
        # Add default dry_run if not present
        if "dry_run" not in intent["options"]:
            intent["options"]["dry_run"] = True
        
        return True
    
    def get_available_intents(self) -> list:
        """Get list of available intent types."""
        return self.INTENT_SCHEMA["properties"]["intent"]["enum"]
    
    def get_intent_help(self, intent_type: str) -> str:
        """Get help text for a specific intent type."""
        help_text = {
            "open_app": "Launch an application. Example: 'open chrome'",
            "close_app": "Close an application. Example: 'close notepad'",
            "read_file": "Read file contents. Example: 'read file.txt'",
            "write_file": "Create or write to a file. Example: 'write hello world to file.txt'",
            "list_files": "List directory contents. Example: 'list files in documents'",
            "run_command": "Execute system command. Example: 'run ls -la'",
            "get_time": "Get current time. Example: 'what time is it'",
            "get_system_info": "Show system information. Example: 'show system status'",
            "search_web": "Search the internet. Example: 'search for python tutorials'",
            "focus_window": "Focus a window. Example: 'focus chrome window'",
            "type_text": "Type text. Example: 'type hello world'",
            "click_at": "Click at coordinates. Example: 'click at 100, 200'",
            "help": "Show help information. Example: 'help'",
            "ask_for_clarification": "Ask for clarification when intent is unclear"
        }
        
        return help_text.get(intent_type, "No help available for this intent.")
