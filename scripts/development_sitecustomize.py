"""Copied only into the managed venv to load DLLs shipped with bundled Python."""

import os
from pathlib import Path
import sys


_dll_handles = []
if os.name == "nt" and hasattr(os, "add_dll_directory"):
    _base = Path(sys.base_prefix)
    _candidates = [_base / "DLLs"]
    if _base.parent.name.lower() == "apps":
        _candidates.append(_base.parent.parent / "bin")
    for _directory in _candidates:
        if _directory.is_dir():
            _dll_handles.append(os.add_dll_directory(str(_directory)))
