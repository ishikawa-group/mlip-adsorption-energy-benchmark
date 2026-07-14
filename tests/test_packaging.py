"""Release metadata for the lightweight benchmark installation."""

from __future__ import annotations

import tomllib
from pathlib import Path


def _project_metadata() -> dict:
    path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    return tomllib.loads(path.read_text(encoding="utf-8"))["project"]


def test_release_version_is_0_1_0():
    assert _project_metadata()["version"] == "0.1.0"


def test_nnp_presets_are_optional_and_selectable():
    metadata = _project_metadata()
    dependencies = " ".join(metadata["dependencies"]).lower()
    assert "ase-calculator-kit" not in dependencies

    extras = metadata["optional-dependencies"]
    backends = ("chgnet", "sevennet", "mattersim", "nequip", "uma")
    for backend in backends:
        requirement = " ".join(extras[backend]).lower()
        assert f"ase-calculator-kit[{backend}]" in requirement
        assert "@v0.3.0" in requirement
    assert "ase-calculator-kit[all]" in " ".join(extras["presets"]).lower()
