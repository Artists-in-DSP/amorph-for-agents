# amorph for agents

Public documentation for AI assistants and MCP clients integrating with **amorph**, the DAW-native platform for creating custom audio tools from language, by [Artists in DSP](https://artistsindsp.com).

**One line:** describe the instrument, effect, or MIDI processor you need → amorph compiles it live from real Cmajor DSP → you play it as a patch in your DAW. The source is yours.

## What this repo is

This repo documents how agents connect to amorph, understand its runtimes, edit
readable Cmajor and UI source, compile safely, run QA probes, and apply changes to a
live patch inside a DAW.

It is for humans setting up agent workflows and for agents that need a compact,
canonical operating guide.

## Three layers

| Layer | What it is |
|-------|------------|
| **Platform** | amorph: language → playable, ownable DSP |
| **Runtimes** | DAW plugins: `Amorph_Instrument` (MIDI→audio), `Amorph_FX` (audio→audio), `Amorph_MIDI` (MIDI→MIDI). MCP variants: `instrument`, `fx`, `midi`. |
| **Patch** | Live Cmajor inside a runtime, no export step, no separate plugin binary |

## What makes it work

Three pieces have to be in the same place at the same time for "imagine it, play it" to actually hold up:

- **Real-time JIT compile.** amorph embeds the Cmajor JIT engine inside the plugin. A prompt becomes playable audio in seconds — no export step, no separate plugin binary, no DAW restart. Every edit hot-reloads the running patch.
- **Cmajor — a C-family DSP language, not a toy DSL.** Generated code is readable, editable, and owned by the user. amorph ships under a [commercial Cmajor license](https://cmajor.dev/docs/Licence.html) — your patches are yours, no GPL copyleft, no runtime royalty. Language reference: [cmajor.dev](https://cmajor.dev).
- **Tailored QA before commit.** `run_qa_probe` renders the patch headlessly — real MIDI (C4 + C6 + GM drums for synths, 440 Hz sine for FX), 32 × 512-sample blocks at 44.1 kHz — and returns RMS, peak, NaN/Inf, silence, clipping, DC offset, stereo correlation, stereo width, phase-cancellation warning, note-off release decay, and a spectral centroid/rolloff/peak FFT for instruments. The agent uses these metrics to decide whether a patch is safe to commit, not just whether it compiles.

These three are the moat. Most "AI audio" tools have one; amorph is the only one with all three inside a DAW runtime.

## Pick your door

| Audience | Start here |
|----------|------------|
| **Paste workflow** (Copy Instructions / external LLM) | [`docs/paste-context/PRODUCT_GUIDE.md`](docs/paste-context/PRODUCT_GUIDE.md) + [`BUILD_COMPAT.md`](BUILD_COMPAT.md) |
| **Connect (MCP)** — Cursor, VS Code, Claude Desktop | [`AGENTS.md`](AGENTS.md) + [`MCP_SETUP.md`](MCP_SETUP.md) — **not in v0.99**; see [`BUILD_COMPAT.md`](BUILD_COMPAT.md) |
| **Explore / share / install** | [`docs/story/SHARE_USER.md`](docs/story/SHARE_USER.md) · [`docs/story/INSTALL.md`](docs/story/INSTALL.md) |
| **What is amorph?** (ontology, tabs, layers) | [`docs/story/ONTOLOGY.md`](docs/story/ONTOLOGY.md) · [`llms.txt`](llms.txt) |

Reference: [`TOOLS.md`](TOOLS.md) (MCP tools) · [`PRODUCT_TIERS.md`](PRODUCT_TIERS.md) (editor · BYOK · MCP · play) · [`CMAJOR_QUICKREF.md`](CMAJOR_QUICKREF.md)

## Build compatibility

MCP, IDE auto-connect, and Connections onboarding are **not in the current Gumroad download (v0.99)**. v0.99 supports copy-paste, in-plugin assistant, and Explore on macOS and Windows. Before MCP setup, confirm **Settings → Connections** exists in the plugin.

See [`BUILD_COMPAT.md`](BUILD_COMPAT.md) for the full gate and v0.99-safe claims.

## Quick links

- **Download (free beta):** https://artistsindsp.gumroad.com/l/amorph
- **Website:** https://artistsindsp.com/
- **Discord:** https://discord.gg/JzVbjU38tp
- **Agent spec (canonical):** this repo — [`llms.txt`](llms.txt) · [`llms-full.txt`](llms-full.txt) (raw GitHub URLs in paste-context). The copies on artistsindsp.com are marketing snapshots; bot fetch may 403 until Cloudflare allowlist — prefer `raw.githubusercontent.com/Artists-in-DSP/amorph-for-agents/main/…`

## MCP in 30 seconds (not in v0.99)

1. Confirm **Settings → Connections** is present ([`BUILD_COMPAT.md`](BUILD_COMPAT.md)). If missing, the user is on v0.99 — use copy-paste or BYOK only.
2. Install amorph and open a runtime in your DAW.
3. Connect your IDE agent via MCP ([setup guide](MCP_SETUP.md)).
4. Call **`get_host_status`** first (works even before the plugin is open).
5. Edit with **`edit_lines`** → **`task_complete`** → **`apply_draft`** to hear changes.

Good first tasks: MIDI-tracked comb filters, transient-reactive delays, evolving drone
synths, generative MIDI sequencers, bespoke modulation processors, and other tools too
specific to buy off the shelf.

---

*Artists in DSP · Switzerland*
