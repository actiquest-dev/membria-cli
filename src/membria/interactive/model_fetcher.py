"""
Dynamically fetch available models from LLM provider APIs.
"""

import asyncio
from typing import List, Dict, Optional
import aiohttp


class ModelFetcher:
    """Fetch available models from various LLM providers via their APIs."""
    
    async def fetch_anthropic_models(self, api_key: str) -> List[str]:
        """Fetch available Claude models from Anthropic."""
        if not api_key:
            return []
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "x-api-key": api_key
                }
                # Anthropic models are known, we can return standard ones
                # In future, check against their API if they add model listing
                return [
                    "claude-3-5-sonnet-latest",
                    "claude-3-5-haiku-latest",
                    "claude-3-opus-20250219",
                    "claude-3-sonnet-20250229",
                ]
        except Exception as e:
            print(f"Error fetching Anthropic models: {e}")
            return []
    
    async def fetch_openai_models(self, api_key: str) -> List[str]:
        """Fetch available models from OpenAI API."""
        if not api_key:
            return []
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {api_key}"}
                async with session.get(
                    "https://api.openai.com/v1/models",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Filter for GPT and relevant models
                        models = [
                            m["id"] for m in data.get("data", [])
                            if any(x in m["id"] for x in ["gpt-4", "gpt-3.5", "gpt-4o", "gpt-4-turbo"])
                        ]
                        return sorted(models, reverse=True)
        except Exception as e:
            print(f"Error fetching OpenAI models: {e}")
            return []
        
        return []
    
    async def fetch_kilo_models(self, endpoint: str, api_key: str) -> List[str]:
        """Fetch available models from Kilo provider."""
        if not api_key or not endpoint:
            return []
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {api_key}"}
                
                # Try standard /v1/models endpoint first
                try:
                    async with session.get(
                        f"{endpoint.rstrip('/')}/v1/models",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if "data" in data:
                                return [m.get("id") or m.get("name") for m in data.get("data", [])]
                except:
                    pass
                
                # Try /models endpoint
                try:
                    async with session.get(
                        f"{endpoint.rstrip('/')}/models",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if isinstance(data, list):
                                return [m.get("id") or m.get("name") for m in data]
                            elif "models" in data:
                                return [m.get("id") or m.get("name") for m in data.get("models", [])]
                except:
                    pass
                
        except Exception as e:
            print(f"Error fetching Kilo models: {e}")
        
        return []
    
    async def fetch_all_models(self, providers: Dict[str, Dict]) -> Dict[str, List[str]]:
        """Fetch available models for all configured providers."""
        result = {}
        tasks = []
        
        for name, config in providers.items():
            if not config.get("api_key"):
                continue
            
            provider_type = config.get("type", "").lower()
            
            if provider_type == "anthropic":
                tasks.append((name, self.fetch_anthropic_models(config["api_key"])))
            elif provider_type == "openai":
                tasks.append((name, self.fetch_openai_models(config["api_key"])))
            elif provider_type == "kilo":
                tasks.append((
                    name,
                    self.fetch_kilo_models(config.get("endpoint", ""), config["api_key"])
                ))
        
        # Execute all fetches concurrently
        if tasks:
            for name, task in tasks:
                try:
                    result[name] = await task
                except Exception as e:
                    print(f"Error fetching models for {name}: {e}")
                    result[name] = []
        
        return result
    
    def fetch_all_models_sync(self, providers: Dict[str, Dict]) -> Dict[str, List[str]]:
        """Synchronous wrapper for fetching models."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.fetch_all_models(providers))
