from __future__ import annotations

from pathlib import Path

from ase.calculators.emt import EMT

from mlip_adsorption_energy_benchmark import runner


def test_runner_builds_one_calculator_per_seed(monkeypatch, tmp_path):
    captured = {}
    data_dir = tmp_path / "data"
    result_dir = tmp_path / "result"

    def ensure(benchmark, root):
        path = Path(root) / "raw_data" / runner.raw_data_filename(benchmark)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
        return path

    class FakeCalculation:
        def __init__(self, calculators, **kwargs):
            captured["calculators"] = calculators
            captured["kwargs"] = kwargs

        def run(self):
            return None

    monkeypatch.setattr(runner, "ensure_benchmark_data", ensure)
    monkeypatch.setattr(runner, "AdsorptionCalculation", FakeCalculation)
    monkeypatch.setattr(
        runner,
        "_relocate_calculator_output",
        lambda bench_dir, calculator, mode: bench_dir / calculator,
    )

    calls = []

    def factory(*, device, seed, checkpoint):
        calls.append((device, seed, checkpoint))
        return EMT()

    output = runner.run_adsorption_benchmark(
        "BM_dataset",
        calculator_factory=factory,
        factory_kwargs={"checkpoint": "model.pt"},
        label="custom-model",
        device="cuda",
        n_seeds=2,
        result_dir=result_dir,
        data_dir=data_dir,
    )

    assert calls == [("cuda", 0, "model.pt"), ("cuda", 1, "model.pt")]
    assert len(captured["calculators"]) == 2
    assert captured["kwargs"]["mlip_name"] == "custom-model"
    assert output == result_dir.resolve() / "BM_dataset" / "custom-model"
