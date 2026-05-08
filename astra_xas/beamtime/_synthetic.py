from __future__ import annotations

from pathlib import Path

import numpy as np


def write_synthetic_xasd(
    path: Path,
    e0: float = 7121.0,
    n_points: int = 401,
    e_min: float = 7000.0,
    e_max: float = 7300.0,
    white_line_height: float = 1.2,
    noise_level: float = 0.01,
    seed: int | None = None,
) -> None:
    """Synthetic test fixture only. Not physically accurate. Do not use as a reference spectrum or for any scientific purpose."""
    rng = np.random.default_rng(seed)
    energy = np.linspace(float(e_min), float(e_max), int(n_points))
    edge = 0.5 + np.arctan((energy - float(e0)) / 4.0) / np.pi
    white_line = float(white_line_height) * np.exp(-0.5 * ((energy - (float(e0) + 5.0)) / 4.0) ** 2)
    mu = 0.12 + 0.9 * edge + 0.08 * white_line
    mu_ref = 0.10 + 0.75 * edge + 0.05 * white_line
    mu_fluo = 0.05 + 0.35 * edge + 0.06 * white_line

    i0 = 1.0e6 * (1.0 + float(noise_level) * rng.normal(size=energy.size))
    i0 = np.clip(i0, 1.0, None)
    i1 = i0 / np.exp(mu)
    i2 = i1 / np.exp(mu_ref)
    if_ = i0 * mu_fluo * (1.0 + float(noise_level) * rng.normal(size=energy.size))
    fdt = np.zeros_like(energy)
    ir = np.zeros_like(energy)
    theta = np.zeros_like(energy)
    dt = np.zeros_like(energy)

    table = np.column_stack([energy, theta, dt, i0, i1, i2, if_, fdt, ir])
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savetxt(path, table, delimiter=",", fmt="%.10g")
