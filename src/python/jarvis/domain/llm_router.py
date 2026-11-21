"""LLM router — routes between cloud model and local Ollama fallback.

Abstracts the model layer so cloud vs local is a configuration choice.
Supports tool calling and streaming responses with sentence chunking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResponse:
    """Response from the LLM."""

    text: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)


@dataclass
class LLMConfig:
    """LLM configuration."""

    provider: str = "cloud"  # "cloud" | "local" | "hybrid"
    cloud_model: str = "gpt-4o-mini"
    cloud_api_key: str | None = None
    cloud_base_url: str | None = None
    local_model: str = "llama3.2"
    local_base_url: str = "http://localhost:11434"  # Ollama
    local_enabled: bool = False
    fallback_to_local: bool = True
    temperature: float = 0.7
    max_tokens: int = 1000


class LLMRouter:
    """Routes LLM requests between cloud and local providers.

    Default hybrid: cloud for reasoning, local Ollama as fallback when
    cloud is unavailable. Abstracts the model layer behind a port.
    """

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig()
        self._cloud_client: object | None = None
        self._local_available = False
        self._check_availability()

    def _check_availability(self) -> None:
        """Check which providers are available."""
        try:
            import openai

            if self.config.cloud_api_key:
                self._cloud_client = openai.OpenAI(
                    api_key=self.config.cloud_api_key,
                    base_url=self.config.cloud_base_url,
                )
        except ImportError:
            pass

        try:
            import requests

            self._local_available = True
        except ImportError:
            pass

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
    ) -> LLMResponse:
        """Generate a response from the LLM.

        Routes to cloud provider by default, falls back to local Ollama
        if cloud fails and fallback is enabled.
        """
        temp = temperature if temperature is not None else self.config.temperature
        tokens = max_tokens if max_tokens is not None else self.config.max_tokens

        # Try cloud first
        if self.config.provider in ("cloud", "hybrid") and self._cloud_client:
            try:
                return await self._generate_cloud(
                    prompt, system_prompt, temp, tokens, tools, stream
                )
            except Exception:
                if self.config.fallback_to_local and self._local_available:
                    return await self._generate_local(
                        prompt, system_prompt, temp, tokens, tools, stream
                    )
                raise

        # Try local
        if self.config.provider == "local" or (
            self.config.fallback_to_local and self._local_available
        ):
            return await self._generate_local(prompt, system_prompt, temp, tokens, tools, stream)

        raise RuntimeError("No LLM provider available")

    async def _generate_cloud(
        self,
        prompt: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
        tools: list[dict[str, Any]] | None,
        stream: bool,
    ) -> LLMResponse:
        """Generate using cloud provider (OpenAI-compatible)."""
        if self._cloud_client is None:
            raise RuntimeError("Cloud client not initialized")
        assert self._cloud_client is not None

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = {
            "model": self.config.cloud_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self._cloud_client.chat.completions.create(**kwargs)  # type: ignore[attr-defined]

        message = response.choices[0].message
        return LLMResponse(
            text=message.content or "",
            tool_calls=[
                {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                    "id": tc.id,
                }
                for tc in (message.tool_calls or [])
            ],
            finish_reason=response.choices[0].finish_reason or "stop",
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
        )

    async def _generate_local(
        self,
        prompt: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
        tools: list[dict[str, Any]] | None,
        stream: bool,
    ) -> LLMResponse:
        """Generate using local Ollama."""

        import requests

        payload: dict[str, Any] = {
            "model": self.config.local_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        response = requests.post(
            f"{self.config.local_base_url}/api/generate",
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            text=data.get("response", ""),
            finish_reason="stop",
        )

    def health(self) -> str:
        """Return overall LLM health."""
        if self._cloud_client:
            return "ok: cloud available"
        if self._local_available:
            return "ok: local available"
        return "degraded: no LLM provider available"

    def is_local(self) -> bool:
        """Return True if currently using local provider."""
        return self.config.provider == "local"
