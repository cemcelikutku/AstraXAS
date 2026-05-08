from __future__ import annotations

import html
import json
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from astra_xas.beamtime.session import read_session_log


DASHBOARD_MAX_RECENT = 20
DASHBOARD_REFRESH_SECONDS = 5


def _esc(value) -> str:
    return html.escape(str(value), quote=True)


def _plot_rel_url(filename: str) -> str:
    rel = Path("plots") / "beamtime" / f"{Path(filename).stem}.png"
    return quote(rel.as_posix(), safe="/")


def _rel_url(path: str) -> str:
    return quote(Path(path).as_posix(), safe="/")


def _status_class(status: str) -> str:
    if status in {"ok", "warn", "reject", "pending", "ready", "error"}:
        return status
    return ""


def _scan_row(row: dict, output_dir: Path) -> str:
    filename = str(row.get("filename", ""))
    plot_path = output_dir / "plots" / "beamtime" / f"{Path(filename).stem}.png"
    if plot_path.exists():
        plot_html = (
            f'<a href="{_plot_rel_url(filename)}">'
            f'<img class="thumb" src="{_plot_rel_url(filename)}" alt="QC plot for {_esc(filename)}"></a>'
        )
    else:
        plot_html = '<span class="noplot">(no plot)</span>'
    status = str(row.get("status", ""))
    return f"""
            <div class="row">
              <div>{_esc(row.get("timestamp_iso", ""))}</div>
              <div><div class="filename">{_esc(filename)}</div>{plot_html}</div>
              <div class="{_status_class(status)}">{_esc(status)}</div>
              <div>{_esc(row.get("n_warnings", 0))}</div>
              <div>{_esc(row.get("n_jumps", 0))}</div>
            </div>"""


def _read_group_summaries(output_dir: Path, log=print) -> list[dict]:
    groups = []
    groups_dir = output_dir / "groups"
    if not groups_dir.exists():
        return groups
    for path in sorted(groups_dir.glob("*_group_summary.json")):
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                groups.append(data)
        except Exception as exc:
            log(f"WARNING: could not read beamtime group summary {path.name}: {exc}")
    return sorted(groups, key=lambda item: str(item.get("last_updated_iso", "")), reverse=True)


def _group_row(group: dict, output_dir: Path) -> str:
    base_name = str(group.get("base_name", ""))
    status = str(group.get("last_merge_status", "pending"))
    output_files = group.get("output_files", {}) if isinstance(group.get("output_files", {}), dict) else {}
    qc_rel = str(output_files.get("qc_plot", ""))
    qc_path = output_dir / qc_rel if qc_rel else None
    if qc_rel and qc_path is not None and qc_path.exists():
        plot_html = (
            f'<a href="{_rel_url(qc_rel)}">'
            f'<img class="thumb" src="{_rel_url(qc_rel)}" alt="Group QC plot for {_esc(base_name)}"></a>'
        )
    else:
        plot_html = '<span class="noplot">(no plot - group pending)</span>'
    error = str(group.get("last_merge_error", ""))
    error_html = f'<div class="noplot">{_esc(error)}</div>' if error else ""
    return f"""
            <div class="group-row">
              <div class="filename">{_esc(base_name)}</div>
              <div>{_esc(group.get("n_accepted", 0))}</div>
              <div class="{_status_class(status)}">{_esc(status)}</div>
              <div>{_esc(group.get("last_updated_iso", ""))}</div>
              <div>{plot_html}{error_html}</div>
            </div>"""


def _groups_section(groups: list[dict], output_dir: Path) -> str:
    if not groups:
        return ""
    rows = "\n".join(_group_row(group, output_dir) for group in groups)
    return f"""
  <h2>Live groups</h2>
  <div class="group-row header">
    <div>group</div>
    <div>replicates</div>
    <div>status</div>
    <div>last updated</div>
    <div>latest QC plot</div>
  </div>
{rows}
"""


def render_dashboard(
    output_dir: Path,
    max_recent: int = DASHBOARD_MAX_RECENT,
    log=print,
) -> None:
    try:
        output_dir = Path(output_dir)
        rows = read_session_log(output_dir / "ASTRA_beamtime_session.log")
        rows_sorted = sorted(rows, key=lambda row: str(row.get("timestamp_iso", "")), reverse=True)
        recent = rows_sorted[: int(max_recent)]
        total = len(rows)
        n_ok = sum(1 for row in rows if row.get("status") == "ok")
        n_warn = sum(1 for row in rows if row.get("status") == "warn")
        n_reject = sum(1 for row in rows if row.get("status") == "reject")
        now_iso = datetime.now().isoformat(timespec="seconds")
        row_html = "\n".join(_scan_row(row, output_dir) for row in recent)
        group_html = _groups_section(_read_group_summaries(output_dir, log=log), output_dir)
        path = output_dir / "index.html"
        tmp = path.with_suffix(path.suffix + ".tmp")
        html_text = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="{DASHBOARD_REFRESH_SECONDS}">
  <title>AstraXAS Beamtime Dashboard</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 1.5rem; color: #222; }}
    h1 {{ font-size: 1.4rem; margin-bottom: 0.2rem; }}
    .meta {{ color: #666; font-size: 0.9rem; margin-bottom: 1.2rem; }}
    .summary {{ margin-bottom: 1rem; }}
    .summary span {{ margin-right: 1.2rem; font-variant-numeric: tabular-nums; }}
    .ok {{ color: #1a7f3a; }}
    .warn {{ color: #b07a00; }}
    .reject {{ color: #b03a3a; }}
    .pending {{ color: #777; }}
    .ready {{ color: #1a7f3a; }}
    .error {{ color: #b03a3a; }}
    h2 {{ font-size: 1.1rem; margin-top: 1.6rem; }}
    .row {{
      display: grid;
      grid-template-columns: 200px 1fr 110px 90px 90px;
      gap: 0.6rem;
      padding: 0.5rem 0;
      border-bottom: 1px solid #eee;
      align-items: center;
    }}
    .group-row {{
      display: grid;
      grid-template-columns: 1fr 90px 110px 200px 320px;
      gap: 0.6rem;
      padding: 0.5rem 0;
      border-bottom: 1px solid #eee;
      align-items: center;
    }}
    .row.header, .group-row.header {{ font-weight: 600; color: #555; }}
    img.thumb {{ max-width: 320px; height: auto; border: 1px solid #ddd; }}
    .filename {{ font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 0.9rem; }}
    .noplot {{ color: #888; font-style: italic; }}
  </style>
</head>
<body>
  <h1>AstraXAS Beamtime Dashboard</h1>
  <div class="meta">
    Output directory: <code>{_esc(output_dir)}</code>
    · Last updated: {_esc(now_iso)} · auto-refresh every {DASHBOARD_REFRESH_SECONDS} s
  </div>
  <div class="summary">
    <span>Total: <b>{total}</b></span>
    <span class="ok">ok: <b>{n_ok}</b></span>
    <span class="warn">warn: <b>{n_warn}</b></span>
    <span class="reject">reject: <b>{n_reject}</b></span>
  </div>
  <h2>Recent scans</h2>
  <div class="row header">
    <div>timestamp</div>
    <div>filename</div>
    <div>status</div>
    <div>warns</div>
    <div>jumps</div>
  </div>
{row_html}
{group_html}
  <p style="color:#888; margin-top:1.5rem; font-size:0.8rem;">
    AstraXAS Beamtime Mode (preview).
    Heuristic per-scan QC; this dashboard is informational.
  </p>
</body>
</html>
"""
        output_dir.mkdir(parents=True, exist_ok=True)
        tmp.write_text(html_text, encoding="utf-8")
        os.replace(tmp, path)
    except Exception as exc:
        log(f"WARNING: could not render beamtime dashboard: {exc}")
