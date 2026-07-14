from __future__ import annotations

import pytest

from mlip_adsorption_energy_benchmark.cli.run import parse_args


def test_factory_cli_arguments():
    args = parse_args(
        [
            "--benchmark",
            "BM_dataset",
            "--calculator-factory",
            "adapter:build",
            "--factory-kwargs-json",
            '{"model":"x"}',
            "--label",
            "model-x",
        ]
    )
    assert args.calculator_factory == "adapter:build"
    assert args.label == "model-x"


def test_factory_requires_label():
    with pytest.raises(SystemExit):
        parse_args(
            ["--benchmark", "BM_dataset", "--calculator-factory", "adapter:build"]
        )


def test_preset_default_remains_all():
    args = parse_args(["--benchmark", "BM_dataset"])
    assert args.calculator == "all"
