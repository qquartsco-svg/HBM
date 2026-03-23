from hbm_system import (
    HBMConfig,
    get_hbm_config_preset,
    get_input_preset,
    build_input_from_engine_snapshots,
    snapshot_from_fabless_observation,
    snapshot_from_memory_observation,
    merge_engine_snapshots,
    build_input_from_typed_states,
    append_observation_to_chain,
    append_journal_alert_to_chain,
    ProtectionState,
    FablessState,
    MemoryState,
    BatteryState,
    VectorState,
    RuntimeState,
    memory_state_from_mapping,
    memory_state_from_observation,
    from_lower_layer_metrics,
    arbitrate_channels,
    observe_hbm_system,
    run_runtime_tick,
    HBMPlantState,
    simulate_hbm_trajectory,
)


def test_arbitration_no_contention_when_capacity_sufficient() -> None:
    r = arbitrate_channels([1.0, 2.0, 1.0], n_channels=8)
    assert r.contention_ratio == 0.0
    assert abs(sum(r.grants) - 4.0) < 1e-9


def test_arbitration_contention_when_over_subscribed() -> None:
    r = arbitrate_channels([10.0, 10.0], n_channels=4)
    assert 0.0 < r.contention_ratio <= 1.0
    assert abs(sum(r.grants) - 4.0) < 1e-9


def test_hbm_health_drops_with_hot_and_risky_input() -> None:
    cfg = HBMConfig()
    base = from_lower_layer_metrics(
        fabless_omega=0.9,
        memory_omega=0.9,
        rowhammer_risk=0.1,
        retention_risk=0.1,
        signal_margin=0.9,
        workload_intensity=0.6,
    )
    hot = from_lower_layer_metrics(
        fabless_omega=0.6,
        memory_omega=0.5,
        rowhammer_risk=0.8,
        retention_risk=0.7,
        signal_margin=0.3,
        workload_intensity=1.0,
        cooling_coeff=0.15,
    )
    o1 = observe_hbm_system(cfg, base)
    o2 = observe_hbm_system(cfg, hot)
    assert o2.omega_hbm < o1.omega_hbm


def test_observer_outputs_reasonable_ranges() -> None:
    cfg = HBMConfig()
    inp = from_lower_layer_metrics(
        fabless_omega=0.8,
        memory_omega=0.75,
        rowhammer_risk=0.3,
        retention_risk=0.25,
        signal_margin=0.7,
        workload_intensity=0.8,
    )
    obs = observe_hbm_system(cfg, inp)
    assert obs.bandwidth_gbps > 0.0
    assert obs.thermal_gradient_c >= 0.0
    assert 0.0 <= obs.tsv_failure_risk <= 1.0
    assert 0.0 <= obs.contention_ratio <= 1.0
    assert 0.0 <= obs.omega_hbm <= 1.0
    assert obs.verdict in {"HEALTHY", "STABLE", "FRAGILE", "CRITICAL"}


def test_presets_and_runtime_tick_work_together() -> None:
    cfg = get_hbm_config_preset("edge_low_power")
    inp = get_input_preset("edge_genai_burst")
    tick = run_runtime_tick(cfg, inp)
    assert tick.policy.mode in {"SAFE", "BALANCED", "PERF"}
    assert tick.observation_after_protection.omega_hbm <= 1.0
    assert tick.config_after_protection.stack_power_w <= cfg.stack_power_w


def test_multi_engine_snapshot_integration_builds_valid_input() -> None:
    inp = build_input_from_engine_snapshots(
        {
            "fabless": {"omega_global": 0.81},
            "memory": {"omega_global": 0.74, "rowhammer_risk": 0.41, "retention_risk": 0.33},
            "battery": {"omega_battery": 0.77},
            "vectorspace": {"omega_vector": 0.79},
            "runtime": {"scheduler_pressure": 0.58},
        },
        workload_intensity=0.8,
    )
    assert 0.0 <= inp.signal_margin <= 1.0
    assert 0.0 <= inp.workload_intensity <= 1.0


def test_runtime_hysteresis_keeps_limited_state_until_recovery() -> None:
    cfg = HBMConfig(
        stack_power_w=20.0,
        edge_power_cap_w_per_stack=10.0,
        thermal_guard_c=10.0,
        thermal_recover_c=8.0,
    )
    inp_hot = from_lower_layer_metrics(
        fabless_omega=0.6,
        memory_omega=0.5,
        rowhammer_risk=0.7,
        retention_risk=0.6,
        signal_margin=0.5,
        workload_intensity=1.0,
        cooling_coeff=0.12,
    )
    tick1 = run_runtime_tick(cfg, inp_hot, protection_state=ProtectionState(is_limited=False))
    assert tick1.protection_state_after.is_limited is True
    assert tick1.config_after_protection.stack_power_w <= 10.0

    inp_mid = from_lower_layer_metrics(
        fabless_omega=0.75,
        memory_omega=0.72,
        rowhammer_risk=0.45,
        retention_risk=0.40,
        signal_margin=0.72,
        workload_intensity=0.8,
        cooling_coeff=0.16,
    )
    tick2 = run_runtime_tick(cfg, inp_mid, protection_state=tick1.protection_state_after)
    assert tick2.protection_state_after.is_limited is True


def test_observer_config_weights_are_effective() -> None:
    inp = from_lower_layer_metrics(
        fabless_omega=0.85,
        memory_omega=0.80,
        rowhammer_risk=0.2,
        retention_risk=0.2,
        signal_margin=0.8,
        workload_intensity=0.75,
    )
    a = observe_hbm_system(HBMConfig(omega_signal_weight=0.30, omega_power_weight=0.05), inp)
    b = observe_hbm_system(HBMConfig(omega_signal_weight=0.05, omega_power_weight=0.30), inp)
    assert abs(a.omega_hbm - b.omega_hbm) > 1e-6


def test_snapshot_helpers_and_chain_adapter() -> None:
    class FabObs:
        Omega_global = 0.81

    class MemObs:
        omega_global = 0.76
        flags = {"rowhammer_risk": 0.31, "retention_risk": 0.28}

    fab = snapshot_from_fabless_observation(FabObs())
    mem = snapshot_from_memory_observation(MemObs())
    merged = merge_engine_snapshots(fabless_obs=FabObs(), memory_obs=MemObs(), runtime_snapshot={"scheduler_pressure": 0.55})
    inp = build_input_from_engine_snapshots(merged)
    obs = observe_hbm_system(HBMConfig(), inp)
    assert fab["omega_global"] == 0.81
    assert mem["omega_global"] == 0.76
    assert 0.0 <= obs.omega_hbm <= 1.0

    class DummyChain:
        def __init__(self) -> None:
            self.called = False
            self.kw = {}

        def append(self, **kwargs):
            self.called = True
            self.kw = kwargs
            return kwargs

    ch = DummyChain()
    append_observation_to_chain(ch, t_s=1.25, obs=obs, policy_mode="SAFE")
    assert ch.called is True
    assert ch.kw["mode"] == "HBM_SAFE"
    append_journal_alert_to_chain(
        ch,
        t_s=1.30,
        alert={
            "severity": "CRITICAL",
            "code": "JOURNAL_REPLAY_INTEGRITY_FAIL",
            "status": "stopped",
            "reason": "hash_chain_mismatch",
            "verified_entries": 0,
            "stopped_at_line": 1,
            "head_hash": "00" * 32,
            "actionable": True,
        },
    )
    assert ch.kw["mode"] == "HBM_ALERT_CRITICAL"
    assert ch.kw["extra"]["event_type"] == "journal_replay_alert"


def test_typed_state_builder_and_trajectory() -> None:
    inp = build_input_from_typed_states(
        fabless=FablessState(omega_global=0.82),
        memory=MemoryState(omega_global=0.76, rowhammer_risk=0.30, retention_risk=0.28),
        battery=BatteryState(omega_battery=0.80),
        vector=VectorState(omega_vector=0.78),
        runtime=RuntimeState(scheduler_pressure=0.62),
    )
    cfg = HBMConfig()
    points = simulate_hbm_trajectory(
        cfg,
        initial=HBMPlantState(t_s=0.0, die_temp_c=35.0),
        inputs=[inp, inp, inp],
        dt_s=0.5,
    )
    assert len(points) == 3
    assert points[-1].state.t_s > points[0].state.t_s
    assert points[-1].state.controller_latency_ms >= 0.0


def test_memory_adapter_normalizes_inputs() -> None:
    st = memory_state_from_mapping({"omega_global": 1.2, "rowhammer_risk": -0.2, "retention_risk": 0.5})
    assert st.omega_global == 1.0
    assert st.rowhammer_risk == 0.0
    assert st.retention_risk == 0.5

    class M:
        omega_global = 0.73
        flags = {"rowhammer_risk": 0.41, "retention_risk": 0.39}

    st2 = memory_state_from_observation(M())
    assert st2.omega_global == 0.73
    assert st2.rowhammer_risk == 0.41
