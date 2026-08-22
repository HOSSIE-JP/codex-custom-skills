from __future__ import annotations

from pathlib import Path

import vn_common_core as _core
from vn_common_core import *


_contained_core = _core.contained


def contained(root: Path, candidate: Path, *, must_exist: bool = False) -> Path:
    try:
        return _contained_core(root, candidate, must_exist=must_exist)
    except OSError as exc:
        missing = candidate.resolve(strict=False)
        raise ValidationError(f"path does not exist or cannot be resolved: {missing}") from exc


_core.contained = contained
