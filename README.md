# create-map

A Claude skill that turns "make a map of..." into a live link you can share with friends and change later, by chatting or in a visual editor. No account, no API key. Powered by [maps.polygrid.dev](https://maps.polygrid.dev).

<!-- HERO GIF: docs/hero.gif -->

## What it does
- Looks at your places, suggests 2-3 layouts (categories with filter legend, numbered itinerary, day by day, clustered, shaded areas, ...), then builds the map.
- Gives you a share link (with a preview picture when pasted into chat apps) and a private edit link.
- Edit later in the same chat ("make it dark"), in a new chat (paste the edit link), or in the browser.
- Maps stay online for 30 days after the last view.

## Install

**claude.ai:** zip the `skills/create-map` folder (`cd skills && zip -r create-map.zip create-map`), then Settings > Capabilities > Skills > Upload. For real share links, enable network access for `maps.polygrid.dev` under Settings > Capabilities > Code execution. Without it the skill gives a link that opens the map ready to publish with one click.

**Claude Code:**
```
cp -r skills/create-map ~/.claude/skills/create-map
```
or as a plugin: `/plugin marketplace add <this-repo>` then `/plugin install create-map@create-map-skill`.

## Example prompts
- "Make a map of the best coffee in Lisbon for my friends."
- "Pin these 5 addresses and draw the walking route between them."
- "Trip map: 4 days in Tokyo, one color per day."
- "Plot our wedding venues and hotels so guests can find them."
- Later: "Make it dark" / "Add restaurants near day 2."

## Development
`python3 skills/create-map/scripts/publish.py --selftest` runs the offline checks. Trigger evals live in `evals/evals.json`.
