# Changelog

## [0.6.0](https://github.com/JacobPEvans/mlx-benchmarks/compare/v0.5.0...v0.6.0) (2026-04-29)


### Features

* add lm-eval reasoning and vllm throughput configs ([#10](https://github.com/JacobPEvans/mlx-benchmarks/issues/10)) ([a9e5608](https://github.com/JacobPEvans/mlx-benchmarks/commit/a9e5608a0ae7c4ac688e60cffeb3dc96d131fb63))
* add uv dev shell with lm-eval as proper dependency ([#8](https://github.com/JacobPEvans/mlx-benchmarks/issues/8)) ([328bb9a](https://github.com/JacobPEvans/mlx-benchmarks/commit/328bb9a283f5e0086d952e8b1bf6e8799725c602))
* add vllm benchmark_serving converter ([6006217](https://github.com/JacobPEvans/mlx-benchmarks/commit/600621795763cd9e8b3101968c957b68280e8ed9))
* **benchmarks:** migrate framework evaluation harness and reports ([#3](https://github.com/JacobPEvans/mlx-benchmarks/issues/3)) ([6e8e03c](https://github.com/JacobPEvans/mlx-benchmarks/commit/6e8e03c4d094a52068d1b4c0742048a33fb5d492))
* Gradio benchmark-viewer Space ([#14](https://github.com/JacobPEvans/mlx-benchmarks/issues/14)) ([5e7cefb](https://github.com/JacobPEvans/mlx-benchmarks/commit/5e7cefb03050d0467d0938047a78683c3bf410a5))
* initial scaffolding for benchmark harness ([#1](https://github.com/JacobPEvans/mlx-benchmarks/issues/1)) ([6fd8afa](https://github.com/JacobPEvans/mlx-benchmarks/commit/6fd8afaff7570a505f12e20f8bf80e64f9d1697f))
* pre-v0.5.0 hardening (CI, security, docs) ([5bf37d4](https://github.com/JacobPEvans/mlx-benchmarks/commit/5bf37d4077947539cdb921126e67e357c0adbfa4))
* production polish — package layout, CI, viewer, docs ([#15](https://github.com/JacobPEvans/mlx-benchmarks/issues/15)) ([0876689](https://github.com/JacobPEvans/mlx-benchmarks/commit/087668915e601613f3b8061e5c8b7b2d754d96ce))
* replace deploy_space.py with huggingface-cli upload ([8764aa8](https://github.com/JacobPEvans/mlx-benchmarks/commit/8764aa80f074b7d32cdd7d210d10baeae3fbfa51))


### Bug Fixes

* **deps:** bump pyarrow + pillow to fix OSV vulnerabilities ([#28](https://github.com/JacobPEvans/mlx-benchmarks/issues/28)) ([5f17230](https://github.com/JacobPEvans/mlx-benchmarks/commit/5f172308ce338f1363b74c031bc20d094e31c76c))
* pass App ID from vars not secrets in release-please ([1589b04](https://github.com/JacobPEvans/mlx-benchmarks/commit/1589b040b52b285b2cd1136161718822e9ab65d1))
* set DEVENV_ROOT and --impure in .envrc for devenv flake ([#9](https://github.com/JacobPEvans/mlx-benchmarks/issues/9)) ([b11881b](https://github.com/JacobPEvans/mlx-benchmarks/commit/b11881ba7bf3b29e68767363989fe436efd80ff1))
* use hf instead of deprecated huggingface-cli in deploy-space ([a27be21](https://github.com/JacobPEvans/mlx-benchmarks/commit/a27be21060e16aff6bef0e86b41c2263cfc25244))


### Documentation

* add project CLAUDE.md and CI badge ([#11](https://github.com/JacobPEvans/mlx-benchmarks/issues/11)) ([846f20d](https://github.com/JacobPEvans/mlx-benchmarks/commit/846f20dda8de717325c6d85aadbecf3215c44dc3))

## [0.5.0](https://github.com/JacobPEvans/mlx-benchmarks/compare/v0.4.0...v0.5.0) (2026-04-27)


### Features

* add lm-eval reasoning and vllm throughput configs ([#10](https://github.com/JacobPEvans/mlx-benchmarks/issues/10)) ([a9e5608](https://github.com/JacobPEvans/mlx-benchmarks/commit/a9e5608a0ae7c4ac688e60cffeb3dc96d131fb63))
* add uv dev shell with lm-eval as proper dependency ([#8](https://github.com/JacobPEvans/mlx-benchmarks/issues/8)) ([328bb9a](https://github.com/JacobPEvans/mlx-benchmarks/commit/328bb9a283f5e0086d952e8b1bf6e8799725c602))
* add vllm benchmark_serving converter ([6006217](https://github.com/JacobPEvans/mlx-benchmarks/commit/600621795763cd9e8b3101968c957b68280e8ed9))
* **benchmarks:** migrate framework evaluation harness and reports ([#3](https://github.com/JacobPEvans/mlx-benchmarks/issues/3)) ([6e8e03c](https://github.com/JacobPEvans/mlx-benchmarks/commit/6e8e03c4d094a52068d1b4c0742048a33fb5d492))
* Gradio benchmark-viewer Space ([#14](https://github.com/JacobPEvans/mlx-benchmarks/issues/14)) ([5e7cefb](https://github.com/JacobPEvans/mlx-benchmarks/commit/5e7cefb03050d0467d0938047a78683c3bf410a5))
* initial scaffolding for benchmark harness ([#1](https://github.com/JacobPEvans/mlx-benchmarks/issues/1)) ([6fd8afa](https://github.com/JacobPEvans/mlx-benchmarks/commit/6fd8afaff7570a505f12e20f8bf80e64f9d1697f))
* pre-v0.5.0 hardening (CI, security, docs) ([5bf37d4](https://github.com/JacobPEvans/mlx-benchmarks/commit/5bf37d4077947539cdb921126e67e357c0adbfa4))
* production polish — package layout, CI, viewer, docs ([#15](https://github.com/JacobPEvans/mlx-benchmarks/issues/15)) ([0876689](https://github.com/JacobPEvans/mlx-benchmarks/commit/087668915e601613f3b8061e5c8b7b2d754d96ce))
* replace deploy_space.py with huggingface-cli upload ([8764aa8](https://github.com/JacobPEvans/mlx-benchmarks/commit/8764aa80f074b7d32cdd7d210d10baeae3fbfa51))


### Bug Fixes

* pass App ID from vars not secrets in release-please ([1589b04](https://github.com/JacobPEvans/mlx-benchmarks/commit/1589b040b52b285b2cd1136161718822e9ab65d1))
* set DEVENV_ROOT and --impure in .envrc for devenv flake ([#9](https://github.com/JacobPEvans/mlx-benchmarks/issues/9)) ([b11881b](https://github.com/JacobPEvans/mlx-benchmarks/commit/b11881ba7bf3b29e68767363989fe436efd80ff1))
* use hf instead of deprecated huggingface-cli in deploy-space ([a27be21](https://github.com/JacobPEvans/mlx-benchmarks/commit/a27be21060e16aff6bef0e86b41c2263cfc25244))


### Documentation

* add project CLAUDE.md and CI badge ([#11](https://github.com/JacobPEvans/mlx-benchmarks/issues/11)) ([846f20d](https://github.com/JacobPEvans/mlx-benchmarks/commit/846f20dda8de717325c6d85aadbecf3215c44dc3))
