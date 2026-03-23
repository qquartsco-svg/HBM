from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from .contracts import HBMConfig, HBMInput, ProtectionState
from .runtime import HBMRuntimeTick, run_runtime_tick


@dataclass(frozen=True)
class HBMPlantParams:
    thermal_tau_s: float = 6.0
    thermal_gain_c_per_w: float = 0.35
    latency_tau_s: float = 1.2
    base_latency_ms: float = 0.45
    perf_mode_latency_boost_ms: float = 0.35
    safe_mode_latency_penalty_ms: float = 0.90
    contention_latency_gain_ms: float = 3.2
    thermal_latency_gain_ms_per_c: float = 0.06


@dataclass(frozen=True)
class HBMPlantState:
    t_s: float
    die_temp_c: float
    controller_latency_ms: float = 0.5
    protection_state: ProtectionState = ProtectionState()


@dataclass(frozen=True)
class HBMTrajectoryPoint:
    state: HBMPlantState
    tick: HBMRuntimeTick


def _step_temperature(
    temp_c: float,
    ambient_c: float,
    power_w_per_stack: float,
    dt_s: float,
    params: HBMPlantParams,
) -> float:
    # First-order thermal dynamics:
    # dT/dt = k*P - (T - Tamb)/tau
    dtemp = params.thermal_gain_c_per_w * power_w_per_stack - (temp_c - ambient_c) / max(1e-6, params.thermal_tau_s)
    return temp_c + dt_s * dtemp


def _latency_target_ms(mode: str, thermal_c: float, contention: float, params: HBMPlantParams) -> float:
    mode_key = mode.upper()
    mode_term = 0.0
    if mode_key == "PERF":
        mode_term = params.perf_mode_latency_boost_ms
    elif mode_key == "SAFE":
        mode_term = params.safe_mode_latency_penalty_ms

    return (
        params.base_latency_ms
        + mode_term
        + params.contention_latency_gain_ms * max(0.0, contention)
        + params.thermal_latency_gain_ms_per_c * max(0.0, thermal_c)
    )


def _step_latency_ms(
    current_ms: float,
    target_ms: float,
    dt_s: float,
    params: HBMPlantParams,
) -> float:
    # First-order response: dL/dt = (L_target - L) / tau
    dl = (target_ms - current_ms) / max(1e-6, params.latency_tau_s)
    return max(0.0, current_ms + dt_s * dl)


def simulate_hbm_trajectory(
    cfg: HBMConfig,
    initial: HBMPlantState,
    inputs: Iterable[HBMInput],
    *,
    dt_s: float = 0.5,
    params: HBMPlantParams = HBMPlantParams(),
) -> List[HBMTrajectoryPoint]:
    out: List[HBMTrajectoryPoint] = []
    st = initial
    for inp in inputs:
        dynamic_inp = HBMInput(
            ambient_temp_c=st.die_temp_c,
            cooling_coeff=inp.cooling_coeff,
            fabless_device_omega=inp.fabless_device_omega,
            memory_cell_omega=inp.memory_cell_omega,
            rowhammer_risk=inp.rowhammer_risk,
            retention_risk=inp.retention_risk,
            signal_margin=inp.signal_margin,
            workload_intensity=inp.workload_intensity,
        )
        tick = run_runtime_tick(cfg, dynamic_inp, protection_state=st.protection_state)
        next_temp = _step_temperature(
            temp_c=st.die_temp_c,
            ambient_c=inp.ambient_temp_c,
            power_w_per_stack=tick.observation_after_protection.power_density_w_per_stack,
            dt_s=dt_s,
            params=params,
        )
        lat_target = _latency_target_ms(
            mode=tick.policy.mode,
            thermal_c=tick.observation_after_protection.thermal_gradient_c,
            contention=tick.observation_after_protection.contention_ratio,
            params=params,
        )
        next_latency = _step_latency_ms(
            current_ms=st.controller_latency_ms,
            target_ms=lat_target,
            dt_s=dt_s,
            params=params,
        )
        st = HBMPlantState(
            t_s=st.t_s + dt_s,
            die_temp_c=next_temp,
            controller_latency_ms=next_latency,
            protection_state=tick.protection_state_after,
        )
        out.append(HBMTrajectoryPoint(state=st, tick=tick))
    return out
