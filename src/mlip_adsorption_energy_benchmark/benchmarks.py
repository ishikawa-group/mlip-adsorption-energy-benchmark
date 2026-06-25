"""Adsorption-energy benchmark datasets (provided by CatBench).

CatBench downloads its reference DFT datasets from Zenodo into a ``raw_data/``
folder *relative to the current working directory*. This module documents the
datasets we care about and provides a small helper that keeps the downloaded
JSON cached under a single ``data/`` directory so it is fetched only once and
shared across every calculator.
"""

from __future__ import annotations

import os
from pathlib import Path

from catbench.adsorption import get_benchmark

#: Datasets known to be useful here, with a short note on each.
#: (CatBench supports more; these are the ones surfaced in --help.)
KNOWN_BENCHMARKS: dict[str, str] = {
    "MamunHighT2019": "45k small-molecule adsorptions on 2,035 bimetallic alloys.",
    "ComerGeneralized2024": "325 adsorptions on metal oxides.",
    "OC20-Dense": "65k dense adsorption configurations (large, ~400 MB).",
    "GameNetOx_oxide": "987 adsorptions on metal-oxide surfaces.",
    "FG_dataset": "2,651 organic-molecule adsorptions.",
    "BM_dataset": "32 industrial large molecules (small; good for smoke tests).",
}

#: File-name suffix CatBench uses for adsorption datasets.
_SUFFIX = "_adsorption.json"


def raw_data_filename(benchmark: str) -> str:
    """Return the on-disk file name CatBench expects for ``benchmark``."""

    return f"{benchmark}{_SUFFIX}"


def ensure_benchmark_data(benchmark: str, data_dir: str | os.PathLike) -> Path:
    """Make sure the dataset JSON for ``benchmark`` exists under ``data_dir``.

    CatBench's ``get_benchmark`` writes to ``<cwd>/raw_data/``. To keep the
    download in one shared place we temporarily ``chdir`` into ``data_dir`` so
    the file lands at ``<data_dir>/raw_data/<benchmark>_adsorption.json``. If it
    is already present we skip the (potentially large) download.

    Returns the path to the cached JSON file.
    """

    data_dir = Path(data_dir).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    cached = data_dir / "raw_data" / raw_data_filename(benchmark)

    if cached.exists():
        return cached

    previous_cwd = Path.cwd()
    try:
        os.chdir(data_dir)
        get_benchmark(benchmark)
    finally:
        os.chdir(previous_cwd)

    if not cached.exists():
        raise FileNotFoundError(
            f"CatBench did not produce the expected dataset file: {cached}"
        )
    return cached
