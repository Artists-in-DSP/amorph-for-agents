# Amorph MCP tools

Tool names use **snake_case** in MCP `tools/call`. Always call **`get_host_status`** first if connection is uncertain.

## Bridge-level

| Tool | When to use |
|------|-------------|
| `get_host_status` | Check connection; get install/onboarding steps when disconnected |
| `list_instances` | List open runtimes (ports, variants, patches, focus) when multiple instances are running |
| `set_active_instance` | Pin routing by `port`, `patch`, or `variant`; or `follow_focus: true` to clear pin |

## Code — read

| Tool | Purpose |
|------|---------|
| `read_code` | Full DSP or UI source (large files may be truncated; use outline/range for precision) |
| `read_code_range` | Specific line range; use exact returned text for edits |
| `get_code_outline` | Token-efficient structural summary; do not copy outline text as edit anchors |
| `search_code` | Regex search in source |

## Code — write

| Tool | Purpose |
|------|---------|
| `edit_lines` | **Preferred** — replace line range |
| `edit_code` | Single anchor-based replacement |
| `edit_code_multi` | Multiple anchors in one call |
| `edit_code_dsp_and_ui` | Edit DSP + UI atomically |
| `regex_replace` | Regex find-and-replace |
| `generate_code` | Replace entire file in the working draft (overwrites; draft-compiles) |
| `undo_last_edit` | Revert last edit |

## Compile & apply

| Tool | Purpose |
|------|---------|
| `get_error` | Last compiler error |
| `task_complete` | Signal goal done — surfaces draft for review (**does not** auto-commit) |
| `apply_draft` | Commit pending draft to the live runtime + compile |
| `reload_from_disk` | Pull `dsp.cmajor` / `index.js` from project folder (default: compile) |

## QA & catalog

| Tool | Purpose |
|------|---------|
| `run_qa_probe` | Headless render with real MIDI (C4 + C6 + GM drums for synths; 440 Hz sine for FX), 32 × 512-sample blocks at 44.1 kHz. Returns: RMS, peak, NaN/Inf, silence (-100 dBFS), clipping, DC offset, stereo correlation, stereo width, phase-cancellation warning, note-off release decay (synths), and 8K-sample FFT spectral centroid/rolloff/peak (instruments). Optional args: `variant` (`fx`/`instrument`/`midi`) and `parameter_overrides` (`param1`, `param2`, ... in real units). The agent uses these metrics to decide whether a patch is safe to commit, not just whether it compiles. |
| `search_components` | Browse built-in DSP/UI snippet catalog |

## Eval/admin tools

Some builds may expose eval/admin tools such as `start_agent_session`, `set_provider`,
and `set_model`. They are not part of the normal external authoring workflow; do not use
them unless you are explicitly testing/evaluating the product.

Internal prompt-loop tools such as `create_checkpoint`, `get_graph_topology`, `plan`,
`clarify`, and `classify_intent` are not part of the normal external MCP workflow.

## Lifecycle

```
read → edit_lines → fix any compile errors returned by the edit/generate result
→ run_qa_probe? → task_complete → apply_draft
```

**Critical:** `generate_code` / edits may compile the draft, but they stay in the working
copy until `task_complete` then `apply_draft` commits them to live audio.

**Never offload commit to the user.** External MCP agents must call `apply_draft` themselves.
Do not ask them to reload the preset, re-select the patch, or click Apply in the plugin UI.
Only say a change is live after `apply_draft` returns OK **including the verified `dsp.cmajor` path**.
If it returns `ERROR`, fix and call `apply_draft` again — never hand-write project files or use `reload_from_disk` as a workaround.

If no edits changed the working copy, `task_complete` may not create a draft; `apply_draft`
then has nothing to apply. `apply_draft` requests the live compile/application; call
`get_error` afterwards if compile status matters.

`reload_from_disk` requires a saved project folder. With default `compile=true`, it pulls
on-disk `dsp.cmajor` / `index.js` into the runtime and applies them without a separate
`task_complete`. Locked/binary patches cannot be reloaded as editable source.

Use `get_error` to inspect current live/reload/runtime compile state when needed. Failed
edit/generate calls usually return their compile error directly, and the failed edit may
have been reverted.

## Conflict protection

Mutating tools fail while the runtime's **in-plugin** agent is running. Poll and retry.

## Locked patches

If `dsp.cmajor` starts with `Cmaj0001`, treat it as locked/binary. Do not edit it. MCP may
be able to work with UI or metadata, but readable DSP source is unavailable and
`reload_from_disk` cannot turn a locked binary patch into editable source.

## Prompts (not tools)

Use `prompts/get`: `cmajor-rules`, `tool-guide`, `ui-rules` (patch `index.js`), `shell-ui-rules` (product shell — ADSP_UI).
