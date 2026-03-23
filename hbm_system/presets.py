from __future__ import annotations

from .contracts import HBMConfig, HBMInput


def get_hbm_config_preset(name: str) -> HBMConfig:
    k = name.strip().lower()
    if k == "hbm2e":
        return HBMConfig(
            n_stacks=4,
            layers_per_stack=8,
            channels_per_stack=8,
            channel_bw_gbps=25.6,
            controller_efficiency=0.86,
            stack_power_w=11.0,
            interposer_loss_w=7.0,
        )
    if k == "hbm3":
        return HBMConfig(
            n_stacks=6,
            layers_per_stack=8,
            channels_per_stack=8,
            channel_bw_gbps=32.0,
            controller_efficiency=0.88,
            stack_power_w=13.0,
            interposer_loss_w=9.0,
        )
    if k == "hbm3e":
        return HBMConfig(
            n_stacks=8,
            layers_per_stack=12,
            channels_per_stack=8,
            channel_bw_gbps=36.0,
            controller_efficiency=0.89,
            stack_power_w=14.5,
            interposer_loss_w=10.0,
        )
    if k == "edge_low_power":
        return HBMConfig(
            n_stacks=2,
            layers_per_stack=8,
            channels_per_stack=8,
            channel_bw_gbps=24.0,
            controller_efficiency=0.90,
            stack_power_w=7.5,
            interposer_loss_w=3.5,
            thermal_guard_c=16.0,
            tsv_guard_risk=0.40,
            edge_power_cap_w_per_stack=9.0,
        )
    raise ValueError(f"Unknown HBM preset: {name}")


def get_input_preset(name: str) -> HBMInput:
    k = name.strip().lower()
    if k == "edge_vision":
        return HBMInput(
            ambient_temp_c=35.0,
            cooling_coeff=0.28,
            fabless_device_omega=0.82,
            memory_cell_omega=0.80,
            rowhammer_risk=0.25,
            retention_risk=0.20,
            signal_margin=0.78,
            workload_intensity=0.70,
        )
    if k == "edge_genai_burst":
        return HBMInput(
            ambient_temp_c=40.0,
            cooling_coeff=0.18,
            fabless_device_omega=0.75,
            memory_cell_omega=0.72,
            rowhammer_risk=0.40,
            retention_risk=0.35,
            signal_margin=0.62,
            workload_intensity=0.95,
        )
    if k == "safe_monitor":
        return HBMInput(
            ambient_temp_c=28.0,
            cooling_coeff=0.38,
            fabless_device_omega=0.90,
            memory_cell_omega=0.88,
            rowhammer_risk=0.12,
            retention_risk=0.12,
            signal_margin=0.90,
            workload_intensity=0.45,
        )
    raise ValueError(f"Unknown input preset: {name}")
