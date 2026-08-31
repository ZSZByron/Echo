"""Unit tests for ImageGenerator module."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.ai.image_generator import (
    GeneratedImage,
    ImageGenerationError,
    ImageGenerator,
)


# -- Helpers ------------------------------------------------------------------


def _mock_response(status_code: int = 200, json_data: dict | None = None) -> httpx.Response:
    """Create a mock httpx.Response."""
    return httpx.Response(
        status_code=status_code,
        json=json_data or {},
        request=httpx.Request("POST", "https://example.com"),
    )


# -- Init tests ---------------------------------------------------------------


def test_init_invalid_provider() -> None:
    """Raises ImageGenerationError for unknown provider."""
    with patch.dict(os.environ, {"IMAGE_PROVIDER": "dalle"}):
        with pytest.raises(ImageGenerationError, match="Invalid IMAGE_PROVIDER"):
            ImageGenerator()


def test_init_zhipu_missing_key() -> None:
    """Raises ImageGenerationError when ZHIPU_API_KEY is not set."""
    with patch.dict(os.environ, {"IMAGE_PROVIDER": "zhipu", "ZHIPU_API_KEY": ""}, clear=False):
        # Ensure key is empty
        env = {"IMAGE_PROVIDER": "zhipu", "ZHIPU_API_KEY": ""}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ImageGenerationError, match="ZHIPU_API_KEY"):
                ImageGenerator()


def test_init_wanxiang_missing_key() -> None:
    """Raises ImageGenerationError when WANXIANG_API_KEY is not set."""
    env = {"IMAGE_PROVIDER": "wanxiang", "WANXIANG_API_KEY": ""}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ImageGenerationError, match="WANXIANG_API_KEY"):
            ImageGenerator()


def test_init_zhipu_success() -> None:
    """Creates ImageGenerator with zhipu provider."""
    env = {"IMAGE_PROVIDER": "zhipu", "ZHIPU_API_KEY": "test-key-123"}
    with patch.dict(os.environ, env, clear=True):
        gen = ImageGenerator()
        assert gen._provider == "zhipu"
        assert gen._api_key == "test-key-123"


def test_init_wanxiang_success() -> None:
    """Creates ImageGenerator with wanxiang provider."""
    env = {"IMAGE_PROVIDER": "wanxiang", "WANXIANG_API_KEY": "test-key-456"}
    with patch.dict(os.environ, env, clear=True):
        gen = ImageGenerator()
        assert gen._provider == "wanxiang"
        assert gen._api_key == "test-key-456"


def test_init_defaults_to_zhipu() -> None:
    """Defaults to zhipu provider when IMAGE_PROVIDER not set."""
    env = {"ZHIPU_API_KEY": "test-key"}
    with patch.dict(os.environ, env, clear=True):
        gen = ImageGenerator()
        assert gen._provider == "zhipu"


# -- Zhipu generation tests ---------------------------------------------------


@pytest.mark.asyncio
async def test_call_zhipu_success() -> None:
    """Zhipu API returns image URL."""
    env = {"IMAGE_PROVIDER": "zhipu", "ZHIPU_API_KEY": "test-key"}
    with patch.dict(os.environ, env, clear=True):
        gen = ImageGenerator()

    mock_resp = _mock_response(
        json_data={"data": [{"url": "https://img.example.com/abc.png"}]}
    )
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.is_closed = False

    gen._client = mock_client
    result = await gen._call_zhipu("a cyberpunk city", "1024x1024", 42)

    assert isinstance(result, GeneratedImage)
    assert result.seed == 42
    assert result.url == "https://img.example.com/abc.png"
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert "cogview-3-plus" in str(call_args)


@pytest.mark.asyncio
async def test_call_zhipu_empty_data() -> None:
    """Zhipu API returns no images -- raises ImageGenerationError."""
    env = {"IMAGE_PROVIDER": "zhipu", "ZHIPU_API_KEY": "test-key"}
    with patch.dict(os.environ, env, clear=True):
        gen = ImageGenerator()

    mock_resp = _mock_response(json_data={"data": []})
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.is_closed = False
    gen._client = mock_client

    with pytest.raises(ImageGenerationError, match="no images"):
        await gen._call_zhipu("test", "1024x1024", 1)


@pytest.mark.asyncio
async def test_call_zhipu_http_error() -> None:
    """Zhipu API returns HTTP 500 -- raises httpx error."""
    env = {"IMAGE_PROVIDER": "zhipu", "ZHIPU_API_KEY": "test-key"}
    with patch.dict(os.environ, env, clear=True):
        gen = ImageGenerator()

    mock_resp = httpx.Response(
        status_code=500,
        request=httpx.Request("POST", "https://example.com"),
    )
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.is_closed = False
    gen._client = mock_client

    with pytest.raises(httpx.HTTPStatusError):
        await gen._call_zhipu("test", "1024x1024", 1)


# -- Wanxiang generation tests -------------------------------------------------


@pytest.mark.asyncio
async def test_call_wanxiang_success() -> None:
    """Wanxiang API returns image URL."""
    env = {"IMAGE_PROVIDER": "wanxiang", "WANXIANG_API_KEY": "test-key"}
    with patch.dict(os.environ, env, clear=True):
        gen = ImageGenerator()

    mock_resp = _mock_response(
        json_data={
            "output": {
                "results": [{"url": "https://img.example.com/wanx.png"}]
            }
        }
    )
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.is_closed = False
    gen._client = mock_client

    result = await gen._call_wanxiang(
        "neon lights", "blurry", "1024x1024", 99
    )

    assert isinstance(result, GeneratedImage)
    assert result.seed == 99
    assert result.url == "https://img.example.com/wanx.png"


@pytest.mark.asyncio
async def test_call_wanxiang_async_task() -> None:
    """Wanxiang returns task_id when no results."""
    env = {"IMAGE_PROVIDER": "wanxiang", "WANXIANG_API_KEY": "test-key"}
    with patch.dict(os.environ, env, clear=True):
        gen = ImageGenerator()

    mock_resp = _mock_response(
        json_data={"output": {"task_id": "task-abc-123"}}
    )
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.is_closed = False
    gen._client = mock_client

    result = await gen._call_wanxiang("neon", "", "1024x1024", 1)
    assert result.url == "dashscope://task/task-abc-123"


@pytest.mark.asyncio
async def test_call_wanxiang_no_data() -> None:
    """Wanxiang returns no data -- raises ImageGenerationError."""
    env = {"IMAGE_PROVIDER": "wanxiang", "WANXIANG_API_KEY": "test-key"}
    with patch.dict(os.environ, env, clear=True):
        gen = ImageGenerator()

    mock_resp = _mock_response(json_data={"output": {}})
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.is_closed = False
    gen._client = mock_client

    with pytest.raises(ImageGenerationError, match="no image data"):
        await gen._call_wanxiang("test", "", "1024x1024", 1)


@pytest.mark.asyncio
async def test_call_wanxiang_http_error() -> None:
    """Wanxiang HTTP error is wrapped in ImageGenerationError."""
    env = {"IMAGE_PROVIDER": "wanxiang", "WANXIANG_API_KEY": "test-key"}
    with patch.dict(os.environ, env, clear=True):
        gen = ImageGenerator()

    mock_resp = httpx.Response(
        status_code=429,
        text="Rate limited",
        request=httpx.Request("POST", "https://example.com"),
    )
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.is_closed = False
    gen._client = mock_client

    with pytest.raises(ImageGenerationError, match="429"):
        await gen._call_wanxiang("test", "", "1024x1024", 1)


# -- Generate batch tests ------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_zhipu_batch(tmp_path: Path) -> None:
    """Generate batch with zhipu, verify metadata saved."""
    env = {"IMAGE_PROVIDER": "zhipu", "ZHIPU_API_KEY": "test-key"}
    with patch.dict(os.environ, env, clear=True):
        gen = ImageGenerator()

    mock_resp = _mock_response(
        json_data={"data": [{"url": "https://img.example.com/img.png"}]}
    )
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.is_closed = False
    gen._client = mock_client

    # Patch _META_DIR to use tmp_path and skip download (unit test focuses on generation)
    meta_dir = tmp_path / "meta"
    with (
        patch("app.ai.image_generator._META_DIR", meta_dir),
        patch("app.utils.gen_helpers.ASSETS_META_DIR", meta_dir),
        patch.object(gen, "_download_image", side_effect=lambda img, *a, **kw: img),
    ):
        results = await gen.generate(
            prompt="cyberpunk terminal",
            negative_prompt="blurry",
            size="1024x1024",
            seed=100,
            num_candidates=3,
            asset_id="asset_001",
        )

    assert len(results) == 3
    for i, img in enumerate(results):
        assert isinstance(img, GeneratedImage)
        assert img.seed == 100 + i

    # Verify meta files were written
    meta_files = list(meta_dir.glob("asset_001_*.json"))
    assert len(meta_files) == 3

    meta = json.loads(meta_files[0].read_text(encoding="utf-8"))
    assert meta["seed"] == 100
    assert meta["prompt"] == "cyberpunk terminal"
    assert meta["negative_prompt"] == "blurry"
    assert meta["provider"] == "zhipu"


@pytest.mark.asyncio
async def test_generate_partial_failure(tmp_path: Path) -> None:
    """Batch continues when individual images fail."""
    env = {"IMAGE_PROVIDER": "zhipu", "ZHIPU_API_KEY": "test-key"}
    with patch.dict(os.environ, env, clear=True):
        gen = ImageGenerator()

    ok_resp = _mock_response(
        json_data={"data": [{"url": "https://img.example.com/ok.png"}]}
    )
    err_resp = httpx.Response(
        status_code=500,
        request=httpx.Request("POST", "https://example.com"),
    )
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(
        side_effect=[ok_resp, err_resp, ok_resp]
    )
    mock_client.is_closed = False
    gen._client = mock_client

    with (
        patch("app.ai.image_generator._META_DIR", tmp_path / "meta"),
        patch.object(gen, "_download_image", side_effect=lambda img, *a, **kw: img),
    ):
        results = await gen.generate(
            prompt="test",
            num_candidates=3,
            asset_id="asset_002",
        )

    # 2 succeeded, 1 failed but was caught
    assert len(results) == 2


@pytest.mark.asyncio
async def test_generate_random_seed_when_none(tmp_path: Path) -> None:
    """When seed is None, random seeds are generated for each candidate."""
    env = {"IMAGE_PROVIDER": "zhipu", "ZHIPU_API_KEY": "test-key"}
    with patch.dict(os.environ, env, clear=True):
        gen = ImageGenerator()

    mock_resp = _mock_response(
        json_data={"data": [{"url": "https://img.example.com/r.png"}]}
    )
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.is_closed = False
    gen._client = mock_client

    with (
        patch("app.ai.image_generator._META_DIR", tmp_path / "meta"),
        patch.object(gen, "_download_image", side_effect=lambda img, *a, **kw: img),
    ):
        results = await gen.generate(
            prompt="test",
            num_candidates=2,
        )

    assert len(results) == 2
    # Seeds should be random (not sequential 0, 1)
    # At minimum they should be ints
    for img in results:
        assert isinstance(img.seed, int)


@pytest.mark.asyncio
async def test_generate_seed_capped_for_dashscope(tmp_path: Path) -> None:
    """Regression: DashScope (qwen/wanxiang) rejects seed > 2^31-1
    (2147483647, max signed int32) with HTTP 400 InvalidParameter,
    which makes the whole batch come back empty ('no images generated').
    generate() must cap every seed sent to the provider to <= 2^31-1.
    """
    env = {"IMAGE_PROVIDER": "qwen", "QWEN_API_KEY": "test-key"}
    with patch.dict(os.environ, env, clear=True):
        gen = ImageGenerator()

    mock_resp = _mock_response(
        json_data={
            "output": {
                "choices": [
                    {"message": {"content": [{"image": "https://img.example.com/x.png"}]}}
                ]
            }
        }
    )
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.is_closed = False
    gen._client = mock_client

    with (
        patch("app.ai.image_generator._META_DIR", tmp_path / "meta"),
        patch.object(gen, "_download_image", side_effect=lambda img, *a, **kw: img),
    ):
        # Explicit oversized seed -> must be capped in the provider payload.
        results = await gen.generate(prompt="x", seed=2**32, num_candidates=1)

    assert len(results) == 1
    sent_payload = mock_client.post.call_args.kwargs["json"]
    assert sent_payload["parameters"]["seed"] <= 2147483647


@pytest.mark.asyncio
async def test_generate_no_meta_when_no_asset_id(tmp_path: Path) -> None:
    """No meta files written when asset_id is empty."""
    env = {"IMAGE_PROVIDER": "zhipu", "ZHIPU_API_KEY": "test-key"}
    with patch.dict(os.environ, env, clear=True):
        gen = ImageGenerator()

    mock_resp = _mock_response(
        json_data={"data": [{"url": "https://img.example.com/x.png"}]}
    )
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.is_closed = False
    gen._client = mock_client

    meta_dir = tmp_path / "meta"
    with (
        patch("app.ai.image_generator._META_DIR", meta_dir),
        patch.object(gen, "_download_image", side_effect=lambda img, *a, **kw: img),
    ):
        results = await gen.generate(
            prompt="test",
            num_candidates=1,
            asset_id="",
        )

    assert len(results) == 1
    # No meta files should be written
    assert len(list(meta_dir.glob("*.json"))) == 0


# -- GeneratedImage model tests ------------------------------------------------


def test_generated_image_defaults() -> None:
    """GeneratedImage has correct defaults."""
    img = GeneratedImage(seed=42)
    assert img.seed == 42
    assert img.image_data == b""
    assert img.url is None
    assert img.file_path is None


def test_generated_image_with_data() -> None:
    """GeneratedImage can hold all fields."""
    img = GeneratedImage(
        seed=123,
        image_data=b"\x89PNG",
        url="https://example.com/img.png",
        file_path="/path/to/img.png",
    )
    assert img.seed == 123
    assert img.image_data == b"\x89PNG"
    assert img.url == "https://example.com/img.png"
    assert img.file_path == "/path/to/img.png"


# -- Lazy client init ----------------------------------------------------------


@pytest.mark.asyncio
async def test_lazy_client_init() -> None:
    """HTTP client is created lazily on first use."""
    env = {"IMAGE_PROVIDER": "zhipu", "ZHIPU_API_KEY": "test-key"}
    with patch.dict(os.environ, env, clear=True):
        gen = ImageGenerator()

    assert gen._client is None

    mock_resp = _mock_response(
        json_data={"data": [{"url": "https://img.example.com/lazy.png"}]}
    )
    mock_instance = AsyncMock()
    mock_instance.post = AsyncMock(return_value=mock_resp)
    mock_instance.is_closed = False

    with patch("httpx.AsyncClient", return_value=mock_instance) as mock_client_cls:
        await gen._call_zhipu("test", "1024x1024", 1)

    # Client was created
    mock_client_cls.assert_called_once()


@pytest.mark.asyncio
async def test_close() -> None:
    """close() calls aclose on the client."""
    env = {"IMAGE_PROVIDER": "zhipu", "ZHIPU_API_KEY": "test-key"}
    with patch.dict(os.environ, env, clear=True):
        gen = ImageGenerator()

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.is_closed = False
    gen._client = mock_client

    await gen.close()
    mock_client.aclose.assert_awaited_once()

    # Double close should be safe
    mock_client.is_closed = True
    await gen.close()
    # aclose should NOT be called again
    assert mock_client.aclose.call_count == 1