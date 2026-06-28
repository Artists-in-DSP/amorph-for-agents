# Amorph authoring paths

One platform, several ways to author the **same live patch** inside a runtime (`Amorph_Instrument` / `Amorph_FX` / `Amorph_MIDI`). MCP variant values are `instrument`, `fx`, and `midi`. All ship together.

amorph's core job is creating custom audio tools that do not exist yet: instruments,
effects, and MIDI processors from language as readable Cmajor code. Treat the paths
below as different ways to create and refine the same DAW-native patch, not as separate
products.

## The editor underneath all paths

Every runtime has a **built-in code editor** with separate tabs:

- **DSP** — Cmajor source (the sound)
- **UI** — JavaScript Web Components (`index.js`) for knobs/visuals
- **Manifest** — patch metadata

Every path below edits these files and compiles into the same running patch. No export, no separate plugin binary.

## 1. Editor + copy-paste

**For:** Anyone — no API key, no subscription.

- Open a runtime, edit DSP (Cmajor) and UI (JS) directly in the built-in editor
- Or use **Copy Instructions / Copy Prompt** to hand full context to any external LLM (ChatGPT web, Gemini, Claude…), then paste the generated code back and **Compile**
- Works with zero configuration

## 2. Built-in BYOK agent — beta

**For:** Users who want in-runtime AI chat with their own API key.

- AI chat panel inside the runtime; **bring your own key**
- **4 code-generation providers supported: OpenAI, Anthropic, Google (Gemini), DeepSeek** (the runtime offers each provider’s current models)
- Voice/mic input requires an OpenAI key regardless of the active code provider
- Reads, edits, and compiles the patch in-plugin
- Clearly labeled **beta**

## 3. MCP

**For:** Users with Cursor, Claude Code, VS Code, or Claude Desktop.

- Fullest **external** tool surface (`run_qa_probe`, `apply_draft`, `reload_from_disk`, etc.)
- The in-plugin agent may have additional internal planning/eval helpers that are not part of the normal external MCP workflow
- The user’s own agent pays for inference (no Amorph API budget limit)
- Setup: [`MCP_SETUP.md`](MCP_SETUP.md) — bridge + `get_host_status` cold start

**Agent message:** “Connect your IDE agent to amorph via MCP — ask it to call `get_host_status` and walk you through setup.”

## Play / control (not authoring)

Users play the loaded patch in the DAW or via the remote browser UI — no code editing.

## Distribution

- **Download:** https://artistsindsp.gumroad.com/l/amorph (canonical build)
- Discord and community links should point to the same Gumroad build — not parallel insider builds
