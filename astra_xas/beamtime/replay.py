from __future__ import annotations

import random
import shutil
import time
from pathlib import Path

import numpy as np

from astra_xas.io import natural_key

from .scenarios import ScenarioError, load_scenario


ALLOWED_SPIKE_CHANNELS = {"I0": 3, "I1": 4, "I2": 5, "IF": 6}


def _copy_atomic(src: Path, dst: Path) -> None:
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    shutil.copy2(src, tmp)
    tmp.replace(dst)


def _inject_drop(src: Path, dst: Path, inject: dict, rng: random.Random) -> str:
    return "drop"


def _inject_truncate_energy(src: Path, dst: Path, inject: dict, rng: random.Random) -> str:
    if "new_max_eV" not in inject:
        raise ScenarioError("truncate_energy injection requires new_max_eV.")
    new_max = float(inject["new_max_eV"])
    data = np.genfromtxt(src, delimiter=",", comments="#")
    if data.ndim != 2 or data.shape[1] < 1:
        raise ScenarioError(f"Could not parse {src} for truncate_energy injection.")
    data = data[data[:, 0] <= new_max]
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    np.savetxt(tmp, data, delimiter=",", fmt="%.10g")
    tmp.replace(dst)
    return "truncate_energy"


def _inject_spike_channel(src: Path, dst: Path, inject: dict, rng: random.Random) -> str:
    channel = str(inject.get("channel", ""))
    if channel not in ALLOWED_SPIKE_CHANNELS:
        allowed = ", ".join(sorted(ALLOWED_SPIKE_CHANNELS))
        raise ScenarioError(f"spike_channel injection channel must be one of: {allowed}.")
    severity = float(inject.get("severity", 20.0))
    data = np.genfromtxt(src, delimiter=",", comments="#")
    if data.ndim != 2 or data.shape[1] <= ALLOWED_SPIKE_CHANNELS[channel]:
        raise ScenarioError(f"Could not parse {src} for spike_channel injection.")
    row = rng.randrange(len(data))
    data[row, ALLOWED_SPIKE_CHANNELS[channel]] *= severity
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    np.savetxt(tmp, data, delimiter=",", fmt="%.10g")
    tmp.replace(dst)
    return "spike_channel"


INJECTORS = {
    "drop": _inject_drop,
    "truncate_energy": _inject_truncate_energy,
    "spike_channel": _inject_spike_channel,
}


def replay(scenario_path: Path, log=print) -> None:
    scenario = load_scenario(scenario_path)
    source_dir = scenario["source_dir"].resolve()
    target_dir = scenario["target_dir"].resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(source_dir.glob("*.xasd"), key=lambda p: natural_key(p.name))
    rng = random.Random(scenario["seed"])
    if scenario["shuffle"]:
        rng.shuffle(files)

    injections_by_index: dict[int, list[dict]] = {}
    for item in scenario["inject"]:
        injections_by_index.setdefault(int(item["scan_index"]), []).append(item)

    replayed = 0
    injected_or_dropped = 0
    try:
        for index, src in enumerate(files, start=1):
            dst = target_dir / src.name
            injections = injections_by_index.get(index, [])
            dropped = False
            applied = False
            for injection in injections:
                inject_type = injection["type"]
                injector = INJECTORS.get(inject_type)
                if injector is None:
                    raise ScenarioError(f"Unknown injection type: {inject_type}")
                result = injector(src, dst, injection, rng)
                injected_or_dropped += 1
                applied = True
                if result == "drop":
                    log(f"dropped: {src.name}")
                    dropped = True
                    break
                log(f"injected {result}: {src.name}")
            if not dropped and not applied:
                _copy_atomic(src, dst)
                log(f"replayed: {src.name}")
            if not dropped:
                replayed += 1
            delay = float(scenario["interval_s"]) + rng.uniform(-float(scenario["jitter_s"]), float(scenario["jitter_s"]))
            time.sleep(max(delay, 0.05))
    except KeyboardInterrupt:
        log(f"Replay interrupted: replayed={replayed}, injected_or_dropped={injected_or_dropped}")
        return
    log(f"Replay complete: replayed={replayed}, injected_or_dropped={injected_or_dropped}")
