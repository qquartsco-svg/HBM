from __future__ import annotations

from .contracts import HBMInput, clamp01


def from_lower_layer_metrics(
    *,
    fabless_omega: float,
    memory_omega: float,
    rowhammer_risk: float,
    retention_risk: float,
    signal_margin: float,
    workload_intensity: float,
    ambient_temp_c: float = 30.0,
    cooling_coeff: float = 0.35,
) -> HBMInput:
    return HBMInput(
        ambient_temp_c=ambient_temp_c,
        cooling_coeff=max(0.05, cooling_coeff),
        fabless_device_omega=clamp01(fabless_omega),
        memory_cell_omega=clamp01(memory_omega),
        rowhammer_risk=clamp01(rowhammer_risk),
        retention_risk=clamp01(retention_risk),
        signal_margin=clamp01(signal_margin),
        workload_intensity=clamp01(workload_intensity),
    )
