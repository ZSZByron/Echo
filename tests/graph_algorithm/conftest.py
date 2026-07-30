"""Pytest configuration for graph algorithm tests."""
import sys
from pathlib import Path

# Add tests/graph_algorithm to Python path for local imports
test_dir = Path(__file__).parent
sys.path.insert(0, str(test_dir))
