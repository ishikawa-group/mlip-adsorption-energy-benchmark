"""mlip-adsorption-energy-benchmark.

A thin workflow layer that benchmarks machine-learning interatomic potentials
(MLIPs) on adsorption energies, gluing together:

* `CatBench <https://github.com/JinukMoon/catbench>`_ -- the benchmark datasets,
  relaxation driver, and analysis/reporting.
* arbitrary user-supplied ASE Calculator factories, with optional built-in MLIP
  presets provided by `ase-calculator-kit`.

Typical use is through the CLIs in the ``cli`` subpackage (run via
``python -m mlip_adsorption_energy_benchmark.cli.run`` etc.) and the TSUBAME4
submission helpers in ``scripts/tsubame4/``, but the building blocks are exposed
here for programmatic use.
"""

from __future__ import annotations

from .analysis import analyze
from .benchmarks import KNOWN_BENCHMARKS, ensure_benchmark_data
from .calculators import (
    ALL_CALCULATORS,
    CALCULATOR_PRESETS,
    CalculatorJob,
    build_calculator,
    parse_calculator_spec,
    resolve_calculator_names,
    resolve_calculator_specs,
    spec_to_string,
)
from .runner import run_adsorption_benchmark
from .factories import build_from_factory, load_calculator_factory, parse_factory_kwargs

__all__ = [
    "KNOWN_BENCHMARKS",
    "ensure_benchmark_data",
    "ALL_CALCULATORS",
    "CALCULATOR_PRESETS",
    "CalculatorJob",
    "build_calculator",
    "parse_calculator_spec",
    "resolve_calculator_names",
    "resolve_calculator_specs",
    "spec_to_string",
    "run_adsorption_benchmark",
    "build_from_factory",
    "load_calculator_factory",
    "parse_factory_kwargs",
    "analyze",
]

__version__ = "0.3.0"
