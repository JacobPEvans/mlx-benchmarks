# Changelog

## [0.18.2](https://github.com/dryvist/mlx-benchmarks/compare/v0.18.1...v0.18.2) (2026-08-16)


### Documentation

* add four traps to the benchmark-traps checklist ([#178](https://github.com/dryvist/mlx-benchmarks/issues/178)) ([e75c9ab](https://github.com/dryvist/mlx-benchmarks/commit/e75c9ab0f56048de004094fc7712430d09c99557))

## [0.18.1](https://github.com/dryvist/mlx-benchmarks/compare/v0.18.0...v0.18.1) (2026-08-16)


### Documentation

* **bench-traps:** fix trap 9, add traps 13-16 from Qwen3.8-27B sweep ([#176](https://github.com/dryvist/mlx-benchmarks/issues/176)) ([9307d36](https://github.com/dryvist/mlx-benchmarks/commit/9307d36df26ece2acbd909243b3862dcde1b02cf))

## [0.18.0](https://github.com/dryvist/mlx-benchmarks/compare/v0.17.0...v0.18.0) (2026-08-15)


### Features

* **scripts:** add run-suite.sh end-to-end benchmark runner ([#174](https://github.com/dryvist/mlx-benchmarks/issues/174)) ([5a5b501](https://github.com/dryvist/mlx-benchmarks/commit/5a5b501c213de76cc1cbe1a3d265263f34dbd10d))

## [0.17.0](https://github.com/dryvist/mlx-benchmarks/compare/v0.16.0...v0.17.0) (2026-07-30)


### Features

* **shootout:** agent-brain comparison — factual suite, ranker, and candidate slate ([#164](https://github.com/dryvist/mlx-benchmarks/issues/164)) ([6f2c78c](https://github.com/dryvist/mlx-benchmarks/commit/6f2c78cedfc57e6874bd39cc8ae00e26c1ba85ec))


### Documentation

* **readme:** cut duplicated suite table to clear the file-size gate ([#172](https://github.com/dryvist/mlx-benchmarks/issues/172)) ([40b8b8c](https://github.com/dryvist/mlx-benchmarks/commit/40b8b8ca8c786de6d46a026b833e12a14a9baeac))

## [0.16.0](https://github.com/dryvist/mlx-benchmarks/compare/v0.15.3...v0.16.0) (2026-07-27)


### Features

* **throughput:** make cumulative tok/s the headline metric ([#169](https://github.com/dryvist/mlx-benchmarks/issues/169)) ([a3c49ce](https://github.com/dryvist/mlx-benchmarks/commit/a3c49ced9fc97d98901f77d47af46ebf05d23db3))

## [0.15.3](https://github.com/dryvist/mlx-benchmarks/compare/v0.15.2...v0.15.3) (2026-07-21)


### Documentation

* **benchmarks:** parameterize Doppler selection ([dc9cc05](https://github.com/dryvist/mlx-benchmarks/commit/dc9cc05eba990178065ed3dd5a739b9b8e772289))
* **benchmarks:** parameterize Doppler selection ([#160](https://github.com/dryvist/mlx-benchmarks/issues/160)) ([d95e1b2](https://github.com/dryvist/mlx-benchmarks/commit/d95e1b22473795063f71ee48151d84eb366a8d98))

## [0.15.2](https://github.com/dryvist/mlx-benchmarks/compare/v0.15.1...v0.15.2) (2026-07-19)


### Documentation

* **mlx-llm-configs:** add serving-config parameter reference + parity checklist ([#158](https://github.com/dryvist/mlx-benchmarks/issues/158)) ([0b25819](https://github.com/dryvist/mlx-benchmarks/commit/0b25819ea808f9a0010d03a842eb8a7f5bd41475))

## [0.15.1](https://github.com/dryvist/mlx-benchmarks/compare/v0.15.0...v0.15.1) (2026-07-19)


### Bug Fixes

* **cli:** accept --kind promptstack in mlx-bench-publish ([abfa91c](https://github.com/dryvist/mlx-benchmarks/commit/abfa91caf8cf9deda40fe3af1798df561f3a4437))


### Documentation

* adopt promptfoo-based prompt-eval framework, supersede promptstack ([e1c8a2c](https://github.com/dryvist/mlx-benchmarks/commit/e1c8a2c1a5d8ec9ec603a887a934245271990915))
* rewrap journal list item that markdownlint read as a plus bullet ([7c9731c](https://github.com/dryvist/mlx-benchmarks/commit/7c9731ca9cc1de99f4d1af6d5d143ab1c36d1723))

## [0.15.0](https://github.com/dryvist/mlx-benchmarks/compare/v0.14.0...v0.15.0) (2026-07-19)


### Features

* **converters:** add bench-serve converter for vllm-mlx bench-serve JSON ([#154](https://github.com/dryvist/mlx-benchmarks/issues/154)) ([b599b52](https://github.com/dryvist/mlx-benchmarks/commit/b599b526296516228297bf5cd4963ee4d6de6b14))

## [0.14.0](https://github.com/dryvist/mlx-benchmarks/compare/v0.13.2...v0.14.0) (2026-07-17)


### Features

* **schema:** env-class, concurrency, serving identity, cluster topology ([#150](https://github.com/dryvist/mlx-benchmarks/issues/150)) ([e4afe60](https://github.com/dryvist/mlx-benchmarks/commit/e4afe60d73d6c1def30fb39a31c1fb8b5648f0ce))

## [0.13.2](https://github.com/dryvist/mlx-benchmarks/compare/v0.13.1...v0.13.2) (2026-07-17)


### Bug Fixes

* **agentic:** runner robustness + honest throughput reporting ([#144](https://github.com/dryvist/mlx-benchmarks/issues/144)) ([fa86427](https://github.com/dryvist/mlx-benchmarks/commit/fa86427e87dbc3239f07d1b4e9bcbd2ab74bd775))

## [0.13.1](https://github.com/dryvist/mlx-benchmarks/compare/v0.13.0...v0.13.1) (2026-07-13)


### Documentation

* **rankings:** land 80B token-truncation finding (fits file-size gate) ([#138](https://github.com/dryvist/mlx-benchmarks/issues/138)) ([ff58d90](https://github.com/dryvist/mlx-benchmarks/commit/ff58d90d4945d98f0b74c1b520c445a785406138))

## [0.13.0](https://github.com/dryvist/mlx-benchmarks/compare/v0.12.0...v0.13.0) (2026-07-13)


### Features

* **agentic:** add --temperature and --repetition-penalty flags ([#136](https://github.com/dryvist/mlx-benchmarks/issues/136)) ([4424311](https://github.com/dryvist/mlx-benchmarks/commit/442431127ea2642ccf66fa08e3ceaa11ef0cc5a8))

## [0.12.0](https://github.com/dryvist/mlx-benchmarks/compare/v0.11.3...v0.12.0) (2026-07-12)


### Features

* **promptstack:** add system-prompt-as-independent-variable eval suite ([#130](https://github.com/dryvist/mlx-benchmarks/issues/130)) ([922b44d](https://github.com/dryvist/mlx-benchmarks/commit/922b44d143906b1953a8cd550cd595390ce833f0))

## [0.11.3](https://github.com/dryvist/mlx-benchmarks/compare/v0.11.2...v0.11.3) (2026-07-12)


### Documentation

* **journal:** TB5 cluster session — concurrency curves, link redesign verdicts, batching recommendation ([#128](https://github.com/dryvist/mlx-benchmarks/issues/128)) ([b0850b6](https://github.com/dryvist/mlx-benchmarks/commit/b0850b6c14e75b31e055c9ea4f3913344eaac916))

## [0.11.2](https://github.com/dryvist/mlx-benchmarks/compare/v0.11.1...v0.11.2) (2026-07-11)


### Documentation

* **bench:** concurrency-cascade + cold-start traps, sweep journal, config guards ([#125](https://github.com/dryvist/mlx-benchmarks/issues/125)) ([5814278](https://github.com/dryvist/mlx-benchmarks/commit/5814278db55228912ba2ccb34e8997caecb56ad1))

## [0.11.1](https://github.com/dryvist/mlx-benchmarks/compare/v0.11.0...v0.11.1) (2026-07-10)


### Documentation

* **runbook:** harden managed-window bootout/restore + rotation guidance ([#122](https://github.com/dryvist/mlx-benchmarks/issues/122)) ([1bb1889](https://github.com/dryvist/mlx-benchmarks/commit/1bb1889b790f7772a2255012acde62d5b6c74cc9))

## [0.11.0](https://github.com/dryvist/mlx-benchmarks/compare/v0.10.6...v0.11.0) (2026-07-10)


### Features

* **publish:** emit flat bench-events JSONL feed for log-pipeline ingest ([#121](https://github.com/dryvist/mlx-benchmarks/issues/121)) ([292e731](https://github.com/dryvist/mlx-benchmarks/commit/292e7315a14fa414cab5a87a4a5069f04aaa87bb)), closes [#119](https://github.com/dryvist/mlx-benchmarks/issues/119)

## [0.10.6](https://github.com/dryvist/mlx-benchmarks/compare/v0.10.5...v0.10.6) (2026-07-09)


### Documentation

* **flagship:** 2026-07-09 isolated-window results — no 60-90GB flagship fits ([#114](https://github.com/dryvist/mlx-benchmarks/issues/114)) ([c58da6f](https://github.com/dryvist/mlx-benchmarks/commit/c58da6f55e002cce029c3f251bd67105a590cf9e))

## [0.10.5](https://github.com/dryvist/mlx-benchmarks/compare/v0.10.4...v0.10.5) (2026-07-08)


### Documentation

* **verdict-policy:** document the 1/4 crediting rule for maturity ([#111](https://github.com/dryvist/mlx-benchmarks/issues/111)) ([6922438](https://github.com/dryvist/mlx-benchmarks/commit/69224380fa184c59dccd79b9ae0e0178b2a945e4))

## [0.10.4](https://github.com/dryvist/mlx-benchmarks/compare/v0.10.3...v0.10.4) (2026-07-08)


### Documentation

* **rankings:** mark all current verdicts 1/4 provisional maturity ([#109](https://github.com/dryvist/mlx-benchmarks/issues/109)) ([f7cbd09](https://github.com/dryvist/mlx-benchmarks/commit/f7cbd09438f986b9262b52031ac74f92190e77d2))

## [0.10.3](https://github.com/dryvist/mlx-benchmarks/compare/v0.10.2...v0.10.3) (2026-07-08)


### Documentation

* self-serve benchmarking playbook (RUNBOOK, RANKINGS, examples) ([#107](https://github.com/dryvist/mlx-benchmarks/issues/107)) ([586dd7d](https://github.com/dryvist/mlx-benchmarks/commit/586dd7dbc2128ffa5070b85bae1682e340bbc31c))

## [0.10.2](https://github.com/dryvist/mlx-benchmarks/compare/v0.10.1...v0.10.2) (2026-07-08)


### Documentation

* **agentic:** record brain-selection run + durable per-class lessons ([#105](https://github.com/dryvist/mlx-benchmarks/issues/105)) ([1df057e](https://github.com/dryvist/mlx-benchmarks/commit/1df057eda6eae10ce30fa7dff88f971829dfd818))

## [0.10.1](https://github.com/dryvist/mlx-benchmarks/compare/v0.10.0...v0.10.1) (2026-07-08)


### Documentation

* **configs:** make the qwen3-tasks overlay the coding-suite default ([#103](https://github.com/dryvist/mlx-benchmarks/issues/103)) ([d1fbeac](https://github.com/dryvist/mlx-benchmarks/commit/d1fbeacb64a813285972b222a0def84ea654d574))

## [0.10.0](https://github.com/dryvist/mlx-benchmarks/compare/v0.9.2...v0.10.0) (2026-07-08)


### Features

* **agentic:** many-tool tool-call reliability suite ([#101](https://github.com/dryvist/mlx-benchmarks/issues/101)) ([83dc048](https://github.com/dryvist/mlx-benchmarks/commit/83dc0484915a43ceb16df5fa6367c6c382233c44))

## [0.9.2](https://github.com/dryvist/mlx-benchmarks/compare/v0.9.1...v0.9.2) (2026-07-08)


### Documentation

* per-model-class agentic tool-calling notes (mid-2026 sourced) ([#99](https://github.com/dryvist/mlx-benchmarks/issues/99)) ([ae162c5](https://github.com/dryvist/mlx-benchmarks/commit/ae162c5365ff1fe6af72258f5e780153c1301bd8))

## [0.9.1](https://github.com/dryvist/mlx-benchmarks/compare/v0.9.0...v0.9.1) (2026-07-08)


### Bug Fixes

* **space:** coalesce dual result layouts so the viewer shows all real data ([#96](https://github.com/dryvist/mlx-benchmarks/issues/96)) ([99eb1ab](https://github.com/dryvist/mlx-benchmarks/commit/99eb1abbe39eed358c544fa15776be01d9189625))

## [0.9.0](https://github.com/dryvist/mlx-benchmarks/compare/v0.8.0...v0.9.0) (2026-07-08)


### ⚠ BREAKING CHANGES

* removes --kind promptfoo, the Splunk ship flags (--ship-splunk / --splunk-*), and --log-format. Publishing now covers lm-eval and vllm only.

### Features

* simplify to schema/publish core; add cross-machine hostname ([#92](https://github.com/dryvist/mlx-benchmarks/issues/92)) ([fbd83ba](https://github.com/dryvist/mlx-benchmarks/commit/fbd83baf280a628ad86aeb26e949c1f5d0d6ac6b))

## [0.8.0](https://github.com/dryvist/mlx-benchmarks/compare/v0.7.6...v0.8.0) (2026-07-03)


### Features

* **promptfoo:** model-comparison suites, converter, and optional Splunk ship ([#88](https://github.com/dryvist/mlx-benchmarks/issues/88)) ([bbb6204](https://github.com/dryvist/mlx-benchmarks/commit/bbb6204f5ddf7d462b1caa974851c5fade2a5a70))

## [0.7.6](https://github.com/dryvist/mlx-benchmarks/compare/v0.7.5...v0.7.6) (2026-07-03)


### Bug Fixes

* **ci:** declare jevans-ms self-hosted runner label for actionlint ([#89](https://github.com/dryvist/mlx-benchmarks/issues/89)) ([b8142df](https://github.com/dryvist/mlx-benchmarks/commit/b8142df3ce08a98468504711250666cf0728f694))

## [0.7.5](https://github.com/dryvist/mlx-benchmarks/compare/v0.7.4...v0.7.5) (2026-06-26)


### Documentation

* **readme:** make standalone — drop cross-repo narrative, link the hub ([#79](https://github.com/dryvist/mlx-benchmarks/issues/79)) ([e4a71e4](https://github.com/dryvist/mlx-benchmarks/commit/e4a71e459d348e695148b695eca87a46fb9a6647))

## [0.7.4](https://github.com/dryvist/mlx-benchmarks/compare/v0.7.3...v0.7.4) (2026-06-12)


### Bug Fixes

* **ci:** repoint shared workflows to dryvist hub ([#76](https://github.com/dryvist/mlx-benchmarks/issues/76)) ([3cc02f7](https://github.com/dryvist/mlx-benchmarks/commit/3cc02f7934bf7a0541243c596fbc139f23040a70))

## [0.7.3](https://github.com/dryvist/mlx-benchmarks/compare/v0.7.2...v0.7.3) (2026-06-06)


### Bug Fixes

* **ci:** use HF_TOKEN_WRITE_ALL for Space deployment ([#72](https://github.com/dryvist/mlx-benchmarks/issues/72)) ([1ad58ab](https://github.com/dryvist/mlx-benchmarks/commit/1ad58abad9750ed5d30bb5f033c99a815a3813a2))
* **space:** use format='ISO8601' for mixed timestamp parsing ([b505370](https://github.com/dryvist/mlx-benchmarks/commit/b5053709d6a8b38525fd2c2e09f2f3b86c9aeda2))


### Refactoring

* **logging:** extract _STANDARD_LOG_ATTRS module-level constant ([#71](https://github.com/dryvist/mlx-benchmarks/issues/71)) ([98e0a55](https://github.com/dryvist/mlx-benchmarks/commit/98e0a55e5b65191001cc6395241032312b2acb0e))

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
