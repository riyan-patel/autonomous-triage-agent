import sys
from pathlib import Path

# worker is imported as "worker.jobs" (matching the dotted path RQ resolves
# jobs by), so the repo root — not this tests/ dir — needs to be on the path.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
