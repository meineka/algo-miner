import sys
from pathlib import Path

# Make sure the project root is on sys.path so tests can import brain / simulator
sys.path.insert(0, str(Path(__file__).parent.parent))
