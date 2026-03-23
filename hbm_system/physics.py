from __future__ import annotations

from .contracts import HBMConfig, HBMInput, clamp01


def estimate_bandwidth_gbps(cfg: HBMConfig, inp: HBMInput) -> float:
    i = inp.normalized()
    raw = (
        cfg.n_stacks
        * cfg.channels_per_stack
        * cfg.channel_bw_gbps
        * cfg.controller_efficiency
    )
    return raw * (0.6 + 0.4 * i.workload_intensity)


def estimate_power_density(cfg: HBMConfig, inp: HBMInput) -> float:
    i = inp.normalized()
    total_stack_power = cfg.n_stacks * cfg.stack_power_w * (0.7 + 0.6 * i.workload_intensity)
    total = total_stack_power + cfg.interposer_loss_w
    return total / max(1, cfg.n_stacks)


def estimate_thermal_gradient_c(cfg: HBMConfig, inp: HBMInput) -> float:
    i = inp.normalized()
    density = estimate_power_density(cfg, i)
    # Higher stacking depth and weak cooling amplify vertical gradient.
    depth_factor = 1.0 + (cfg.layers_per_stack - 4) * 0.08
    cooling_factor = 1.0 / i.cooling_coeff
    return density * depth_factor * 0.45 * cooling_factor


def estimate_tsv_failure_risk(cfg: HBMConfig, inp: HBMInput) -> float:
    i = inp.normalized()
    gradient = estimate_thermal_gradient_c(cfg, i)
    tsv_density = cfg.tsv_count_per_stack / 4096.0
    thermal_term = gradient / 45.0
    signal_term = 1.0 - i.signal_margin
    risk = 0.15 * tsv_density + 0.55 * thermal_term + 0.30 * signal_term
    return clamp01(risk)
