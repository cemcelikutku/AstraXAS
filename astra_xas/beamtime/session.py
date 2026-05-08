from __future__ import annotations

from datetime import datetime
from pathlib import Path


SESSION_HEADER = "# timestamp_iso\tfilename\tstatus\tn_warnings\tn_jumps\tnotes\n"


def _timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def append_session_row(log_path: Path, row: dict) -> None:
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not log_path.exists() or log_path.stat().st_size == 0
    with log_path.open("a", encoding="utf-8") as f:
        if needs_header:
            f.write(SESSION_HEADER)
        f.write(
            "\t".join(
                [
                    str(row.get("timestamp_iso", _timestamp())),
                    str(row.get("filename", "")),
                    str(row.get("status", "")),
                    str(int(row.get("n_warnings", 0))),
                    str(int(row.get("n_jumps", 0))),
                    str(row.get("notes", "")).replace("\t", " ").replace("\n", " "),
                ]
            )
            + "\n"
        )


def read_session_log(log_path: Path) -> list[dict]:
    log_path = Path(log_path)
    if not log_path.exists():
        return []
    rows: list[dict] = []
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t", 5)
            if len(parts) < 6:
                continue
            rows.append(
                {
                    "timestamp_iso": parts[0],
                    "filename": parts[1],
                    "status": parts[2],
                    "n_warnings": int(parts[3]),
                    "n_jumps": int(parts[4]),
                    "notes": parts[5],
                }
            )
    return rows


def write_session_ended_marker(log_path: Path) -> None:
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not log_path.exists() or log_path.stat().st_size == 0
    with log_path.open("a", encoding="utf-8") as f:
        if needs_header:
            f.write(SESSION_HEADER)
        f.write(f"# session ended at {_timestamp()}\n")
