"""Style profile extraction and prompt injection for scene consistency."""
from __future__ import annotations

from typing import Optional

from app.models.asset import SceneStyleProfile


# 五维度关键词库
_PALETTE_KEYWORDS = [
    "cyan", "neon-green", "deep-black", "bronze", "amber", "red", "blue", "white",
    "purple", "pink", "orange", "yellow", "green", "brown", "gray", "silver", "gold"
]

_LIGHTING_TYPES = ["volumetric", "directional", "ambient"]
_LIGHTING_DIRECTIONS = ["side", "top", "bottom", "front", "back"]

_MATERIAL_KEYWORDS = [
    "marble", "metal", "stone", "bronze", "concrete", "glass", "wood", "fabric",
    "plastic", "ceramic", "rubber", "leather", "cloth", "paper"
]

_RENDERING_STYLES = ["cyberpunk", "realistic", "concept-art", "anime"]
_CAMERA_SHOTS = ["low-angle", "wide-shot", "close-up", "bird-eye"]

_ATMOSPHERE_MOODS = ["dark", "melancholic", "mystical", "bright", "gloomy"]
_ATMOSPHERE_WEATHER = ["mist", "fog", "rain", "clear", "cloudy", "hazy"]


def extract_style_profile_from_prompt(prompt: str) -> SceneStyleProfile:
    """Extract five-dimension style profile from prompt text (deterministic)."""
    prompt_lower = prompt.lower()

    # 提取 palette（颜色）
    palette = [word for word in _PALETTE_KEYWORDS if word in prompt_lower]

    # 提取 lighting
    lighting_type = None
    lighting_dir = None
    for ltype in _LIGHTING_TYPES:
        if ltype in prompt_lower:
            lighting_type = ltype
            break
    for ldir in _LIGHTING_DIRECTIONS:
        if ldir in prompt_lower:
            lighting_dir = ldir
            break
    lighting = {}
    if lighting_type:
        lighting["type"] = lighting_type
    if lighting_dir:
        lighting["direction"] = lighting_dir

    # 提取 material
    material = [word for word in _MATERIAL_KEYWORDS if word in prompt_lower]

    # 提取 rendering
    rendering = {}
    for rstyle in _RENDERING_STYLES:
        if rstyle in prompt_lower:
            rendering["style"] = rstyle
            break
    for cam in _CAMERA_SHOTS:
        if cam in prompt_lower:
            rendering["camera"] = cam
            break

    # 提取 atmosphere
    atmosphere = {}
    for mood in _ATMOSPHERE_MOODS:
        if mood in prompt_lower:
            atmosphere["mood"] = mood
            break
    for weather in _ATMOSPHERE_WEATHER:
        if weather in prompt_lower:
            atmosphere["weather"] = weather
            break

    return SceneStyleProfile(
        palette=palette,
        lighting=lighting,
        material=material,
        rendering=rendering,
        atmosphere=atmosphere,
    )


def inject_style_prompt(base_prompt: str, profile: SceneStyleProfile) -> str:
    """Inject style profile as prefix into prompt."""
    parts = []
    if profile.palette:
        parts.append(f"Scene style: {', '.join(profile.palette[:5])}")
    if profile.lighting and profile.lighting.get("type"):
        parts.append(f"{profile.lighting['type']} lighting")
        if profile.lighting.get("direction"):
            parts.append(f"from {profile.lighting['direction']}")
    if profile.material:
        parts.append(f"materials: {', '.join(profile.material[:3])}")

    prefix = ". ".join(parts) + ". "
    return prefix + base_prompt
