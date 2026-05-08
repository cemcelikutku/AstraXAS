from __future__ import annotations

import json
import threading
import time

from astra_xas import AstraConfig
from astra_xas.beamtime._synthetic import write_synthetic_xasd
from astra_xas.beamtime.replay import replay
from astra_xas.beamtime.session import read_session_log
from astra_xas.beamtime.watcher import watch


def test_beamtime_replay_and_watch(tmp_path):
    source = tmp_path / "source"
    incoming = tmp_path / "incoming"
    output = tmp_path / "output"
    source.mkdir()
    for i in range(1, 6):
        write_synthetic_xasd(source / f"scan_{i:03d}.xasd", seed=i)

    scenario = tmp_path / "scenario.yaml"
    scenario.write_text(
        "\n".join(
            [
                f"source_dir: {source}",
                f"target_dir: {incoming}",
                "interval_s: 0.1",
                "jitter_s: 0.0",
                "shuffle: false",
                "inject: []",
                "",
            ]
        ),
        encoding="utf-8",
    )

    stop_event = threading.Event()
    thread = threading.Thread(
        target=watch,
        kwargs={
            "incoming_dir": incoming,
            "output_dir": output,
            "config": AstraConfig(),
            "stop_event": stop_event,
            "max_files": 5,
        },
        daemon=True,
    )
    thread.start()

    replay(scenario, log=lambda *_: None)

    log_path = output / "ASTRA_beamtime_session.log"
    deadline = time.monotonic() + 15.0
    rows = []
    while time.monotonic() < deadline:
        rows = read_session_log(log_path)
        if len(rows) == 5:
            break
        time.sleep(0.1)
    else:
        raise AssertionError(f"Timed out waiting for 5 session rows; saw {len(rows)}")

    stop_event.set()
    thread.join(timeout=5.0)
    if thread.is_alive():
        raise AssertionError("Beamtime watcher thread did not stop after max_files.")

    rows = read_session_log(log_path)
    assert len(rows) == 5
    assert all(row["status"] in {"ok", "warn", "reject"} for row in rows)

    checkpoint_path = output / "_astra_session" / "checkpoint.json"
    assert checkpoint_path.exists()
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert len(checkpoint["processed"]) == 5
