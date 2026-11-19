---
name: create-map
description: Use this skill to turn places into a shareable, live web map link, and to work with maps it has already made. Use it when someone wants to pin, plot, or show places on a map, from a tiny map of 2-3 points to long lists with filters (addresses, landmarks, restaurants, trip itineraries, cycling or walking routes, neighbourhoods, recommendations). Also use it for choropleth "map of X by district/region/country" from numbers per area. Also use it when the user changes, exports, embeds, or downloads (GeoJSON, for Google My Maps or QGIS) a map made earlier, or pastes a link to an existing map, such as maps.polygrid.dev, to copy, remix, or edit it. Supports geocoding, routes, category filters, and popups with links and photos. Do NOT use for charts, graphs, mind maps, diagrams, sitemaps, code or map() functions, map API or billing questions, or driving directions that are only to be read.
---

# create-map

Turn a plain-language request into a live, shareable map link that can be edited later. The user is usually not technical: never show JSON, field names, tokens, or API words. Talk about places, pins, colors, links.

API: `https://maps.polygrid.dev` (no key needed). Everything goes through `scripts/publish.py` (Python 3, nothing to install). If the `polygrid-maps` MCP tools (`create_map`, `get_map`, `update_map`) are available and Python is not, use those instead; the flow is the same. Field details: `https://maps.polygrid.dev/llms.txt`; layout recipes: `references/layouts.md`; optional deep-research recipes (only when the user asks for more detail): `references/place-details.md`; customising and handing the map back: `references/customise.md`; commands and API notes: `references/api-cheatsheet.md`.

## Flow

### 0. Stay current
Once per conversation, before anything else, run `python3 scripts/publish.py version`. If it says `"outdated": true`, run `python3 scripts/publish.py self-update`, then read the `SKILL.md` it points to (`skill_md`), follow that version from here on, and tell the user in one plain line ("Updated the map skill to 2.1.0"). Do the same whenever any command prints `UPDATE AVAILABLE` (it has already started the update; read the new `SKILL.md`). If the check fails or you are offline, continue silently.

### 1. Understand
Work out the places, the purpose (trip, event, recommendations, moving, run route, ...) and the audience (just me, friends, public). If the request is already concrete ("pin these 5 addresses"), skip to step 3 and pick the layout yourself.

### 2. Profile the data, then offer layouts
Before asking anything, size up the data: how many places; one kind or mixed; any order or sequence (itinerary, days, race course); how spread out (one street, a city, a country); geometry (points, routes, areas); shared attributes (type, day, price, rating).

Ask ONE round of questions, layout first:
- **Layout question (always):** offer the 2-3 layouts from `references/layouts.md` that fit this data, best fit first, each with a one-line reason. Ask with your clickable-question tool if you have one (AskUserQuestion in Claude Code), putting the ASCII mockup from layouts.md in each option's preview; otherwise use a short numbered list with the mockups.
- **Up to 2 more questions in the same round**, each with a smart default and a "skip" option: which places (when the user wants suggestions, propose a researched list and ask them to confirm it), travel mode (on foot / metro / car / bike) when there is a route and the user did not state one, look (light / streets / dark).
- If the user has no places yet, research real ones first (web search if available), then ask.

### 3. Build the map
Write the body to a file (e.g. `map-body.json` in a temp or scratch folder, not the user's project). Use named `places` (geocoded for you) in preference to guessed coordinates; add city and country to each name. For small venues (cafes, shops, bars) put the street address in `q` when you know it, since names alone can match the wrong spot. If a place still lands in the wrong spot, fix it with an address or leave it out, and tell the user in one plain sentence; never mention lookups, downloads or other internals. If you do use coordinates, they are `[longitude, latitude]`.
- Make the map fast. Do 1-2 web searches for the whole list (at least one, unless every place is a famous landmark) and fill only what those results already show: `title`, a short `description`, `category` and emoji `marker-symbol` when useful, `address` and `url` (website) when seen, and 1-2 extra fields that fit the purpose (Title Case keys, e.g. "Known for"). Skip per-place lookups and photo hunting; omit anything not confirmed, never invent addresses, hours, prices or URLs. Without web access use only what you reliably know (landmarks) and say once that details were not verified. Deeper research (hours, photos, per-place lookups; recipes in `references/place-details.md`) only when the user asks.
- If you show opening hours, end the description with "check before you go".
- Travel mode (routes): use the mode the user states (drive/car/road trip -> `car`; bike/cycle -> `bike`; walk/on foot/hike/run -> `foot`; metro/bus/tram/train/public transport -> `transit`). If they don't say: city sightseeing -> `foot` within an area and `transit` for hops over ~2 km (give that place `"mode": "transit"`, the mode of the leg arriving there); road trips, countryside or a list of towns -> `car`; running route -> `foot`; bike tour -> `bike`. Never default to car inside a city. Families with kids or limited mobility: shorter walks, more transit. `transit` draws a dashed line with a metro badge and a public transport directions button, no times.
- Set a `title` that says what and where ("Best coffee in Lisbon"), and a one-sentence `description`.
- Set `legend_title` when categories are days or tiers (see layouts.md).

Good-map rules (apply silently, do not lecture):
- At most 7 categories; merge the rest into "Other". At most 50 places per map; split bigger lists by category or area.
- Colors carry meaning (green parks, red food, blue water/transport); never two near-identical colors.
- One emoji per category, used consistently.
- Fit the view to everything. If one place is far from the rest (probably a wrong match), drop it and say so.
- Prefer the simplest layout that answers the user's purpose.

### 4. Publish
```
python3 scripts/publish.py create body.json
```
It prints the result. Keep from it (for yourself): `url`, `edit_token`, `edit_url`, `id`, `warnings`, `route`, `routes`. Also save the body file: it lets you recreate the map later.
- If it prints a `fallback_url` instead (sandbox cannot reach the API), tell the user, positively and without technical detail: "Your map is ready. Open this link and press **Publish map** to make it live." Do not suggest changing network settings, connectors or admins; this link is the normal way here. Show the link prominently. After publishing, that page shows their share link and their private edit link; ask them to paste the edit link back here if they want you to change the map later. Suggest enabling network access for maps.polygrid.dev (Settings > Capabilities > Code execution) to get real share links next time.
- If it exits with an API error, read its `hint`, fix the body, retry once. If a place could not be found, offer another spelling or address, or to leave it out.

### 5. Answer visually and briefly
Keep it short. Use this template, every line on its own line, nothing else:
0. The thumbnail (`preview_markdown` from the publish output) only where the chat really renders outside images (e.g. ChatGPT, Cursor chat). Do NOT add it in claude.ai, Claude Desktop, Cowork, terminal agents (Claude Code CLI, Codex CLI, Gemini CLI) or with the fallback publish link; when unsure, skip it.
1. `## [Open your map](URL)`
2. One-line summary: what is on it ("8 sights in Lisbon in 2 categories"). With routes, add the travel mode and offer the switch ("Walking, with metro between areas; tell me if you'll drive"). Then any warnings in plain words.
3. One line on the popups (only what you really filled in) plus the offer: "Each pin has a short note and the address; want hours and photos too? I can add them."
4. "Your private edit link (keep it, don't share it): EDIT_URL"
5. Two tweak ideas in one line ("Make it dark? Add cafés nearby?").
Embeds, downloads, link previews and the 30-day expiry: mention only when the user asks. If you have a built-in browser, open the map's share link in it as your very last step of the whole turn, so the chat shows a live preview card of the map. Don't navigate anywhere after it.

### 6. Give the map back, customise
**When the user asks to change, add to or restyle a map you made in this conversation (add routes, add places, make it dark, rename...), update that map in place with its edit token: same link, no new map. Create a new map only when they ask for a separate or new one.** Multi-day or multi-leg routes go into one map with `routes` (`route_view` tabs), not one map per day. Never show the raw edit token; give the private edit link only.

This is what makes the map useful after step 5. Offer it, do not lecture. Details and recipes: `references/customise.md`.

Quick tweaks in chat (same share link, live for everyone). One command changes a few settings without rebuilding the map:
```
python3 scripts/publish.py set ID --token TOKEN basemap=dark labels=true
```
Typical asks: "make it dark / streets / light" (`basemap`; don't set a basemap on create unless they ask for a look), "rename it" (`title`, `description`), "show names" (`labels=true`), "cluster the pins" (`cluster=true`), "smaller dots" (`marker=dot`), "different color" (`color=#e11d48`), "legend heading" (`legend_title`). **"Add routes / another day to my map" updates the existing map in place (same link): `patch ID --token TOKEN changes.json` with `{"routes":[...only the new routes...]}`, never a new map.** For anything bigger (add or remove places, new layout) edit the saved body and run `update ID --token TOKEN body.json` (this replaces the whole map; same link).

What people usually need, and what to give them:
- **A link to share:** the share link (`links ID`). It never contains the edit token.
- **Just a look in another style:** a view link such as `?basemap=dark` on the share link. Nothing is changed for others. Also `?marker=dot`, `?labels=1`, `?cluster=1`.
- **Change texts, colors, icons or photos themselves, in the browser:** the private edit link. Explain it opens a simple editor (names, texts, links, photos, colors, icons, removing places). Adding places or changing layout, style or routes is done by you in chat.
- **Put it on a website, blog or Notion:** give the embed code from `links ID` (call it "embed code", never oEmbed or endpoint) and say where to paste it (a "custom HTML" / "embed" block). In Notion, a plain "/embed" block with the share link works too.
- **Open it in QGIS, Google My Maps, Mapbox, a spreadsheet:** the download link ending in `.geojson`. Say what to do with it ("in Google My Maps choose Import and upload this file").
- **A picture (slides, printing, a document):** only when asked, `python3 scripts/publish.py png ID map.png`, then tell them where the file is. Pictures are limited, do it at most once per request and never in a loop.
- **Open it in the browser** (when you run on their computer and they want it): `open URL` on macOS, `xdg-open URL` on Linux, `start URL` on Windows. Do not do it unasked.

If you are a coding agent working in a project, offer to save the share link or embed snippet into the project (README, docs page, page template). Never save the edit link into files that are committed or published.

### 7. Come back later (new chat, pasted link)
The user may paste a link and say "change this map". Read the link yourself, never ask them to dissect it.
- **Edit link** (`.../m/ID/edit#t=TOKEN`): you have everything. Pass the whole link as the ID to the commands (`set "EDIT_URL" basemap=dark` works; the token is picked up from the link). First `get` it to see what is on the map, then change it.
- **Share link only** (no `#t=`): you can read it (`get`, `links`, view variants, downloads) but not change it. Say so plainly and offer: a fresh copy with the changes (new link; the old one stays as it is), or they can paste the private edit link if they have it. Never guess tokens.
- **No link, but a saved body** (same project/session): recreate with `create`.
- **Errors:** 403 means the edit link is for a different map, ask for the right one. 404 means the map expired (30 days without views): offer to recreate it from the saved body, or from `get` output if you still have it, as a new link. Update restarts the 30-day clock.
- After any change, re-show the same share link and say the change is live. Keep to plain words: "done, the map is dark now".

## Data maps of areas
For "map of X by district / region / country" with a number per admin area, use `areas` instead of inventing polygons or hunting for GeoJSON: the API draws the real boundaries from a name, you only supply numbers.
```json
{"areas": {"within": "Czechia"}, "color_by": "population", "palette": "viridis", "legend_title": "Population"}
{"areas": {"within": "Berlin", "values": {"Mitte": 12.1, "Pankow": 8.4, "Neukölln": 15.3}}, "title": "Unemployment by district", "legend_title": "Unemployment (%)"}
```
Rules:
- `within` is an area name ("Berlin", "Praha, Czechia") or a Wherebox id; `level` is "auto" by default (Berlin gives its 12 districts), or 2-11, or "none". Read `warnings` (ambiguous name, unmatched `values` keys) and fix them.
- Use real numbers the user gave or that you sourced (say where from); never invent values. Without data, `color_by: "population"` or `"area_km2"` works on its own.
- Always set `title` and `legend_title` as "Name (unit)", e.g. `"Unemployment (%)"`: popups then show "Unemployment  4.3 %" as the first row. For other value names use `property_labels`, e.g. `{"value": "Unemployment rate", "median_income": "Median income (€)"}`. Popups already humanise keys (`median_income` becomes "Median income") and format numbers.
- Pick the palette: `rdbu` for diverging data (above/below a midpoint), otherwise a sequential one (`blues`, `viridis`, ...).
- `basemap: "blank-auto"` is a good default for embeds (follows light/dark); plain `areas` already defaults to `blank`.
- Pins and routes can be added on top with `places` or `data`.

## Several routes (days of a trip, alternatives)
- A multi-day itinerary is one map with `routes`, one route per day (`name` "Day 1", `mode`, `places`) and the default `route_view: "tabs"`; never one map per day. Details and example: `references/layouts.md` (Route per day).
- Comparing options (3 bike routes, car or train) is `routes` with `"route_view": "together"`.
- Shared places (hotel, sights) go in top-level `places`; they show with every route. Limits: 6 routes, 2-25 places per route, 50 places in total.
- Switching the travel mode later ("we'll drive") updates the same map: `patch` with `{"routes":[{"name":"Day 1","mode":"car"},...]}` and no places (every leg gets that mode, same link).
- A single route stays `route` (or `connect`).

## Guardrails
- Never put the edit token in anything shared; the share link is `url` only.
- No private home addresses unless the user supplied them; ask before mapping people's homes.
- Max 50 places. Coordinates are lng,lat (the API also fixes swapped ones and tells you in `warnings`).
- Do not claim facts about places you did not verify. Addresses, hours, prices, links and photos must come from a source you actually saw (search result, fetched page, the user); never fill them in from memory, omit the field instead.
- Do not show JSON, curl commands or error codes to the user.

## Body cheat sheet (for you)
Top level: `title`, `description`, `areas` (`{within, level?, values?}`: real admin boundaries from a name, e.g. `{"within":"Berlin","values":{"Mitte":12.1}}`), `places` (names or objects `{q,title,description,category,marker-symbol,marker-color,url,image}`), `data` (GeoJSON), `connect`, `route` (car|bike|foot|transit), `routes` (`[{name,mode,places,color?,remove?}]`, mode car|bike|foot|transit, default foot; a place object may carry its own `mode` for the leg arriving at it; max 6, 2-25 places each: a route per day or alternative), `route_view` (tabs|together), `basemap` (omit it: auto follows each viewer's light/dark setting; set one only when the user asks for a look: positron|liberty|bright|dark|fiord|blank|blank-dark|blank-auto; blank = no map tiles, only your shapes; blank-auto follows the viewer's light/dark setting), `lock` (keep viewers near the data; default on for blank), `color_by` (numeric feature property → choropleth classes + range legend), `palette` (blues|greens|oranges|reds|purples|greys|viridis|rdbu), `classes` (3–7), `marker` (pin|dot|none), `color`, `cluster`, `labels`, `legend_title` ("Name (unit)"), `property_labels` ({key: popup label}), `center`, `zoom`. Feature properties (a place's `image` is its popup photo): `title`, `description`, `category`, `marker-symbol`, `marker-color`, `url`, `image`, `address`, `phone`, `opening_hours`, `price`, `rating`, `email`, `instagram`, any other key shown as a detail line, `stroke`, `fill`, `fill-opacity`. For mixed geometry use `data` with styled features; for pure named places use `places`.
