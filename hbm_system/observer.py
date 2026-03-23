from __future__ import annotations

from .contracts import HBMConfig, HBMInput, HBMObservation, clamp01
from .controller import arbitrate_channels
from .physics import (
    estimate_bandwidth_gbps,
    estimate_power_density,
    estimate_thermal_gradient_c,
    estimate_tsv_failure_risk,
)


def _verdict_from_omega(omega: float) -> str:
    if omega >= 0.80:
        return "HEALTHY"
    if omega >= 0.60:
        return "STABLE"
    if omega >= 0.40:
        return "FRAGILE"
    return "CRITICAL"


def observe_hbm_system(cfg: HBMConfig, inp: HBMInput) -> HBMObservation:
    i = inp.normalized()

    bw = estimate_bandwidth_gbps(cfg, i)
    grad = estimate_thermal_gradient_c(cfg, i)
    tsv_risk = estimate_tsv_failure_risk(cfg, i)
    power_density = estimate_power_density(cfg, i)

    arb = arbitrate_channels(
        requests=[i.workload_intensity * cfg.arbitration_request_scale for _ in range(cfg.n_stacks)],
        n_channels=cfg.n_stacks * cfg.channels_per_stack,
    )

    omega_thermal = clamp01(1.0 - grad / cfg.omega_thermal_scale_c)
    omega_tsv = clamp01(1.0 - tsv_risk)
    omega_power = clamp01(1.0 - power_density / cfg.omega_power_scale_w)
    omega_signal = i.signal_margin
    omega_lower_layers = clamp01(
        0.55 * i.fabless_device_omega
        + 0.45 * i.memory_cell_omega
        - 0.20 * i.rowhammer_risk
        - 0.15 * i.retention_risk
    )
    omega_contention = clamp01(1.0 - arb.contention_ratio)

    omega_hbm = clamp01(
        cfg.omega_thermal_weight * omega_thermal
        + cfg.omega_tsv_weight * omega_tsv
        + cfg.omega_power_weight * omega_power
        + cfg.omega_signal_weight * omega_signal
        + cfg.omega_lower_weight * omega_lower_layers
        + cfg.omega_contention_weight * omega_contention
    )

    return HBMObservation(
        bandwidth_gbps=bw,
        thermal_gradient_c=grad,
        tsv_failure_risk=tsv_risk,
        power_density_w_per_stack=power_density,
        contention_ratio=arb.contention_ratio,
        omega_hbm=omega_hbm,
        verdict=_verdict_from_omega(omega_hbm),
    )
