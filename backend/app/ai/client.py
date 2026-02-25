import logging

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

_client = None


def get_ai_client() -> AsyncOpenAI:
    global _client
    if _client is None or _client.api_key != settings.AI_API_KEY:
        _client = AsyncOpenAI(
            api_key=settings.AI_API_KEY,
            base_url=settings.AI_API_BASE_URL,
        )
    return _client


async def chat_completion(
    messages: list[dict],
    temperature: float | None = None,
    max_tokens: int | None = None,
    response_format: dict | None = None,
) -> dict:
    """Make a chat completion request and return the parsed response."""
    client = get_ai_client()

    kwargs = {
        "model": settings.AI_MODEL,
        "messages": messages,
        "temperature": temperature or settings.AI_TEMPERATURE,
        "max_tokens": max_tokens or settings.AI_MAX_TOKENS,
    }
    if response_format:
        kwargs["response_format"] = response_format

    response = await client.chat.completions.create(**kwargs)

    return {
        "content": response.choices[0].message.content,
        "tokens_used": response.usage.total_tokens if response.usage else 0,
        "model": response.model,
    }


async def chat_completion_stream(
    messages: list[dict],
    temperature: float | None = None,
    max_tokens: int | None = None,
):
    """Stream a chat completion response token by token."""
    client = get_ai_client()

    stream = await client.chat.completions.create(
        model=settings.AI_MODEL,
        messages=messages,
        temperature=temperature or settings.AI_TEMPERATURE,
        max_tokens=max_tokens or settings.AI_MAX_TOKENS,
        stream=True,
    )

    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
