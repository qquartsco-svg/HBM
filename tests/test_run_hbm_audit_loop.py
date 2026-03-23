from pathlib import Path
import runpy


def test_run_hbm_audit_loop_script_generates_json() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_hbm_audit_loop.py"
    runpy.run_path(str(script), run_name="__main__")
    out = root / "reports" / "HBM_AUDIT_CHAIN.json"
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "HBM_" in text
    assert "controller_latency_ms" in text
