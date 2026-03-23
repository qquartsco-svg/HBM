from __future__ import annotations

from typing import Any, Mapping

from .contracts import (
    HBMInput,
    FablessState,
    MemoryState,
    BatteryState,
    VectorState,
    RuntimeState,
    clamp01,
)
from .memory_adapter import memory_state_from_observation


def _get_float(x: Mapping[str, Any], key: str, default: float) -> float:
    v = x.get(key, default)
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def build_input_from_engine_snapshots(
    snapshots: Mapping[str, Mapping[str, Any]],
    *,
    ambient_temp_c: float = 30.0,
    cooling_coeff: float = 0.30,
    workload_intensity: float = 0.7,
) -> HBMInput:
    fab = snapshots.get("fabless", {})
    mem = snapshots.get("memory", {})
    batt = snapshots.get("battery", {})
    vector = snapshots.get("vectorspace", {})
    runtime = snapshots.get("runtime", {})

    fab_omega = clamp01(_get_float(fab, "omega_global", 0.75))
    mem_omega = clamp01(_get_float(mem, "omega_global", 0.75))
    rowhammer_risk = clamp01(_get_float(mem, "rowhammer_risk", 0.25))
    retention_risk = clamp01(_get_float(mem, "retention_risk", 0.25))

    battery_health = clamp01(_get_float(batt, "omega_battery", 0.8))
    vector_health = clamp01(_get_float(vector, "omega_vector", 0.8))
    sched_pressure = clamp01(_get_float(runtime, "scheduler_pressure", 0.3))

    signal_margin = clamp01(0.45 * fab_omega + 0.25 * mem_omega + 0.20 * battery_health + 0.10 * vector_health)
    inferred_workload = clamp01(0.65 * workload_intensity + 0.35 * sched_pressure)
    inferred_cooling = max(0.05, cooling_coeff * (0.75 + 0.25 * battery_health))

    return HBMInput(
        ambient_temp_c=ambient_temp_c,
        cooling_coeff=inferred_cooling,
        fabless_device_omega=fab_omega,
        memory_cell_omega=mem_omega,
        rowhammer_risk=rowhammer_risk,
        retention_risk=retention_risk,
        signal_margin=signal_margin,
        workload_intensity=inferred_workload,
    )


def snapshot_from_fabless_observation(obs: Any) -> Mapping[str, Any]:
    omega = getattr(obs, "Omega_global", getattr(obs, "omega_global", 0.75))
    return {"omega_global": float(omega)}


def snapshot_from_memory_observation(obs: Any) -> Mapping[str, Any]:
    st = memory_state_from_observation(obs)
    return {
        "omega_global": float(st.omega_global),
        "rowhammer_risk": float(st.rowhammer_risk),
        "retention_risk": float(st.retention_risk),
    }


def merge_engine_snapshots(
    *,
    fabless_obs: Any | None = None,
    memory_obs: Any | None = None,
    battery_snapshot: Mapping[str, Any] | None = None,
    vectorspace_snapshot: Mapping[str, Any] | None = None,
    runtime_snapshot: Mapping[str, Any] | None = None,
) -> Mapping[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    if fabless_obs is not None:
        out["fabless"] = snapshot_from_fabless_observation(fabless_obs)
    if memory_obs is not None:
        out["memory"] = snapshot_from_memory_observation(memory_obs)
    if battery_snapshot is not None:
        out["battery"] = dict(battery_snapshot)
    if vectorspace_snapshot is not None:
        out["vectorspace"] = dict(vectorspace_snapshot)
    if runtime_snapshot is not None:
        out["runtime"] = dict(runtime_snapshot)
    return out


def build_input_from_typed_states(
    *,
    fabless: FablessState,
    memory: MemoryState,
    battery: BatteryState | None = None,
    vector: VectorState | None = None,
    runtime: RuntimeState | None = None,
    ambient_temp_c: float = 30.0,
    cooling_coeff: float = 0.30,
    workload_intensity: float = 0.7,
) -> HBMInput:
    snapshots: dict[str, Mapping[str, Any]] = {
        "fabless": {"omega_global": fabless.omega_global},
        "memory": {
            "omega_global": memory.omega_global,
            "rowhammer_risk": memory.rowhammer_risk,
            "retention_risk": memory.retention_risk,
        },
    }
    if battery is not None:
        snapshots["battery"] = {"omega_battery": battery.omega_battery}
    if vector is not None:
        snapshots["vectorspace"] = {"omega_vector": vector.omega_vector}
    if runtime is not None:
        snapshots["runtime"] = {"scheduler_pressure": runtime.scheduler_pressure}
    return build_input_from_engine_snapshots(
        snapshots,
        ambient_temp_c=ambient_temp_c,
        cooling_coeff=cooling_coeff,
        workload_intensity=workload_intensity,
    )
