# Reliable Agentic LLM Systems Rename Design

Date: 2026-07-23

## Goal

Retire InferMatrix as an umbrella brand and give the two existing repositories
independent, capability-specific identities:

| Capability | Repository | Python package | CLI |
| --- | --- | --- | --- |
| Evaluation | `agent-eval-lab` | `agent_eval_lab` | `agent-eval` |
| Inference | `decoder-inference-lab` | `decoder_inference_lab` | None |

The shared portfolio theme is:

> Reliable Agentic LLM Systems — Runtime · Evaluation · Inference

This change is a breaking rename at version `0.1.0`. It does not add a
compatibility layer for old imports, distributions, or CLI commands.

## Baselines

The migration uses the latest active development line in each repository:

- Evaluation: `temp` at `d2f3738`, a direct descendant of `phase-e1d`.
- Inference: `d4-rmsnorm` at `b76ae5a`.

The separate Model Lab D5 training branch is not merged as part of this work.
Feature integration and brand migration must remain separate changes.

The untracked `D:\infermatrix\.handoff-review\` directory is user-owned and
must not be modified or committed.

## Evaluation Repository Migration

Rename:

- Distribution `infermatrix` to `agent-eval-lab`.
- Package `infermatrix` to `agent_eval_lab`.
- CLI command `infermatrix` to `agent-eval`.
- Product references `InferMatrix` to `Agent Eval Lab`.
- Domain type `InferCase` to `EvalCase`.
- Domain type `InferCaseLoader` to `EvalCaseLoader`.

Update all affected imports, annotations, fixtures, examples, scripts, tests,
entry points, error messages, report metadata, reproduction commands, and
current documentation.

Keep general-purpose architecture names when they remain accurate, including:

- `RunReport`
- `Pipeline`
- `BackendConfig`
- `ProtocolConfig`
- `HttpExchange`
- `SseDecoder`
- `AnalyzerResult`

The README positioning is:

> Evaluation infrastructure for agentic LLM systems, starting from
> reproducible model-interface behavior and extending to agent traces,
> recovery and failure attribution.

The rename must not claim that future Agent Trace, recovery, or failure
attribution capabilities already exist.

## Inference Repository Migration

Rename:

- Distribution `infermatrix-model-lab` to `decoder-inference-lab`.
- Package `infermatrix_model_lab` to `decoder_inference_lab`.
- Product references `InferMatrix Model Lab` to `Decoder Inference Lab`.

Update all affected imports, tests, scripts, configuration, artifact project
identifiers, ownership documentation, and the README.

The README must describe the repository as a decoder-only Transformer learning
and measurement lab covering mechanisms such as attention, normalization,
prefill/decode, generation, and later KV-cache work. It must distinguish
implemented capability from roadmap work.

## Historical Documents

Historical plans and design documents keep their original technical content.
Documents that predate the rename receive this note near the top:

> Historical note: this document predates the rename from InferMatrix Model
> Lab to Decoder Inference Lab.

The Evaluation repository uses the equivalent note when an old document names
InferMatrix:

> Historical note: this document predates the rename from InferMatrix to Agent
> Eval Lab.

Historical filenames are retained unless the filename itself contains an old
brand or package identifier. This preserves chronology without pretending the
new name existed when the document was written.

## Repository Directory and Remote Rename

Code and packaging changes are completed and verified before repository
directories or remotes are renamed.

After validation:

- `D:\infermatrix_model_lab` becomes `D:\decoder-inference-lab`.
- `D:\infermatrix` becomes `D:\agent-eval-lab`.

Renaming the active workspace root may require the surrounding Codex workspace
to be reopened at the new location. GitHub repository names and profile links
are a separate final network-side operation and are not required for local
code validation.

## Test Policy

Existing tests are migrated with the code and retained when they verify real
behavior. A test is not obsolete merely because its imports or displayed names
change.

Deletion is limited to:

- Temporary smoke-test artifacts created only for this migration.
- Exact duplicate tests with no distinct assertion value.
- Tests whose sole purpose is compatibility with an old import path or old CLI
  command, because this migration deliberately provides no compatibility layer.

No behavioral regression test is deleted simply to obtain a passing suite.

## Verification

Record a clean baseline before modifying each repository. After the rename,
verify each repository independently.

Evaluation verification:

1. Run the complete pytest suite.
2. Run Ruff over source and tests.
3. Build wheel and source distributions.
4. Install the wheel into a clean temporary virtual environment.
5. Import `agent_eval_lab`.
6. Run `agent-eval --help`.
7. Run a representative CLI smoke case.

Inference verification:

1. Run the complete CPU-capable pytest suite.
2. Run CUDA tests when compatible CUDA hardware and runtime are available;
   otherwise report them separately rather than hiding the limitation.
3. Run Ruff over source and tests.
4. Build wheel and source distributions.
5. Install the wheel into a clean temporary virtual environment.
6. Import `decoder_inference_lab`.
7. Run the environment verification and a representative training or
   generation smoke command when supported by the local environment.

Finally, scan both repositories for:

- `InferMatrix`
- `infermatrix`
- `InferCase`
- `infer-matrix`

Remaining matches are allowed only in explicit historical rename notes or
unmodified Git history. Generated build artifacts must not be used to excuse
source-tree matches.

## Commit Boundaries

Keep the migration reviewable:

1. Commit this approved design separately.
2. Create one pure rename commit in the Evaluation repository.
3. Create one pure rename commit in the Inference repository.
4. Do not mix feature development, branch integration, or unrelated cleanup
   into either rename commit.

