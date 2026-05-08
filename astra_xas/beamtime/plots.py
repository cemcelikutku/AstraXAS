from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from astra_xas.config import AstraConfig


PLOT_DPI = 120


def _analysis_signal(entry: dict, config: AstraConfig):
    mode = getattr(config, "analysis_mode", "fluo")
    key = {
        "fluo": "mu_fluo",
        "trans": "mu_trans",
        "ref": "mu_ref",
    }.get(mode, "mu_fluo")
    return mode, np.asarray(entry.get("energy"), dtype=float), np.asarray(entry.get(key), dtype=float)


def _plot_signal(ax, energy, signal, config: AstraConfig, title: str) -> None:
    mask = np.isfinite(energy) & np.isfinite(signal)
    if mask.any():
        ax.plot(energy[mask], signal[mask], color="steelblue", linewidth=1.1)
        e_min = float(np.nanmin(energy[mask]))
        e_max = float(np.nanmax(energy[mask]))
        e0 = float(getattr(config, "e0", np.nan))
        if np.isfinite(e0) and e_min <= e0 <= e_max:
            ax.axvline(e0, color="grey", linestyle="--", linewidth=0.8)
    else:
        ax.text(0.5, 0.5, "no data", ha="center", va="center", transform=ax.transAxes, color="#666")
    ax.set_title(title)
    ax.set_xlabel("Energy (eV)")
    ax.set_ylabel("μ(E)")
    ax.grid(True, alpha=0.25)


def _plot_raw_channels(ax, entry: dict) -> None:
    energy = np.asarray(entry.get("energy"), dtype=float)
    offset = 0.0
    plotted = False
    for name in ("I0", "I1", "I2", "IF"):
        values = entry.get(name)
        if values is None:
            continue
        values = np.asarray(values, dtype=float)
        mask = np.isfinite(energy) & np.isfinite(values)
        if not mask.any():
            continue
        scale = float(np.nanmax(np.abs(values[mask])))
        if not np.isfinite(scale) or scale <= 0:
            continue
        ax.plot(energy[mask], values[mask] / scale + offset, linewidth=0.9, label=name)
        offset += 1.15
        plotted = True
    if plotted:
        ax.legend(fontsize=7, loc="best")
    else:
        ax.text(0.5, 0.5, "no detector data", ha="center", va="center", transform=ax.transAxes, color="#666")
    ax.set_title("Raw detector channels (normalized to per-channel max)")
    ax.set_xlabel("Energy (eV)")
    ax.set_ylabel("normalized + offset")
    ax.grid(True, alpha=0.25)


def _plot_alignment_window(ax, energy, signal, config: AstraConfig) -> None:
    lo = float(getattr(config, "align_window_min", np.nan))
    hi = float(getattr(config, "align_window_max", np.nan))
    mask = (energy >= lo) & (energy <= hi) & np.isfinite(energy) & np.isfinite(signal)
    if mask.any():
        ax.plot(energy[mask], signal[mask], color="steelblue", linewidth=1.1)
    else:
        ax.text(
            0.5,
            0.5,
            "no data in alignment window",
            ha="center",
            va="center",
            transform=ax.transAxes,
            color="#666",
        )
    if np.isfinite(lo) and np.isfinite(hi):
        ax.set_xlim(lo, hi)
    ax.set_title("Alignment window")
    ax.set_xlabel("Energy (eV)")
    ax.set_ylabel("μ(E)")
    ax.grid(True, alpha=0.25)


def _status_color(status: str) -> str:
    return {
        "ok": "#edf7ef",
        "warn": "#fff8df",
        "reject": "#fdeeee",
    }.get(status, "#f4f4f4")


def _plot_status_panel(
    ax,
    entry: dict,
    config: AstraConfig,
    status: str,
    n_warnings: int,
    n_jumps: int,
    timestamp_iso: str,
) -> None:
    ax.set_facecolor(_status_color(status))
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    lines = [
        f"filename: {entry.get('filename', '')}",
        f"status:   {status}",
        f"warnings: {n_warnings}",
        f"jumps:    {n_jumps}",
        f"mode:     {getattr(config, 'analysis_mode', 'fluo')}",
        f"e0:       {float(getattr(config, 'e0', float('nan'))):.3f} eV",
        f"time:     {timestamp_iso}",
    ]
    ax.text(
        0.04,
        0.96,
        "\n".join(lines),
        ha="left",
        va="top",
        transform=ax.transAxes,
        family="monospace",
        fontsize=9,
        color="#222",
    )


def _write_placeholder(output_path: Path, filename: str, reason: str, log=print) -> None:
    fig = None
    try:
        fig, ax = plt.subplots(figsize=(4, 3), dpi=PLOT_DPI)
        ax.axis("off")
        ax.text(
            0.5,
            0.55,
            filename,
            ha="center",
            va="center",
            fontsize=9,
            wrap=True,
        )
        ax.text(
            0.5,
            0.4,
            f"plot generation failed: {reason}",
            ha="center",
            va="center",
            fontsize=8,
            color="#666",
            wrap=True,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=PLOT_DPI)
    except Exception as exc:
        log(f"WARNING: could not write placeholder beamtime plot for {filename}: {exc}")
    finally:
        if fig is not None:
            plt.close(fig)


def render_per_scan_plot(
    entry: dict,
    config: AstraConfig,
    status: str,
    n_warnings: int,
    n_jumps: int,
    timestamp_iso: str,
    output_path: Path,
    log=print,
) -> None:
    fig = None
    filename = str(entry.get("filename", "unknown"))
    output_path = Path(output_path)
    try:
        mode, energy, signal = _analysis_signal(entry, config)
        fig, axes = plt.subplots(2, 2, figsize=(10, 7), dpi=PLOT_DPI)
        fig.suptitle(f"Beamtime QC: {filename}", fontsize=13)
        _plot_signal(axes[0, 0], energy, signal, config, f"Analysis signal ({mode})")
        _plot_raw_channels(axes[0, 1], entry)
        _plot_alignment_window(axes[1, 0], energy, signal, config)
        _plot_status_panel(axes[1, 1], entry, config, status, n_warnings, n_jumps, timestamp_iso)
        fig.tight_layout(rect=(0, 0, 1, 0.95))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=PLOT_DPI)
    except Exception as exc:
        log(f"WARNING: beamtime plot generation failed for {filename}: {exc}")
        if fig is not None:
            plt.close(fig)
            fig = None
        _write_placeholder(output_path, filename, str(exc), log=log)
    finally:
        if fig is not None:
            plt.close(fig)
