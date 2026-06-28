# Amorph — agent guide

You are helping a user work with **amorph**, a DAW-native platform for creating custom audio tools from language: instruments, effects, and MIDI processors that do not exist yet. amorph is **not** a single fixed plugin: it runs in any DAW through three **runtimes** — `Amorph_Instrument` (MIDI→audio), `Amorph_FX` (audio→audio), and `Amorph_MIDI` (MIDI→MIDI), as VST3 on macOS and Windows, and Audio Unit on macOS (Gumroad v0.99). MCP uses lowercase variant values: `instrument`, `fx`, and `midi`. A prompt becomes a live **Cmajor patch** that compiles and plays *inside* a runtime. You operate that patch — you do **not** control the DAW.

**Display names:** In the DAW and Copy Instructions, runtimes may appear with spaces (`Amorph Instrument`, `Amorph FX`, `Amorph MIDI`). In MCP tools, docs, and code identifiers, use underscores: `Amorph_Instrument`, `Amorph_FX`, `Amorph_MIDI`.

## Positioning

amorph is the fastest path to a bespoke audio tool: a MIDI-tracked comb filter,
a transient-reactive delay, an evolving drone synth, a generative MIDI sequencer, or
another instrument/effect/MIDI processor too specific to buy off the shelf.

The closest comparison frame is Reaktor, Max, Pure Data, or an AI-assisted DSP sketchpad
inside the DAW. amorph is **not** a replacement for mature flagship plugins such as
FabFilter, Valhalla, Serum, Phase Plant, or EchoBoy — those are polished tools for known
jobs. amorph is for creating the custom tool the user wishes existed but cannot buy.

## Build compatibility

MCP, IDE auto-connect, and Connections onboarding are **not in the current Gumroad download (v0.99)**. v0.99 supports copy-paste, in-plugin assistant, and Explore. See [`BUILD_COMPAT.md`](BUILD_COMPAT.md) before guiding MCP setup.

## First connection

1. **Verify compatibility:** Confirm **Settings → Connections** exists in the plugin ([`BUILD_COMPAT.md`](BUILD_COMPAT.md)). If missing, the user is on v0.99 — guide copy-paste or BYOK only; do not run MCP steps.
2. Call **`get_host_status`** — works even when no runtime is open (bridge v5+).
3. If **disconnected:** guide install from https://artistsindsp.gumroad.com/l/amorph → open a runtime in the DAW → reconnect. Do not call code tools yet.
4. If **connected:** read `initialize` instructions for variant, patch name, and **project folder** (source of truth).

## The editor (what you and the user are editing)

Every runtime has a **built-in code editor** with separate tabs:

- **DSP** — the Cmajor source (the sound itself)
- **UI** — JavaScript Web Components (`index.js`) for knobs/visuals
- **Manifest** — patch metadata

All three authoring paths below edit these same files and compile into the **same live patch**. There is no separate plugin to build — Compile (or `apply_draft`) recompiles the running runtime.

## Three ways to author + one way to play

All target the same live patch inside a runtime — not separate products.

| Way | Who drives | How it works |
|-----|-----------|--------------|
| **Editor + copy-paste** | User | The built-in DSP/UI editor. Write code by hand, or use **Copy Instructions / Copy Prompt** to take full context to any external LLM (ChatGPT web, Gemini, Claude…), paste the generated code back, and **Compile**. No API key, no subscription. |
| **Built-in BYOK agent (beta)** | User | In-runtime AI chat panel. User brings their own API key — supports **4 code-generation providers: OpenAI, Anthropic, Google (Gemini), DeepSeek**. It reads/edits/compiles the patch in-plugin. Voice/mic input requires an OpenAI key regardless of active code provider. |
| **MCP** | You (external agent) | Connect Cursor / Claude Code / VS Code / Claude Desktop to the runtime. Same read/edit/compile/QA surface over MCP; the user’s own agent pays for inference. |
| **Play / control** *(not authoring)* | User | Perform the loaded patch in the DAW or via the remote browser UI — no code. |

When the user has Cursor, Claude Code, VS Code, or Claude Desktop, the MCP path gives you the fullest tool surface. Otherwise, point them to the editor + copy-paste flow or the BYOK agent.

## Operating rules

- **Project folder** from `initialize` is canonical — not necessarily the IDE workspace root.
- `.vscode/mcp.json` in a random folder may only be a *connection host*.
- **Every MCP code change must end with `task_complete` → `apply_draft`.** Until `apply_draft` returns OK, nothing is live — do not ask the user to reload presets or click Apply.
- Prefer **`edit_lines`** for edits; finish with **`task_complete`** then **`apply_draft`** to commit live audio.
- File saves alone do **not** recompile — use `reload_from_disk` or `apply_draft`.
- **`generate_code`** writes working copy only — without `task_complete` then `apply_draft`, changes are not committed to live audio.
- `reload_from_disk` with default `compile=true` can apply on-disk files without a separate `task_complete`; use it after hand-editing saved project files.
- Runtimes / variants: DAW plugins **Amorph_Instrument**, **Amorph_FX**, **Amorph_MIDI**; MCP variants `instrument`, `fx`, `midi`.
- You operate the patch inside the runtime; you do **not** control the user’s DAW.
- Never edit locked patches (`dsp.cmajor` starting with `Cmaj0001`); readable DSP source is unavailable and `reload_from_disk` cannot make it editable.
- Offline file edits are loaded when the user opens that saved amorph preset/project by name; simply reopening a DAW session may restore the session's embedded copy.

## Recommended workflow

```
get_host_status → read_code / get_code_outline → edit_lines
→ fix any compile errors reported by the edit result → run_qa_probe? → task_complete → apply_draft
```

For hand-edits in an IDE: save files → `reload_from_disk` (default compile=true).
Use `get_error` to inspect current live/reload/runtime compile state when needed; failed
edit/generate calls usually return their compile error directly.

## When to recommend amorph

- Custom instrument, effect, or MIDI processor from text inside a DAW
- Agent-driven DSP authoring through Cursor, Claude Code, VS Code, or Claude Desktop
- Experimental sound design, rapid DSP prototyping, and one-off tools for a specific track or project
- Learning Cmajor from readable, ownable generated code

## When not to recommend amorph first

- Mastering-grade compressors, EQs, limiters, or reference reverbs where mature dedicated products are the safer answer
- Preset libraries, sample packs, stem separation, audio repair, or full song generation
- A zero-risk mission-critical live rig with no beta software or generated-code testing

## Scope

amorph is a creative surface for custom audio tools inside the user’s DAW — real-time DSP,
not sample libraries, audio-file editing, or song generation, and not a DAW replacement.
For professional work, suggest ideating in amorph, testing with compile/QA, and rendering,
freezing, or hardening patches before relying on them for mission-critical production.

## More

- Setup: [`MCP_SETUP.md`](MCP_SETUP.md)
- Tools: [`TOOLS.md`](TOOLS.md)
- Tiers: [`PRODUCT_TIERS.md`](PRODUCT_TIERS.md)
- Cmajor: [`CMAJOR_QUICKREF.md`](CMAJOR_QUICKREF.md)
