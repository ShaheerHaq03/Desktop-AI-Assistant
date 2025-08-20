"""
Ollama LLM Client for local AI inference
Handles communication with Ollama API at localhost:11434
"""

import asyncio
import json
import time
from typing import Optional, Dict, Any
import httpx
import logging

logger = logging.getLogger(__name__)

class OllamaClient:
    """Client for communicating with Ollama local API."""
    
    def __init__(self, base_url="http://localhost:11434", model="gemma3:12b", timeout=30):
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def is_available(self) -> bool:
        """Check if Ollama server is running and accessible."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama server not available: {e}")
            return False
    
    async def list_models(self) -> list:
        """List available models on the Ollama server."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            return []
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
    
    async def generate(self, prompt: str, max_retries=3) -> Optional[str]:
        """Generate text using Ollama with retry logic."""
        for attempt in range(max_retries):
            try:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_tokens": 1000
                    }
                }
                
                start_time = time.time()
                response = await self.client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    duration = time.time() - start_time
                    logger.info(f"LLM response received in {duration:.2f}s")
                    return result.get("response", "").strip()
                else:
                    logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                    
            except asyncio.TimeoutError:
                logger.warning(f"LLM request timeout (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                logger.error(f"LLM request failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        return None
    
    async def generate_structured(self, prompt: str, schema: Dict[str, Any], max_retries=3) -> Optional[Dict]:
        """Generate structured JSON response using Ollama."""
        # Add JSON formatting instruction to prompt
        structured_prompt = f"""
{prompt}

Please respond with a valid JSON object that follows this schema:
{json.dumps(schema, indent=2)}

Your response should be ONLY the JSON object, no additional text or explanations.
"""
        
        for attempt in range(max_retries):
            try:
                response_text = await self.generate(structured_prompt, max_retries=1)
                if not response_text:
                    continue
                
                # Try to extract JSON from response
                response_text = response_text.strip()
                
                # Handle cases where LLM adds extra text
                if "```json" in response_text:
                    start = response_text.find("```json") + 7
                    end = response_text.find("```", start)
                    response_text = response_text[start:end].strip()
                elif "{" in response_text and "}" in response_text:
                    start = response_text.find("{")
                    end = response_text.rfind("}") + 1
                    response_text = response_text[start:end]
                
                # Parse JSON
                try:
                    result = json.loads(response_text)
                    return result
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON response (attempt {attempt + 1}): {e}")
                    logger.debug(f"Raw response: {response_text[:200]}...")
                    
            except Exception as e:
                logger.error(f"Structured generation failed (attempt {attempt + 1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
        
        logger.error("Failed to generate valid structured response after all retries")
        return None
    
    async def chat(self, messages: list, max_retries=3) -> Optional[str]:
        """Chat interface for conversation-style interactions."""
        try:
            # Convert messages to a single prompt
            prompt_parts = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    prompt_parts.append(f"Human: {content}")
                elif role == "assistant":
                    prompt_parts.append(f"Assistant: {content}")
                elif role == "system":
                    prompt_parts.append(f"System: {content}")
            
            prompt = "\n".join(prompt_parts) + "\nAssistant:"
            
            response = await self.generate(prompt, max_retries)
            return response
            
        except Exception as e:
            logger.error(f"Chat request failed: {e}")
            return None
    
    def set_model(self, model: str):
        """Change the model used for generation."""
        self.model = model
        logger.info(f"Switched to model: {model}")
    
    async def pull_model(self, model: str) -> bool:
        """Pull a model from Ollama registry."""
        try:
            payload = {"name": model}
            response = await self.client.post(
                f"{self.base_url}/api/pull",
                json=payload
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to pull model {model}: {e}")
            return False

# Singleton instance for convenience
_default_client = None

def get_default_client() -> OllamaClient:
    """Get or create the default Ollama client."""
    global _default_client
    if _default_client is None:
        _default_client = OllamaClient()
    return _default_client

# Fallback implementation for when Ollama is not available
class MockLLMClient:
    """Mock LLM client for testing and fallback scenarios."""
    
    def __init__(self):
        self.model = "mock"
    
    async def is_available(self) -> bool:
        return True
    
    async def generate(self, prompt: str, max_retries=3) -> str:
        """Generate mock responses for testing."""
        logger.warning("Using mock LLM client - Ollama not available")
        
        if "intent" in prompt.lower() or "json" in prompt.lower():
            return """{
                "intent": "ask_for_clarification",
                "target": "",
                "options": {
                    "message": "I'm a mock AI assistant. Please install and start Ollama to use real AI capabilities."
                }
            }"""
        
        return "I'm a mock AI assistant. Please install and start Ollama for full functionality."
    
    async def generate_structured(self, prompt: str, schema: Dict[str, Any], max_retries=3) -> Dict:
        """Generate mock structured responses."""
        return {
            "intent": "ask_for_clarification",
            "target": "",
            "options": {
                "message": "Mock response - Ollama not available"
            }
        }
    
    async def chat(self, messages: list, max_retries=3) -> str:
        return "Mock response - please install Ollama for real AI capabilities."
    
    def set_model(self, model: str):
        self.model = model
