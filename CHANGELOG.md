# Changelog

## [0.7.2](https://github.com/dryvist/mlx-benchmarks/compare/v0.7.1...v0.7.2) (2026-06-02)


### Bug Fixes

* **ci:** repoint release-please caller to org-native reusable workflow ([#68](https://github.com/dryvist/mlx-benchmarks/issues/68)) ([01ee035](https://github.com/dryvist/mlx-benchmarks/commit/01ee035f9031b0cbe40a3cc5e2b65681e1e3c0c5))
* **ci:** retarget reusable-workflow uses: refs to current org homes ([#66](https://github.com/dryvist/mlx-benchmarks/issues/66)) ([4622ef8](https://github.com/dryvist/mlx-benchmarks/commit/4622ef8a520ce35fae0e4027b9963a8b35b0e291))

## [0.7.1](https://github.com/JacobPEvans/mlx-benchmarks/compare/v0.7.0...v0.7.1) (2026-05-25)


### Bug Fixes

* **ci-gate:** sync pip-audit ignore-vulns with osv-scanner.toml ([#48](https://github.com/JacobPEvans/mlx-benchmarks/issues/48)) ([43c0478](https://github.com/JacobPEvans/mlx-benchmarks/commit/43c04786e5a24cc8d9a8d25dc928b86626dd83b7))
* **deps:** floor huggingface-hub at major-only (&gt;=1.0.0) ([#60](https://github.com/JacobPEvans/mlx-benchmarks/issues/60)) ([750da34](https://github.com/JacobPEvans/mlx-benchmarks/commit/750da340ee3ad7c14049e1c9b256ac700a0e9a50))
* **deps:** update dependency google-adk to &gt;=2.0.0 ([#57](https://github.com/JacobPEvans/mlx-benchmarks/issues/57)) ([9528615](https://github.com/JacobPEvans/mlx-benchmarks/commit/95286158d932666ed9a85c84121c27f8edd480a1))
* **deps:** update dependency pyarrow to v24.0.0 ([#59](https://github.com/JacobPEvans/mlx-benchmarks/issues/59)) ([b10c91b](https://github.com/JacobPEvans/mlx-benchmarks/commit/b10c91bc087a1a381e46597c6789c91a38709ab5))
* **security:** bump pyarrow &gt;=23.0.1 for PYSEC-2026-113 ([#55](https://github.com/JacobPEvans/mlx-benchmarks/issues/55)) ([0c9a047](https://github.com/JacobPEvans/mlx-benchmarks/commit/0c9a0477c7a5f4045fa09d1e320305c3250898f9))
* **security:** ignore unfixable PyPI advisories + bump idna 3.15 ([#45](https://github.com/JacobPEvans/mlx-benchmarks/issues/45)) ([21b1502](https://github.com/JacobPEvans/mlx-benchmarks/commit/21b1502a15b643322f3e050ae92de68d388c21fe))


### Documentation

* add themed architecture diagrams and ecosystem section ([#49](https://github.com/JacobPEvans/mlx-benchmarks/issues/49)) ([7c861cb](https://github.com/JacobPEvans/mlx-benchmarks/commit/7c861cb5e07d9de6a736373bf8480e764512a7c3))

## [0.7.0](https://github.com/JacobPEvans/mlx-benchmarks/compare/v0.6.1...v0.7.0) (2026-05-14)


### Features

* **envelope:** add tokens-per-second metrics ([#38](https://github.com/JacobPEvans/mlx-benchmarks/issues/38)) ([6d65d81](https://github.com/JacobPEvans/mlx-benchmarks/commit/6d65d817d6bd45e897f44d53224cfd7a9a913fd3))


### Bug Fixes

* **deps:** update dependency lm-eval to v0.4.12 ([#41](https://github.com/JacobPEvans/mlx-benchmarks/issues/41)) ([1698c37](https://github.com/JacobPEvans/mlx-benchmarks/commit/1698c373ba0ae25aaf448349c5819d2d05006acd))


### Documentation

* add quick-reset guide for local LLM memory refresh ([#42](https://github.com/JacobPEvans/mlx-benchmarks/issues/42)) ([8e7f348](https://github.com/JacobPEvans/mlx-benchmarks/commit/8e7f34807c52b586a4b891edd32cf8322ffb7f34))

## [0.6.1](https://github.com/JacobPEvans/mlx-benchmarks/compare/v0.6.0...v0.6.1) (2026-05-03)


### Bug Fixes

* **ci:** remove deprecated app-id secret passthrough ([435846d](https://github.com/JacobPEvans/mlx-benchmarks/commit/435846da8063f148d8608cf1292d862abb25a0f8))

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
