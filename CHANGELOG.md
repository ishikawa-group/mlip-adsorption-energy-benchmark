# Changelog

## v0.1.0 - 2026-07-14

- Add a public arbitrary ASE Calculator factory API.
- Add `--calculator-factory`, `--factory-kwargs-json`, and `--label` to the
  local and TSUBAME4 workflows.
- Keep all NNP stacks optional. Install `presets` for every supported backend,
  or select one of `chgnet`, `sevennet`, `mattersim`, `nequip`, and `uma`.
- Depend on `ase-calculator-kit` v0.3.0 for lightweight and selectable NNP
  installations.
- Preserve the existing preset API and calculator-spec syntax.
- Set TSUBAME4 jobs to 23:55 so submissions remain below the 24-hour limit.
