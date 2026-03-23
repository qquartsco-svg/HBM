from pathlib import Path
import sys

from hbm_system import HBMConfig, from_lower_layer_metrics, observe_hbm_system, append_observation_to_chain


def test_syd_drift_command_chain_roundtrip_if_available() -> None:
    root = Path(__file__).resolve().parents[2]
    syd_root = root.parent / "SYD_DRIFT"
    if not syd_root.is_dir():
        return

    syd_path = str(syd_root)
    if syd_path not in sys.path:
        sys.path.insert(0, syd_path)

    try:
        from syd_drift import CommandChain
    except Exception:
        return

    chain = CommandChain()
    obs = observe_hbm_system(
        HBMConfig(),
        from_lower_layer_metrics(
            fabless_omega=0.8,
            memory_omega=0.77,
            rowhammer_risk=0.3,
            retention_risk=0.25,
            signal_margin=0.75,
            workload_intensity=0.8,
        ),
    )
    append_observation_to_chain(chain, t_s=0.5, obs=obs, policy_mode="BALANCED")
    assert len(chain) == 1
    assert chain.verify_integrity() is True
