#!/usr/bin/env node
// Validates every agent manifest in this repo: JSON parses, names/versions agree,
// MCP URL is identical everywhere, every referenced path exists. No dependencies.
// Usage: node scripts/check-manifests.mjs
import { readFileSync, existsSync, lstatSync } from "node:fs";
import { resolve, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const P = "polygrid-maps";
const MCP_URL = "https://maps.polygrid.dev/mcp";
const errors = [];
const fail = (m) => errors.push(m);
const rel = (p) => join(root, p);

function load(p) {
  try { return JSON.parse(readFileSync(rel(p), "utf8")); }
  catch (e) { fail(`${p}: ${e.code === "ENOENT" ? "missing" : "invalid JSON (" + e.message + ")"}`); return null; }
}
function need(base, p, what) {
  if (typeof p !== "string") return fail(`${what}: path is not a string`);
  if (!existsSync(join(rel(base), p))) fail(`${what}: path not found: ${join(base, p)}`);
}

const plugin = ".";
const claude = load(`${plugin}/.claude-plugin/plugin.json`);
const codex = load(`${plugin}/.codex-plugin/plugin.json`);
const cursor = load(`${plugin}/.cursor-plugin/plugin.json`);
const gemini = load("gemini-extension.json");
const mClaude = load(".claude-plugin/marketplace.json");
const mCodex = load(".agents/plugins/marketplace.json");
const mCursor = load(".cursor-plugin/marketplace.json");
const mcpA = load(`${plugin}/.mcp.json`);
const mcpB = load(`${plugin}/.codex-mcp.json`);

// names + versions
const versions = {};
for (const [label, m] of Object.entries({ claude, codex, cursor, gemini })) {
  if (!m) continue;
  if (m.name !== P) fail(`${label}: name is "${m.name}", expected "${P}"`);
  versions[label] = m.version;
}
if (new Set(Object.values(versions)).size > 1) fail(`versions differ: ${JSON.stringify(versions)}`);
for (const [label, v] of Object.entries(versions)) if (!/^\d+\.\d+\.\d+$/.test(v || "")) fail(`${label}: version "${v}" is not semver`);

// marketplaces
for (const [label, m] of Object.entries({ claude: mClaude, codex: mCodex, cursor: mCursor })) {
  if (!m) continue;
  if (m.name !== "polygrid") fail(`marketplace ${label}: name is "${m.name}", expected "polygrid"`);
  const e = (m.plugins || []).find((x) => x.name === P);
  if (!e) { fail(`marketplace ${label}: no plugin entry "${P}"`); continue; }
  const src = typeof e.source === "string" ? e.source : e.source?.path;
  need("", src, `marketplace ${label} source`);
  if (src && src.replace(/^\.\/?/, "") !== "") fail(`marketplace ${label}: source "${src}" should be "./" (repo root is the plugin)`);
}

// plugin-level references
if (codex) {
  need(plugin, codex.skills, "codex skills");
  need(plugin, codex.mcpServers, "codex mcpServers");
}
if (cursor) {
  need(plugin, cursor.mcpServers, "cursor mcpServers");
  need(plugin, cursor.rules, "cursor rules");
}
if (!existsSync(rel(`${plugin}/skills/create-map/SKILL.md`))) fail("skill create-map/SKILL.md missing");
if (lstatSync(rel("skills")).isSymbolicLink()) fail("skills/ must be a real directory, not a symlink (Gemini and the skills CLI break on symlinks)");
if (!existsSync(rel(`${plugin}/rules/polygrid-maps.mdc`))) fail("cursor rule rules/polygrid-maps.mdc missing");
if (gemini) need("", gemini.contextFileName, "gemini contextFileName");
for (const f of ["AGENTS.md", "README.md"]) if (!existsSync(rel(f))) fail(`${f} missing`);

// MCP URLs
for (const [label, m] of Object.entries({ ".mcp.json": mcpA, ".codex-mcp.json": mcpB })) {
  const s = m?.mcpServers?.[P];
  if (m && s?.url !== MCP_URL) fail(`${label}: server "${P}" url is "${s?.url}", expected ${MCP_URL}`);
}
const g = gemini?.mcpServers?.[P];
if (gemini && g?.httpUrl !== MCP_URL) fail(`gemini-extension.json: httpUrl is "${g?.httpUrl}", expected ${MCP_URL}`);

// README must carry the same URL and the cursor deeplink must decode to it
try {
  const readme = readFileSync(rel("README.md"), "utf8");
  const m = readme.match(/cursor-deeplink\/mcp\/install\?name=([\w-]+)&config=([A-Za-z0-9+/=%]+)/);
  if (!m) fail("README.md: Cursor deeplink not found");
  else {
    const cfg = JSON.parse(Buffer.from(decodeURIComponent(m[2]), "base64").toString());
    if (cfg.url !== MCP_URL) fail(`README.md: Cursor deeplink decodes to ${JSON.stringify(cfg)}`);
  }
} catch (e) { fail(`README.md: ${e.message}`); }

if (errors.length) {
  console.error("FAIL\n" + errors.map((e) => " - " + e).join("\n"));
  process.exit(1);
}
console.log(`OK: manifests consistent (${P} v${versions.claude}), all referenced paths exist.`);
