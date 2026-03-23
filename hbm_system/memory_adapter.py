from __future__ import annotations

from typing import Any, Mapping

from .contracts import MemoryState, clamp01


def memory_state_from_mapping(data: Mapping[str, Any]) -> MemoryState:
    omega = clamp01(float(data.get("omega_global", 0.75)))
    rowhammer = clamp01(float(data.get("rowhammer_risk", 0.25)))
    retention = clamp01(float(data.get("retention_risk", 0.25)))
    return MemoryState(
        omega_global=omega,
        rowhammer_risk=rowhammer,
        retention_risk=retention,
    )


def memory_state_from_observation(obs: Any) -> MemoryState:
    omega = getattr(obs, "omega_global", 0.75)
    flags = getattr(obs, "flags", {}) or {}
    rowhammer = getattr(obs, "rowhammer_risk", flags.get("rowhammer_risk", 0.25))
    retention = getattr(obs, "retention_risk", flags.get("retention_risk", 0.25))
    return MemoryState(
        omega_global=clamp01(float(omega)),
        rowhammer_risk=clamp01(float(rowhammer)),
        retention_risk=clamp01(float(retention)),
    )
