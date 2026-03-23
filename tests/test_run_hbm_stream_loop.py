from pathlib import Path
import runpy
import socket
import threading
from unittest.mock import patch
import tempfile
import hashlib
import hmac
import json


def test_run_hbm_stream_loop_generates_chain_json() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_hbm_stream_loop.py"
    runpy.run_path(str(script), run_name="__main__")
    out = root / "reports" / "HBM_STREAM_AUDIT_CHAIN.json"
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "stream_file" in text
    assert "HBM_" in text


def test_run_hbm_stream_loop_tcp_source_generates_chain_json() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_hbm_stream_loop.py"
    out = root / "reports" / "HBM_STREAM_AUDIT_CHAIN_TCP.json"

    host = "127.0.0.1"
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind((host, 0))
    srv.listen(1)
    port = srv.getsockname()[1]

    payloads = [
        '{"t_s":0.0,"ambient_temp_c":33.0,"fabless":{"omega_global":0.82},"memory":{"omega_global":0.78,"rowhammer_risk":0.22,"retention_risk":0.2},"runtime":{"scheduler_pressure":0.5}}',
        '{"t_s":0.5,"ambient_temp_c":35.0,"fabless":{"omega_global":0.77},"memory":{"omega_global":0.71,"rowhammer_risk":0.35,"retention_risk":0.3},"runtime":{"scheduler_pressure":0.7}}',
    ]

    def _serve() -> None:
        conn, _ = srv.accept()
        with conn:
            for line in payloads:
                conn.sendall((line + "\n").encode("utf-8"))
        srv.close()

    th = threading.Thread(target=_serve, daemon=True)
    th.start()

    with patch(
        "sys.argv",
        [
            str(script),
            "--source",
            "tcp",
            "--tcp-host",
            host,
            "--tcp-port",
            str(port),
            "--max-packets",
            "2",
            "--output",
            str(out),
        ],
    ):
        runpy.run_path(str(script), run_name="__main__")
    th.join(timeout=2.0)

    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "stream_tcp" in text


def test_run_hbm_stream_loop_tcp_server_source_generates_chain_json() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_hbm_stream_loop.py"
    out = root / "reports" / "HBM_STREAM_AUDIT_CHAIN_TCP_SERVER.json"

    host = "127.0.0.1"
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind((host, 0))
    port = probe.getsockname()[1]
    probe.close()

    payloads = [
        '{"t_s":0.0,"ambient_temp_c":34.0,"fabless":{"omega_global":0.80},"memory":{"omega_global":0.75,"rowhammer_risk":0.25,"retention_risk":0.22},"runtime":{"scheduler_pressure":0.55}}',
        '{"t_s":0.5,"ambient_temp_c":36.0,"fabless":{"omega_global":0.74},"memory":{"omega_global":0.68,"rowhammer_risk":0.38,"retention_risk":0.33},"runtime":{"scheduler_pressure":0.73}}',
    ]

    def _client_push() -> None:
        for _ in range(50):
            try:
                conn = socket.create_connection((host, port), timeout=0.2)
                with conn:
                    for line in payloads:
                        conn.sendall((line + "\n").encode("utf-8"))
                return
            except OSError:
                continue

    th = threading.Thread(target=_client_push, daemon=True)
    th.start()

    with patch(
        "sys.argv",
        [
            str(script),
            "--source",
            "tcp_server",
            "--tcp-host",
            host,
            "--tcp-port",
            str(port),
            "--max-packets",
            "2",
            "--tcp-server-idle-timeout-s",
            "3.0",
            "--output",
            str(out),
        ],
    ):
        runpy.run_path(str(script), run_name="__main__")
    th.join(timeout=2.0)

    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "stream_tcp_server" in text


def test_run_hbm_stream_loop_strict_schema_drops_invalid_packet() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_hbm_stream_loop.py"
    out = root / "reports" / "HBM_STREAM_AUDIT_CHAIN_STRICT.json"

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as tf:
        tf.write(
            '{"t_s":0.0,"ambient_temp_c":33.0,"cooling_coeff":0.3,"workload_intensity":0.7,"fabless":{"omega_global":0.8},"memory":{"omega_global":0.75,"rowhammer_risk":0.2,"retention_risk":0.2},"runtime":{"scheduler_pressure":0.4}}\n'
        )
        tf.write('{"t_s":"bad","fabless":{}}\n')
        in_path = tf.name

    with patch(
        "sys.argv",
        [
            str(script),
            "--source",
            "file",
            "--input",
            in_path,
            "--strict-schema",
            "--output",
            str(out),
        ],
    ):
        runpy.run_path(str(script), run_name="__main__")

    assert out.exists()
    text = out.read_text(encoding="utf-8")
    # Only one valid packet should be recorded
    assert '"block_count": 1' in text


def test_run_hbm_stream_loop_auth_token_filters_packets() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_hbm_stream_loop.py"
    out = root / "reports" / "HBM_STREAM_AUDIT_CHAIN_AUTH.json"

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as tf:
        tf.write(
            '{"auth_token":"secret","t_s":0.0,"ambient_temp_c":33.0,"cooling_coeff":0.3,"workload_intensity":0.7,"fabless":{"omega_global":0.8},"memory":{"omega_global":0.75,"rowhammer_risk":0.2,"retention_risk":0.2},"runtime":{"scheduler_pressure":0.4}}\n'
        )
        tf.write(
            '{"auth_token":"wrong","t_s":0.5,"ambient_temp_c":34.0,"cooling_coeff":0.3,"workload_intensity":0.8,"fabless":{"omega_global":0.7},"memory":{"omega_global":0.65,"rowhammer_risk":0.3,"retention_risk":0.25},"runtime":{"scheduler_pressure":0.6}}\n'
        )
        in_path = tf.name

    with patch(
        "sys.argv",
        [
            str(script),
            "--source",
            "file",
            "--input",
            in_path,
            "--auth-token",
            "secret",
            "--output",
            str(out),
        ],
    ):
        runpy.run_path(str(script), run_name="__main__")

    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert '"block_count": 1' in text


def test_run_hbm_stream_loop_hmac_accepts_valid_and_drops_invalid() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_hbm_stream_loop.py"
    out = root / "reports" / "HBM_STREAM_AUDIT_CHAIN_HMAC.json"

    secret = "topsecret"
    valid_payload = {
        "nonce": "n-hmac-1",
        "t_s": 10.0,
        "ambient_temp_c": 33.0,
        "cooling_coeff": 0.3,
        "workload_intensity": 0.7,
        "fabless": {"omega_global": 0.8},
        "memory": {"omega_global": 0.75, "rowhammer_risk": 0.2, "retention_risk": 0.2},
        "runtime": {"scheduler_pressure": 0.4},
    }
    msg = json.dumps(valid_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    valid_sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    valid_packet = dict(valid_payload)
    valid_packet["hmac_sha256"] = valid_sig

    invalid_packet = dict(valid_payload)
    invalid_packet["nonce"] = "n-hmac-2"
    invalid_packet["t_s"] = 10.5
    invalid_packet["hmac_sha256"] = "deadbeef"

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as tf:
        tf.write(json.dumps(valid_packet, ensure_ascii=False) + "\n")
        tf.write(json.dumps(invalid_packet, ensure_ascii=False) + "\n")
        in_path = tf.name

    with patch(
        "sys.argv",
        [
            str(script),
            "--source",
            "file",
            "--input",
            in_path,
            "--hmac-secret",
            secret,
            "--clock-t-s",
            "10.0",
            "--hmac-max-age-s",
            "5.0",
            "--output",
            str(out),
        ],
    ):
        runpy.run_path(str(script), run_name="__main__")

    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert '"block_count": 1' in text


def test_run_hbm_stream_loop_hmac_replay_window_drops_old_packets() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_hbm_stream_loop.py"
    out = root / "reports" / "HBM_STREAM_AUDIT_CHAIN_HMAC_AGE.json"

    secret = "topsecret"
    payload = {
        "nonce": "n-old-1",
        "t_s": 1.0,
        "ambient_temp_c": 33.0,
        "cooling_coeff": 0.3,
        "workload_intensity": 0.7,
        "fabless": {"omega_global": 0.8},
        "memory": {"omega_global": 0.75, "rowhammer_risk": 0.2, "retention_risk": 0.2},
        "runtime": {"scheduler_pressure": 0.4},
    }
    msg = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    packet = dict(payload)
    packet["hmac_sha256"] = sig

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as tf:
        tf.write(json.dumps(packet, ensure_ascii=False) + "\n")
        in_path = tf.name

    with patch(
        "sys.argv",
        [
            str(script),
            "--source",
            "file",
            "--input",
            in_path,
            "--hmac-secret",
            secret,
            "--clock-t-s",
            "20.0",
            "--hmac-max-age-s",
            "2.0",
            "--output",
            str(out),
        ],
    ):
        runpy.run_path(str(script), run_name="__main__")

    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert '"block_count": 0' in text


def test_run_hbm_stream_loop_enforce_nonce_drops_duplicate_nonce() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_hbm_stream_loop.py"
    out = root / "reports" / "HBM_STREAM_AUDIT_CHAIN_NONCE.json"

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as tf:
        tf.write(
            '{"nonce":"n-1","t_s":0.0,"ambient_temp_c":33.0,"cooling_coeff":0.3,"workload_intensity":0.7,"fabless":{"omega_global":0.8},"memory":{"omega_global":0.75,"rowhammer_risk":0.2,"retention_risk":0.2},"runtime":{"scheduler_pressure":0.4}}\n'
        )
        tf.write(
            '{"nonce":"n-1","t_s":0.5,"ambient_temp_c":34.0,"cooling_coeff":0.3,"workload_intensity":0.8,"fabless":{"omega_global":0.7},"memory":{"omega_global":0.65,"rowhammer_risk":0.3,"retention_risk":0.25},"runtime":{"scheduler_pressure":0.6}}\n'
        )
        in_path = tf.name

    with patch(
        "sys.argv",
        [
            str(script),
            "--source",
            "file",
            "--input",
            in_path,
            "--enforce-nonce",
            "--output",
            str(out),
        ],
    ):
        runpy.run_path(str(script), run_name="__main__")

    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert '"block_count": 1' in text


def test_run_hbm_stream_loop_hmac_requires_nonce() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_hbm_stream_loop.py"
    out = root / "reports" / "HBM_STREAM_AUDIT_CHAIN_HMAC_NONCE.json"

    secret = "topsecret"
    payload = {
        "t_s": 10.0,
        "ambient_temp_c": 33.0,
        "cooling_coeff": 0.3,
        "workload_intensity": 0.7,
        "fabless": {"omega_global": 0.8},
        "memory": {"omega_global": 0.75, "rowhammer_risk": 0.2, "retention_risk": 0.2},
        "runtime": {"scheduler_pressure": 0.4},
    }
    msg = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    payload["hmac_sha256"] = sig

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as tf:
        tf.write(json.dumps(payload, ensure_ascii=False) + "\n")
        in_path = tf.name

    with patch(
        "sys.argv",
        [
            str(script),
            "--source",
            "file",
            "--input",
            in_path,
            "--hmac-secret",
            secret,
            "--clock-t-s",
            "10.0",
            "--hmac-max-age-s",
            "5.0",
            "--output",
            str(out),
        ],
    ):
        runpy.run_path(str(script), run_name="__main__")

    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert '"block_count": 0' in text


def test_run_hbm_stream_loop_nonce_store_persists_and_blocks_replay_after_restart() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_hbm_stream_loop.py"
    out1 = root / "reports" / "HBM_STREAM_AUDIT_CHAIN_NONCE_STORE_1.json"
    out2 = root / "reports" / "HBM_STREAM_AUDIT_CHAIN_NONCE_STORE_2.json"

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as tf:
        tf.write(
            '{"nonce":"persist-n-1","t_s":50.0,"ambient_temp_c":33.0,"cooling_coeff":0.3,"workload_intensity":0.7,"fabless":{"omega_global":0.8},"memory":{"omega_global":0.75,"rowhammer_risk":0.2,"retention_risk":0.2},"runtime":{"scheduler_pressure":0.4}}\n'
        )
        in_path = tf.name

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as sf:
        store_path = sf.name

    with patch(
        "sys.argv",
        [
            str(script),
            "--source",
            "file",
            "--input",
            in_path,
            "--enforce-nonce",
            "--nonce-store",
            store_path,
            "--clock-t-s",
            "50.0",
            "--nonce-ttl-s",
            "30.0",
            "--output",
            str(out1),
        ],
    ):
        runpy.run_path(str(script), run_name="__main__")

    with patch(
        "sys.argv",
        [
            str(script),
            "--source",
            "file",
            "--input",
            in_path,
            "--enforce-nonce",
            "--nonce-store",
            store_path,
            "--clock-t-s",
            "52.0",
            "--nonce-ttl-s",
            "30.0",
            "--output",
            str(out2),
        ],
    ):
        runpy.run_path(str(script), run_name="__main__")

    assert out1.exists()
    assert out2.exists()
    text1 = out1.read_text(encoding="utf-8")
    text2 = out2.read_text(encoding="utf-8")
    assert '"block_count": 1' in text1
    assert '"block_count": 0' in text2


def test_run_hbm_stream_loop_nonce_store_ttl_allows_reuse_after_expiration() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_hbm_stream_loop.py"
    out = root / "reports" / "HBM_STREAM_AUDIT_CHAIN_NONCE_TTL.json"

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as sf:
        store_path = sf.name

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as tf:
        tf.write(
            '{"nonce":"ttl-n-1","t_s":10.0,"ambient_temp_c":33.0,"cooling_coeff":0.3,"workload_intensity":0.7,"fabless":{"omega_global":0.8},"memory":{"omega_global":0.75,"rowhammer_risk":0.2,"retention_risk":0.2},"runtime":{"scheduler_pressure":0.4}}\n'
        )
        in_path = tf.name

    # First run writes nonce at t=10
    with patch(
        "sys.argv",
        [
            str(script),
            "--source",
            "file",
            "--input",
            in_path,
            "--enforce-nonce",
            "--nonce-store",
            store_path,
            "--clock-t-s",
            "10.0",
            "--nonce-ttl-s",
            "2.0",
            "--output",
            str(out),
        ],
    ):
        runpy.run_path(str(script), run_name="__main__")

    # Second run far in future, nonce should expire from cache and be accepted again.
    with patch(
        "sys.argv",
        [
            str(script),
            "--source",
            "file",
            "--input",
            in_path,
            "--enforce-nonce",
            "--nonce-store",
            store_path,
            "--clock-t-s",
            "20.0",
            "--nonce-ttl-s",
            "2.0",
            "--output",
            str(out),
        ],
    ):
        runpy.run_path(str(script), run_name="__main__")

    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert '"block_count": 1' in text


def test_run_hbm_stream_loop_nonce_journal_append_and_compact() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_hbm_stream_loop.py"
    out = root / "reports" / "HBM_STREAM_AUDIT_CHAIN_NONCE_JOURNAL.json"

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as sf:
        store_path = sf.name
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as jf:
        journal_path = jf.name
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as tf:
        tf.write(
            '{"nonce":"jn-1","t_s":12.0,"ambient_temp_c":33.0,"cooling_coeff":0.3,"workload_intensity":0.7,"fabless":{"omega_global":0.8},"memory":{"omega_global":0.75,"rowhammer_risk":0.2,"retention_risk":0.2},"runtime":{"scheduler_pressure":0.4}}\n'
        )
        in_path = tf.name

    with patch(
        "sys.argv",
        [
            str(script),
            "--source",
            "file",
            "--input",
            in_path,
            "--enforce-nonce",
            "--nonce-store",
            store_path,
            "--nonce-journal",
            journal_path,
            "--output",
            str(out),
        ],
    ):
        runpy.run_path(str(script), run_name="__main__")

    # journal should contain appended nonce event
    jtxt = Path(journal_path).read_text(encoding="utf-8")
    assert "jn-1" in jtxt
    assert '"payload_digest"' in jtxt
    assert '"prev_hash"' in jtxt
    assert '"hash"' in jtxt

    with patch(
        "sys.argv",
        [
            str(script),
            "--source",
            "file",
            "--input",
            in_path,
            "--enforce-nonce",
            "--nonce-store",
            store_path,
            "--nonce-journal",
            journal_path,
            "--nonce-journal-compact",
            "--output",
            str(out),
        ],
    ):
        runpy.run_path(str(script), run_name="__main__")

    # compact should truncate journal
    jtxt2 = Path(journal_path).read_text(encoding="utf-8")
    assert jtxt2 == ""


def test_run_hbm_stream_loop_nonce_journal_tamper_stops_replay() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_hbm_stream_loop.py"
    out = root / "reports" / "HBM_STREAM_AUDIT_CHAIN_NONCE_JOURNAL_TAMPER.json"

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as sf:
        store_path = sf.name
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as jf:
        journal_path = jf.name
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as tf:
        tf.write(
            '{"nonce":"jt-1","t_s":20.0,"ambient_temp_c":33.0,"cooling_coeff":0.3,"workload_intensity":0.7,"fabless":{"omega_global":0.8},"memory":{"omega_global":0.75,"rowhammer_risk":0.2,"retention_risk":0.2},"runtime":{"scheduler_pressure":0.4}}\n'
        )
        in_path = tf.name

    # First run writes one valid journal entry.
    with patch(
        "sys.argv",
        [
            str(script),
            "--source",
            "file",
            "--input",
            in_path,
            "--enforce-nonce",
            "--nonce-store",
            store_path,
            "--nonce-journal",
            journal_path,
            "--clock-t-s",
            "20.0",
            "--nonce-ttl-s",
            "60.0",
            "--output",
            str(out),
        ],
    ):
        runpy.run_path(str(script), run_name="__main__")

    # Tamper the journal hash.
    jline = Path(journal_path).read_text(encoding="utf-8").strip()
    row = json.loads(jline)
    row["hash"] = "00" * 32
    Path(journal_path).write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")

    # Replay same nonce: tampered journal should not replay nonce, so packet is accepted once.
    with patch(
        "sys.argv",
        [
            str(script),
            "--source",
            "file",
            "--input",
            in_path,
            "--enforce-nonce",
            "--nonce-store",
            "",  # rely only on journal replay to test chain-check path
            "--nonce-journal",
            journal_path,
            "--clock-t-s",
            "21.0",
            "--nonce-ttl-s",
            "60.0",
            "--output",
            str(out),
        ],
    ):
        runpy.run_path(str(script), run_name="__main__")

    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert '"block_count": 2' in text


def test_run_hbm_stream_loop_nonce_journal_tamper_payload_digest_stops_replay() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_hbm_stream_loop.py"
    out = root / "reports" / "HBM_STREAM_AUDIT_CHAIN_NONCE_JOURNAL_TAMPER_PD.json"

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as sf:
        store_path = sf.name
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as jf:
        journal_path = jf.name
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as tf:
        tf.write(
            '{"nonce":"jtpd-1","t_s":30.0,"ambient_temp_c":33.0,"cooling_coeff":0.3,"workload_intensity":0.7,"fabless":{"omega_global":0.8},"memory":{"omega_global":0.75,"rowhammer_risk":0.2,"retention_risk":0.2},"runtime":{"scheduler_pressure":0.4}}\n'
        )
        in_path = tf.name

    with patch(
        "sys.argv",
        [
            str(script),
            "--source",
            "file",
            "--input",
            in_path,
            "--enforce-nonce",
            "--nonce-store",
            store_path,
            "--nonce-journal",
            journal_path,
            "--clock-t-s",
            "30.0",
            "--nonce-ttl-s",
            "60.0",
            "--output",
            str(out),
        ],
    ):
        runpy.run_path(str(script), run_name="__main__")

    # Tamper payload digest.
    jline = Path(journal_path).read_text(encoding="utf-8").strip()
    row = json.loads(jline)
    row["payload_digest"] = "11" * 32
    Path(journal_path).write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")

    with patch(
        "sys.argv",
        [
            str(script),
            "--source",
            "file",
            "--input",
            in_path,
            "--enforce-nonce",
            "--nonce-store",
            "",  # force replay-only path
            "--nonce-journal",
            journal_path,
            "--clock-t-s",
            "31.0",
            "--nonce-ttl-s",
            "60.0",
            "--output",
            str(out),
        ],
    ):
        runpy.run_path(str(script), run_name="__main__")

    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert '"block_count": 2' in text


def test_run_hbm_stream_loop_journal_verify_report_ok() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_hbm_stream_loop.py"
    out = root / "reports" / "HBM_STREAM_AUDIT_CHAIN_VERIFY_REPORT_OK.json"

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as sf:
        store_path = sf.name
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as jf:
        journal_path = jf.name
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as rf:
        report_path = rf.name
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as tf:
        tf.write(
            '{"nonce":"jvr-ok-1","t_s":40.0,"ambient_temp_c":33.0,"cooling_coeff":0.3,"workload_intensity":0.7,"fabless":{"omega_global":0.8},"memory":{"omega_global":0.75,"rowhammer_risk":0.2,"retention_risk":0.2},"runtime":{"scheduler_pressure":0.4}}\n'
        )
        in_path = tf.name

    with patch(
        "sys.argv",
        [
            str(script),
            "--source",
            "file",
            "--input",
            in_path,
            "--enforce-nonce",
            "--nonce-store",
            store_path,
            "--nonce-journal",
            journal_path,
            "--clock-t-s",
            "40.0",
            "--nonce-ttl-s",
            "60.0",
            "--journal-verify-report",
            report_path,
            "--output",
            str(out),
        ],
    ):
        runpy.run_path(str(script), run_name="__main__")

    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    assert report["status"] == "ok"
    assert report["reason"] == "journal_verified"
    assert report["verified_entries"] >= 0
    assert "journal_head_after_replay" in report


def test_run_hbm_stream_loop_journal_verify_report_stopped_on_tamper() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_hbm_stream_loop.py"
    out = root / "reports" / "HBM_STREAM_AUDIT_CHAIN_VERIFY_REPORT_TAMPER.json"

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as jf:
        journal_path = jf.name
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as rf:
        report_path = rf.name
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as tf:
        tf.write(
            '{"nonce":"jvr-tamper-1","t_s":41.0,"ambient_temp_c":33.0,"cooling_coeff":0.3,"workload_intensity":0.7,"fabless":{"omega_global":0.8},"memory":{"omega_global":0.75,"rowhammer_risk":0.2,"retention_risk":0.2},"runtime":{"scheduler_pressure":0.4}}\n'
        )
        in_path = tf.name

    # Seed journal with a valid row first.
    with patch(
        "sys.argv",
        [
            str(script),
            "--source",
            "file",
            "--input",
            in_path,
            "--enforce-nonce",
            "--nonce-store",
            "",
            "--nonce-journal",
            journal_path,
            "--clock-t-s",
            "41.0",
            "--nonce-ttl-s",
            "60.0",
            "--output",
            str(out),
        ],
    ):
        runpy.run_path(str(script), run_name="__main__")

    row = json.loads(Path(journal_path).read_text(encoding="utf-8").strip())
    row["hash"] = "22" * 32
    Path(journal_path).write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")

    with patch(
        "sys.argv",
        [
            str(script),
            "--source",
            "file",
            "--input",
            in_path,
            "--enforce-nonce",
            "--nonce-store",
            "",
            "--nonce-journal",
            journal_path,
            "--journal-verify-report",
            report_path,
            "--clock-t-s",
            "42.0",
            "--nonce-ttl-s",
            "60.0",
            "--output",
            str(out),
        ],
    ):
        runpy.run_path(str(script), run_name="__main__")

    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    assert report["status"] == "stopped"
    assert report["reason"] == "hash_chain_mismatch"
    assert report["stopped_at_line"] == 1


def test_run_hbm_stream_loop_journal_alert_output_critical_on_tamper() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_hbm_stream_loop.py"
    out = root / "reports" / "HBM_STREAM_AUDIT_CHAIN_ALERT_TAMPER.json"

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as jf:
        journal_path = jf.name
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as af:
        alert_path = af.name
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as tf:
        tf.write(
            '{"nonce":"jal-tamper-1","t_s":51.0,"ambient_temp_c":33.0,"cooling_coeff":0.3,"workload_intensity":0.7,"fabless":{"omega_global":0.8},"memory":{"omega_global":0.75,"rowhammer_risk":0.2,"retention_risk":0.2},"runtime":{"scheduler_pressure":0.4}}\n'
        )
        in_path = tf.name

    # Seed journal.
    with patch(
        "sys.argv",
        [
            str(script),
            "--source",
            "file",
            "--input",
            in_path,
            "--enforce-nonce",
            "--nonce-store",
            "",
            "--nonce-journal",
            journal_path,
            "--clock-t-s",
            "51.0",
            "--nonce-ttl-s",
            "60.0",
            "--output",
            str(out),
        ],
    ):
        runpy.run_path(str(script), run_name="__main__")

    row = json.loads(Path(journal_path).read_text(encoding="utf-8").strip())
    row["hash"] = "33" * 32
    Path(journal_path).write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")

    with patch(
        "sys.argv",
        [
            str(script),
            "--source",
            "file",
            "--input",
            in_path,
            "--enforce-nonce",
            "--nonce-store",
            "",
            "--nonce-journal",
            journal_path,
            "--journal-alert-output",
            alert_path,
            "--clock-t-s",
            "52.0",
            "--nonce-ttl-s",
            "60.0",
            "--output",
            str(out),
        ],
    ):
        runpy.run_path(str(script), run_name="__main__")

    alert = json.loads(Path(alert_path).read_text(encoding="utf-8"))
    assert alert["severity"] == "CRITICAL"
    assert alert["code"] == "JOURNAL_REPLAY_INTEGRITY_FAIL"
    assert alert["status"] == "stopped"
    assert alert["actionable"] is True


def test_run_hbm_stream_loop_journal_alert_output_ok_on_clean_replay() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_hbm_stream_loop.py"
    out = root / "reports" / "HBM_STREAM_AUDIT_CHAIN_ALERT_OK.json"

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as jf:
        journal_path = jf.name
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as af:
        alert_path = af.name
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as tf:
        tf.write(
            '{"nonce":"jal-ok-1","t_s":61.0,"ambient_temp_c":33.0,"cooling_coeff":0.3,"workload_intensity":0.7,"fabless":{"omega_global":0.8},"memory":{"omega_global":0.75,"rowhammer_risk":0.2,"retention_risk":0.2},"runtime":{"scheduler_pressure":0.4}}\n'
        )
        in_path = tf.name

    with patch(
        "sys.argv",
        [
            str(script),
            "--source",
            "file",
            "--input",
            in_path,
            "--enforce-nonce",
            "--nonce-store",
            "",
            "--nonce-journal",
            journal_path,
            "--clock-t-s",
            "61.0",
            "--nonce-ttl-s",
            "60.0",
            "--output",
            str(out),
        ],
    ):
        runpy.run_path(str(script), run_name="__main__")

    with patch(
        "sys.argv",
        [
            str(script),
            "--source",
            "file",
            "--input",
            in_path,
            "--enforce-nonce",
            "--nonce-store",
            "",
            "--nonce-journal",
            journal_path,
            "--journal-alert-output",
            alert_path,
            "--clock-t-s",
            "62.0",
            "--nonce-ttl-s",
            "60.0",
            "--output",
            str(out),
        ],
    ):
        runpy.run_path(str(script), run_name="__main__")

    alert = json.loads(Path(alert_path).read_text(encoding="utf-8"))
    assert alert["severity"] == "OK"
    assert alert["code"] == "JOURNAL_REPLAY_VERIFIED"
    assert alert["status"] == "ok"
    assert alert["actionable"] is False
