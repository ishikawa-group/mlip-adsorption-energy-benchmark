"""Run a single (benchmark, calculator) adsorption-energy calculation.

CatBench is driven entirely through the current working directory: it reads the
dataset from ``<cwd>/raw_data/`` and writes results to ``<cwd>/result/<name>/``.
To get the layout requested for this project -- ``result/<benchmark>/<calc>/`` --
we run CatBench inside a per-benchmark working directory and then lift the
produced calculator folder up one level (removing CatBench's intermediate
``result/`` wrapper).
"""

from __future__ import annotations

import contextlib
import os
import re
import shutil
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from catbench.adsorption import AdsorptionCalculation

from .benchmarks import ensure_benchmark_data, raw_data_filename
from .calculators import build_calculator
from .factories import build_from_factory, load_calculator_factory


@contextlib.contextmanager
def _working_directory(path: Path):
    """Temporarily ``chdir`` into ``path`` (CatBench is cwd-driven)."""

    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _link_raw_data(bench_dir: Path, data_dir: Path, benchmark: str) -> None:
    """Expose the cached dataset to CatBench as ``<bench_dir>/raw_data/``.

    We symlink to the shared cache so the dataset is downloaded only once and
    every calculator for this benchmark reuses it.

    This must be **idempotent and safe under concurrency**: on the cluster many
    jobs for the same benchmark run in parallel and share this single link. The
    key is to do nothing when the link already points at the cache (so siblings
    never race on unlink/recreate); the retry loop only covers the first-time
    creation window.
    """

    bench_dir.mkdir(parents=True, exist_ok=True)
    link = bench_dir / "raw_data"
    source = (data_dir / "raw_data").resolve()
    source_str = str(source)

    for _ in range(5):
        try:
            if link.is_symlink():
                if os.path.realpath(link) == source_str:
                    return  # already correct -> no mutation, no race
                link.unlink()
            elif link.exists():
                return  # a real directory is here; leave it untouched
            link.symlink_to(source, target_is_directory=True)
            return
        except FileExistsError:
            # A sibling job created the link between our check and symlink call.
            if link.is_symlink() and os.path.realpath(link) == source_str:
                return
            # Wrong/stale link created concurrently; retry to fix it.
        except FileNotFoundError:
            # A sibling removed it between our check and unlink; retry.
            continue

    # Final attempt; surface any genuine error.
    if not (link.is_symlink() or link.exists()):
        link.symlink_to(source, target_is_directory=True)


def _relocate_calculator_output(bench_dir: Path, calculator: str, mode: str) -> Path:
    """Move CatBench's ``result*/<calc>`` folder up to ``<bench_dir>/<calc>``."""

    # mode="basic" -> "result/", other modes -> "result_<mode>/".
    candidates = ["result"] if mode == "basic" else [f"result_{mode}", "result"]
    dest = bench_dir / calculator

    for wrapper in candidates:
        produced = bench_dir / wrapper / calculator
        if produced.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.move(str(produced), str(dest))
            # Remove the now-empty CatBench wrapper directory if nothing's left.
            with contextlib.suppress(OSError):
                (bench_dir / wrapper).rmdir()
            return dest

    raise FileNotFoundError(
        f"Could not find CatBench output for {calculator!r} under {bench_dir} "
        f"(looked in: {', '.join(candidates)})"
    )


def run_adsorption_benchmark(
    benchmark: str,
    calculator: str | None = None,
    *,
    label: str | None = None,
    calculator_factory: str | Callable[..., Any] | None = None,
    factory_kwargs: Mapping[str, Any] | None = None,
    device: str = "auto",
    n_seeds: int = 1,
    result_dir: str | os.PathLike,
    data_dir: str | os.PathLike,
    model: str | None = None,
    task: str | None = None,
    modal: str | None = None,
    dispersion: bool = False,
    enable_cueq: bool = False,
    f_crit_relax: float = 0.05,
    n_crit_relax: int = 999,
    mode: str = "basic",
    save_files: bool = True,
) -> Path:
    """Benchmark one calculator variant on one dataset; return the output dir.

    Parameters
    ----------
    benchmark:
        CatBench dataset name (see :data:`benchmarks.KNOWN_BENCHMARKS`).
    calculator:
        Preset name from :data:`calculators.CALCULATOR_PRESETS` (selects the
        backend); ``model`` / ``task`` / ``modal`` override its defaults.
    calculator_factory:
        Arbitrary ASE Calculator factory, either a callable or a
        ``"module:callable"`` reference. It is invoked once per seed and may
        accept ``device`` and ``seed`` plus entries from ``factory_kwargs``.
        Mutually exclusive with ``calculator``.
    label:
        Output-folder / CatBench ``mlip_name`` for this variant. Defaults to
        ``calculator``; pass a distinct label (e.g. ``"sevennet-omat24"``) when
        sweeping variants so results do not overwrite each other.
    n_seeds:
        How many identical calculator instances to run (CatBench uses this to
        assess run-to-run reproducibility of the MLIP).
    result_dir / data_dir:
        Project ``result/`` and ``data/`` roots (absolute paths recommended).
    model / task / modal:
        Optional overrides of the preset defaults.
    """

    if calculator_factory is not None and calculator is not None:
        raise ValueError("Use either a preset calculator or calculator_factory, not both.")
    if calculator_factory is None and calculator is None:
        raise ValueError("A preset calculator or calculator_factory is required.")
    if calculator_factory is not None and not label:
        raise ValueError("label is required when using calculator_factory.")

    label = label or calculator
    assert label is not None
    if label in {".", ".."} or re.search(r"[^A-Za-z0-9_.-]", label):
        raise ValueError("label may contain only letters, digits, '.', '_' and '-'.")
    result_dir = Path(result_dir).resolve()
    data_dir = Path(data_dir).resolve()
    bench_dir = result_dir / benchmark

    # 1) Make sure the reference dataset is available (downloaded once, shared).
    ensure_benchmark_data(benchmark, data_dir)
    _link_raw_data(bench_dir, data_dir, benchmark)

    # Sanity-check the symlinked dataset is visible where CatBench will look.
    expected = bench_dir / "raw_data" / raw_data_filename(benchmark)
    if not expected.exists():
        raise FileNotFoundError(f"Dataset not visible to CatBench at {expected}")

    # 2) Build N identical calculators (reproducibility seeds).
    if calculator_factory is not None:
        factory = (
            load_calculator_factory(calculator_factory)
            if isinstance(calculator_factory, str)
            else calculator_factory
        )
        calculators = [
            build_from_factory(
                factory,
                device=device,
                seed=seed,
                factory_kwargs=factory_kwargs,
            )
            for seed in range(max(1, int(n_seeds)))
        ]
    else:
        assert calculator is not None
        calculators = [
            build_calculator(
                calculator,
                device=device,
                model=model,
                task=task,
                modal=modal,
                dispersion=dispersion,
                enable_cueq=enable_cueq,
            )
            for _ in range(max(1, int(n_seeds)))
        ]

    # 3) Run CatBench inside the per-benchmark working directory.
    with _working_directory(bench_dir):
        AdsorptionCalculation(
            calculators,
            mlip_name=label,
            benchmark=benchmark,
            mode=mode,
            f_crit_relax=f_crit_relax,
            n_crit_relax=n_crit_relax,
            save_files=save_files,
        ).run()

    # 4) Flatten CatBench's layout to result/<benchmark>/<label>/.
    return _relocate_calculator_output(bench_dir, label, mode)
