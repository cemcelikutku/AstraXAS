from __future__ import annotations

import threading
import time

from astra_xas import AstraConfig
from astra_xas.beamtime._synthetic import write_synthetic_xasd
from astra_xas.beamtime.replay import replay
from astra_xas.beamtime.session import read_session_log
from astra_xas.beamtime.watcher import watch


def test_beamtime_per_scan_plots_and_dashboard(tmp_path):
    source = tmp_path / "source"
    incoming = tmp_path / "incoming"
    output = tmp_path / "output"
    source.mkdir()
    expected_names = [f"scan_{i:03d}.xasd" for i in range(1, 6)]
    for i, name in enumerate(expected_names, start=1):
        write_synthetic_xasd(source / name, seed=i)

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
    plot_dir = output / "plots" / "beamtime"
    dashboard_path = output / "index.html"
    deadline = time.monotonic() + 15.0
    missing = ""
    while time.monotonic() < deadline:
        rows = read_session_log(log_path)
        pngs = sorted(plot_dir.glob("*.png")) if plot_dir.exists() else []
        dashboard_text = dashboard_path.read_text(encoding="utf-8") if dashboard_path.exists() else ""
        has_rows = len(rows) == 5
        has_pngs = len(pngs) == 5
        has_dashboard = bool(dashboard_text) and all(name in dashboard_text for name in expected_names)
        if has_rows and has_pngs and has_dashboard:
            break
        missing = (
            f"rows={len(rows)}/5, pngs={len(pngs)}/5, "
            f"dashboard={'yes' if dashboard_path.exists() else 'no'}"
        )
        time.sleep(0.1)
    else:
        raise AssertionError(f"Timed out waiting for beamtime phase 2 artifacts: {missing}")

    stop_event.set()
    thread.join(timeout=5.0)
    if thread.is_alive():
        raise AssertionError("Beamtime watcher thread did not stop after max_files.")

    rows = read_session_log(log_path)
    pngs = sorted(plot_dir.glob("*.png"))
    dashboard_text = dashboard_path.read_text(encoding="utf-8")

    assert len(rows) == 5
    assert all(row["status"] in {"ok", "warn", "reject"} for row in rows)
    assert len(pngs) == 5
    assert {path.stem for path in pngs} == {name.removesuffix(".xasd") for name in expected_names}
    assert dashboard_path.exists()
    assert "AstraXAS Beamtime Dashboard" in dashboard_text
    assert all(name in dashboard_text for name in expected_names)
    assert 'content="5"' in dashboard_text
