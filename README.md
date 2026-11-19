# Polygrid Maps for AI agents

Turn "make a map of..." into a live, shareable, editable web map link. No account, no API key. Powered by [maps.polygrid.dev](https://maps.polygrid.dev).

You get two things, in whichever form your agent supports:

- **MCP server** `https://maps.polygrid.dev/mcp` (streamable HTTP, no auth) with the `create_map` tool (and `get_map`, `update_map`).
- **`create-map` skill** (SKILL.md plus a small Python stdlib script): the full workflow for layouts, geocoding, routes, categories and edits.

Example prompts: "Make a map of the best coffee in Lisbon for my friends." / "Pin these 5 addresses and draw the walking route." / "Trip map: 4 days in Tokyo, one color per day." / "Make it dark."

## Claude Code

```
claude plugin marketplace add polygrid/plugins
claude plugin install polygrid-maps@polygrid
```

Installs the skill and registers the MCP server. MCP only: `claude mcp add --transport http polygrid-maps https://maps.polygrid.dev/mcp`

## Codex

```
codex plugin marketplace add polygrid/plugins
codex plugin add polygrid-maps@polygrid
```

Installs the skill and the MCP server. MCP only, either run `codex mcp add polygrid-maps --url https://maps.polygrid.dev/mcp` or add to `~/.codex/config.toml`:

```toml
[mcp_servers.polygrid-maps]
url = "https://maps.polygrid.dev/mcp"
```

## Cursor

One click: [Add to Cursor](cursor://anysphere.cursor-deeplink/mcp/install?name=polygrid-maps&config=eyJ1cmwiOiJodHRwczovL21hcHMucG9seWdyaWQuZGV2L21jcCJ9)

```
cursor://anysphere.cursor-deeplink/mcp/install?name=polygrid-maps&config=eyJ1cmwiOiJodHRwczovL21hcHMucG9seWdyaWQuZGV2L21jcCJ9
```

Plugin (MCP server plus an agent rule): `npx -y plugins add polygrid/plugins -t cursor -y`

Manual, in `~/.cursor/mcp.json` (or `.cursor/mcp.json` in a project):

```json
{ "mcpServers": { "polygrid-maps": { "url": "https://maps.polygrid.dev/mcp" } } }
```

## Claude Desktop and claude.ai

- **Connector (recommended):** Settings > Connectors > Add custom connector, name `Polygrid Maps`, URL `https://maps.polygrid.dev/mcp`. No sign-in needed.
- **Skill:** download [create-map.zip](https://maps.polygrid.dev/create-map.zip), then Settings > Capabilities > Skills > Upload. For real share links, allow network access to `maps.polygrid.dev` under Settings > Capabilities > Code execution.

## Gemini CLI

```
gemini extensions install https://github.com/polygrid/plugins
```

Installs the MCP server, the skill and a context file. MCP only: `gemini mcp add --transport http polygrid-maps https://maps.polygrid.dev/mcp`

## VS Code / GitHub Copilot

Command Palette > `MCP: Open User Configuration` (or `.vscode/mcp.json` in a workspace), then add:

```json
{ "servers": { "polygrid-maps": { "type": "http", "url": "https://maps.polygrid.dev/mcp" } } }
```

Copilot's portable `.mcp.json` (workspace root) and `~/.copilot/mcp-config.json` use `mcpServers` instead of `servers`:

```json
{ "mcpServers": { "polygrid-maps": { "type": "http", "url": "https://maps.polygrid.dev/mcp" } } }
```

## Any MCP client

Remote URL, streamable HTTP, no authentication: `https://maps.polygrid.dev/mcp`. Per client:

| Client | File | Snippet |
| --- | --- | --- |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` | `{ "mcpServers": { "polygrid-maps": { "serverUrl": "https://maps.polygrid.dev/mcp" } } }` |
| Zed | `settings.json` | `{ "context_servers": { "polygrid-maps": { "url": "https://maps.polygrid.dev/mcp" } } }` |
| OpenCode | `opencode.json` | `{ "mcp": { "servers": { "polygrid-maps": { "type": "remote", "url": "https://maps.polygrid.dev/mcp" } } } }` |
| Cline | `cline_mcp_settings.json` | `{ "mcpServers": { "polygrid-maps": { "type": "streamableHttp", "url": "https://maps.polygrid.dev/mcp" } } }` |
| Generic JSON | `mcp.json` | `{ "mcpServers": { "polygrid-maps": { "type": "http", "url": "https://maps.polygrid.dev/mcp" } } }` |

Clients that only speak stdio can bridge with `npx -y mcp-remote https://maps.polygrid.dev/mcp`.

## Skill only (any agent)

```
npx -y skills add polygrid/plugins --skill create-map
```

Works with the [`skills`](https://github.com/vercel-labs/skills) CLI for Claude Code, Codex, Cursor, Gemini CLI, OpenCode and many more. Agents that read `AGENTS.md` find a short pointer in [AGENTS.md](AGENTS.md).

## Layout

```
.claude-plugin/marketplace.json     Claude Code marketplace "polygrid"
.agents/plugins/marketplace.json    Codex marketplace
.cursor-plugin/marketplace.json     Cursor marketplace
gemini-extension.json, GEMINI.md    Gemini CLI extension (root of the repo)
AGENTS.md                           generic agent context
skills -> polygrid-maps/skills      symlink for Gemini and the skills CLI
polygrid-maps/                      the plugin: .claude-plugin, .codex-plugin, .cursor-plugin,
                                    .mcp.json, .codex-mcp.json, rules/, skills/create-map
scripts/check-manifests.mjs         consistency check
evals/                              trigger evals
```

## Development

- `node scripts/check-manifests.mjs` checks that all manifests parse, name and version agree, and every referenced path exists. Bump the version in all four manifests together (`polygrid-maps/.claude-plugin`, `.codex-plugin`, `.cursor-plugin`, `gemini-extension.json`).
- `claude plugin validate polygrid-maps && claude plugin validate .`
- `python3 polygrid-maps/skills/create-map/scripts/publish.py --selftest` runs the skill's offline checks.
