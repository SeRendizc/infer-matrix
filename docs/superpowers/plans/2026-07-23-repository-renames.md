# Repository Renames Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge the latest verified development lines, replace the retired InferMatrix brand with Agent Eval Lab and Decoder Inference Lab, update both READMEs to the code's real state, and prove both renamed distributions still work.

**Architecture:** Treat the work as two independent repository migrations. First establish passing baselines and fast-forward each active development line into `main`; then perform one breaking, compatibility-free package rename per repository, migrate existing tests unchanged in intent, and validate source, build, installation, and CLI behavior before renaming local repository directories.

**Tech Stack:** Python 3.10/3.11, setuptools, pytest, Ruff, Typer, Pydantic, HTTPX, PyTorch, PowerShell, Git

---

### Task 1: Verify and Merge Decoder Inference Baseline

**Files:**
- Verify: `D:\infermatrix_model_lab\src\infermatrix_model_lab\`
- Verify: `D:\infermatrix_model_lab\tests\`
- Merge target: `D:\infermatrix_model_lab\.git\refs\heads\main`

- [ ] **Step 1: Confirm repository state and ancestry**

Run:

```powershell
git -C D:\infermatrix_model_lab status --short --branch
git -C D:\infermatrix_model_lab merge-base --is-ancestor main d4-rmsnorm
```

Expected: branch `d4-rmsnorm`, no worktree changes, and the ancestry command exits `0`.

- [ ] **Step 2: Run the complete branch baseline**

Run:

```powershell
D:\infermatrix_model_lab\.venv\Scripts\python.exe -m pytest tests -q
D:\infermatrix_model_lab\.venv\Scripts\python.exe -m ruff check .
```

Expected: all CPU tests pass; CUDA tests either pass or are explicitly skipped by their existing markers; Ruff exits `0`.

- [ ] **Step 3: Fast-forward the verified branch into main**

Run:

```powershell
git -C D:\infermatrix_model_lab switch main
git -C D:\infermatrix_model_lab merge --ff-only d4-rmsnorm
```

Expected: `main` advances to `b76ae5a` with no merge commit.

- [ ] **Step 4: Re-run the baseline on main**

Run:

```powershell
D:\infermatrix_model_lab\.venv\Scripts\python.exe -m pytest tests -q
D:\infermatrix_model_lab\.venv\Scripts\python.exe -m ruff check .
```

Expected: results match Step 2.

### Task 2: Verify and Merge Agent Evaluation Baseline

**Files:**
- Verify: `D:\infermatrix\src\infermatrix\`
- Verify: `D:\infermatrix\tests\`
- Preserve: `D:\infermatrix\.handoff-review\`
- Merge target: `D:\infermatrix\.git\refs\heads\main`

- [ ] **Step 1: Confirm repository state and ancestry**

Run:

```powershell
git -C D:\infermatrix status --short --branch
git -C D:\infermatrix merge-base --is-ancestor main temp
```

Expected: only `.handoff-review/` is untracked, and the ancestry command exits `0`.

- [ ] **Step 2: Run the complete branch baseline**

Run:

```powershell
D:\infermatrix\.venv\Scripts\python.exe -m pytest -q
D:\infermatrix\.venv\Scripts\python.exe -m ruff check .
```

Expected: all tests pass and Ruff exits `0`.

- [ ] **Step 3: Fast-forward the verified branch into main**

Run:

```powershell
git -C D:\infermatrix switch main
git -C D:\infermatrix merge --ff-only temp
```

Expected: `main` advances to the tip of `temp`, including the approved rename design and this implementation plan, without touching `.handoff-review/`.

- [ ] **Step 4: Re-run the baseline on main**

Run:

```powershell
D:\infermatrix\.venv\Scripts\python.exe -m pytest -q
D:\infermatrix\.venv\Scripts\python.exe -m ruff check .
```

Expected: results match Step 2.

### Task 3: Rename the Evaluation Package and Domain Types

**Files:**
- Rename: `D:\infermatrix\src\infermatrix\` → `D:\infermatrix\src\agent_eval_lab\`
- Modify: `D:\infermatrix\pyproject.toml`
- Modify: every tracked `*.py` under `D:\infermatrix\src\` and `D:\infermatrix\tests\`
- Modify: `D:\infermatrix\examples\basic_chat.yaml`
- Modify: `D:\infermatrix\examples\streaming_json.yaml`
- Modify: `D:\infermatrix\docs\report_format.md`

- [ ] **Step 1: Rename the tracked package directory**

Run:

```powershell
git -C D:\infermatrix mv src/infermatrix src/agent_eval_lab
```

Expected: Git records a package-directory rename.

- [ ] **Step 2: Change distribution and CLI entry point**

Set these exact `pyproject.toml` values:

```toml
[project]
name = "agent-eval-lab"
description = "Evaluation infrastructure for reliable agentic LLM systems"

[project.scripts]
agent-eval = "agent_eval_lab.cli:app"
```

Remove the `infermatrix` console entry point.

- [ ] **Step 3: Migrate Python imports and branded domain types**

Apply these exact identifier mappings throughout tracked Python source and tests:

```text
infermatrix        -> agent_eval_lab
InferCase          -> EvalCase
InferCaseLoader    -> EvalCaseLoader
```

Keep `RunReport`, `Pipeline`, `BackendConfig`, `ProtocolConfig`, `HttpExchange`,
`SseDecoder`, and other accurate generic types unchanged.

- [ ] **Step 4: Make migrated tests prove old identifiers are gone**

Run:

```powershell
rg -n "from infermatrix|import infermatrix|InferCase|InferCaseLoader" D:\infermatrix\src D:\infermatrix\tests
```

Expected: no matches.

- [ ] **Step 5: Run focused loader and CLI regression tests**

Run:

```powershell
D:\infermatrix\.venv\Scripts\python.exe -m pytest tests/test_case_loader.py tests/test_cli_reports.py -q
```

Expected: all focused tests pass using `EvalCase`, `EvalCaseLoader`, and the new package path.

### Task 4: Rewrite the Agent Eval Lab README and Current Documentation

**Files:**
- Replace: `D:\infermatrix\README.md`
- Modify: `D:\infermatrix\docs\report_format.md`
- Modify: `D:\infermatrix\docs\superpowers\plans\2026-07-19-chat-streaming-full-body.md`
- Modify: `D:\infermatrix\docs\superpowers\specs\2026-07-19-chat-streaming-full-body-design.md`
- Modify: `D:\infermatrix\docs\superpowers\specs\2026-07-23-reliable-agentic-llm-systems-rename-design.md`
- Modify: `D:\infermatrix\docs\superpowers\plans\2026-07-23-repository-renames.md`

- [ ] **Step 1: Replace the corrupted and stale README**

Write a UTF-8 README headed `# Agent Eval Lab` that states:

```text
Evaluation infrastructure for agentic LLM systems, starting from reproducible
model-interface behavior and extending to agent traces, recovery and failure
attribution.
```

Document only capabilities present in `main`: YAML evaluation cases, mock
backend, OpenAI-compatible non-streaming and streaming clients, raw HTTP
evidence and redaction, SSE wire decoding, parsing/checking, reports, pipeline,
and CLI. Mark real vLLM/SGLang evidence, Responses API, agent traces, recovery,
and cross-backend attribution as roadmap work.

- [ ] **Step 2: Update commands and structure**

All current examples use:

```powershell
agent-eval run examples/basic_chat.yaml
python -m pytest
python -m ruff check .
```

The package tree uses `src/agent_eval_lab/`, and the core flow names `EvalCase`.

- [ ] **Step 3: Annotate historical documents**

Add this note after the title of each pre-rename document that uses the old brand:

```text
Historical note: this document predates the rename from InferMatrix to Agent Eval Lab.
```

Do not rewrite historical decisions as if the new name existed at the time.

- [ ] **Step 4: Scan current documentation**

Run:

```powershell
rg -n -i "infermatrix|infer-matrix|infercase" D:\infermatrix --glob "!.git/**" --glob "!.handoff-review/**"
```

Expected: old names occur only in explicit historical notes and the two rename design/implementation records.

### Task 5: Rename the Decoder Inference Package

**Files:**
- Rename: `D:\infermatrix_model_lab\src\infermatrix_model_lab\` → `D:\infermatrix_model_lab\src\decoder_inference_lab\`
- Modify: `D:\infermatrix_model_lab\pyproject.toml`
- Modify: tracked Python files under `D:\infermatrix_model_lab\scripts\`, `src\`, and `tests\`
- Modify: `D:\infermatrix_model_lab\artifacts\d1_environment.json`

- [ ] **Step 1: Rename the tracked package directory**

Run:

```powershell
git -C D:\infermatrix_model_lab mv src/infermatrix_model_lab src/decoder_inference_lab
```

Expected: Git records a package-directory rename.

- [ ] **Step 2: Change distribution metadata**

Set these exact values:

```toml
[project]
name = "decoder-inference-lab"
description = "Decoder-only Transformer learning and inference measurement lab"
```

- [ ] **Step 3: Migrate imports and environment identifiers**

Apply:

```text
infermatrix_model_lab -> decoder_inference_lab
infermatrix-model-lab -> decoder-inference-lab
InferMatrix Model Lab -> Decoder Inference Lab
```

Update source, tests, training scripts, artifact project identifiers, and
documentation links. Do not change mathematical APIs or model behavior.

- [ ] **Step 4: Run focused model regressions**

Run:

```powershell
D:\infermatrix_model_lab\.venv\Scripts\python.exe -m pytest tests/test_config.py tests/test_norm.py tests/test_block.py tests/test_decoder.py -q
```

Expected: all focused tests pass using `decoder_inference_lab`.

### Task 6: Rewrite the Decoder Inference Lab README and Historical Notes

**Files:**
- Replace: `D:\infermatrix_model_lab\README.md`
- Modify: historical Markdown files under `D:\infermatrix_model_lab\docs\`
- Modify: `D:\infermatrix_model_lab\src\decoder_inference_lab\model\OWNERSHIP.md`

- [ ] **Step 1: Replace the corrupted and stale README**

Write a UTF-8 README headed `# Decoder Inference Lab`. Its implemented progress
must be derived from source and passing tests, including configuration/data,
causal self-attention, MLP, RMSNorm, pre-norm block, decoder, generation,
next-token loss/training utilities when present on the merged branch, and
CPU/CUDA test coverage. KV cache and explicit prefill/decode optimization stay
in the roadmap unless code proves them implemented.

- [ ] **Step 2: Update installation, paths, and environment commands**

Use `src/decoder_inference_lab/`, `decoder-inference-lab`, and:

```powershell
python -m pip install -e ".[dev]"
python -m pytest tests -q
python -m ruff check .
```

- [ ] **Step 3: Annotate historical documents**

Add this note after the title of each pre-rename document that uses the old brand:

```text
Historical note: this document predates the rename from InferMatrix Model Lab to Decoder Inference Lab.
```

- [ ] **Step 4: Scan current documentation**

Run:

```powershell
rg -n -i "infermatrix|infer-matrix" D:\infermatrix_model_lab --glob "!.git/**"
```

Expected: old names occur only in explicit historical notes.

### Task 7: Validate and Commit Both Renames

**Files:**
- Verify all tracked files in both repositories
- Create: temporary build and virtual-environment directories outside tracked source

- [ ] **Step 1: Run complete Evaluation verification**

Run:

```powershell
D:\infermatrix\.venv\Scripts\python.exe -m pytest -q
D:\infermatrix\.venv\Scripts\python.exe -m ruff check .
D:\infermatrix\.venv\Scripts\python.exe -m build
```

Expected: tests and Ruff pass; wheel and sdist are created for `agent-eval-lab`.

- [ ] **Step 2: Install and smoke-test Evaluation in isolation**

Create a temporary virtual environment, install the built wheel, then run:

```powershell
python -c "import agent_eval_lab; print(agent_eval_lab.__name__)"
agent-eval --help
agent-eval run D:\infermatrix\examples\basic_chat.yaml
```

Expected: import prints `agent_eval_lab`; CLI help exits `0`; representative case exits successfully.

- [ ] **Step 3: Run complete Inference verification**

Run:

```powershell
D:\infermatrix_model_lab\.venv\Scripts\python.exe -m pytest tests -q
D:\infermatrix_model_lab\.venv\Scripts\python.exe -m ruff check .
D:\infermatrix_model_lab\.venv\Scripts\python.exe -m build
```

Expected: all applicable tests pass, CUDA outcomes are reported explicitly,
Ruff passes, and wheel/sdist names use `decoder_inference_lab`.

- [ ] **Step 4: Install and smoke-test Inference in isolation**

Create a temporary virtual environment, install the built wheel, then run:

```powershell
python -c "import decoder_inference_lab; print(decoder_inference_lab.__name__)"
python D:\infermatrix_model_lab\scripts\verify_environment.py --help
```

Expected: import prints `decoder_inference_lab`; the environment script starts successfully.

- [ ] **Step 5: Review test deletion candidates**

Run:

```powershell
git -C D:\infermatrix diff --name-status --diff-filter=D
git -C D:\infermatrix_model_lab diff --name-status --diff-filter=D
```

Expected: no behavioral test is deleted. Remove only temporary migration smoke
artifacts or tests that solely enforce an intentionally unsupported old name.

- [ ] **Step 6: Commit the Evaluation rename**

Stage only tracked rename-related files and commit:

```powershell
git -C D:\infermatrix commit -m "Rename InferMatrix to Agent Eval Lab"
```

Expected: `.handoff-review/` remains untracked and absent from the commit.

- [ ] **Step 7: Commit the Inference rename**

Stage only tracked rename-related files and commit:

```powershell
git -C D:\infermatrix_model_lab commit -m "Rename Model Lab to Decoder Inference Lab"
```

Expected: one pure rename/documentation commit with no feature integration.

### Task 8: Rename Local Repository Directories

**Files:**
- Rename: `D:\infermatrix_model_lab\` → `D:\decoder-inference-lab\`
- Rename: `D:\infermatrix\` → `D:\agent-eval-lab\`

- [ ] **Step 1: Confirm final repository state**

Run:

```powershell
git -C D:\infermatrix status --short --branch
git -C D:\infermatrix_model_lab status --short --branch
```

Expected: both repositories are on `main`; Evaluation has only the preserved
`.handoff-review/` untracked; Inference is clean.

- [ ] **Step 2: Rename the inactive Inference directory**

Resolve and verify both absolute paths are direct children of `D:\`, then use
PowerShell `Move-Item -LiteralPath` to rename the directory.

Expected: `D:\decoder-inference-lab` exists and its Git worktree is healthy.

- [ ] **Step 3: Rename the active Evaluation directory**

Rename only after all work and commits are complete. Because it is the active
Codex workspace root, report that the user may need to reopen the workspace at
`D:\agent-eval-lab`.

- [ ] **Step 4: Defer GitHub remote renames**

Do not change GitHub repository names or profile links without a separate
network-side action. Report the exact remaining remote rename step.

