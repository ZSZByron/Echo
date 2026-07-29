"""AI image generation runtime module.

Provides async provider wrappers for Zhipu (CogView-3-Plus) and Wanxiang (DashScope),
with background removal and seed management for the Echo cyberpunk terminal demo.

Provider SDKs (rembg, zhipuai) are NOT hard dependencies -- all are lazily imported
inside functions so the module can be imported without them installed.
"""

from __future__ import annotations

import json
import logging
import os
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Absolute path for meta file storage and image output
_META_DIR = Path(r"H:\UGC\data\assets\meta")
_OUTPUT_DIR = Path(r"H:\UGC\data\assets")
_CANDIDATES_DIR = _OUTPUT_DIR / "candidates"


# -- Exceptions ----------------------------------------------------------------

class ImageGenerationError(Exception):
    """Raised when image generation fails due to config or API errors."""


# -- Models --------------------------------------------------------------------

class GeneratedImage(BaseModel):
    """Result of a single image generation call.

    Attributes:
        seed: The seed used (or generated) for this image.
        image_data: Raw image bytes (PNG/JPEG).
        url: Optional URL if the provider returns a URL instead of bytes.
        file_path: Optional local file path if saved to disk.
    """

    seed: int
    image_data: bytes = b""
    url: Optional[str] = None
    file_path: Optional[str] = None


# -- Image Generator -----------------------------------------------------------

class ImageGenerator:
    """Async image generation with multiple provider backends.

    Supported providers:
        - "zhipu": CogView-3-Plus via Zhipu API
        - "wanxiang": DashScope image synthesis API (支持万相2.7)
        - "qwen": DashScope multimodal-generation API (qwen-image-2.0-pro)
        - "local": Local fallback generator with cyberpunk placeholders

    Reads configuration from environment variables:
        - IMAGE_PROVIDER: provider name (default "zhipu")
        - ZHIPU_API_KEY: API key for Zhipu
        - WANXIANG_API_KEY: API key for Wanxiang (DashScope)
        - WANXIANG_MODEL: Model name for Wanxiang (default "flux-dev", supports "flux-dev", "wanx-v1" etc)
        - QWEN_API_KEY: API key for Qwen/DashScope (same key as WANXIANG_API_KEY)
    """

    _VALID_PROVIDERS = frozenset({"zhipu", "wanxiang", "qwen", "local"})

    def __init__(self) -> None:
        self._provider = os.environ.get("IMAGE_PROVIDER", "zhipu").strip().lower()
        if self._provider not in self._VALID_PROVIDERS:
            raise ImageGenerationError(
                f"Invalid IMAGE_PROVIDER '{self._provider}'. "
                f"Must be one of: {', '.join(sorted(self._VALID_PROVIDERS))}"
            )

        self._api_key: str = ""
        self._model: str = ""  # 添加模型名称配置
        
        if self._provider == "zhipu":
            self._api_key = os.environ.get("ZHIPU_API_KEY", "").strip()
            self._model = "cogview-3-plus"  # 智谱默认模型
            if not self._api_key:
                raise ImageGenerationError(
                    "ZHIPU_API_KEY environment variable is not set."
                )
        elif self._provider == "wanxiang":
            self._api_key = os.environ.get("WANXIANG_API_KEY", "").strip()
            self._model = os.environ.get("WANXIANG_MODEL", "flux-dev").strip()  # 万相2.7默认模型
            if not self._api_key:
                raise ImageGenerationError(
                    "WANXIANG_API_KEY environment variable is not set."
                )
        elif self._provider == "qwen":
            # qwen-image-2.0-pro 通过 DashScope multimodal-generation API 调用
            # 复用 QWEN_API_KEY 或 WANXIANG_API_KEY（同一个 DashScope key）
            self._api_key = os.environ.get("QWEN_API_KEY", "").strip()
            if not self._api_key:
                self._api_key = os.environ.get("WANXIANG_API_KEY", "").strip()
            if not self._api_key:
                raise ImageGenerationError(
                    "QWEN_API_KEY (or WANXIANG_API_KEY) environment variable is not set."
                )
            self._model = os.environ.get("QWEN_IMAGE_MODEL", "qwen-image-2.0-pro").strip()
        elif self._provider == "local":
            # Local provider doesn't need API key
            pass

        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy-init the async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    async def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        size: str = "1024x1024",
        seed: Optional[int] = None,
        num_candidates: int = 4,
        asset_id: str = "",
        asset_name: str = "",
        reference_asset_ids: list[str] | None = None,
    ) -> list[GeneratedImage]:
        """Generate multiple image candidates.

        For each candidate, generates a random seed if none provided, calls the
        provider API, and saves seed + prompt metadata to disk.

        Per-image failures are logged and skipped -- the batch continues.

        Args:
            prompt: Text prompt for image generation.
            negative_prompt: Negative prompt (avoided content).
            size: Image size string, e.g. "1024x1024".
            seed: Optional base seed. Each candidate gets seed + i.
            num_candidates: Number of images to generate.
            asset_id: Asset identifier for metadata file naming.

            reference_asset_ids: Optional list of asset IDs for style reference.

        Returns:
            List of successfully generated images (may be fewer than num_candidates).
        """
        if reference_asset_ids is None:
            reference_asset_ids = []

        from app.config.features import SCENE_CONSISTENCY
        if not SCENE_CONSISTENCY:
            reference_asset_ids = []

        _META_DIR.mkdir(parents=True, exist_ok=True)

        results: list[GeneratedImage] = []

        for i in range(num_candidates):
            candidate_seed = (
                (seed + i) if seed is not None else random.randint(0, 2**32 - 1)
            )
            try:
                if self._provider == "zhipu":
                    img = await self._call_zhipu(prompt, size, candidate_seed)
                elif self._provider == "wanxiang":
                    img = await self._call_wanxiang(
                        prompt, negative_prompt, size, candidate_seed
                    )
                elif self._provider == "qwen":
                    img = await self._call_qwen(
                        prompt, negative_prompt, size, candidate_seed,
                        reference_asset_ids=reference_asset_ids,
                    )
                elif self._provider == "local":
                    img = await self._call_local(
                        prompt, negative_prompt, size, candidate_seed, asset_id, i, asset_name
                    )
                else:
                    raise ImageGenerationError(
                        f"Unknown provider: {self._provider}"
                    )

                # Download remote URL to local file so frontend can display it
                img = await self._download_image(img, asset_id, i, asset_name)

                results.append(img)
                self._save_meta(
                    asset_id, i, candidate_seed, prompt, negative_prompt, size
                )
            except Exception as exc:
                logger.warning(
                    "Image generation failed for candidate %d (seed=%d): %s",
                    i,
                    candidate_seed,
                    exc,
                )

        return results

    def _save_meta(
        self,
        asset_id: str,
        index: int,
        seed: int,
        prompt: str,
        negative_prompt: str,
        size: str,
    ) -> None:
        """Save generation metadata to JSON file."""
        if not asset_id:
            return

        meta = {
            "seed": seed,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "size": size,
            "provider": self._provider,
        }
        filepath = _META_DIR / f"{asset_id}_{index}.json"
        filepath.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    async def _call_local(
        self,
        prompt: str,
        negative_prompt: str,
        size: str,
        seed: int,
        asset_id: str,
        index: int,
        asset_name: str = "",
    ) -> GeneratedImage:
        """Call local fallback generator.
        
        Creates cyberpunk-style placeholder images with prompt information
        and automatically opens them for viewing.
        """
        from app.ai.local_generator import get_local_generator
        
        local_gen = get_local_generator()
        width, height = self._parse_size(size)
        
        # Generate local image with prompts
        image_path = await local_gen._create_cyberpunk_placeholder(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            seed=seed,
            asset_id=asset_id,
            index=index,
            asset_name=asset_name,
        )
        
        return GeneratedImage(
            seed=seed,
            image_data=b"",
            url=None,
            file_path=str(image_path)
        )

    async def _call_zhipu(
        self, prompt: str, size: str, seed: int
    ) -> GeneratedImage:
        """Call Zhipu CogView-3-Plus API.

        POST https://open.bigmodel.cn/api/paas/v4/images/generations
        """
        client = await self._get_client()
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": "cogview-3-plus",
            "prompt": prompt,
            "size": size,
        }
        resp = await client.post(
            "https://open.bigmodel.cn/api/paas/v4/images/generations",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

        images = data.get("data", [])
        if not images:
            raise ImageGenerationError("Zhipu API returned no images.")

        url = images[0].get("url", "")
        return GeneratedImage(seed=seed, url=url if url else None)

    async def _call_wanxiang(
        self,
        prompt: str,
        negative_prompt: str,
        size: str,
        seed: int,
    ) -> GeneratedImage:
        """Call Wanxiang (DashScope) image synthesis API.

        POST https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis
        """
        client = await self._get_client()
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }
        payload: dict[str, Any] = {
            "model": self._model,  # 使用配置的模型名称（支持flux-dev, wanx-v1等）
            "input": {
                "prompt": prompt,
            },
            "parameters": {
                "size": size,
                "seed": seed,
            },
        }
        if negative_prompt:
            payload["input"]["negative_prompt"] = negative_prompt

        try:
            resp = await client.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

            output = data.get("output", {})
            results = output.get("results", [])
            if results:
                url = results[0].get("url", "")
                return GeneratedImage(seed=seed, url=url if url else None)

            task_id = output.get("task_id", "")
            if task_id:
                return GeneratedImage(seed=seed, url=f"dashscope://task/{task_id}")

            raise ImageGenerationError("Wanxiang API returned no image data.")
        except httpx.HTTPStatusError as exc:
            raise ImageGenerationError(
                f"Wanxiang API error {exc.response.status_code}: {exc.response.text}"
            ) from exc

    async def _call_qwen(
        self,
        prompt: str,
        negative_prompt: str,
        size: str,
        seed: int,
        reference_asset_ids: list[str] | None = None,
    ) -> GeneratedImage:
        """Call Qwen image generation via DashScope multimodal-generation API.

        Uses the messages-based multimodal endpoint (NOT the text2image endpoint).
        Model defaults to qwen-image-2.0-pro.

        Supports 3-level reference degradation:
            Level 1: base64 reference image embedded in message
            Level 2: Style profile extracted from reference prompt and injected
            Level 3: No reference (original prompt as-is)

        POST https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation
        """
        if reference_asset_ids is None:
            reference_asset_ids = []

        client = await self._get_client()
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        # qwen-image API uses 'W*H' format (not 'WxH')
        qwen_size = size.lower().replace("x", "*")

        content_items: list[dict[str, Any]] = [{"text": prompt}]

        # Level 1: base64 参考图
        if reference_asset_ids:
            from app.state.asset_store import AssetStore
            store = AssetStore()
            for ref_id in reference_asset_ids:
                ref_asset = store.get_asset(ref_id)
                if ref_asset and ref_asset.file_path:
                    try:
                        import base64
                        img_path = Path(ref_asset.file_path)
                        if img_path.exists():
                            b64_data = base64.b64encode(img_path.read_bytes()).decode('utf-8')
                            content_items.append({
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{b64_data}"},
                            })
                            logger.info("Using base64 reference image from %s", ref_id)
                            break  # 只使用第一个参考图
                    except Exception as e:
                        logger.warning("Failed to load reference image: %s", e)
                        # Fall through to Level 2

        # Level 2: StyleProfile prompt 注入（Level 1 失败时降级）
        if reference_asset_ids and not any(
            item.get("type") == "image_url" for item in content_items
        ):
            from app.state.asset_store import AssetStore
            from app.ai.style_extractor import extract_style_profile_from_prompt, inject_style_prompt
            store = AssetStore()
            for ref_id in reference_asset_ids:
                ref_asset = store.get_asset(ref_id)
                if ref_asset and ref_asset.prompt:
                    profile = extract_style_profile_from_prompt(ref_asset.prompt)
                    enhanced_prompt = inject_style_prompt(prompt, profile)
                    logger.info("Using style prompt injection from %s", ref_id)
                    content_items[0] = {"text": enhanced_prompt}
                    break

        payload: dict[str, Any] = {
            "model": self._model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": content_items,
                    }
                ]
            },
            "parameters": {
                "size": qwen_size,
                "seed": seed,
                "n": 1,
                "prompt_extend": True,
                "watermark": False,
            },
        }
        if negative_prompt:
            payload["parameters"]["negative_prompt"] = negative_prompt

        try:
            resp = await client.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

            # Response: output.choices[0].message.content[0].image
            choices = data.get("output", {}).get("choices", [])
            if not choices:
                raise ImageGenerationError("Qwen API returned no choices.")

            content = choices[0].get("message", {}).get("content", [])
            if not content:
                raise ImageGenerationError("Qwen API returned no content.")

            image_url = content[0].get("image", "")
            if not image_url:
                raise ImageGenerationError("Qwen API returned no image URL.")

            return GeneratedImage(seed=seed, url=image_url)
        except httpx.HTTPStatusError as exc:
            raise ImageGenerationError(
                f"Qwen API error {exc.response.status_code}: {exc.response.text}"
            ) from exc

    def _parse_size(self, size_str: str) -> tuple[int, int]:
        """Parse size string like '1024x1024' to (1024, 1024)."""
        try:
            width, height = size_str.lower().split("x")
            return int(width), int(height)
        except (ValueError, AttributeError):
            return 1024, 1024

    async def _download_image(
        self,
        image: GeneratedImage,
        asset_id: str,
        index: int,
        asset_name: str = "",
    ) -> GeneratedImage:
        """Download a remote URL image to local ``data/assets/`` directory.

        If ``image.file_path`` is already set (local provider), returns as-is.
        If ``image.url`` is a remote HTTP(S) URL, downloads and saves locally.
        Sets ``image.file_path`` to the absolute local path on success.

        Filename format: ``{asset_name}_{model}_{timestamp}{ext}``
        e.g. ``temple_ruins_bg_qwen-image-2.0-pro_20260728_153012.png``
        """
        if image.file_path:
            return image

        if not image.url or not image.url.startswith(("http://", "https://")):
            return image

        _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        ext = ".png"
        client = await self._get_client()
        resp = await client.get(image.url, follow_redirects=True)
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "jpeg" in content_type or "jpg" in content_type:
            ext = ".jpg"
        elif "webp" in content_type:
            ext = ".webp"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_slug = self._model.replace("/", "_")
        id_slug = asset_id if asset_id else "unknown"
        filename = f"{id_slug}_{model_slug}_{timestamp}{ext}"

        if index is not None and index >= 0:
            candidate_dir = _CANDIDATES_DIR / id_slug
            candidate_dir.mkdir(parents=True, exist_ok=True)
            filepath = candidate_dir / filename
        else:
            filepath = _OUTPUT_DIR / filename

        filepath.write_bytes(resp.content)

        image.file_path = str(filepath)
        return image
