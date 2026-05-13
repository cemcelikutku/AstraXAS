# AstraXAS examples

Two reproducible end-to-end examples demonstrating the offline pipeline on real synchrotron data. Each example contains the raw `.xasd` input files and a JSON config — run AstraXAS on the folder to produce the full set of processed outputs, QC plots, and a PDF report.

The two examples are deliberately chosen to demonstrate different aspects of the pipeline:

- **inline_ref/** demonstrates the per-scan reference channel alignment workflow (operando-style measurements).
- **separate_foil/** demonstrates the periodic foil scan workflow with self-absorption diagnostic, alignment-quality scoring, and full Sprint 3-style validation.

## inline_ref/ — Phosphorus K-edge in fluorescence mode

Five fluorescence scans of 60 wt% phosphoric acid (P K-edge at ~2151 eV), measured with inline reference channel alignment (per-scan `ln(I1/I2)`). Demonstrates the `alignment_source = "inline_ref"` workflow typical for operando experiments where the experiment cannot be paused for separate foil scans.

To reproduce:

```bash
astra-xas examples/inline_ref \
    -c examples/inline_ref/p_k_inline_ref.json \
    -o examples/inline_ref/results
```

Expected outputs include:

- `examples/inline_ref/results/PhosphoricAcid_60wt_fluo_norm.dat` — merged normalized μ(E)
- `examples/inline_ref/results/plots/overview/normalized_overview.png` — overview spectrum
- `examples/inline_ref/results/plots/replicate_qc/PhosphoricAcid_60wt_fluo_normalized_replicate_qc.png` — replicate QC
- `examples/inline_ref/results/ASTRA_processing_and_QC_report.pdf` — full PDF report

All five scans align reliably (quality ≥ 0.997). Auto-deglitching interpolates a small number of isolated detector spikes. The self-absorption diagnostic is disabled in this config because the inline reference channel is not sample transmission, and the diagnostic needs simultaneously-available sample transmission to be meaningful.

## separate_foil/ — Iron K-edge with separate Fe foil drift correction

Seven scans from an operando electrocatalysis experiment on sample S3 (an Fe-based catalyst) at varying applied potentials in Ar atmosphere, plus two reference Fe foil scans for drift correction. Sample state codes: `OC` = open circuit, `m0p8` = -0.8 V applied potential. Originally measured at ASTRA/SOLARIS.

Demonstrates the `alignment_source = "separate_foil"` workflow, where periodic foil scans are used as the energy drift reference. Also exercises the self-absorption diagnostic, which is meaningful here because sample transmission data is available alongside fluorescence.

To reproduce:

```bash
astra-xas examples/separate_foil \
    -c examples/separate_foil/fe_k_separate_foil.json \
    -o examples/separate_foil/results
```

Expected outputs include all standard AstraXAS outputs (processed, normalized, flat, replicate QC, drift tracker, PDF report, detector raw exports, etc.).

This example triggers the self-absorption diagnostic: the `Run59_S3_m0p8_Ar` group is flagged as showing suppressed fluorescence white-line amplitude relative to its simultaneously-available sample transmission — a likely self-absorption indicator. See `ASTRA_self_absorption_flags.dat` and `Run59_S3_m0p8_Ar_self_absorption_qc.png` in the output for details.

## Full reference outputs

If you want to inspect the complete expected outputs without running the tool yourself (e.g., to verify your install matches the reference, or just to browse the PDF reports), download the full `Demo_AstraXAS.zip` from the [v0.4.1 release](https://github.com/cemcelikutku/AstraXAS/releases/tag/v0.4.1).

## Notes on the data

Both datasets are real experimental data. Energy calibration and processing parameters were chosen for demonstration purposes and may differ from publication-quality analysis decisions. The examples are intended to demonstrate that AstraXAS produces sensible end-to-end outputs from real synchrotron data, not to serve as canonical analyses of these specific samples.
