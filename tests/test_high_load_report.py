from pathlib import Path
import runpy


def test_high_load_report_script_generates_report_file() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "high_load_thermal_stress_report.py"
    runpy.run_path(str(script), run_name="__main__")

    out = root / "reports" / "HIGH_LOAD_THERMAL_STRESS_REPORT.md"
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "High-Load Thermal Stress Report" in text
    assert "thermal_stress" in text
    assert "omega_hbm" in text
