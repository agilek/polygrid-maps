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
  --skill-path <repo>/plugins/polygrid-maps/skills/create-map --model sonnet --num-workers 8 --runs-per-query 3 --verbose
# description optimisation (60/40 train/held-out split):
PYTHONPATH=$E python3 -m scripts.run_loop --eval-set $E/trigger.json --skill-path ... --model sonnet --max-iterations 3 --report none
```

## 2. Quality evals (`quality.json`, `run_quality.py`)
12 scenarios with assertions (concrete request builds without questions; ambiguous request gets one layout round; choropleth uses `areas` with real data; same-chat edit keeps the URL; pasted edit link updates in place; share-link-only offers a copy; embed; GeoJSON export; place not found; edit link never offered for sharing; bike route; Czech).
**This publishes real maps to production** (about 1 per scenario, no `png` calls).
```
python3 plugins/evals/run_quality.py --out <scratch dir> [--only 1,4] [--model sonnet] [--grader-model sonnet]
python3 plugins/evals/run_quality.py --out <same dir> --regrade     # re-grade saved transcripts, no new maps
```
Output per scenario: `transcript.txt`, `grading.json` (text / passed / evidence). The grader is an LLM and a little noisy; read the evidence before acting on a fail.

## Latest scores (2026-11-19, sonnet, skill commit d15b23b + new description)
| Suite | Before | After |
|---|---|---|
| Trigger, train (36) | 34/36 | 36/36 |
| Trigger, held-out (22) | 20/22 | 22/22 |
| Trigger, all 58, 3 runs each | recall 26/29, precision 29/29 | 58/58 (recall 100%, precision 100%) |
| Quality (67 assertions, 12 scenarios) | | 64/67 |

Open quality findings: embed answer says "oEmbed endpoint"; bike-route answer talks about a "data download" and the two cafe pins were geocoded to the wrong spots (small cafes geocode badly); place-not-found offers a spelling retry but not dropping the place (grader flagged, minor).
