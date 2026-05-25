# Schema migration guide

`schema.json` is the authoritative versioned contract for every published shard.
This document records the concrete steps to safely roll out schema changes so
the path is clear before the moment arrives.

## 1. Backwards-compatible add (no version bump)

Use this path when adding an optional field or extending the `suite` enum.

- [ ] Add the field as `optional` in `schema.json` with a descriptive comment.
- [ ] Update `detect_system()` (in `src/mlx_benchmarks/system.py`) or the
      relevant converter to populate the new field when available.
- [ ] Add or extend a fixture in `examples/` that exercises the new field.
- [ ] Run `scripts/validate_schema.py` locally — existing fixtures must still
      pass; the new fixture must also pass.
- [ ] Verify the Gradio viewer (`space/`) loads existing shards unchanged
      (run `pytest space/tests` or open the local viewer on a real shard).
- [ ] Update `docs/schema.md` with the new field's description and when it is
      populated.

No `schema_version` bump needed — v1 consumers ignore unknown optional fields.

## 2. Breaking change (`v2` workflow)

Use this path when removing a required field, narrowing an allowed value set,
or changing a field's semantics in a way that would fail existing v1 validators.

### 2a. Schema update

- [ ] Copy `schema.json` to `schema-v1.json` (archive snapshot).
- [ ] Bump `$id` in `schema.json` to `…/schema-v2.json`.
- [ ] Add `"2"` to the `schema_version` enum; remove `"1"` from the main
      schema (it lives in the v1 snapshot).
- [ ] Apply the breaking change to `schema.json`.

### 2b. Code update

- [ ] Update `validate_envelope()` in `src/mlx_benchmarks/envelope.py` to
      dispatch on `schema_version` and validate against the matching schema
      (`schema.json` for v2, `schema-v1.json` for v1).
- [ ] Update `publish()` in `src/mlx_benchmarks/publish.py` and all
      converters under `src/mlx_benchmarks/converters/` to emit v2 envelopes.
- [ ] Update the Gradio viewer (`space/`) to handle both v1 and v2 shards
      (or migrate v1 → v2 on read).

### 2c. Tests and fixtures

- [ ] Add CI fixtures in `tests/fixtures/` for both versions.
- [ ] Ensure `pytest tests space/tests` passes with both fixture sets.
- [ ] Run `scripts/validate_schema.py` — v1 fixtures validate against
      `schema-v1.json`, v2 fixtures against `schema.json`.

### 2d. Documentation

- [ ] Update `docs/schema.md` to describe the v2 field set and note the v1
      archive.
- [ ] Add a migration entry to `CHANGELOG.md` under `## [Unreleased]` — use
      a `feat!:` commit subject so `release-please` marks this MAJOR.
- [ ] Update `CONTRIBUTING.md` step 5 to reference both schema versions.

## 3. Rollout

- [ ] Tag the last v1 commit (e.g. `git tag schema-v1-freeze`) to allow
      historical replay and auditability.
- [ ] Open the PR with `feat!: schema v2 — <short summary>` as the commit
      subject; `release-please` will create a MAJOR release entry.
- [ ] Announce in the PR body: what changed, why, how existing publishers
      should update, and the date after which v1 is read-only.

## Reference

- Authoritative schema: [`schema.json`](../schema.json)
- Prose field walk-through: [`docs/schema.md`](schema.md)
- Envelope validator: `src/mlx_benchmarks/envelope.py`
- Publisher: `src/mlx_benchmarks/publish.py`
