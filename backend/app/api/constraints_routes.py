"""Constraints API routes for 6-dimension constraint generation."""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_dimension_generator
from app.models.dimension import CreationLayer, DimensionResultSet
from app.domains.creation.constraint.dimension_generator import (
    DimensionGenerator,
    DimensionParseError,
    WeightMatrixError,
)

logger = logging.getLogger(__name__)

constraints_router = APIRouter(prefix="/api/constraints", tags=["constraints"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ConstraintGenerateRequest(BaseModel):
    """Request for constraint generation."""
    seed_input: str = Field(..., min_length=1, description="种子概念名称")
    seed_description: str = Field("", description="种子描述（可选）")
    layer: CreationLayer = Field(..., description="创作层级")
    intent: str = Field("", description="创作意图（可选）")


class ConstraintGenerateResponse(BaseModel):
    """Response for constraint generation."""
    layer: CreationLayer
    weights: dict[str, int]
    dimensions: DimensionResultSet
    elapsed_seconds: float


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@constraints_router.post("/generate", response_model=ConstraintGenerateResponse)
async def generate_constraints(
    request: ConstraintGenerateRequest,
    generator: DimensionGenerator = Depends(get_dimension_generator),  # noqa: B008
) -> ConstraintGenerateResponse:
    """Generate 6-dimension constraints for a seed at a specific layer."""
    start = time.time()

    try:
        result = await generator.generate(
            seed_input=request.seed_input,
            seed_description=request.seed_description,
            layer=request.layer,
            intent=request.intent,
        )
    except WeightMatrixError as e:
        raise HTTPException(status_code=503, detail=f"Weight matrix error: {e.detail}") from e
    except DimensionParseError as e:
        raise HTTPException(status_code=502, detail=f"LLM output parsing failed: {e.errors}") from e

    elapsed = time.time() - start

    # Get weights for echo
    weights = generator._loader.get_weights(request.layer)

    return ConstraintGenerateResponse(
        layer=request.layer,
        weights={k.value: v for k, v in weights.to_dict().items()},
        dimensions=result,
        elapsed_seconds=round(elapsed, 2),
    )
