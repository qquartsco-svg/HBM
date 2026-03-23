from __future__ import annotations

from dataclasses import replace

from .contracts import EdgePolicyDecision, HBMConfig, HBMInput


def decide_edge_policy(cfg: HBMConfig, inp: HBMInput) -> EdgePolicyDecision:
    i = inp.normalized()

    if i.workload_intensity >= 0.92 and i.cooling_coeff <= 0.16:
        return EdgePolicyDecision(
            mode="SAFE",
            workload_scale=0.72,
            power_cap_scale=0.78,
            reason="high burst workload under weak cooling",
        )
    if i.signal_margin < 0.45 or i.rowhammer_risk > 0.65:
        return EdgePolicyDecision(
            mode="SAFE",
            workload_scale=0.76,
            power_cap_scale=0.80,
            reason="signal margin or memory risk exceeded",
        )
    if i.workload_intensity > 0.75:
        return EdgePolicyDecision(
            mode="PERF",
            workload_scale=1.05,
            power_cap_scale=1.0,
            reason="throughput-priority workload",
        )
    return EdgePolicyDecision(
        mode="BALANCED",
        workload_scale=1.0,
        power_cap_scale=0.95,
        reason="normal edge-ai operating point",
    )


def apply_policy_to_input(inp: HBMInput, dec: EdgePolicyDecision) -> HBMInput:
    i = inp.normalized()
    return replace(
        i,
        workload_intensity=max(0.0, min(1.0, i.workload_intensity * dec.workload_scale)),
    )
