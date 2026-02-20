import os
import json
import base64
import asyncio
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, AsyncIterator
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
import httpx
from .models import AgentConfig, OrchestrationConfig

DEFAULT_TIMEOUT = float(os.environ.get("MEMBRIA_PROVIDER_TIMEOUT", "15"))

class Message(BaseModel):
    role: str  # user, assistant, system
    content: str

class CompletionResponse(BaseModel):
    content: str
    usage: Dict[str, int] = Field(default_factory=dict)
    finish_reason: Optional[str] = None

class BaseProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        auth_token: Optional[str] = None,
        auth_method: Optional[str] = None,
    ):
        self.api_key = api_key
        self.endpoint = endpoint
        self.auth_token = auth_token
        self.auth_method = auth_method

    @abstractmethod
    async def complete(
        self, 
        model: str, 
        messages: List[Message], 
        stream: bool = False,
        **kwargs
    ) -> AsyncIterator[str] | CompletionResponse:
        """Get completion from provider."""
        pass

class AnthropicProvider(BaseProvider):
    async def complete(self, model, messages, stream=False, **kwargs):
        # Phase 5: Routing via Membria Proxy for Plus/Pro or OAuth
        if not self.api_key and self.auth_token:
            if self.auth_method == "oauth":
                base = self.endpoint or "https://api.anthropic.com/v1/messages"
                url = f"{base}?beta=true"
                headers = {
                    "Authorization": f"Bearer {self.auth_token}",
                    "anthropic-version": "2023-06-01",
                    "anthropic-beta": "oauth-2025-04-20,interleaved-thinking-2025-05-14",
                    "user-agent": "claude-cli/2.1.2 (external, cli)",
                    "content-type": "application/json",
                }
            else:
                url = f"{self.endpoint or 'https://proxy.membria.ai'}/v1/anthropic/messages"
                headers = {
                    "Authorization": f"Bearer {self.auth_token}",
                    "X-Membria-Proxy": "true",
                    "content-type": "application/json"
                }
        else:
            url = self.endpoint or "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
        data = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages if m.role != "system"],
            "stream": stream,
            "max_tokens": kwargs.get("max_tokens", 4096)
        }
        
        # Add system prompt if present
        system_msg = next((m.content for m in messages if m.role == "system"), None)
        if system_msg:
            data["system"] = system_msg

        async with httpx.AsyncClient() as client:
            if stream:
                # Handle SSE streaming logic
                pass
            else:
                response = await client.post(url, headers=headers, json=data, timeout=DEFAULT_TIMEOUT)
                response.raise_for_status()
                res_data = response.json()
                return CompletionResponse(
                    content=res_data["content"][0]["text"],
                    usage={
                        "input_tokens": res_data["usage"]["input_tokens"],
                        "output_tokens": res_data["usage"]["output_tokens"]
                    }
                )

class OpenAIProvider(BaseProvider):
    async def complete(self, model, messages, stream=False, **kwargs):
        # Phase 5: Routing via Membria Proxy for Plus/Pro or OAuth
        if not self.api_key and self.auth_token:
            if self.auth_method == "oauth":
                url = self.endpoint or "https://chatgpt.com/backend-api/codex/responses"
                headers = {
                    "Authorization": f"Bearer {self.auth_token}",
                    "Content-Type": "application/json",
                    "openai-beta": "responses=experimental",
                    "originator": "codex_cli_rs",
                    "accept": "application/json",
                }
                account_id = _extract_openai_account_id(self.auth_token)
                if account_id:
                    headers["chatgpt-account-id"] = account_id
                data = {
                    "model": model,
                    "input": _messages_to_prompt(messages),
                    "stream": False,
                }
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, headers=headers, json=data, timeout=DEFAULT_TIMEOUT)
                    response.raise_for_status()
                    res_data = response.json()
                    content = _extract_openai_response_text(res_data)
                    return CompletionResponse(content=content, usage={})
            else:
                url = f"{self.endpoint or 'https://proxy.membria.ai'}/v1/openai/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.auth_token}",
                    "X-Membria-Proxy": "true",
                    "Content-Type": "application/json"
                }
        else:
            url = self.endpoint or "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        data = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": stream
        }
        
        async with httpx.AsyncClient() as client:
            if stream:
                pass
            else:
                response = await client.post(url, headers=headers, json=data, timeout=DEFAULT_TIMEOUT)
                response.raise_for_status()
                res_data = response.json()
                return CompletionResponse(
                    content=res_data["choices"][0]["message"]["content"],
                    usage={
                        "input_tokens": res_data["usage"].get("prompt_tokens", 0),
                        "output_tokens": res_data["usage"].get("completion_tokens", 0)
                    }
                )

class ClaudeCLIProvider(BaseProvider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._claude_bin = shutil.which("claude") or str(Path.home() / ".local" / "bin" / "claude")

    def _normalize_model(self, model: str) -> str:
        if not model:
            return model
        mapping = {
            "claude-opus-4.6": "claude-opus-4-6",
            "claude-sonnet-4.6": "claude-sonnet-4-6",
            "claude-haiku-4.5": "claude-haiku-4-5",
        }
        return mapping.get(model, model)

    async def complete(self, model, messages, stream=False, **kwargs):
        if stream:
            raise NotImplementedError("Streaming not supported for Claude CLI provider")
        if not self._claude_bin or not os.path.exists(self._claude_bin):
            raise RuntimeError("claude CLI not found. Install Claude Code or add it to PATH.")

        system_msg = next((m.content for m in messages if m.role == "system"), None)
        prompt = _messages_to_prompt(messages)
        cmd = [
            self._claude_bin,
            "--print",
            "--output-format",
            "json",
        ]
        if model:
            cmd += ["--model", self._normalize_model(model)]
        if system_msg:
            cmd += ["--append-system-prompt", system_msg]
        cmd.append(prompt)

        def _run():
            return subprocess.run(cmd, capture_output=True, text=True)

        result = await asyncio.to_thread(_run)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Claude CLI error")

        raw = (result.stdout or "").strip()
        if not raw:
            raise RuntimeError("Claude CLI returned empty response")
        # Claude CLI may output multiple lines; parse last JSON line
        data = None
        for line in reversed(raw.splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                break
            except Exception:
                continue
        if not isinstance(data, dict):
            raise RuntimeError("Claude CLI returned non-JSON output")
        if data.get("is_error"):
            raise RuntimeError(data.get("result") or "Claude CLI authentication error")
        content = data.get("result") if isinstance(data.get("result"), str) else data.get("result", "")
        return CompletionResponse(content=content or "", usage={})

class OllamaProvider(BaseProvider):
    async def complete(self, model, messages, stream=False, **kwargs):
        url = f"{self.endpoint or 'http://localhost:11434'}/api/chat"
        data = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": stream
        }
        
        async with httpx.AsyncClient() as client:
            if stream:
                pass
            else:
                response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
                response.raise_for_status()
                res_data = response.json()
                return CompletionResponse(
                    content=res_data["message"]["content"],
                    usage={
                        "input_tokens": res_data.get("prompt_eval_count", 0),
                        "output_tokens": res_data.get("eval_count", 0)
                    }
                )

class ProviderFactory:
    @staticmethod
    def get_provider(
        name: str,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        auth_token: Optional[str] = None,
        auth_method: Optional[str] = None,
    ) -> BaseProvider:
        name = name.lower()
        if name == "anthropic":
            if auth_method == "oauth" and not api_key:
                return ClaudeCLIProvider(api_key, endpoint, auth_token, auth_method)
            return AnthropicProvider(api_key, endpoint, auth_token, auth_method)
        elif name in ["openai", "kilocode", "kilo", "kilo-code", "openrouter"]:
            # These are OpenAI-compatible
            return OpenAIProvider(api_key, endpoint, auth_token, auth_method)
        elif name == "ollama":
            return OllamaProvider(api_key, endpoint, auth_token, auth_method)
        raise ValueError(f"Unknown provider: {name}")


def _extract_openai_account_id(access_token: Optional[str]) -> Optional[str]:
    if not access_token or "." not in access_token:
        return None
    try:
        payload_b64 = access_token.split(".")[1]
        padding = "=" * (-len(payload_b64) % 4)
        payload = base64.urlsafe_b64decode(payload_b64 + padding).decode("utf-8")
        data = json.loads(payload)
        return data.get("chatgpt_account_id")
    except Exception:
        return None


def _messages_to_prompt(messages: List[Message]) -> str:
    parts = []
    for m in messages:
        role = m.role.upper()
        parts.append(f"{role}:\n{m.content}")
    return "\n\n".join(parts)


def _extract_openai_response_text(data: Dict[str, Any]) -> str:
    if isinstance(data, dict):
        output = data.get("output")
        if isinstance(output, list):
            for item in output:
                content = item.get("content", [])
                if isinstance(content, list):
                    for c in content:
                        text = c.get("text")
                        if text:
                            return text
        if "choices" in data:
            try:
                return data["choices"][0]["message"]["content"]
            except Exception:
                pass
    return str(data)
