"""Feature flags controlled by environment variables."""
import os

SCENE_CONSISTENCY: bool = os.getenv("FEATURE_SCENE_CONSISTENCY", "true").lower() == "true"
