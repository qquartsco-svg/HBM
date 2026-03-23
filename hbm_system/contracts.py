from __future__ import annotations

from dataclasses import dataclass


def clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


@dataclass(frozen=True)
class HBMConfig:
    n_stacks: int = 4
    layers_per_stack: int = 8
    channels_per_stack: int = 8
    channel_bw_gbps: float = 32.0
    controller_efficiency: float = 0.88
    stack_power_w: float = 12.0
    interposer_loss_w: float = 8.0
    tsv_count_per_stack: int = 4096
    arbitration_request_scale: float = 1.5
    omega_thermal_scale_c: float = 35.0
    omega_power_scale_w: float = 30.0
    omega_thermal_weight: float = 0.22
    omega_tsv_weight: float = 0.20
    omega_power_weight: float = 0.16
    omega_signal_weight: float = 0.14
    omega_lower_weight: float = 0.18
    omega_contention_weight: float = 0.10
    thermal_guard_c: float = 22.0
    thermal_recover_c: float = 18.0
    tsv_guard_risk: float = 0.55
    tsv_recover_risk: float = 0.42
    edge_power_cap_w_per_stack: float = 16.0


@dataclass(frozen=True)
class HBMInput:
    ambient_temp_c: float = 30.0
    cooling_coeff: float = 0.35
    fabless_device_omega: float = 0.8
    memory_cell_omega: float = 0.8
    rowhammer_risk: float = 0.2
    retention_risk: float = 0.2
    signal_margin: float = 0.8
    workload_intensity: float = 0.7

    def normalized(self) -> "HBMInput":
        return HBMInput(
            ambient_temp_c=self.ambient_temp_c,
            cooling_coeff=max(0.05, self.cooling_coeff),
            fabless_device_omega=clamp01(self.fabless_device_omega),
            memory_cell_omega=clamp01(self.memory_cell_omega),
            rowhammer_risk=clamp01(self.rowhammer_risk),
            retention_risk=clamp01(self.retention_risk),
            signal_margin=clamp01(self.signal_margin),
            workload_intensity=clamp01(self.workload_intensity),
        )


@dataclass(frozen=True)
class HBMObservation:
    bandwidth_gbps: float
    thermal_gradient_c: float
    tsv_failure_risk: float
    power_density_w_per_stack: float
    contention_ratio: float
    omega_hbm: float
    verdict: str


@dataclass(frozen=True)
class EdgePolicyDecision:
    mode: str
    workload_scale: float
    power_cap_scale: float
    reason: str


@dataclass(frozen=True)
class ProtectionState:
    is_limited: bool = False
    last_reason: str = ""


@dataclass(frozen=True)
class FablessState:
    omega_global: float


@dataclass(frozen=True)
class MemoryState:
    omega_global: float
    rowhammer_risk: float
    retention_risk: float


@dataclass(frozen=True)
class BatteryState:
    omega_battery: float


@dataclass(frozen=True)
class VectorState:
    omega_vector: float


@dataclass(frozen=True)
class RuntimeState:
    scheduler_pressure: float
