# Customising and handing the map back

Plain words to the user always: "map", "link", "pins", "style". Never JSON, tokens, status codes.

## Command map (for you)
| User says | Do |
|---|---|
| "make it dark / streets / light / no background map" | `set ID --token T basemap=dark` (`liberty`, `positron`, `blank-auto`) |
| "rename it", "new description" | `set ID --token T "title=Best coffee in Lisbon"` |
| "show the names", "cluster the pins", "dots instead of pins" | `labels=true`, `cluster=true`, `marker=dot` |
| "zoom closer / start in X" | `zoom=12`, `center=[lng,lat]` |
| "remove the legend title / reset a setting" | `key=null` removes it |
| add/remove places, new route, new layout, areas | edit saved body, `update ID --token T body.json` |
| "give me the link" | `links ID` |
| "I want to edit it myself" | the private edit link |
| "put it on my site" | `links ID` -> `embed_html` |
| "download the data" | `geojson_url` |
| "I need a picture" | `png ID out.png` (once) |

`set` keeps everything else on the map (places, routes, areas already resolved). `ID` can be the share link or the edit link. Booleans and numbers are typed automatically; title, description, legend_title, basemap, palette, color, marker stay text.

Caveat: a map built from `areas` is stored as drawn shapes, so `set` never loses them, but changing which area is shown needs a new `create`.

## Embedding
Paste `embed_html` into: a website or blog's "custom HTML" block, WordPress "Custom HTML", Squarespace/Wix "Embed code", Ghost "HTML card". Notion, Slack-like docs: paste the share link into an embed block. Dark variant: add `&basemap=dark` to the iframe `src`. Height can be changed in the snippet (`height="450"`). The map stays live only while it gets views at least every 30 days; an embed counts as views.

## Download formats
- GeoJSON (`.geojson`): QGIS (Layer > Add Layer > Vector), Google My Maps (Import), Mapbox/Leaflet, geojson.io. Contains pins, lines, shapes and their texts.
- PNG (1200x630): slides, print, documents. Rendered on the server the first time it is asked for and rendering is limited: do it once, on request, and keep the file.
- CSV / KML / GPX are not offered; if asked, convert the GeoJSON yourself (e.g. a small script) and say it is a conversion.

## Opening in a browser (coding agents)
Only if the user wants it: `open URL` (macOS), `xdg-open URL` (Linux), `start "" URL` (Windows). In claude.ai or sandboxes just show the link.

## Where to keep things
- Share link: fine anywhere (README, docs, chat).
- Edit link: private. Show it once at creation, offer to save it in their password manager or notes. Do not commit it, do not put it in embeds.
- Saved body: keep the body file in the scratch folder or, if the user wants durability, in their project, so the map can be recreated after expiry.

## If the user pastes a link in a new chat
See SKILL.md step 7. Quick triage: contains `#t=` -> editable by you; no `#t=` -> read-only, offer a copy; unknown or 404 -> expired, recreate.

## Make a copy with changes (when only a share link is available)
`get SHARE_URL > body.json`, edit the file (the body holds ready shapes, no re-geocoding), then `create body.json`. Tell the user it is a new link and the old one is unchanged. Credit the original only if the user cares.

## Tailoring suggestions
After create, offer 3 tweaks that fit: itinerary -> "route on foot", "dark style for night use"; many pins -> "cluster them", "filter legend"; data map -> "another color scale", "embed on your site".
