# Amorph MCP setup

Each amorph runtime (`Amorph_Instrument` / `Amorph_FX` / `Amorph_MIDI`) exposes MCP over a local HTTP server (ports **7331–7399**) plus a **stdio bridge** (v5+) for IDE clients. One **`amorph`** MCP entry serves every open instance — no variant picker, no per-variant server list.

## Prerequisites

1. **Verify compatibility:** Confirm **Settings → Connections** exists in the plugin. **v0.99 (Gumroad)** has no MCP or BYOK. **v1 beta** adds MCP, BYOK, and share-via-link (unlisted — not Explore catalog listing). See [`BUILD_COMPAT.md`](BUILD_COMPAT.md). Preview: Discord `#announcements`.
2. Install amorph: https://artistsindsp.gumroad.com/l/amorph  
3. Open an amorph runtime in your DAW (instrument, fx, or midi variant). In the DAW,
   the plugins may appear as `Amorph Instrument`, `Amorph FX`, and `Amorph MIDI` (spaces) or `Amorph_Instrument`, `Amorph_FX`, `Amorph_MIDI` (underscores in MCP/docs).
4. Python 3 on PATH (bridge script — zero extra dependencies).

## Connect flow (status-first)

Primary onboarding path (matches Settings → Connections). **Opening the project folder is not required on Cursor / Claude Desktop / Windsurf** — only on VS Code (and optional on Cursor for hand-editing files).

| Step | What to do | What you should see |
|------|------------|---------------------|
| **1. Open** | Load amorph in your DAW | Settings → **Connections** shows MCP status; header badge → **Not connected** |
| **2. Create** | **New blank patch** + save in Amorph, **or** ask your agent to call `create_project` | Named folder under `Projects/<PresetName>/` (+ `.vscode/mcp.json` on save) |
| **3. Connect** | See **by client** below | Badge → **Editor connected** on first MCP tool call |

**Step 1 detail:** Opening the plugin starts the MCP HTTP server and deploys bridge v5. On load, amorph **auto-registers** a single `amorph` entry in **Cursor**, **Claude Desktop**, and **Windsurf** (if those apps are installed). No manual JSON paste required for those clients.

**Step 2 detail — create vs compile-only:**

| Action | Project folder | `.vscode/mcp.json` |
|--------|----------------|--------------------|
| **Save** (named preset) or **`create_project`** | `Projects/<PresetName>/` | Written on save / create |
| **Compile only** (unsaved scratch) | May land in `Projects/Scratch/` | **Not** written — name or `create_project` first |

**Step 3 detail — by client:**

| Client | What to do |
|--------|------------|
| **Cursor / Claude Desktop / Windsurf** | Chat from **any** workspace (auto-registered). Reload MCP servers once if the client was already open before Amorph. |
| **VS Code** | **File → Open Folder…** → `Projects/<PresetName>/`. The saved `.vscode/mcp.json` wires MCP from that window. |
| **Hand-editing files (optional)** | Open `Projects/<PresetName>/` in Cursor or VS Code to browse/edit `dsp.cmajor` / `index.js` in the file tree; finish with `reload_from_disk` or `apply_draft`. |

Check the header badge or Settings → Connections: **Editor connected** means your MCP client recently ran a tool — not merely that you opened a folder.

**Copy setup** (below) is troubleshooting only when auto-register failed.

## Bridge location (auto-deployed)

```
~/Library/Presets/Artists_in_DSP/AMORPH/mcp_bridge.py        # macOS
%APPDATA%\Artists_in_DSP\AMORPH\mcp_bridge.py                # Windows
```

The runtime deploys/updates this on load (**bridge v5**). On Windows, use the expanded `%APPDATA%` path in any manual config.

Registry (running instances):

```
~/Library/Presets/Artists_in_DSP/AMORPH/mcp_registry/<port>.json   # macOS
%APPDATA%\Artists_in_DSP\AMORPH\mcp_registry\<port>.json           # Windows
```

Each file: `port`, `token`, `variant`, `patch_name`, `pid`, `focused_at`.

## Universal MCP config (single `amorph` entry)

Bridge v5 routes every tool call dynamically (CLI filter → session pin → focused window → sole instance → newest). One unfiltered entry is all most users need.

**Claude Desktop** — `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

**VS Code / Cursor workspace** — save as `<workspace-root>/.vscode/mcp.json`:

```json
{
  "servers": {
    "amorph": {
      "command": "python3",
      "args": ["/Users/YOUR_USER/Library/Presets/Artists_in_DSP/AMORPH/mcp_bridge.py"]
    }
  }
}
```

**Claude Code CLI:**

```bash
claude mcp add amorph python3 ~/Library/Presets/Artists_in_DSP/AMORPH/mcp_bridge.py
```

On preset **save**, amorph auto-writes `.vscode/mcp.json` into `Projects/<PresetName>/` (variant + patch pinned for that workspace). Prefer opening that folder over hand-editing config.

Project folder roots (variant-scoped):

- macOS: `~/Library/Presets/Artists_in_DSP/AMORPH/{Instruments,FX,MIDI}/Projects/<PresetName>/`
- Windows: `%APPDATA%\Artists_in_DSP\AMORPH\{Instruments,FX,MIDI}\Projects\<PresetName>\`

Legacy `AMORPH/Projects` paths are migration-only. Trust the **Project folder** reported by MCP `initialize` / `get_host_status` for the connected patch.

If a custom `.vscode/mcp.json` already exists and does not look Amorph-generated, the product leaves it alone.

### Multiple open instances

When several amorph plugins run at once, the bridge picks the **focused** window (or the sole/newest instance). Agents can inspect or pin explicitly:

- `list_instances` — ports, variants, patches, focus state
- `set_active_instance` — pin by `port`, `patch`, or `variant`; or `follow_focus: true` to clear the pin

Optional CLI filters for power users (not needed in normal setup): `--variant fx`, `--patch "My Patch"`, `--port 7331`.

## Copy setup (troubleshooting fallback only)

Use **Settings → Connections → Troubleshooting → Copy setup** only when auto-register failed or a client needs manual repair.

1. Pick target (Cursor / VS Code / Claude Desktop / Claude Code / Windsurf).
2. Copy setup — one `amorph` entry, no variant picker.
3. Paste into that client's MCP config file (not chat), or run the CLI command for Claude Code.

Some MCP clients pass JSON args directly and do **not** expand `~` or `%APPDATA%` — use the absolute bridge path from `/mcp/setup` or Connections.

Windows example (replace `YOUR_USER`; if `python3` is not on PATH, use the Python launcher that works on that machine):

```json
{
  "servers": {
    "amorph": {
      "command": "python3",
      "args": ["C:\\Users\\YOUR_USER\\AppData\\Roaming\\Artists_in_DSP\\AMORPH\\mcp_bridge.py"]
    }
  }
}
```

## Cold start (plugin not open)

- Bridge probes ~2s on connect (`AMORPH_MCP_INIT_WAIT_SECONDS`).
- If no instance: only **`get_host_status`** is available; follow its install steps.
- Connection **self-heals** when the user opens the plugin. Reconnecting/reloading MCP is optional; calling `get_host_status` verifies readiness, and forwarded tool calls rediscover the plugin after it opens.

Environment variables:

- `AMORPH_INSTALL_URL` overrides cold-start install guidance. The bridge default may point
  to the website; the public download link is https://artistsindsp.gumroad.com/l/amorph.
- `AMORPH_MCP_INIT_WAIT_SECONDS` controls the short initialize probe.
- `AMORPH_MCP_WAIT_SECONDS` controls the longer rediscovery wait for forwarded tool calls.

Standalone/testing builds may identify themselves as `AmorphServer`; user-facing DAW
workflows should still open one of the amorph runtime plugins.

## Setup JSON (browser)

With plugin running:

```
GET http://localhost:<port>/mcp/setup
```

Returns connection info + ready-to-paste configs (single `amorph` entry). No auth on GET.

This endpoint returns the actual expanded bridge path, registry file, variant, patch
name, client configs, and lifecycle guidance for the running instance. Prefer it over
guessing paths by hand.

Direct HTTP clients (not using the stdio bridge) must read the registry file and send
`Authorization: Bearer <token>` on POST `/mcp`. The stdio bridge handles this token
automatically.

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
| No tools / connection failed | `get_host_status` → open plugin in DAW |
| “Plugin busy” | Internal agent running — wait and retry |
| Edits don’t play | Call `apply_draft` or `reload_from_disk` |
| Wrong patch / wrong instance | `list_instances` → `set_active_instance`, or focus the target plugin window |
| No project folder / no mcp.json | **Save** the preset or use agent **`create_project`** (compile-only scratch may be `Scratch/` without mcp.json) |
| Auto-register missing | Reload MCP in the client; if still missing, use **Copy setup** (fallback) |
| `reload_from_disk` fails | Save the preset first so a project folder exists; locked/binary patches cannot be reloaded as editable source |
| Offline edit missing after DAW reopen | Load the saved amorph preset/project by name; reopening a DAW session may restore its embedded copy instead of offline file edits |

See [`TOOLS.md`](TOOLS.md) for the full tool list.
