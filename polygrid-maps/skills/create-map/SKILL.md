---
name: create-map
description: Creates a shareable web map with a live link from places the user names, such as addresses, landmarks, restaurants, a trip itinerary, a route or areas. Also makes choropleth data maps ("map of X by district/region/country") from real numbers per administrative area. Use whenever someone asks to "make a map of", "pin these places", "plot these addresses", "put these on a map", "show me where these are", build a "trip map" or itinerary map, map recommendations, or "share a map with friends", and also to change a map made earlier. Handles geocoding, routes, categories with a filter legend, links and photos in popups. Do NOT use for charts or graphs, mind maps or diagrams, sitemaps, code or architecture maps, or driving directions the user only wants to read.
---

# create-map

Turn a plain-language request into a live, shareable map link that can be edited later. The user is usually not technical: never show JSON, field names, tokens, or API words. Talk about places, pins, colors, links.

API: `https://maps.polygrid.dev` (no key needed). Everything goes through `scripts/publish.py`. Field details are in the API docs at `https://maps.polygrid.dev/llms.txt` (fetch if you need a field not listed here); layout recipes are in `references/layouts.md`.

## Flow

### 1. Understand
Work out the places, the purpose (trip, event, recommendations, moving, run route, ...) and the audience (just me, friends, public). If the request is already concrete ("pin these 5 addresses"), skip to step 3 and pick the layout yourself.

### 2. Profile the data, then offer layouts
Before asking anything, size up the data: how many places; one kind or mixed; any order or sequence (itinerary, days, race course); how spread out (one street, a city, a country); geometry (points, routes, areas); shared attributes (type, day, price, rating).

Ask ONE round of questions, layout first:
- **Layout question (always):** offer the 2-3 layouts from `references/layouts.md` that fit this data, best fit first, each with a one-line reason. In Claude Code use AskUserQuestion with the ASCII mockup from layouts.md in each option's `preview`. In claude.ai use whatever clickable option UI is available; otherwise a short numbered list with the mockups.
- **Up to 2 more questions in the same round**, each with a smart default and a "skip" option: which places (when the user wants suggestions, propose a researched list and ask them to confirm it), travel mode (car / bike / on foot) when there is a route, look (light / streets / dark).
- If the user has no places yet, research real ones first (web search if available), then ask.

### 3. Build the map
Write the body to a file (e.g. `map-body.json` in a temp or scratch folder, not the user's project). Use named `places` (geocoded for you) in preference to guessed coordinates; add city and country to each name. If you do use coordinates, they are `[longitude, latitude]`.
- Every place gets: `title`, a one-line `description` saying why it is on the map, a `category` (when there are several kinds), an emoji `marker-symbol` matching the category, and `url` / `image` (https only) when you actually know a good link or photo. Never invent URLs.
- Set a `title` that says what and where ("Best coffee in Lisbon"), and a one-sentence `description`.
- Do not set `"image"`: the share link gets its own preview picture when it is pasted into a chat app, and preview renders are limited.
- Set `legend_title` when categories are days or tiers (see layouts.md).

Good-map rules (apply silently, do not lecture):
- At most 7 categories; merge the rest into "Other". At most 50 places per map; split bigger lists by category or area.
- Colors carry meaning (green parks, red food, blue water/transport); never two near-identical colors.
- One emoji per category, used consistently.
- Fit the view to everything. If one place is far from the rest (probably a wrong match), drop it and say so.
- Prefer the simplest layout that answers the user's purpose.

### 4. Publish
```
python3 scripts/publish.py body.json
```
It prints the API result. Keep from it: `url`, `edit_token`, `edit_url`, `id`, `warnings`, `route`.
- If it prints a `fallback_url` instead (sandbox cannot reach the API), tell the user: "I can't publish from here, but this link opens your map ready to go. Click it, check it, then press **Publish map**." Show the link prominently. After publishing, that page shows their share link and their private edit link; ask them to paste the edit link back here if they want you to change the map later. Suggest enabling network access for maps.polygrid.dev (Settings > Capabilities > Code execution) to get real share links next time.
- If it exits with an API error, read its `hint`, fix the body, retry once. If a place could not be found, ask for another spelling or drop it.

### 5. Answer visually and briefly
In this order:
1. The share link, large and on its own line: `## [Open your map](URL)`.
2. One line: when they paste the link into WhatsApp, iMessage or Slack, it shows a preview picture of the map.
3. One-line summary ("14 places in 3 categories, walking route 4.2 km"). Then warnings in plain words ("I couldn't find *Cafe X*, want me to try another spelling?"). If a route fell back to straight lines, say it is not a road route.
4. The private edit link, labeled: "Your private edit link (keep this, it lets you change the map in the browser or ask me to change it later): EDIT_URL". Keep it separate from the share link and never tell the user to send it to friends.
5. Three suggested tweaks tailored to this map (e.g. "add restaurants nearby", "make it dark", "draw the walking route"). Say that the map stays online for 30 days after its last view.

### 6. Modify
- **Same chat:** keep the last body and the token. Apply the change, then `python3 scripts/publish.py body.json --id ID --token TOKEN`. The share link does not change; re-show the (same) link and say the change is live for everyone who has it.
- **New chat:** the user pastes the edit link `https://maps.polygrid.dev/m/{id}/edit#t={token}`. Take `id` from the path and `token` after `#t=`. Run `python3 scripts/publish.py --get ID` to load the current map, change it, then PUT as above. If they paste only the share link, there is no token: offer to make a fresh copy (new link).
- **In the browser:** the edit link opens a simple editor for small changes: map title and description, category names, colors and icons, and each place's text, link, photo, icon and color, or removing a place. The layout, map style, routes and the places themselves stay as they are there, so for adding places or changing the layout they ask you.
- If the PUT returns 403, the token is wrong or from a different map; ask for the right edit link. If 404, the map expired; offer to recreate it from the saved body.

## Data maps of areas
For "map of X by district / region / country" with a number per admin area, use `areas` instead of inventing polygons or hunting for GeoJSON: the API draws the real boundaries from a name, you only supply numbers.
```json
{"areas": {"within": "Czechia"}, "color_by": "population", "palette": "viridis", "legend_title": "Population"}
{"areas": {"within": "Berlin", "values": {"Mitte": 12.1, "Pankow": 8.4, "Neukölln": 15.3}}, "title": "Unemployment by district (%)", "legend_title": "%"}
```
Rules:
- `within` is an area name ("Berlin", "Praha, Czechia") or a Wherebox id; `level` is "auto" by default (Berlin gives its 12 districts), or 2-11, or "none". Read `warnings` (ambiguous name, unmatched `values` keys) and fix them.
- Use real numbers the user gave or that you sourced (say where from); never invent values. Without data, `color_by: "population"` or `"area_km2"` works on its own.
- Always set `title` and `legend_title` with units.
- Pick the palette: `rdbu` for diverging data (above/below a midpoint), otherwise a sequential one (`blues`, `viridis`, ...).
- `basemap: "blank-auto"` is a good default for embeds (follows light/dark); plain `areas` already defaults to `blank`.
- Pins and routes can be added on top with `places` or `data`.

## Guardrails
- Never put the edit token in anything shared; the share link is `url` only.
- No private home addresses unless the user supplied them; ask before mapping people's homes.
- Max 50 places. Coordinates are lng,lat (the API also fixes swapped ones and tells you in `warnings`).
- Do not claim facts about places you did not verify (opening hours, prices); put only what you know in popups.
- Do not show JSON, curl commands or error codes to the user.

## Body cheat sheet (for you)
Top level: `title`, `description`, `areas` (`{within, level?, values?}`: real admin boundaries from a name, e.g. `{"within":"Berlin","values":{"Mitte":12.1}}`), `places` (names or objects `{q,title,description,category,marker-symbol,marker-color,url,image}`), `data` (GeoJSON), `connect`, `route` (car|bike|foot), `basemap` (positron|liberty|bright|dark|fiord|blank|blank-dark|blank-auto; blank = no map tiles, only your shapes; blank-auto follows the viewer's light/dark setting), `lock` (keep viewers near the data; default on for blank), `color_by` (numeric feature property → choropleth classes + range legend), `palette` (blues|greens|oranges|reds|purples|greys|viridis|rdbu), `classes` (3–7), `marker` (pin|dot|none), `color`, `cluster`, `labels`, `legend_title`, `center`, `zoom`. Feature properties (a place's `image` is its popup photo): `title`, `description`, `category`, `marker-symbol`, `marker-color`, `url`, `image`, `stroke`, `fill`, `fill-opacity`. For mixed geometry use `data` with styled features; for pure named places use `places`.
