from __future__ import annotations

import argparse
import json
import signal
import threading
from dataclasses import fields
from pathlib import Path

from astra_xas.config import AstraConfig

from .replay import replay
from .watcher import watch


def load_config_json(path: Path) -> AstraConfig:
    path = Path(path).expanduser()
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Config JSON must contain an object.")
    allowed = {field.name for field in fields(AstraConfig)}
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ValueError(f"Unknown AstraConfig field(s): {', '.join(unknown)}")
    config = AstraConfig()
    for key, value in data.items():
        setattr(config, key, value)
    return config


def main() -> None:
    parser = argparse.ArgumentParser(description="AstraXAS Beamtime Mode utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    replay_parser = subparsers.add_parser("replay", help="Replay a scenario into a watch folder.")
    replay_parser.add_argument("scenario", help="Path to replay scenario YAML.")

    watch_parser = subparsers.add_parser("watch", help="Watch a folder for new .xasd scans.")
    watch_parser.add_argument("incoming_dir", help="Folder receiving .xasd scans.")
    watch_parser.add_argument("-o", "--output-dir", default=None, help="Output folder. Default: <incoming>-beamtime")
    watch_parser.add_argument("-c", "--config", default=None, help="Optional AstraConfig JSON file.")

    args = parser.parse_args()
    if args.command == "replay":
        replay(Path(args.scenario))
        return

    if args.command == "watch":
        config = load_config_json(Path(args.config)) if args.config else AstraConfig()
        stop_event = threading.Event()
        previous_handler = signal.getsignal(signal.SIGINT)

        def _handle_sigint(signum, frame):
            stop_event.set()

        signal.signal(signal.SIGINT, _handle_sigint)
        try:
            watch(
                incoming_dir=Path(args.incoming_dir),
                output_dir=Path(args.output_dir) if args.output_dir else None,
                config=config,
                stop_event=stop_event,
            )
        except KeyboardInterrupt:
            stop_event.set()
        finally:
            signal.signal(signal.SIGINT, previous_handler)


if __name__ == "__main__":
    main()
