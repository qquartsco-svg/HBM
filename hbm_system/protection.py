from __future__ import annotations

from dataclasses import replace

from .contracts import HBMConfig, HBMObservation, ProtectionState


def clamp_power_if_needed(cfg: HBMConfig, obs: HBMObservation, state: ProtectionState) -> tuple[HBMConfig, ProtectionState]:
    trip = obs.thermal_gradient_c > cfg.thermal_guard_c or obs.tsv_failure_risk > cfg.tsv_guard_risk
    recover = obs.thermal_gradient_c < cfg.thermal_recover_c and obs.tsv_failure_risk < cfg.tsv_recover_risk

    limited = state.is_limited
    reason = state.last_reason
    if not limited and trip:
        limited = True
        if obs.thermal_gradient_c > cfg.thermal_guard_c:
            reason = "thermal guard exceeded"
        else:
            reason = "tsv guard exceeded"
    elif limited and recover:
        limited = False
        reason = "recovered below hysteresis thresholds"

    if limited:
        capped = min(cfg.stack_power_w, cfg.edge_power_cap_w_per_stack)
        return replace(cfg, stack_power_w=capped), ProtectionState(is_limited=True, last_reason=reason)
    return cfg, ProtectionState(is_limited=False, last_reason=reason)
