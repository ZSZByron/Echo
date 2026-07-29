"""Local image generator using fallback rendering."""
from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import Any, Optional

from PIL import Image, ImageDraw, ImageFont
import numpy as np

logger = logging.getLogger(__name__)

# Local assets directory
_ASSETS_DIR = Path(r"H:\UGC\data\assets")
_META_DIR = _ASSETS_DIR / "meta"


class LocalImageGenerator:
    """Local image generator with prompt rendering and auto-open.
    
    Creates cyberpunk-style placeholders with full prompt information,
    then automatically opens the generated image.
    """
    
    def __init__(self) -> None:
        self._assets_dir = _ASSETS_DIR
        self._meta_dir = _META_DIR
        self._assets_dir.mkdir(parents=True, exist_ok=True)
        self._meta_dir.mkdir(parents=True, exist_ok=True)
    
    async def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        size: str = "1024x1024",
        seed: Optional[int] = None,
        num_candidates: int = 1,
        asset_id: str = "",
    ) -> list[Any]:
        """Generate local images with prompt rendering.
        
        Creates cyberpunk-style placeholder images with full prompt information,
        saves them to disk, and automatically opens the first generated image.
        
        Args:
            prompt: Main generation prompt
            negative_prompt: Negative prompt (what to avoid)
            size: Image size string "1024x1024"
            seed: Random seed for reproducibility
            num_candidates: Number of images to generate
            asset_id: Asset identifier for file naming
            
        Returns:
            List of generated image metadata with file paths
        """
        from app.ai.image_generator import GeneratedImage
        
        results = []
        width, height = self._parse_size(size)
        
        for i in range(num_candidates):
            candidate_seed = (
                (seed + i) if seed is not None else random.randint(0, 2**32 - 1)
            )
            
            try:
                # Generate cyberpunk placeholder with prompt
                image_path = await self._create_cyberpunk_placeholder(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    width=width,
                    height=height,
                    seed=candidate_seed,
                    asset_id=asset_id,
                    index=i
                )
                
                # Create result object
                result = GeneratedImage(
                    seed=candidate_seed,
                    image_data=b"",  # Empty since we save to file
                    url=None,
                    file_path=str(image_path)
                )
                
                results.append(result)
                
                # Save metadata
                self._save_meta(
                    asset_id=asset_id,
                    index=i,
                    seed=candidate_seed,
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    size=size,
                    provider="local"
                )
                
                # Image saved — frontend will display it via /assets/<filename>
                # Do NOT auto-open system viewer; the web UI handles display.
                    
            except Exception as exc:
                logger.warning(
                    "Local generation failed for candidate %d (seed=%d): %s",
                    i, candidate_seed, exc
                )
        
        return results
    
    def _parse_size(self, size_str: str) -> tuple[int, int]:
        """Parse size string like '1024x1024' to (1024, 1024)."""
        try:
            width, height = size_str.lower().split("x")
            return int(width), int(height)
        except (ValueError, AttributeError):
            return 1024, 1024
    
    async def _create_cyberpunk_placeholder(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        seed: int,
        asset_id: str,
        index: int,
        asset_name: str = "",
    ) -> Path:
        """Create a cyberpunk-style placeholder image with prompt info."""
        
        # Create image with cyberpunk gradient background
        img = Image.new("RGB", (width, height), color=(10, 10, 20))
        draw = ImageDraw.Draw(img)
        
        # Create cyberpunk gradient background
        for y in range(height):
            # Dark blue to cyan gradient
            r = int(10 + (y / height) * 20)
            g = int(10 + (y / height) * 80)
            b = int(30 + (y / height) * 100)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        # Add neon grid lines
        grid_spacing = 50
        for x in range(0, width, grid_spacing):
            draw.line([(x, 0), (x, height)], fill=(0, 100, 100), width=1)
        for y in range(0, height, grid_spacing):
            draw.line([(0, y), (width, y)], fill=(0, 100, 100), width=1)
        
        # Generate pseudo-random pattern based on seed
        random.seed(seed)
        num_shapes = 20
        for _ in range(num_shapes):
            x = random.randint(0, width)
            y = random.randint(0, height)
            size = random.randint(20, 100)
            
            # Cyberpunk colors: cyan, magenta, yellow
            color = random.choice([
                (0, 255, 255),   # Cyan
                (255, 0, 255),   # Magenta  
                (255, 255, 0),   # Yellow
                (0, 200, 200),   # Darker cyan
                (200, 0, 200),   # Darker magenta
            ])
            
            # Random shapes
            shape_type = random.choice(["circle", "rect", "line"])
            if shape_type == "circle":
                draw.ellipse([x-size//2, y-size//2, x+size//2, y+size//2], 
                           outline=color, width=2)
            elif shape_type == "rect":
                draw.rectangle([x-size//2, y-size//2, x+size//2, y+size//2], 
                              outline=color, width=2)
            else:
                end_x = random.randint(0, width)
                end_y = random.randint(0, height)
                draw.line([(x, y), (end_x, end_y)], fill=color, width=2)
        
        # Add text information
        try:
            # Try to use a system font, fallback to default
            try:
                font_large = ImageFont.truetype("arial.ttf", 36)
                font_medium = ImageFont.truetype("arial.ttf", 24)
                font_small = ImageFont.truetype("arial.ttf", 18)
            except:
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
            # Title
            title = f"LOCAL PREVIEW - {asset_id.upper()}"
            draw.text((width//2, 50), title, fill=(0, 255, 255), 
                     font=font_large, anchor="mm")
            
            # Seed info
            seed_text = f"SEED: {seed}"
            draw.text((width//2, 100), seed_text, fill=(255, 255, 0), 
                     font=font_medium, anchor="mm")
            
            # Prompt section (word wrapped)
            prompt_lines = self._wrap_text(prompt, 40)
            y_offset = 180
            draw.text((50, y_offset), "PROMPT:", fill=(255, 0, 255), 
                     font=font_medium)
            y_offset += 40
            for line in prompt_lines[:10]:  # Max 10 lines
                draw.text((50, y_offset), line, fill=(200, 200, 200), 
                         font=font_small)
                y_offset += 25
            
            # Negative prompt section
            if negative_prompt:
                y_offset += 20
                neg_lines = self._wrap_text(f"NEG: {negative_prompt}", 50)
                draw.text((50, y_offset), "NEGATIVE PROMPT:", fill=(255, 100, 100), 
                         font=font_small)
                y_offset += 30
                for line in neg_lines[:5]:  # Max 5 lines for negative
                    draw.text((50, y_offset), line, fill=(150, 150, 150), 
                             font=font_small)
                    y_offset += 20
            
            # Footer
            footer = f"Generated: {seed} | Size: {width}x{height}"
            draw.text((width//2, height-30), footer, fill=(0, 255, 255), 
                     font=font_small, anchor="mm")
            
        except Exception as e:
            logger.warning(f"Text rendering failed: {e}")
        
        # Save image
        filename = f"{asset_id}_{index}.png" if asset_id else f"generated_{index}.png"
        image_path = self._assets_dir / filename
        img.save(image_path, "PNG")
        logger.info(f"Generated local image: {image_path}")
        
        return image_path
    
    def _wrap_text(self, text: str, width: int) -> list[str]:
        """Wrap text to fit within specified character width."""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            if len(" ".join(current_line + [word])) <= width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(" ".join(current_line))
        
        return lines
    
    def _save_meta(
        self,
        asset_id: str,
        index: int,
        seed: int,
        prompt: str,
        negative_prompt: str,
        size: str,
        provider: str
    ) -> None:
        """Save generation metadata to JSON file."""
        meta = {
            "seed": seed,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "size": size,
            "provider": provider,
            "asset_id": asset_id,
            "index": index
        }
        
        filepath = self._meta_dir / f"{asset_id}_{index}.json"
        filepath.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), 
            encoding="utf-8"
        )
        logger.info(f"Saved metadata: {filepath}")


# Singleton instance
_local_generator: Optional[LocalImageGenerator] = None


def get_local_generator() -> LocalImageGenerator:
    """Get singleton local image generator instance."""
    global _local_generator
    if _local_generator is None:
        _local_generator = LocalImageGenerator()
    return _local_generator