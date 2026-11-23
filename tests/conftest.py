from __future__ import annotations

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Prevent importing custom_components.obedience.__init__ (pulls HA cloud stack).
cc = sys.modules.setdefault("custom_components", types.ModuleType("custom_components"))
cc.__path__ = [str(ROOT / "custom_components")]
pkg = sys.modules.setdefault(
    "custom_components.obedience", types.ModuleType("custom_components.obedience")
)
pkg.__path__ = [str(ROOT / "custom_components" / "obedience")]
