from __future__ import annotations

import sys
import types

import pytest
from ase.calculators.emt import EMT

from mlip_adsorption_energy_benchmark.factories import (
    build_from_factory,
    load_calculator_factory,
    parse_factory_kwargs,
)


def test_load_and_build_factory_injects_context(monkeypatch):
    module = types.ModuleType("test_external_calculator")
    calls = []

    def build(*, device, seed, scale):
        calls.append((device, seed, scale))
        return EMT()

    module.build = build
    monkeypatch.setitem(sys.modules, module.__name__, module)
    factory = load_calculator_factory("test_external_calculator:build")
    calculator = build_from_factory(
        factory, device="cuda", seed=3, factory_kwargs={"scale": 2.0}
    )
    assert isinstance(calculator, EMT)
    assert calls == [("cuda", 3, 2.0)]


def test_factory_may_ignore_context():
    assert isinstance(build_from_factory(EMT, device="cuda", seed=9), EMT)


def test_factory_return_type_is_checked():
    with pytest.raises(TypeError, match="must return"):
        build_from_factory(lambda: object(), device="cpu", seed=0)


def test_parse_factory_kwargs_inline_and_file(tmp_path):
    assert parse_factory_kwargs('{"model":"x"}') == {"model": "x"}
    path = tmp_path / "kwargs.json"
    path.write_text('{"model":"y"}', encoding="utf-8")
    assert parse_factory_kwargs(f"@{path}") == {"model": "y"}
    with pytest.raises(ValueError, match="object"):
        parse_factory_kwargs("[]")
