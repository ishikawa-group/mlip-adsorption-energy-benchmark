"""Load arbitrary ASE calculator factories for programmatic and CLI use."""

from __future__ import annotations

import importlib
import inspect
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from ase.calculators.calculator import Calculator

CalculatorFactory = Callable[..., Calculator]


def load_calculator_factory(reference: str) -> CalculatorFactory:
    """Load ``module:callable`` and validate that it is callable."""

    module_name, separator, attribute_path = str(reference).strip().partition(":")
    if not separator or not module_name or not attribute_path:
        raise ValueError(
            "Calculator factory must use 'module:callable' syntax, for example "
            "'my_model.ase:build_calculator'."
        )
    value: Any = importlib.import_module(module_name)
    for attribute in attribute_path.split("."):
        value = getattr(value, attribute)
    if not callable(value):
        raise TypeError(f"Calculator factory {reference!r} is not callable.")
    return value


def parse_factory_kwargs(value: str | None) -> dict[str, Any]:
    """Parse a JSON object or ``@path/to/file.json`` into factory kwargs."""

    if value is None or not str(value).strip():
        return {}
    text = str(value).strip()
    if text.startswith("@"):
        text = Path(text[1:]).expanduser().read_text(encoding="utf-8")
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Factory kwargs JSON must contain an object at the top level.")
    return parsed


def build_from_factory(
    factory: CalculatorFactory,
    *,
    device: str,
    seed: int,
    factory_kwargs: Mapping[str, Any] | None = None,
) -> Calculator:
    """Invoke a factory, injecting supported ``device`` and ``seed`` context.

    A factory may declare ``device`` and/or ``seed`` explicitly, accept arbitrary
    ``**kwargs``, or ignore both. Explicit values in ``factory_kwargs`` win.
    """

    kwargs = dict(factory_kwargs or {})
    try:
        signature = inspect.signature(factory)
    except (TypeError, ValueError):
        signature = None

    if signature is not None:
        accepts_var_kwargs = any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD
            for parameter in signature.parameters.values()
        )
        keyword_parameters = {
            name
            for name, parameter in signature.parameters.items()
            if parameter.kind
            in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
        }
        if "device" not in kwargs and ("device" in keyword_parameters or accepts_var_kwargs):
            kwargs["device"] = device
        if "seed" not in kwargs and ("seed" in keyword_parameters or accepts_var_kwargs):
            kwargs["seed"] = seed

    calculator = factory(**kwargs)
    if not isinstance(calculator, Calculator):
        raise TypeError(
            "Calculator factory must return an ase.calculators.calculator.Calculator; "
            f"got {type(calculator).__name__}."
        )
    return calculator
