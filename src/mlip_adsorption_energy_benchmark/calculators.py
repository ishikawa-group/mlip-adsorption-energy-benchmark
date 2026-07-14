"""MLIP calculator presets for adsorption-energy benchmarking.

This module is a thin layer on top of :mod:`ase_calculator_kit`. Its only job is
to translate a short, human-friendly *preset name* (e.g. ``"uma"``) into a fully
specified ASE calculator that is sensible for **adsorption-energy** problems.

Why presets?
------------
Different universal MLIPs expose different "flavours" of the same model. Two
choices matter for adsorption energies in particular:

* **UMA / fairchem** is multi-task. The ``task`` selects which training domain to
  use; ``"oc20"`` is the catalysis / adsorption domain, so that is our default.
* **SevenNet (7net-omni)** is multi-fidelity. The ``modal`` selects the reference
  level of theory; ``"mpa"`` is the general PBE(+U) materials head.

Everything here is overridable from the command line, so a chemist who wants a
different model/task/modal can do so without touching the code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class CalculatorPreset:
    """A named, adsorption-ready configuration for one MLIP backend.

    Attributes
    ----------
    backend:
        Backend name understood by :func:`ase_calculator_kit.get_calculator`
        (e.g. ``"uma"``, ``"sevennet"``, ``"mattersim"``, ``"chgnet"``,
        ``"nequip"``).
    kwargs:
        Backend-specific keyword arguments (``model``, ``task``, ``modal`` ...).
        ``device`` is added separately at build time.
    description:
        One-line human-readable note shown in ``--help`` / the README.
    """

    backend: str
    kwargs: dict[str, Any] = field(default_factory=dict)
    description: str = ""


# ---------------------------------------------------------------------------
# Preset registry. Keys are the names accepted by the ``--calculator`` flag.
# Defaults are chosen to be reasonable for adsorption-energy benchmarks.
# ---------------------------------------------------------------------------
CALCULATOR_PRESETS: dict[str, CalculatorPreset] = {
    # UMA is multi-task; "oc20" is the catalysis/adsorption domain.
    "uma": CalculatorPreset(
        backend="uma",
        kwargs={"model": "uma-s-1p2", "task": "oc20"},
        description="UMA (fairchem) small model, OC20 catalysis task.",
    ),
    # SevenNet 7net-omni is multi-fidelity; "mpa" is the general PBE(+U) head.
    "sevennet": CalculatorPreset(
        backend="sevennet",
        kwargs={"model": "7net-omni", "modal": "mpa"},
        description="SevenNet 7net-omni, MPA (PBE+U materials) modal.",
    ),
    # MatterSim 5M is the more accurate of the two released sizes.
    "mattersim": CalculatorPreset(
        backend="mattersim",
        kwargs={"model": "5M"},
        description="MatterSim v1.0.0 5M model.",
    ),
    # CHGNet: use the bundled default checkpoint.
    "chgnet": CalculatorPreset(
        backend="chgnet",
        kwargs={},
        description="CHGNet bundled default model.",
    ),
    # NequIP OAM: "L" is a good accuracy/speed compromise (MPS unsupported).
    "nequip": CalculatorPreset(
        backend="nequip",
        kwargs={"model": "L"},
        description="NequIP OAM, size L.",
    ),
}

#: Convenience list for the ``--calculator all`` shortcut and job submission.
ALL_CALCULATORS: list[str] = list(CALCULATOR_PRESETS)


def resolve_calculator_names(value: str) -> list[str]:
    """Expand a ``--calculator`` argument into concrete preset names.

    Accepts ``"all"`` (case-insensitive) or a comma-separated list of preset
    names. Raises ``ValueError`` on unknown names so mistakes fail fast.
    """

    raw = str(value).strip()
    if not raw or raw.lower() == "all":
        return list(ALL_CALCULATORS)

    names: list[str] = []
    for part in raw.split(","):
        name = part.strip()
        if not name:
            continue
        if name not in CALCULATOR_PRESETS:
            allowed = ", ".join(ALL_CALCULATORS)
            raise ValueError(f"Unknown calculator {name!r}. Allowed: all, {allowed}")
        if name not in names:
            names.append(name)
    if not names:
        raise ValueError("--calculator must be 'all' or a comma-separated list.")
    return names


def build_calculator(
    preset_name: str,
    device: str = "auto",
    *,
    model: str | None = None,
    task: str | None = None,
    modal: str | None = None,
    dispersion: bool = False,
    enable_cueq: bool = False,
    extra_kwargs: dict[str, Any] | None = None,
):
    """Instantiate the ASE calculator for ``preset_name``.

    Preset defaults are applied first, then optionally overridden by the
    explicit ``model`` / ``task`` / ``modal`` arguments (None means "keep the
    preset default"). ``device`` is forwarded to the backend; ``"auto"`` lets
    ase-calculator-kit pick cuda > mps > cpu.

    ``enable_cueq`` turns on CuEquivariance acceleration; it is only meaningful
    for the SevenNet backend, so it is injected only there.
    """

    if preset_name not in CALCULATOR_PRESETS:
        allowed = ", ".join(ALL_CALCULATORS)
        raise ValueError(f"Unknown calculator {preset_name!r}. Allowed: {allowed}")

    try:
        from ase_calculator_kit import get_calculator
    except ImportError as exc:
        raise ImportError(
            "Preset calculators require ase-calculator-kit. Install one backend, "
            "for example `pip install 'mlip-adsorption-energy-benchmark[chgnet]'`, "
            "or install all with `[presets]`."
        ) from exc

    preset = CALCULATOR_PRESETS[preset_name]
    kwargs: dict[str, Any] = dict(preset.kwargs)
    kwargs["device"] = device

    if model is not None:
        kwargs["model"] = model
    if task is not None:
        kwargs["task"] = task
    if modal is not None:
        kwargs["modal"] = modal
    if dispersion:
        kwargs["dispersion"] = True
    if enable_cueq and preset.backend == "sevennet":
        kwargs["enable_cueq"] = True
    if extra_kwargs:
        kwargs.update(extra_kwargs)

    return get_calculator(preset.backend, **kwargs)


# ---------------------------------------------------------------------------
# Calculator "specs": a preset plus optional variant overrides.
#
# A spec lets you benchmark several *variants* of the same backend in one sweep
# while keeping each variant in its own result folder / job. Syntax::
#
#     <preset>[:<key>=<value>[;<key>=<value>...]]
#
# where <key> is one of model / task / modal, e.g.::
#
#     uma:task=oc22            -> result/<benchmark>/uma-oc22/
#     sevennet:modal=omat24    -> result/<benchmark>/sevennet-omat24/
#     nequip:model=m           -> result/<benchmark>/nequip-m/
#     chgnet:model=0.3.0       -> result/<benchmark>/chgnet-0.3.0/
#
# A bare preset name (or "all") keeps its original label, i.e. the preset name.
# ---------------------------------------------------------------------------

#: Override keys a spec may set (mapped straight onto ``build_calculator``).
OVERRIDE_KEYS = ("model", "task", "modal")


@dataclass(frozen=True)
class CalculatorJob:
    """One concrete calculator variant to benchmark.

    Attributes
    ----------
    preset:
        Preset name (key of :data:`CALCULATOR_PRESETS`).
    label:
        Unique, filesystem-safe identifier used as the result-folder and job
        name (e.g. ``"sevennet-omat24"``). Equals ``preset`` when there are no
        overrides.
    overrides:
        Subset of ``{"model", "task", "modal"}`` overriding the preset default.
    """

    preset: str
    label: str
    overrides: dict[str, str] = field(default_factory=dict)


def _safe_label(text: str) -> str:
    """Make ``text`` safe for use as a directory and SGE job name."""

    return re.sub(r"[^A-Za-z0-9_.-]", "-", text)


def parse_calculator_spec(spec: str) -> CalculatorJob:
    """Parse a single ``<preset>[:key=value;...]`` spec into a CalculatorJob."""

    raw = str(spec).strip()
    preset, sep, rest = raw.partition(":")
    preset = preset.strip()
    if preset not in CALCULATOR_PRESETS:
        allowed = ", ".join(ALL_CALCULATORS)
        raise ValueError(f"Unknown calculator {preset!r}. Allowed: all, {allowed}")

    overrides: dict[str, str] = {}
    if sep:
        for pair in rest.split(";"):
            pair = pair.strip()
            if not pair:
                continue
            key, eq, value = pair.partition("=")
            key, value = key.strip().lower(), value.strip()
            if not eq or key not in OVERRIDE_KEYS or not value:
                raise ValueError(
                    f"Invalid override {pair!r} in spec {raw!r}. "
                    f"Use one of {OVERRIDE_KEYS} as key=value."
                )
            overrides[key] = value

    # Build a readable label: preset followed by each override value in order.
    label = preset
    for key in OVERRIDE_KEYS:
        if key in overrides:
            label = f"{label}-{overrides[key]}"
    return CalculatorJob(preset=preset, label=_safe_label(label), overrides=overrides)


def spec_to_string(job: CalculatorJob) -> str:
    """Inverse of :func:`parse_calculator_spec` (round-trips a CalculatorJob)."""

    if not job.overrides:
        return job.preset
    parts = [f"{k}={job.overrides[k]}" for k in OVERRIDE_KEYS if k in job.overrides]
    return f"{job.preset}:" + ";".join(parts)


def resolve_calculator_specs(value: str) -> list[CalculatorJob]:
    """Expand a ``--calculator`` argument into a list of CalculatorJob.

    Accepts ``"all"`` or a comma-separated list of specs. Duplicate labels are
    dropped so the same variant is not benchmarked twice.
    """

    raw = str(value).strip()
    if not raw or raw.lower() == "all":
        return [CalculatorJob(p, p, {}) for p in ALL_CALCULATORS]

    jobs: list[CalculatorJob] = []
    seen: set[str] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        job = parse_calculator_spec(part)
        if job.label in seen:
            continue
        seen.add(job.label)
        jobs.append(job)
    if not jobs:
        raise ValueError("--calculator must be 'all' or a comma-separated list of specs.")
    return jobs
