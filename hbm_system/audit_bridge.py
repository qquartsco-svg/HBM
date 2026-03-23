from __future__ import annotations

from typing import Any, Dict

from .contracts import HBMObservation


def append_observation_to_chain(
    chain: Any,
    *,
    t_s: float,
    obs: HBMObservation,
    policy_mode: str,
    extra: Dict[str, Any] | None = None,
) -> Any:
    """
    Append HBM runtime observation to an external audit chain.

    Expected duck-typed API:
      chain.append(t_s=..., accel=..., steer=..., mode=..., verdict=..., omega=..., speed_ms=..., range_m=..., extra=...)
    This matches SYD_DRIFT CommandChain without introducing a hard dependency.
    """
    payload_extra: Dict[str, Any] = {
        "bandwidth_gbps": round(obs.bandwidth_gbps, 3),
        "thermal_gradient_c": round(obs.thermal_gradient_c, 3),
        "tsv_failure_risk": round(obs.tsv_failure_risk, 5),
        "power_density_w_per_stack": round(obs.power_density_w_per_stack, 3),
        "contention_ratio": round(obs.contention_ratio, 5),
        "domain": "HBM_System",
    }
    if extra:
        payload_extra.update(extra)

    return chain.append(
        t_s=t_s,
        accel=0.0,
        steer=0.0,
        mode=f"HBM_{policy_mode}",
        verdict=obs.verdict,
        omega=obs.omega_hbm,
        speed_ms=obs.bandwidth_gbps,
        range_m=max(0.0, 100.0 - obs.thermal_gradient_c),
        extra=payload_extra,
    )


def append_journal_alert_to_chain(
    chain: Any,
    *,
    t_s: float,
    alert: Dict[str, Any],
) -> Any:
    """
    Append startup journal replay alert event to external audit chain.
    """
    severity = str(alert.get("severity", "INFO"))
    code = str(alert.get("code", "JOURNAL_REPLAY_INFO"))
    status = str(alert.get("status", "unknown"))
    reason = str(alert.get("reason", "unknown"))

    payload_extra: Dict[str, Any] = {
        "domain": "HBM_System",
        "event_type": "journal_replay_alert",
        "severity": severity,
        "code": code,
        "status": status,
        "reason": reason,
        "verified_entries": int(alert.get("verified_entries", 0)),
        "stopped_at_line": int(alert.get("stopped_at_line", 0)),
        "head_hash": str(alert.get("head_hash", "")),
        "actionable": bool(alert.get("actionable", False)),
    }

    return chain.append(
        t_s=t_s,
        accel=0.0,
        steer=0.0,
        mode=f"HBM_ALERT_{severity}",
        verdict=severity,
        omega=0.0 if severity == "CRITICAL" else 1.0,
        speed_ms=0.0,
        range_m=0.0,
        extra=payload_extra,
    )
