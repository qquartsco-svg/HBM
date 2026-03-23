from __future__ import annotations

from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
_ROOT_S = str(_ROOT)
if _ROOT_S not in sys.path:
    sys.path.insert(0, _ROOT_S)

from hbm_system import (  # noqa: E402
    HBMConfig,
    HBMPlantState,
    append_observation_to_chain,
    from_lower_layer_metrics,
    simulate_hbm_trajectory,
)


def _load_chain():
    syd_root = _ROOT.parent / "SYD_DRIFT"
    syd_path = str(syd_root)
    if syd_path not in sys.path:
        sys.path.insert(0, syd_path)
    from syd_drift import CommandChain  # type: ignore

    return CommandChain()


def main() -> None:
    chain = _load_chain()
    cfg = HBMConfig()

    seq = [
        from_lower_layer_metrics(
            fabless_omega=0.84,
            memory_omega=0.82,
            rowhammer_risk=0.20,
            retention_risk=0.18,
            signal_margin=0.82,
            workload_intensity=0.60,
        ),
        from_lower_layer_metrics(
            fabless_omega=0.80,
            memory_omega=0.76,
            rowhammer_risk=0.30,
            retention_risk=0.25,
            signal_margin=0.72,
            workload_intensity=0.85,
            cooling_coeff=0.22,
        ),
        from_lower_layer_metrics(
            fabless_omega=0.70,
            memory_omega=0.62,
            rowhammer_risk=0.55,
            retention_risk=0.45,
            signal_margin=0.50,
            workload_intensity=1.00,
            cooling_coeff=0.14,
        ),
    ]

    traj = simulate_hbm_trajectory(
        cfg,
        initial=HBMPlantState(t_s=0.0, die_temp_c=34.0),
        inputs=seq,
        dt_s=0.5,
    )

    for p in traj:
        append_observation_to_chain(
            chain,
            t_s=p.state.t_s,
            obs=p.tick.observation_after_protection,
            policy_mode=p.tick.policy.mode,
            extra={
                "controller_latency_ms": round(p.state.controller_latency_ms, 4),
                "protection_limited": p.state.protection_state.is_limited,
            },
        )

    out = _ROOT / "reports" / "HBM_AUDIT_CHAIN.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    chain.export_json(str(out))
    print(f"Wrote: {out}")
    print(chain.summary())


if __name__ == "__main__":
    main()
