# @paperclipai/adapter-utils

## Unreleased

### Patch Changes

- Session-end autosave: add `runSessionEndAutosave` and `runAdapterSessionEndAutosave` helpers that wrap `scripts/session_end_autosave.py` for adapter `execute()` termination paths. The wrapper is contractually non-throwing (a snapshot failure must never block run termination), honors `PAPERCLIP_NO_AUTOSAVE=1` / `AUTOSAVE=0` opt-outs, and forwards the run-id, workspace cwd, and issue identifier so the WIP commit subject and push target stay correct. Wired into `claude-local`, `codex-local`, `cursor-local`, `cursor-cloud`, `opencode-local`, `gemini-local`, `grok-local`, `pi-local`, `acpx-local`, `openclaw-gateway`, and `hermes` adapter `execute()` finally blocks (BTCAAAAA-39074). The `hermes-gateway` shim delegates to an external workspace package and is intentionally out of scope here.

## 0.3.1

### Patch Changes

- Stable release preparation for 0.3.1

## 0.3.0

### Minor Changes

- Stable release preparation for 0.3.0

## 0.2.7

### Patch Changes

- Version bump (patch)

## 0.2.6

### Patch Changes

- Version bump (patch)

## 0.2.5

### Patch Changes

- Version bump (patch)

## 0.2.4

### Patch Changes

- Version bump (patch)

## 0.2.3

### Patch Changes

- Version bump (patch)

## 0.2.2

### Patch Changes

- Version bump (patch)

## 0.2.1

### Patch Changes

- Version bump (patch)
