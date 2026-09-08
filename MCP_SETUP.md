# Amorph MCP setup

One hub URL serves every open runtime (`Amorph_Instrument` / `Amorph_FX` / `Amorph_MIDI`):

```
http://127.0.0.1:7330/mcp
```

Streamable HTTP, loopback only, no bearer. Amorph **never** writes into another application's config. One **`amorph`** entry — no variant picker.

Per-instance servers on **7331–7399** still exist (hub forwarding + Remote UI + Bearer). They are **not** the user add path. Prefer the hub.

## Prerequisites

1. **Verify compatibility:** Confirm **Settings → Your AI** is visible. That panel appears only when **Outside Amorph** + **Live via MCP**. If missing, the user is on **v0.99** — copy-paste in Build only; do not run MCP or BYOK steps. See [`BUILD_COMPAT.md`](BUILD_COMPAT.md).
2. Install amorph: https://artistsindsp.gumroad.com/l/amorph
3. Open a runtime in the DAW. Display names may use spaces (`Amorph Instrument`); MCP variants are `instrument`, `fx`, `midi`.
4. Keep the plugin window open (minimised is fine). MCP starts with the plugin.

Python is **not** required for Cursor, VS Code, Windsurf, or Claude Code. It is required only for **Claude Desktop** (stdio).

## Connect flow (status-first)

Opening the project folder is **optional** — only for hand-editing `dsp.cmajor` / `index.js`. VS Code has a one-click HTTP install; do not require File → Open Folder.

| Step | What to do | What you should see |
|------|------------|---------------------|
| **1. Open** | Load amorph in your DAW; Settings → **Outside Amorph** → **Live via MCP** | Settings → **Your AI**; badge → **Waiting for your AI** |
| **2. Add once** | **Add to Cursor** or **Add to VS Code**, or copy Other clients (below) | Client lists an `amorph` server at the hub URL |
| **3. Create** | **New blank patch** + save, **or** ask the agent to call `create_project` (`name` optional) | Folder under `Projects/<PatchName>/` (+ hub `.vscode/mcp.json` on save) |
| **4. Work** | Agent calls `get_host_status`, then edits | Badge → **AI connected** on first tool call; **AI working** while a tool runs |

**Step 2 — leftover configs:** if a previous beta wrote `python3 …/mcp_bridge.py` into Cursor / Windsurf / Claude Desktop, replace that entry with the hub HTTP config (or Claude Desktop stdio from Your AI). Do not tell HTTP clients to install the bridge.

**Step 3 — create vs compile-only:**

| Action | Project folder | `.vscode/mcp.json` |
|--------|----------------|--------------------|
| **Save** (named patch) or **`create_project`** | `Projects/<PatchName>/` | Hub HTTP on save / create |
| **Compile only** (unsaved scratch) | May land in `Projects/Scratch/` | **Not** written — save or `create_project` first |

`create_project` may omit `name` — Amorph assigns `New patch`, `New patch (2)`, …

**Step 2 detail — by client:**

| Client | What to do |
|--------|------------|
| **Cursor** | Settings → Your AI → **Add to Cursor** (one-click). Or paste the Cursor JSON below. Folder optional. |
| **VS Code** | Settings → Your AI → **Add to VS Code** (one-click). Folder optional. Saved `.vscode/mcp.json` is hub HTTP. |
| **Claude Code** | `claude mcp add --transport http amorph http://127.0.0.1:7330/mcp` |
| **Windsurf** | Copy the Windsurf / Antigravity JSON from Your AI → Other clients (`serverUrl`). |
| **Claude Desktop** | Copy the Claude Desktop config (stdio + Python). Windows: `py -3` if `python3` is not on PATH. |
| **Hand-editing files (optional)** | Open `Projects/<PatchName>/` to browse `dsp.cmajor` / `index.js`; finish with `reload_from_disk` or `apply_draft`. |

Browser ChatGPT / claude.ai / Gemini are not MCP — use **Share without MCP**.

Machine-readable add doc (plugin running):

```
GET http://127.0.0.1:7330/mcp/setup
```

Prefer that URL over a random instance port. Do not treat per-instance `/mcp/setup` + Bearer as how to connect.

## Client configs (single `amorph` entry)

**Cursor** — `~/.cursor/mcp.json` (or the client's MCP settings):

```json
{
  "mcpServers": {
    "amorph": {
      "url": "http://127.0.0.1:7330/mcp"
    }
  }
}
```

**VS Code** — user MCP settings, or `Projects/<PatchName>/.vscode/mcp.json` (written on save):

```json
{
  "servers": {
    "amorph": {
      "type": "http",
      "url": "http://127.0.0.1:7330/mcp"
    }
  }
}
```

**Windsurf:**

```json
{
  "mcpServers": {
    "amorph": {
      "serverUrl": "http://127.0.0.1:7330/mcp"
    }
  }
}
```

**Claude Code:**

```bash
claude mcp add --transport http amorph http://127.0.0.1:7330/mcp
```

**Claude Desktop only** — `~/Library/Application Support/Claude/claude_desktop_config.json` (stdio; Python required):

```json
{
  "mcpServers": {
    "amorph": {
      "command": "python3",
      "args": ["/Users/YOUR_USER/Library/Presets/Artists_in_DSP/AMORPH/mcp_bridge.py"]
    }
  }
}
```

On Windows Claude Desktop, use `"command": "py"` and `"args": ["-3", "C:\\Users\\YOUR_USER\\AppData\\Roaming\\Artists_in_DSP\\AMORPH\\mcp_bridge.py"]`. Copy the block from Settings → Your AI instead of guessing the path.

If a custom `.vscode/mcp.json` already exists and does not look Amorph-generated, the product leaves it alone.

Project folder roots (variant-scoped):

- macOS: `~/Library/Presets/Artists_in_DSP/AMORPH/{Instruments,FX,MIDI}/Projects/<PatchName>/`
- Windows: `%APPDATA%\Artists_in_DSP\AMORPH\{Instruments,FX,MIDI}\Projects\<PatchName>\`

Legacy `AMORPH/Projects` paths are migration-only. Trust the **Project folder** from `initialize` / `get_host_status`.

## Routing (several plugins open)

The hub routes each call: **pin → focused window → sole instance → newest**. Writes are refused when several plugins are live and none is focused or pinned.

- `list_instances` — ports, variants, patches, focus, hub owner
- `set_active_instance` — pin by `port`, `patch`, or `variant`; or `follow_focus: true` to clear the pin
- Not required when only one instance is open

## Cold start (plugin not open)

- If no instance: only **`get_host_status`** is available; follow its install steps.
- Connection **self-heals** when the user opens the plugin. Call `get_host_status` again after they do.
- HTTP clients talk to the hub URL. Do not configure `python3 mcp_bridge.py` for Cursor / VS Code / Claude Code.

The stdio bridge (`mcp_bridge.py`) is still deployed for Claude Desktop. HTTP clients must not use it.

## Prompts (via MCP)

| Prompt | Content |
|--------|---------|
| `cmajor-rules` | Full Cmajor language reference |
| `tool-guide` | Tool usage patterns |
| `ui-rules` | Patch Web Component UI (`index.js`) |
| `shell-ui-rules` | Product shell UI (AppShellWebView, borderless tonal) — synced from ADSP_UI |

Call `prompts/get` with the prompt name when needed.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| No tools / connection failed | `get_host_status` → open plugin in DAW; confirm Your AI → Add to Cursor / VS Code used the hub URL |
| Client still launches `python3 mcp_bridge.py` | Leftover from an older beta — replace with the hub HTTP entry (or Claude Desktop stdio from Your AI) |
| Looking for Settings → Connections | The panel is **Your AI** (Outside + Live via MCP). Connections is not the v1 surface |
| “Plugin busy” | Internal agent running — wait and retry |
| Edits don’t play | Call `apply_draft` or `reload_from_disk` |
| Wrong patch / wrong instance | `list_instances` → `set_active_instance`, or focus the target plugin window |
| Writes refused (several plugins) | Focus or pin one instance; hub will not guess |
| No project folder / no mcp.json | **Save** the patch or use agent **`create_project`** (`name` optional) |
| `reload_from_disk` fails | Save the patch first so a project folder exists; locked/binary patches cannot be reloaded as editable source |
| `apply_draft` says saved patch was not updated | Call `apply_draft` again to retry canonical `.amorph` sync; do not replace the MCP apply flow with `reload_from_disk` |
| `apply_draft` returns unexpected `NO DRAFT` | Call `get_draft_state` and inspect working-copy / snapshot state before retrying |
| Offline edit missing after DAW reopen | Load the saved amorph patch/project by name; reopening a DAW session may restore its embedded copy instead of offline file edits |

Finish line: `task_complete` → `apply_draft` → `get_error` none. See [`TOOLS.md`](TOOLS.md) for the tool list.
