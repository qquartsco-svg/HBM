from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from .contracts import clamp01


@dataclass(frozen=True)
class ArbitrationResult:
    grants: List[float]
    contention_ratio: float


def arbitrate_channels(requests: Iterable[float], n_channels: int) -> ArbitrationResult:
    reqs = [max(0.0, float(x)) for x in requests]
    total_req = sum(reqs)
    capacity = float(max(1, n_channels))
    if total_req <= 0.0:
        return ArbitrationResult(grants=[0.0 for _ in reqs], contention_ratio=0.0)

    if total_req <= capacity:
        return ArbitrationResult(grants=reqs, contention_ratio=0.0)

    scale = capacity / total_req
    grants = [x * scale for x in reqs]
    contention = clamp01((total_req - capacity) / total_req)
    return ArbitrationResult(grants=grants, contention_ratio=contention)
