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

from dataclasses import dataclass, field
from typing import Any

from ase_calculator_kit import get_calculator


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
    extra_kwargs: dict[str, Any] | None = None,
):
    """Instantiate the ASE calculator for ``preset_name``.

    Preset defaults are applied first, then optionally overridden by the
    explicit ``model`` / ``task`` / ``modal`` arguments (None means "keep the
    preset default"). ``device`` is forwarded to the backend; ``"auto"`` lets
    ase-calculator-kit pick cuda > mps > cpu.
    """

    if preset_name not in CALCULATOR_PRESETS:
        allowed = ", ".join(ALL_CALCULATORS)
        raise ValueError(f"Unknown calculator {preset_name!r}. Allowed: {allowed}")

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
    if extra_kwargs:
        kwargs.update(extra_kwargs)

    return get_calculator(preset.backend, **kwargs)
