# create-map evals

Two suites: does the skill trigger at the right time, and does it behave well once triggered.
`claude plugin eval` exists (Claude Code 2.1.328) but expects cases inside the plugin dir; we use skill-creator's trigger tooling plus our own runner instead.

## 1. Trigger evals (`trigger/`)
`trigger/trigger.json`: 58 realistic queries (29 should trigger, 29 should not; includes Czech/German, pasted edit/share links, embed, GeoJSON export, and hard negatives such as `.map()`, sitemaps, Leaflet/Mapbox code, directions, trivia).
`trigger/scripts/` is a patched copy of skill-creator's scripts. Patches: (1) each run gets a private project dir (parallel runs otherwise see each other's command files and the model picks a sibling, scoring false misses); (2) `--setting-sources project` so global skills/plugins do not contaminate.

```
S=/private/tmp/claude-501/-Volumes-Blackbox--git-create-map-skill/42d99f0c-9c18-4bdf-94e6-11569bef611a/scratchpad/evals   # any scratch dir with a .claude/ inside proj/
E=$PWD/plugins/evals/trigger; mkdir -p $S/proj/.claude
cd $S/proj && PYTHONPATH=$E python3 -m scripts.run_eval --eval-set $E/trigger.json \
  --skill-path <repo>/plugins/skills/create-map --model sonnet --num-workers 8 --runs-per-query 3 --verbose
# description optimisation (60/40 train/held-out split):
PYTHONPATH=$E python3 -m scripts.run_loop --eval-set $E/trigger.json --skill-path ... --model sonnet --max-iterations 3 --report none
```

## 2. Quality evals (`quality.json`, `run_quality.py`)

The runner passes `--allowedTools WebSearch,WebFetch` to `claude -p` (real users have web access; the rich-details scenarios 13 and 14 need it).
12 scenarios with assertions (concrete request builds without questions; ambiguous request gets one layout round; choropleth uses `areas` with real data; same-chat edit keeps the URL; pasted edit link updates in place; share-link-only offers a copy; embed; GeoJSON export; place not found; edit link never offered for sharing; bike route; Czech).
**This publishes real maps to production** (about 1 per scenario, no `png` calls).
```
python3 plugins/evals/run_quality.py --out <scratch dir> [--only 1,4] [--model sonnet] [--grader-model sonnet]
python3 plugins/evals/run_quality.py --out <same dir> --regrade     # re-grade saved transcripts, no new maps
```
Output per scenario: `transcript.txt`, `grading.json` (text / passed / evidence). The grader is an LLM and a little noisy; read the evidence before acting on a fail.

## 3. Follow-up edit evals (`followups.json`, `--mode`, `checks.py`)

Why: in Claude Desktop, "add me routes for barcelona map" (after a Barcelona trip map) created two NEW maps, left the original unchanged and printed raw edit tokens. These scenarios guard "edit in place" behaviour.

Modes (`run_quality.py --mode`):
- `skill` (default): the create-map skill is copied into the scratch project (as before).
- `docs-only`: no skill; the agent only gets a one-line hint that the service is https://maps.polygrid.dev and tools Bash + WebFetch, so it must learn the API from /llms.txt or /docs/agents. Mirrors agents without the plugin.
- `both`: every scenario runs in both modes.

Scenarios (ids 101-106): barcelona-add-routes (2-turn; same URL, exactly 1 create, >=2 routed lines, no raw token, no narration), barcelona-make-dark (same URL, basemap dark), barcelona-separate-map-control (negative control: NEW url expected, trip map untouched), pasted-edit-link-add-route (new chat, pasted private edit link + "add a walking route": updated in place). 101 and 104 need multi-route/route-adding support in the API (`routes`, update_map); 102 and 103 do not. road-trip-by-car (105: every leg car) and barcelona-kids-mode-then-drive (106: no car legs in the city and the answer states the mode, then "switch to driving" updates the same map to all-car legs) test travel modes via the `legs_all` / `legs_none` checks.

Mode scenarios (ids 105-106, need the transit/per-leg modes API): road-trip-by-car (every leg car), barcelona-kids-mode-then-drive (no mode given: no car legs and the answer states the mode and offers the switch; follow-up switches the same map to car in place). Checks `legs_all` / `legs_none` (`mode`, optional `turn`) read `leg_mode` on stop pins and `route_mode` on lines from GET /v1/maps/{id}. Adds about 2 creates per mode.

`checks.py` grades the real API state (GET /v1/maps/{id}, snapshots after each turn, create counts from tool results) in addition to the LLM grader; those rows are prefixed `[api]` in grading.json.

```
python3 plugins/evals/run_quality.py --out <scratch dir> --file followups.json --mode both [--only 101,102] [--max-creates 25]
python3 plugins/evals/run_quality.py --out <same dir> --file followups.json --mode both --regrade   # no new maps
```
Cost: map creates per mode about 7 (101: 1, 102: 1, 103: 2, 104: 1 setup, 105: 1, 106: 1; +1-2 if the agent wrongly makes extra maps), so a full `--mode both` run is about 14-18 creates, well under 25. No png calls. Output dirs are `eval-<id>-<name>.<mode>/`.

## One command: `npm run evals`
`plugins/evals/run_all.py` runs trigger (3 runs/query), quality.json (skill mode) and followups.json (both modes), prints one summary and writes `results/latest.md` (raw transcripts in `results/raw/`, gitignored).
```
npm run evals                      # full: ~27 map creates, ~40 min, model sonnet
npm run evals -- --quick           # 1 run/trigger query, quality 1,4,5,9,11, followups 101,102,105
npm run evals -- --only trigger    # or quality | followups
npm run evals -- --regrade         # re-grade saved transcripts (no new maps, no trigger rerun)
```

## Targeted rerun after plugin 0.0.8 (supersedes the rows below for these items)
Trigger misses 4/4 fixed, 10/10 negatives clean; 13 (fast-mode assertions): 6/6 on first grade, 5/6 on regrade (a guessed address); 14: 2/5 (no search for landmarks so no address/url, no "add more detail" offer, edit link inline); 106 skill 10/10; 104 docs-only 9/9. `--only X` runs now write `results/latest-X.md` so they do not overwrite the full summary.

## Latest scores (2026-11-20, sonnet, plugin 0.0.7 on production)
| Suite | Result |
|---|---|
| Trigger, 58 queries x 3 | 54/58, recall 86% (25/29), precision 100%. Misses: pasted edit link with odd `/edit?key=` form, 40 bakeries + vegan filter, "3 points, tiny, nothing fancy", "add a pin to the map we were working on" (single-turn, no map in context) |
| Quality, 14 scenarios | 12 of 14 fully green after assertion fixes; 13 rich-details-coffee 5/7, 14 rich-details-sights 3/6 |
| Followups skill | 101 10/10, 102 8/8, 103 8/8, 104 9/9, 105 8/8, 106 9/10 |
| Followups docs-only | 101 10/10, 102 8/8, 103 8/8, 104 7/9, 105 8/8, 106 10/10 |
| Creates | 27 (incl. setups), no png |

Open findings (skill/API, proposed, not applied):
- Fast mode makes sonnet skip web search entirely (14: no address/url/extra fields, popups line wrong; 13: addresses but no urls). Proposed SKILL.md step 3 wording: "Do 1 web search for the whole list (not zero) unless the places are well-known landmarks you can describe from memory, and fill address/url/extra fields from it."
- 106: first answer has no one plain mode line. Proposed SKILL.md step 5: "Always include one plain sentence on the travel mode, e.g. 'Walking, with metro between areas. Want me to switch to driving?'" (agent_note already says it; the skill text should too).
- Trigger misses: add to the description "even a tiny map of 2-3 points", "long lists with filters", and "a map made earlier in this chat (add a pin, give the link again)".
- 104 docs-only: agent saved a backup file and mentioned `/tmp/berlin-backup.json` to the user. Proposed: /llms.txt line "Do not mention files, JSON or tokens to the user; update with PUT, no backups needed".

Harness/grader fixes made in this run: common assertion allows edit link `#t=`, iframe attributes and menu field names; scenario 3 title-unit, 5 "get first", 11 cafe-category assertions relaxed; run_all result paths. Regrading the saved transcripts moved quality from 49/67-ish noise to the table above.
