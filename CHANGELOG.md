# Changelog

## v0.3.0 - 2026-07-14

- Add a public arbitrary ASE Calculator factory API.
- Add `--calculator-factory`, `--factory-kwargs-json`, and `--label` to the
  local and TSUBAME4 workflows.
- Make the `ase-calculator-kit` preset backends optional via the `presets`
  dependency extra, avoiding installation of unused MLIP stacks.
- Preserve the existing preset API and calculator-spec syntax.
- Set TSUBAME4 jobs to 23:55 so submissions remain below the 24-hour limit.
