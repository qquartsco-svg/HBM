from __future__ import annotations

from dataclasses import dataclass

from .contracts import EdgePolicyDecision, HBMConfig, HBMInput, HBMObservation, ProtectionState
from .edge_policy import apply_policy_to_input, decide_edge_policy
from .observer import observe_hbm_system
from .protection import clamp_power_if_needed


@dataclass(frozen=True)
class HBMRuntimeTick:
    policy: EdgePolicyDecision
    protection_state_before: ProtectionState
    protection_state_after: ProtectionState
    observation_before_protection: HBMObservation
    observation_after_protection: HBMObservation
    config_after_protection: HBMConfig


def run_runtime_tick(cfg: HBMConfig, inp: HBMInput, protection_state: ProtectionState = ProtectionState()) -> HBMRuntimeTick:
    policy = decide_edge_policy(cfg, inp)
    inp2 = apply_policy_to_input(inp, policy)

    obs0 = observe_hbm_system(cfg, inp2)
    cfg2, st2 = clamp_power_if_needed(cfg, obs0, protection_state)
    obs1 = observe_hbm_system(cfg2, inp2)

    return HBMRuntimeTick(
        policy=policy,
        protection_state_before=protection_state,
        protection_state_after=st2,
        observation_before_protection=obs0,
        observation_after_protection=obs1,
        config_after_protection=cfg2,
    )
