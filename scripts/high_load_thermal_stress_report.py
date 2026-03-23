from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
_ROOT_S = str(_ROOT)
if _ROOT_S not in sys.path:
    sys.path.insert(0, _ROOT_S)

from hbm_system import HBMConfig, from_lower_layer_metrics, observe_hbm_system


def _format_row(label: str, obs) -> str:
    return (
        f"| {label} | {obs.bandwidth_gbps:.2f} | {obs.thermal_gradient_c:.2f} | "
        f"{obs.tsv_failure_risk:.3f} | {obs.power_density_w_per_stack:.2f} | "
        f"{obs.contention_ratio:.3f} | {obs.omega_hbm:.3f} | {obs.verdict} |"
    )


def generate_report_text() -> str:
    cfg = HBMConfig()

    base_inp = from_lower_layer_metrics(
        fabless_omega=0.88,
        memory_omega=0.86,
        rowhammer_risk=0.15,
        retention_risk=0.15,
        signal_margin=0.85,
        workload_intensity=0.65,
        cooling_coeff=0.35,
    )
    high_load_inp = from_lower_layer_metrics(
        fabless_omega=0.72,
        memory_omega=0.68,
        rowhammer_risk=0.35,
        retention_risk=0.30,
        signal_margin=0.62,
        workload_intensity=0.95,
        cooling_coeff=0.22,
    )
    thermal_stress_inp = from_lower_layer_metrics(
        fabless_omega=0.60,
        memory_omega=0.55,
        rowhammer_risk=0.70,
        retention_risk=0.65,
        signal_margin=0.35,
        workload_intensity=1.00,
        cooling_coeff=0.12,
    )

    o_base = observe_hbm_system(cfg, base_inp)
    o_high = observe_hbm_system(cfg, high_load_inp)
    o_stress = observe_hbm_system(cfg, thermal_stress_inp)

    lines = [
        "# High-Load Thermal Stress Report",
        "",
        f"- generated_at_utc: {datetime.now(timezone.utc).isoformat()}",
        "- engine: HBM_System v0.1.0",
        "",
        "| Scenario | bandwidth_gbps | thermal_gradient_c | tsv_failure_risk | power_density_w_per_stack | contention_ratio | omega_hbm | verdict |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
        _format_row("baseline", o_base),
        _format_row("high_load", o_high),
        _format_row("thermal_stress", o_stress),
        "",
        "## Readout",
        f"- omega drop (baseline -> thermal_stress): {(o_base.omega_hbm - o_stress.omega_hbm):.3f}",
        f"- thermal gradient increase: {(o_stress.thermal_gradient_c - o_base.thermal_gradient_c):.2f} C",
        f"- verdict path: {o_base.verdict} -> {o_high.verdict} -> {o_stress.verdict}",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    report_text = generate_report_text()
    root = Path(__file__).resolve().parents[1]
    out_path = root / "reports" / "HIGH_LOAD_THERMAL_STRESS_REPORT.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report_text, encoding="utf-8")
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()
