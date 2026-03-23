from __future__ import annotations

import argparse
import hashlib
import hmac
import json
from pathlib import Path
import socket
import sys
from typing import Any, Dict, Iterable, Iterator, Tuple

_ROOT = Path(__file__).resolve().parents[1]
_ROOT_S = str(_ROOT)
if _ROOT_S not in sys.path:
    sys.path.insert(0, _ROOT_S)

from hbm_system import (  # noqa: E402
    HBMConfig,
    HBMPlantState,
    RuntimeState,
    build_input_from_engine_snapshots,
    run_runtime_tick,
    append_observation_to_chain,
    append_journal_alert_to_chain,
)

JOURNAL_GENESIS = "NONCE_JOURNAL_GENESIS_V1"


def _load_chain():
    syd_root = _ROOT.parent / "SYD_DRIFT"
    syd_path = str(syd_root)
    if syd_path not in sys.path:
        sys.path.insert(0, syd_path)
    from syd_drift import CommandChain  # type: ignore

    return CommandChain()


def _iter_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            yield json.loads(s)


def _iter_stdin_jsonl() -> Iterator[Dict[str, Any]]:
    for line in sys.stdin:
        s = line.strip()
        if not s:
            continue
        yield json.loads(s)


def _iter_tcp_jsonl(host: str, port: int, timeout_s: float, max_packets: int) -> Iterator[Dict[str, Any]]:
    count = 0
    with socket.create_connection((host, port), timeout=timeout_s) as sock:
        sock_file = sock.makefile("r", encoding="utf-8")
        for line in sock_file:
            s = line.strip()
            if not s:
                continue
            yield json.loads(s)
            count += 1
            if max_packets > 0 and count >= max_packets:
                break


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="HBM stream runner (file/stdin/tcp/tcp_server)")
    p.add_argument("--source", choices=["file", "stdin", "tcp", "tcp_server"], default="file")
    p.add_argument("--input", default=str(_ROOT / "examples" / "hbm_stream_input.jsonl"))
    p.add_argument("--output", default=str(_ROOT / "reports" / "HBM_STREAM_AUDIT_CHAIN.json"))
    p.add_argument("--tcp-host", default="127.0.0.1")
    p.add_argument("--tcp-port", type=int, default=18081)
    p.add_argument("--tcp-timeout-s", type=float, default=5.0)
    p.add_argument("--max-packets", type=int, default=0, help="0 means no explicit cap")
    p.add_argument("--tcp-server-idle-timeout-s", type=float, default=10.0)
    p.add_argument("--auth-token", default="", help="Optional shared token. If set, packet.auth_token must match.")
    p.add_argument("--strict-schema", action="store_true", help="Enable strict packet schema/type validation.")
    p.add_argument("--hmac-secret", default="", help="Optional HMAC secret for packet signature verification.")
    p.add_argument("--hmac-field", default="hmac_sha256", help="Packet field name containing hex HMAC signature.")
    p.add_argument("--hmac-max-age-s", type=float, default=5.0, help="Allowed absolute age window for packet t_s.")
    p.add_argument("--clock-t-s", type=float, default=0.0, help="Reference clock in seconds for replay-window checks.")
    p.add_argument("--nonce-field", default="nonce", help="Packet field name used for anti-replay nonce.")
    p.add_argument("--nonce-cache-size", type=int, default=4096, help="Max number of seen nonces kept in memory.")
    p.add_argument("--enforce-nonce", action="store_true", help="Require nonce and drop duplicate nonce packets.")
    p.add_argument("--nonce-ttl-s", type=float, default=30.0, help="Nonce time-to-live in seconds for replay cache.")
    p.add_argument(
        "--nonce-store",
        default="",
        help="Optional nonce persistence file (JSON) to survive process restarts.",
    )
    p.add_argument(
        "--nonce-journal",
        default="",
        help="Optional append-only nonce journal file (JSONL).",
    )
    p.add_argument(
        "--nonce-journal-compact",
        action="store_true",
        help="Compact journal after snapshot save by truncating old entries.",
    )
    p.add_argument(
        "--journal-verify-report",
        default="",
        help="Optional JSON report path for nonce journal replay verification result.",
    )
    p.add_argument(
        "--journal-alert-output",
        default="",
        help="Optional JSON output path for derived journal replay alert event.",
    )
    return p


def _packet_iter(args: argparse.Namespace) -> Iterable[Dict[str, Any]]:
    if args.source == "stdin":
        return _iter_stdin_jsonl()
    if args.source == "tcp":
        return _iter_tcp_jsonl(
            host=args.tcp_host,
            port=args.tcp_port,
            timeout_s=args.tcp_timeout_s,
            max_packets=args.max_packets,
        )
    if args.source == "tcp_server":
        return _iter_tcp_server_jsonl(
            host=args.tcp_host,
            port=args.tcp_port,
            idle_timeout_s=args.tcp_server_idle_timeout_s,
            max_packets=args.max_packets,
        )
    return _iter_jsonl(Path(args.input))


def _iter_tcp_server_jsonl(host: str, port: int, idle_timeout_s: float, max_packets: int) -> Iterator[Dict[str, Any]]:
    count = 0
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((host, port))
        srv.listen(1)
        srv.settimeout(idle_timeout_s)
        conn, _addr = srv.accept()
        with conn:
            conn.settimeout(idle_timeout_s)
            sock_file = conn.makefile("r", encoding="utf-8")
            for line in sock_file:
                s = line.strip()
                if not s:
                    continue
                yield json.loads(s)
                count += 1
                if max_packets > 0 and count >= max_packets:
                    break


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _validate_packet(packet: Dict[str, Any], strict: bool) -> Tuple[bool, str]:
    if not strict:
        return True, "ok"

    required_top = ["t_s", "ambient_temp_c", "cooling_coeff", "workload_intensity", "fabless", "memory", "runtime"]
    for k in required_top:
        if k not in packet:
            return False, f"missing:{k}"

    if not _is_number(packet["t_s"]):
        return False, "type:t_s"
    if not _is_number(packet["ambient_temp_c"]):
        return False, "type:ambient_temp_c"
    if not _is_number(packet["cooling_coeff"]):
        return False, "type:cooling_coeff"
    if not _is_number(packet["workload_intensity"]):
        return False, "type:workload_intensity"
    if not isinstance(packet["fabless"], dict):
        return False, "type:fabless"
    if not isinstance(packet["memory"], dict):
        return False, "type:memory"
    if not isinstance(packet["runtime"], dict):
        return False, "type:runtime"

    if "omega_global" not in packet["fabless"] or not _is_number(packet["fabless"]["omega_global"]):
        return False, "fabless:omega_global"

    mem = packet["memory"]
    for k in ["omega_global", "rowhammer_risk", "retention_risk"]:
        if k not in mem or not _is_number(mem[k]):
            return False, f"memory:{k}"

    rt = packet["runtime"]
    if "scheduler_pressure" not in rt or not _is_number(rt["scheduler_pressure"]):
        return False, "runtime:scheduler_pressure"

    return True, "ok"


def _canonical_payload_json(packet: Dict[str, Any], hmac_field: str) -> str:
    data = {k: v for k, v in packet.items() if k != hmac_field}
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _verify_hmac(packet: Dict[str, Any], *, secret: str, hmac_field: str, max_age_s: float, clock_t_s: float) -> Tuple[bool, str]:
    sig = str(packet.get(hmac_field, ""))
    if not sig:
        return False, "missing_hmac"
    if "t_s" not in packet or not _is_number(packet["t_s"]):
        return False, "invalid_t_s"

    t_s = float(packet["t_s"])
    if max_age_s > 0.0:
        age = abs(clock_t_s - t_s)
        if age > max_age_s:
            return False, "hmac_expired"

    msg = _canonical_payload_json(packet, hmac_field).encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return False, "hmac_mismatch"
    return True, "ok"


def _check_and_record_nonce(
    packet: Dict[str, Any],
    *,
    nonce_field: str,
    seen_nonces: set[str],
    nonce_order: list[str],
    cache_size: int,
    require: bool,
) -> Tuple[bool, str]:
    nonce = packet.get(nonce_field, None)
    if nonce is None or str(nonce) == "":
        if require:
            return False, "missing_nonce"
        return True, "ok"

    n = str(nonce)
    if n in seen_nonces:
        return False, "replayed_nonce"

    seen_nonces.add(n)
    nonce_order.append(n)
    while len(nonce_order) > max(1, cache_size):
        old = nonce_order.pop(0)
        seen_nonces.discard(old)
    return True, "ok"


def _load_nonce_store(path: str) -> Dict[str, float]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    out: Dict[str, float] = {}
    for k, v in data.items():
        if isinstance(k, str) and _is_number(v):
            out[k] = float(v)
    return out


def _save_nonce_store(path: str, store: Dict[str, float]) -> None:
    if not path:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(store, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _packet_digest(packet: Dict[str, Any]) -> str:
    payload = json.dumps(packet, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _journal_hash(nonce: str, t_s: float, payload_digest: str, prev_hash: str) -> str:
    raw = f"{nonce}|{t_s:.6f}|{payload_digest}|{prev_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _append_nonce_journal(path: str, nonce: str, t_s: float, payload_digest: str, prev_hash: str) -> str:
    if not path:
        return prev_hash
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    h = _journal_hash(nonce, t_s, payload_digest, prev_hash)
    with p.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "nonce": nonce,
                    "t_s": t_s,
                    "payload_digest": payload_digest,
                    "prev_hash": prev_hash,
                    "hash": h,
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    return h


def _save_journal_verify_report(path: str, report: Dict[str, Any]) -> None:
    if not path:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _journal_alert_from_report(report: Dict[str, Any]) -> Dict[str, Any]:
    status = str(report.get("status", "unknown"))
    reason = str(report.get("reason", "unknown"))
    severity = "INFO"
    code = "JOURNAL_REPLAY_INFO"
    actionable = False

    if status in {"stopped", "error"}:
        severity = "CRITICAL"
        code = "JOURNAL_REPLAY_INTEGRITY_FAIL"
        actionable = True
    elif status == "ok":
        severity = "OK"
        code = "JOURNAL_REPLAY_VERIFIED"
    elif status in {"empty", "not_enabled"}:
        severity = "INFO"
        code = "JOURNAL_REPLAY_NOT_ACTIVE"
    else:
        severity = "WARN"
        code = "JOURNAL_REPLAY_UNKNOWN_STATUS"

    return {
        "severity": severity,
        "code": code,
        "status": status,
        "reason": reason,
        "verified_entries": int(report.get("verified_entries", 0)),
        "stopped_at_line": int(report.get("stopped_at_line", 0)),
        "head_hash": str(report.get("head_hash", "")),
        "actionable": actionable,
    }


def _save_json(path: str, data: Dict[str, Any]) -> None:
    if not path:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _replay_nonce_journal(path: str, store: Dict[str, float]) -> Tuple[Dict[str, float], str, Dict[str, Any]]:
    head = JOURNAL_GENESIS
    report: Dict[str, Any] = {
        "source_path": path,
        "status": "not_enabled",
        "verified_entries": 0,
        "stopped_at_line": 0,
        "reason": "journal_not_configured",
        "head_hash": head,
    }
    if not path:
        return store, head, report
    p = Path(path)
    report["status"] = "ok"
    report["reason"] = "journal_verified"
    report["source_path"] = str(p)
    if not p.exists():
        report["status"] = "empty"
        report["reason"] = "journal_not_found"
        return store, head, report
    try:
        line_no = 0
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line_no += 1
                s = line.strip()
                if not s:
                    continue
                try:
                    row = json.loads(s)
                except Exception:
                    report["status"] = "stopped"
                    report["stopped_at_line"] = line_no
                    report["reason"] = "invalid_json"
                    continue
                n = row.get("nonce", None)
                ts = row.get("t_s", None)
                pd = row.get("payload_digest", "")
                prev_hash = row.get("prev_hash", "")
                h = row.get("hash", "")
                if (
                    isinstance(n, str)
                    and n
                    and _is_number(ts)
                    and isinstance(pd, str)
                    and len(pd) == 64
                    and isinstance(prev_hash, str)
                    and isinstance(h, str)
                ):
                    expected_prev = head
                    expected_hash = _journal_hash(n, float(ts), pd, expected_prev)
                    if prev_hash != expected_prev or h != expected_hash:
                        # Chain broken: stop replay at first tampered record.
                        report["status"] = "stopped"
                        report["stopped_at_line"] = line_no
                        report["reason"] = "hash_chain_mismatch"
                        break
                    store[n] = float(ts)
                    head = h
                    report["verified_entries"] = int(report["verified_entries"]) + 1
                else:
                    report["status"] = "stopped"
                    report["stopped_at_line"] = line_no
                    report["reason"] = "invalid_row_schema"
                    break
    except Exception:
        report["status"] = "error"
        report["reason"] = "journal_read_exception"
        report["head_hash"] = head
        return store, head, report
    report["head_hash"] = head
    return store, head, report


def _compact_nonce_journal(path: str) -> None:
    if not path:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("", encoding="utf-8")


def _purge_nonce_store(
    store: Dict[str, float],
    *,
    clock_t_s: float,
    nonce_ttl_s: float,
    nonce_cache_size: int,
) -> Dict[str, float]:
    if nonce_ttl_s > 0.0:
        store = {k: v for k, v in store.items() if abs(clock_t_s - v) <= nonce_ttl_s}
    if len(store) > max(1, nonce_cache_size):
        # Keep newest by timestamp.
        pairs = sorted(store.items(), key=lambda kv: kv[1], reverse=True)[: max(1, nonce_cache_size)]
        store = {k: v for k, v in pairs}
    return store


def main(argv: list[str] | None = None) -> None:
    args, _unknown = _build_parser().parse_known_args(argv)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cfg = HBMConfig()
    chain = _load_chain()
    state = HBMPlantState(t_s=0.0, die_temp_c=34.0)
    accepted = 0
    dropped = 0
    seen_nonces: set[str] = set()
    nonce_order: list[str] = []
    nonce_store = _load_nonce_store(args.nonce_store)
    nonce_store, journal_head, journal_verify_report = _replay_nonce_journal(args.nonce_journal, nonce_store)
    nonce_store = _purge_nonce_store(
        nonce_store,
        clock_t_s=float(args.clock_t_s),
        nonce_ttl_s=float(args.nonce_ttl_s),
        nonce_cache_size=int(args.nonce_cache_size),
    )
    for n in nonce_store.keys():
        seen_nonces.add(n)
        nonce_order.append(n)

    for packet in _packet_iter(args):
        if args.auth_token:
            pkt_token = str(packet.get("auth_token", ""))
            if pkt_token != args.auth_token:
                dropped += 1
                continue

        ok, _reason = _validate_packet(packet, strict=args.strict_schema)
        if not ok:
            dropped += 1
            continue

        if args.hmac_secret:
            ok_hmac, _hmac_reason = _verify_hmac(
                packet,
                secret=args.hmac_secret,
                hmac_field=args.hmac_field,
                max_age_s=float(args.hmac_max_age_s),
                clock_t_s=float(args.clock_t_s),
            )
            if not ok_hmac:
                dropped += 1
                continue

        require_nonce = bool(args.enforce_nonce or args.hmac_secret)
        ok_nonce, _nonce_reason = _check_and_record_nonce(
            packet,
            nonce_field=args.nonce_field,
            seen_nonces=seen_nonces,
            nonce_order=nonce_order,
            cache_size=int(args.nonce_cache_size),
            require=require_nonce,
        )
        if not ok_nonce:
            dropped += 1
            continue
        n = packet.get(args.nonce_field, None)
        if n is not None and str(n) != "":
            t_pkt = float(packet.get("t_s", args.clock_t_s))
            nonce_store[str(n)] = t_pkt
            pd = _packet_digest(packet)
            journal_head = _append_nonce_journal(args.nonce_journal, str(n), t_pkt, pd, journal_head)

        snapshots = {
            "fabless": dict(packet.get("fabless", {})),
            "memory": dict(packet.get("memory", {})),
            "battery": dict(packet.get("battery", {})),
            "vectorspace": dict(packet.get("vectorspace", {})),
            "runtime": dict(packet.get("runtime", {})),
        }
        inp = build_input_from_engine_snapshots(
            snapshots,
            ambient_temp_c=float(packet.get("ambient_temp_c", 30.0)),
            cooling_coeff=float(packet.get("cooling_coeff", 0.30)),
            workload_intensity=float(packet.get("workload_intensity", 0.7)),
        )
        tick = run_runtime_tick(cfg, inp, protection_state=state.protection_state)
        t_s = float(packet.get("t_s", state.t_s + 0.5))
        state = HBMPlantState(
            t_s=t_s,
            die_temp_c=state.die_temp_c,
            controller_latency_ms=state.controller_latency_ms,
            protection_state=tick.protection_state_after,
        )
        append_observation_to_chain(
            chain,
            t_s=t_s,
            obs=tick.observation_after_protection,
            policy_mode=tick.policy.mode,
            extra={
                "source": f"stream_{args.source}",
                "scheduler_pressure": RuntimeState(
                    scheduler_pressure=float(packet.get("runtime", {}).get("scheduler_pressure", 0.3))
                ).scheduler_pressure,
                "protection_limited": tick.protection_state_after.is_limited,
            },
        )
        accepted += 1

    nonce_store = _purge_nonce_store(
        nonce_store,
        clock_t_s=float(args.clock_t_s),
        nonce_ttl_s=float(args.nonce_ttl_s),
        nonce_cache_size=int(args.nonce_cache_size),
    )
    _save_nonce_store(args.nonce_store, nonce_store)
    journal_verify_report["loaded_nonces_after_purge"] = len(nonce_store)
    journal_verify_report["journal_head_after_replay"] = journal_head
    _save_journal_verify_report(args.journal_verify_report, journal_verify_report)
    journal_alert = _journal_alert_from_report(journal_verify_report)
    _save_json(args.journal_alert_output, journal_alert)
    if journal_alert["severity"] == "CRITICAL":
        append_journal_alert_to_chain(
            chain,
            t_s=float(args.clock_t_s),
            alert=journal_alert,
        )
    if args.nonce_journal and args.nonce_journal_compact:
        _compact_nonce_journal(args.nonce_journal)

    chain.export_json(str(out_path))
    print(f"Wrote: {out_path}")
    print(f"Ingestion stats: accepted={accepted} dropped={dropped}")
    print(
        "Journal replay alert: "
        f"{journal_alert['severity']} "
        f"{journal_alert['code']} "
        f"(status={journal_alert['status']}, reason={journal_alert['reason']})"
    )
    print(chain.summary())


if __name__ == "__main__":
    main()
