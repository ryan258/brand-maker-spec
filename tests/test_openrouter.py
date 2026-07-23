import json
from collections.abc import AsyncIterator

import httpx
import pytest

from brand_maker.openrouter import (
    ContextOverflow,
    ModelUnavailable,
    OpenRouterClient,
    ProviderError,
    ProviderRefusal,
)


def make_response(content: str) -> dict[str, object]:
    return {
        "id": "generation-1",
        "model": "test/model",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": content},
            }
        ],
    }


@pytest.mark.asyncio
async def test_generate_sends_bounded_json_request_without_leaking_key() -> None:
    observed: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        observed["authorization"] = request.headers["authorization"]
        observed["body"] = json.loads(request.content)
        return httpx.Response(200, json=make_response('{"brand_name":"Floogle"}'))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = OpenRouterClient(http=http, api_key="secret-test-key")
        content = await client.generate(brand_name="Floogle", model="test/model")

    assert content == '{"brand_name":"Floogle"}'
    assert observed["authorization"] == "Bearer secret-test-key"
    body = observed["body"]
    assert isinstance(body, dict)
    assert body["model"] == "test/model"
    assert body["temperature"] == 0.8
    assert body["max_tokens"] == 1500
    assert body["response_format"] == {"type": "json_object"}
    assert "secret-test-key" not in json.dumps(body)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (404, "not_found"),
        (429, "rate_limit_exceeded"),
        (502, "provider_unavailable"),
        (503, "provider_overloaded"),
    ],
)
async def test_generate_classifies_unavailable_models(status: int, error_type: str) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status,
            json={
                "error": {
                    "code": status,
                    "message": "model unavailable",
                    "metadata": {"error_type": error_type},
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = OpenRouterClient(http=http, api_key="test-key")
        with pytest.raises(ModelUnavailable):
            await client.generate(brand_name="Floogle", model="missing/model")


@pytest.mark.asyncio
async def test_generate_classifies_model_not_found_message_as_unavailable() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "error": {
                    "code": 400,
                    "message": "The requested model was not found",
                    "metadata": {"error_type": "invalid_request"},
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(ModelUnavailable):
            await OpenRouterClient(http=http, api_key="test-key").generate(
                brand_name="Floogle", model="missing/model"
            )


@pytest.mark.asyncio
async def test_generate_classifies_embedded_rate_limit_as_unavailable() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "error": {
                    "code": 429,
                    "message": "Provider returned error",
                },
                "choices": [],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(ModelUnavailable):
            await OpenRouterClient(http=http, api_key="test-key").generate(
                brand_name="Floogle", model="busy/model"
            )


@pytest.mark.asyncio
async def test_generate_classifies_context_overflow() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "error": {
                    "code": 400,
                    "message": "context length exceeded",
                    "metadata": {"error_type": "context_length_exceeded"},
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(ContextOverflow):
            await OpenRouterClient(http=http, api_key="test-key").generate(
                brand_name="Floogle", model="test/model"
            )


@pytest.mark.asyncio
async def test_generate_classifies_provider_refusal() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "error": {
                    "code": 400,
                    "message": "refused",
                    "metadata": {"error_type": "refusal"},
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(ProviderRefusal):
            await OpenRouterClient(http=http, api_key="test-key").generate(
                brand_name="Floogle", model="test/model"
            )


@pytest.mark.asyncio
async def test_generate_preserves_http_status_when_embedded_code_differs() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={
                "error": {
                    "code": "provider_policy",
                    "message": "request declined",
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(ProviderRefusal):
            await OpenRouterClient(http=http, api_key="test-key").generate(
                brand_name="Floogle", model="test/model"
            )


@pytest.mark.asyncio
async def test_generate_detects_error_embedded_in_http_200_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "error": {
                    "code": 502,
                    "message": "provider disconnected",
                    "metadata": {"error_type": "provider_unavailable"},
                },
                "choices": [],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(ModelUnavailable):
            await OpenRouterClient(http=http, api_key="test-key").generate(
                brand_name="Floogle", model="test/model"
            )


@pytest.mark.asyncio
async def test_generate_rejects_malformed_success_envelope() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(ProviderError, match="malformed"):
            await OpenRouterClient(http=http, api_key="test-key").generate(
                brand_name="Floogle", model="test/model"
            )


@pytest.mark.asyncio
async def test_complete_supports_a_custom_judge_prompt() -> None:
    observed: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        observed.update(json.loads(request.content))
        return httpx.Response(200, json=make_response('{"overall":4.5}'))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        content = await OpenRouterClient(http=http, api_key="test-key").complete(
            messages=[{"role": "system", "content": "Judge this."}],
            model="judge/model",
            temperature=0.0,
            max_tokens=300,
        )

    assert content == '{"overall":4.5}'
    assert observed["messages"] == [{"role": "system", "content": "Judge this."}]
    assert observed["temperature"] == 0.0
    assert observed["max_tokens"] == 300


class CountingStream(httpx.AsyncByteStream):
    def __init__(self) -> None:
        self.chunks_read = 0

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for _ in range(3):
            self.chunks_read += 1
            yield b"x" * 600_000


@pytest.mark.asyncio
async def test_complete_stops_reading_when_response_exceeds_limit() -> None:
    stream = CountingStream()

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=stream)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(ProviderError, match="safety limit"):
            await OpenRouterClient(http=http, api_key="test-key").complete(
                messages=[{"role": "user", "content": "test"}],
                model="test/model",
                temperature=0.0,
                max_tokens=10,
            )

    assert stream.chunks_read == 2
